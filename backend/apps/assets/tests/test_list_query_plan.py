import json
import random
import unicodedata
from datetime import timedelta
from decimal import Decimal
from typing import NamedTuple

import pytest
from django.contrib.gis.db.models import GeometryField
from django.contrib.gis.geos import Point
from django.db import connection
from django.db.models import FloatField, Func
from django.db.models.functions import Cast
from django.test.utils import CaptureQueriesContext

from apps.assets.location import PRIVACY_RADII
from apps.assets.models import Asset, PriceUnit
from apps.assets.rules import COHERENCE_LATITUDE, COHERENCE_LONGITUDE
from apps.assets.selectors import PUBLIC_FIELDS, visible_assets_in_zone
from apps.assets.tests.conftest import NOW
from apps.assets.zone import Zone
from apps.categories.models import Category
from apps.users.models import User

pytestmark = pytest.mark.measurement

SEED = 8
OWNER_COUNT = 500
DEACTIVATED_OWNER_COUNT = 5
ASSET_COUNT = 50_000
BATCH_SIZE = 5000
ACTIVE_SHARE = 0.8
VALENCIA_SHARE = 0.4
VALENCIA_LATITUDE = (39.0, 40.0)
VALENCIA_LONGITUDE = (-1.0, 0.0)
# Porcentaje de bienes de estas categorías; el resto se reparte a partes iguales
CATEGORY_PERCENTAGES = {"kayak": 8, "ski": 2}
# Grados de desplazamiento de la ubicación exacta respecto a la pública
EXACT_OFFSET = 0.002
SECONDS_PER_DAY = 86_400
CREATION_DAYS = 365
UPDATE_DAYS = 30
DESCRIPTION = "Bien sintético para medir el plan de la consulta de la lista"
NOUNS = (
    "Bicicleta eléctrica",
    "Bicicleta de montaña",
    "Bici de paseo",
    "Soporte para bici",
    "Esquí",
    "Botas de esquí",
    "Tabla de surf",
    "Tabla de paddle",
    "Kayak",
    "Piragua",
    "Barca hinchable",
    "Traje de neopreno",
    "Caña de pescar",
    "Tienda de campaña",
    "Carpa para eventos",
    "Taladro",
    "Amoladora",
    "Sierra circular",
    "Cortacésped",
    "Hidrolimpiadora",
    "Escalera",
    "Andamio",
    "Hormigonera",
    "Compresor",
    "Generador eléctrico",
    "Remolque",
    "Autocaravana",
    "Caravana",
    "Furgoneta",
    "Barbacoa",
    "Piscina desmontable",
    "Proyector",
    "Altavoz",
    "Cámara de fotos",
    "Dron",
    "Mesa plegable",
    "Casco de ciclista",
    "Patinete eléctrico",
    "Pista de pádel",
    "Sala de ensayo",
)
ADJECTIVES = (
    "compacto",
    "profesional",
    "ligero",
    "reforzado",
    "nuevo",
    "económico",
    "silencioso",
    "potente",
)

LIMIT = 200
WARM_UP_RUNS = 1
MEASURED_RUNS = 5
TABLE = "assets_asset"


def _zone(south, west, north, east):
    return Zone(*(Decimal(value) for value in (south, west, north, east)))


ZONES = (
    ("Z1", _zone("39.3", "-0.6", "39.7", "-0.2")),
    ("Z2", _zone("38.5", "-2", "40.5", "1")),
)


class Case(NamedTuple):
    label: str
    category_slug: str | None
    fragment: str | None


CASES = (
    Case("sin filtro", None, None),
    Case("categoría kayak", "kayak", None),
    Case("categoría ski", "ski", None),
    Case("texto «bici»", None, "bici"),
    Case("texto de 1 carácter «a»", None, "a"),
    Case("texto de 2 caracteres «es»", None, "es"),
    Case("texto sin coincidencias «zzzz»", None, "zzzz"),
    Case("categoría kayak y texto «bici»", "kayak", "bici"),
)


class Measurement(NamedTuple):
    median_ms: float
    fastest_ms: float
    slowest_ms: float
    access_node: str
    rows_removed: int
    loops: int
    buffers: int


# --- Datos sintéticos ----------------------------------------------------------


def _create_owners():
    owners = [
        User(
            email=f"owner{number}@example.com",
            is_active=number >= DEACTIVATED_OWNER_COUNT,
        )
        for number in range(OWNER_COUNT)
    ]
    return User.objects.bulk_create(owners)


def _category_weights(categories):
    slugs = {category.slug for category in categories}
    assert set(CATEGORY_PERCENTAGES) <= slugs
    shared = (100 - sum(CATEGORY_PERCENTAGES.values())) / (
        len(categories) - len(CATEGORY_PERCENTAGES)
    )
    return [CATEGORY_PERCENTAGES.get(category.slug, shared) for category in categories]


def _public_coordinates(rng):
    if rng.random() < VALENCIA_SHARE:
        return rng.uniform(*VALENCIA_LATITUDE), rng.uniform(*VALENCIA_LONGITUDE)
    return rng.uniform(*COHERENCE_LATITUDE), rng.uniform(*COHERENCE_LONGITUDE)


# Cerca de la pública y sin salir de la caja de coherencia
def _exact_coordinate(rng, public_value, limits):
    shifted = public_value + rng.uniform(-EXACT_OFFSET, EXACT_OFFSET)
    return min(max(shifted, limits[0]), limits[1])


def _title(rng):
    return f"{rng.choice(NOUNS)} {rng.choice(ADJECTIVES)} {rng.randint(1, 999)}"


def _build_asset(rng, owners, category):
    latitude, longitude = _public_coordinates(rng)
    created_at = NOW - timedelta(seconds=rng.randrange(CREATION_DAYS * SECONDS_PER_DAY))
    updated_at = min(
        created_at + timedelta(seconds=rng.randrange(UPDATE_DAYS * SECONDS_PER_DAY)),
        NOW,
    )
    return Asset(
        owner=rng.choice(owners),
        category=category,
        title=_title(rng),
        description=DESCRIPTION,
        price=Decimal(rng.randint(1, 99_999)) / 100,
        currency="EUR",
        price_unit=rng.choice(PriceUnit.values),
        exact_location=Point(
            _exact_coordinate(rng, longitude, COHERENCE_LONGITUDE),
            _exact_coordinate(rng, latitude, COHERENCE_LATITUDE),
            srid=4326,
        ),
        public_location=Point(longitude, latitude, srid=4326),
        privacy_radius=rng.choice(PRIVACY_RADII),
        status="active" if rng.random() < ACTIVE_SHARE else "paused",
        created_at=created_at,
        updated_at=updated_at,
    )


def _build_assets(rng, owners, categories):
    chosen = rng.choices(
        categories, weights=_category_weights(categories), k=ASSET_COUNT
    )
    return [_build_asset(rng, owners, category) for category in chosen]


# Un fallo del generador no debe pasar inadvertido en la tabla
def _assert_generated_titles(assets):
    titles = [asset.title for asset in assets]
    assert not any("zzzz" in title.lower() for title in titles)
    assert all(unicodedata.is_normalized("NFC", title) for title in titles)
    assert any("bici" in title.lower() for title in titles)


# --- Consultas -----------------------------------------------------------------


def _selector_sql(zone):
    with CaptureQueriesContext(connection) as context:
        visible_assets_in_zone(zone=zone, limit=LIMIT)
    assert len(context.captured_queries) == 1
    return context.captured_queries[0]["sql"], None


# Réplica de la consulta del selector con los filtros que este aún no admite
def _candidate_sql(zone, category_slug, fragment):
    geometry = Cast("public_location", GeometryField())
    queryset = (
        Asset.objects.filter(status="active", owner__is_active=True)
        .annotate(
            longitude=Func(geometry, function="ST_X", output_field=FloatField()),
            latitude=Func(geometry, function="ST_Y", output_field=FloatField()),
        )
        .filter(
            longitude__range=(zone.west, zone.east),
            latitude__range=(zone.south, zone.north),
        )
    )
    if category_slug is not None:
        queryset = queryset.filter(category__slug=category_slug)
    if fragment is not None:
        queryset = queryset.filter(title__icontains=fragment)
    queryset = queryset.order_by("-created_at", "-id").values(*PUBLIC_FIELDS)
    return queryset[: LIMIT + 1].query.sql_with_params()


def _query_of(case, zone):
    if case.category_slug is None and case.fragment is None:
        return _selector_sql(zone)
    return _candidate_sql(zone, case.category_slug, case.fragment)


# --- Medición ------------------------------------------------------------------


def _explain(sql, params):
    with connection.cursor() as cursor:
        cursor.execute(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {sql}", params)
        document = cursor.fetchone()[0]
    if isinstance(document, str):
        document = json.loads(document)
    return document[0]


def _access_node(plan):
    if plan.get("Relation Name") == TABLE:
        return plan
    for child in plan.get("Plans", []):
        found = _access_node(child)
        if found is not None:
            return found
    return None


def _summarize(document):
    plan = document["Plan"]
    node = _access_node(plan)
    assert node is not None
    return (
        node["Node Type"],
        node.get("Rows Removed by Filter", 0),
        node["Actual Loops"],
        plan["Shared Hit Blocks"] + plan["Shared Read Blocks"],
    )


def _measure(sql, params):
    for _ in range(WARM_UP_RUNS):
        _explain(sql, params)
    documents = sorted(
        (_explain(sql, params) for _ in range(MEASURED_RUNS)),
        key=lambda document: document["Execution Time"],
    )
    median = documents[MEASURED_RUNS // 2]
    access_node, rows_removed, loops, buffers = _summarize(median)
    return Measurement(
        median_ms=median["Execution Time"],
        fastest_ms=documents[0]["Execution Time"],
        slowest_ms=documents[-1]["Execution Time"],
        access_node=access_node,
        rows_removed=rows_removed,
        loops=loops,
        buffers=buffers,
    )


def _format_table(headers, rows):
    widths = [
        max(len(cell) for cell in column) for column in zip(headers, *rows, strict=True)
    ]

    def line(cells):
        return "  ".join(
            cell.ljust(width) for cell, width in zip(cells, widths, strict=True)
        )

    return "\n".join(
        [line(headers), line(["-" * width for width in widths]), *map(line, rows)]
    )


def _describe_zone(name, zone):
    return (
        f"{name} = latitud {zone.south} a {zone.north}, "
        f"longitud {zone.west} a {zone.east}"
    )


# --- Tests ---------------------------------------------------------------------


def test_probe_the_test_database_environment(db):
    statements = (
        "SHOW server_version",
        "SELECT datctype FROM pg_database WHERE datname = current_database()",
        "SHOW server_encoding",
    )
    volatility_query = (
        "SELECT proname, pg_get_function_identity_arguments(oid), provolatile "
        "FROM pg_proc WHERE proname = 'translate'"
    )
    with connection.cursor() as cursor:
        for statement in statements:
            cursor.execute(statement)
            print(f"{statement}: {cursor.fetchone()[0]}")
        cursor.execute(volatility_query)
        for name, arguments, volatility in cursor.fetchall():
            print(f"{name}({arguments}): provolatile = {volatility}")


def test_measure_the_list_query_plans(db):
    rng = random.Random(SEED)
    owners = _create_owners()
    categories = list(Category.objects.order_by("slug"))
    assets = _build_assets(rng, owners, categories)
    _assert_generated_titles(assets)
    Asset.objects.bulk_create(assets, batch_size=BATCH_SIZE)
    assert Asset.objects.count() == ASSET_COUNT
    with connection.cursor() as cursor:
        cursor.execute(f"ANALYZE {TABLE}")

    rows = []
    for case in CASES:
        for name, zone in ZONES:
            result = _measure(*_query_of(case, zone))
            rows.append(
                [
                    case.label,
                    name,
                    f"{result.median_ms:.2f}",
                    f"{result.fastest_ms:.2f}",
                    f"{result.slowest_ms:.2f}",
                    result.access_node,
                    str(result.rows_removed),
                    str(result.loops),
                    str(result.buffers),
                ]
            )

    headers = [
        "Consulta",
        "Zona",
        "Mediana ms",
        "Mín ms",
        "Máx ms",
        "Nodo de acceso",
        "Filas descartadas",
        "Bucles",
        "Buffers",
    ]
    print()
    print(
        f"Bienes: {ASSET_COUNT}. Propietarios: {OWNER_COUNT} "
        f"({DEACTIVATED_OWNER_COUNT} con la cuenta desactivada)"
    )
    print(f"Semilla: {SEED}")
    print(*(_describe_zone(name, zone) for name, zone in ZONES), sep="\n")
    print(
        f"Por consulta: {WARM_UP_RUNS} calentamiento y {MEASURED_RUNS} medidas. "
        "«Mediana ms» es la mediana de «Execution Time»; nodo, filas descartadas "
        "(«Rows Removed by Filter»), bucles y buffers (shared hit + read del plan "
        "completo) son de la ejecución mediana."
    )
    print(_format_table(headers, rows))

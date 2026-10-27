import pytest

from apps.assets.location import approximate_location

MADRID = (40.4168, -3.7038)
LAS_PALMAS = (28.1235, -15.4363)
PALMA = (39.5696, 2.6502)

# Calculados con GDAL 3.10.3 y contrastados con la fórmula LAEA elipsoidal
REFERENCE_CENTRES = [
    (MADRID, 500, (40.415675, -3.705231)),
    (MADRID, 1000, (40.413861, -3.701849)),
    (MADRID, 2000, (40.408605, -3.706674)),
    (LAS_PALMAS, 500, (28.125591, -15.435455)),
    (LAS_PALMAS, 1000, (28.12415, -15.432384)),
    (LAS_PALMAS, 2000, (28.129963, -15.428838)),
    (PALMA, 500, (39.570937, 2.64738)),
    (PALMA, 1000, (39.568466, 2.644751)),
    (PALMA, 2000, (39.564398, 2.651027)),
]


@pytest.mark.parametrize(("point", "radius", "expected"), REFERENCE_CENTRES)
def test_the_cell_centre_matches_its_reference(point, radius, expected):
    assert approximate_location(*point, radius) == expected

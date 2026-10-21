# Validación — 001-backend-skeleton
Fecha: 2026-10-21 · Rama: `feature/001-backend-skeleton` · Django 5.2.18 · PostGIS 18-3.6

Evidencia de los RF que no cubre un test automático. Las órdenes se ejecutan desde la raíz del repo.

## Validación en entorno

| RF | Orden | Resultado |
|---|---|---|
| RF-1 | Clon nuevo del repo local en el scratchpad (`git clone`, commit 98750f0), `cp .env.example .env`, `docker-compose.override.yml` solo en el clon con los puertos 127.0.0.1:15432 y 127.0.0.1:18000 (`!override`), `docker compose -p rentradar-scratch up -d --build` y `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:18000/` | 200. La BD quedó healthy y el backend arrancó. `docker volume ls`: antes solo `rentradar_db-data`; con el stack arriba además `rentradar-scratch_db-data`; tras `down -v` con `-p rentradar-scratch`, solo `rentradar_db-data` |
| RF-2 | Huella de solo lectura de la BD de desarrollo (ver abajo), `docker compose down`, `docker volume ls` (sigue `rentradar_db-data`), `docker compose up -d` sin `-v` y la misma huella | Huella idéntica antes y después |
| RF-3 | Proyecto `-p rentradar-scratch`: `run --rm --no-deps backend` sin BD, y 20 s después `run -d --no-deps --use-aliases db` | El backend esperó, la BD llegó a las 08:31:38 y el arranque terminó con salida 0 a las 08:31:43. Un primer intento fue inválido (la BD lanzada con `run` no tenía el alias `db` y el backend agotó los 60 s); se repitió con `--use-aliases` |
| RF-4 | Proyecto `-p rentradar-scratch`, sin BD: `run --rm --no-deps backend python -c "print('arrancó')"` | Salida 1 a los 60 s (1 min 10 s con el build). Mensaje fijo: «La base de datos no estuvo disponible en 60 segundos. El arranque falla por la base de datos, no por la aplicación.» Sin host, usuario ni contraseña. El proyecto scratch se eliminó con `down -v` |
| RF-6 | `docker compose exec backend id -u` | 10001 |
| RF-7 | `docker compose config --format json`, analizado sin imprimirlo | `backend` 127.0.0.1:8000→8000 y `db` 127.0.0.1:5432→5432 |
| RF-8 | `git check-ignore` y `git ls-files` | Ignorados: `.env`, `.env.local`, `.env.production`, `.env.development.local`, `prod.env`, `backend/.env`. No ignorado y versionado: `.env.example`. Ningún otro `.env*` en git |
| RF-17 | `pytest -q` lanzado en el contenedor y terminado con `kill -9` a los 7 s; consulta de `pg_database`; nueva ejecución de `pytest -q` | Tras la muerte, `rentradar` y `rentradar_test`. La siguiente ejecución sin intervención: 161 passed y solo queda `rentradar` |
| RF-34 | Huella de solo lectura de la BD de desarrollo antes y después de `pytest -q` | Huella idéntica; 161 passed |
| T1 | `docker compose exec backend python -c "from django.contrib.gis.gdal import gdal_version; from django.contrib.gis.geos import geos_version; print(gdal_version(), geos_version())"` | `b'3.10.3' b'3.13.1-CAPI-1.19.2'` |

Huella de la BD de desarrollo (solo `SELECT`, no escribe): número de tablas de `public`, filas y md5 de `django_migrations` y filas de `django_session`. Valor en las cuatro lecturas (inicial, antes y después de la suite, y tras `down` y `up -d`): `5 tablas; 2 migraciones; md5 bf7f88c1e11e4f0958db02499850a21c; 0 sesiones`.

No se usó la fila centinela del plan (RF-2, RF-34) porque habría escrito en la BD de desarrollo.

## Suite y lint
`pytest -q` en el contenedor: 161 passed. `ruff check .` y `ruff format --check .`: sin avisos.

## Revisores

| Vuelta | Seguridad | Docs | Calidad |
|---|---|---|---|
| Inicial | APTA CON OPCIONALES | B3 | B1 y B2. Veredicto: NO APTA |
| 1 (commits 788c170, 200ae12, ebc2bbf) | APROBADO | APROBADO | CAMBIOS NECESARIOS: `plan.md` decía Django 5.2.17 y el test de UTC no aportaba cobertura |
| 1, calidad repetida (133d892, 98750f0) | — | — | APROBADO |

Notas:
- El revisor de docs afirmó que la 5.2.18 no traía correcciones de seguridad. Es falso según las notas oficiales (docs.djangoproject.com/en/5.2/releases/5.2.18/): corrige cuatro CVE, una baja y tres moderadas.
- Pendiente según calidad: T1 no tiene test automático y su evidencia es la de esta tabla; GDAL y GEOS solo los cubre `test_postgis.py` de forma indirecta.

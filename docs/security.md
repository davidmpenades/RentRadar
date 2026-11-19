# Plan de seguridad
Lo que falta en seguridad, ordenado por la spec que lo resuelve. Lo que ya está hecho se describe en `docs/architecture.md` y en la validación de cada spec.

## Objetivo
OWASP ASVS nivel 2, verificado, más detección y recuperación.

## Proceso
- Cada spec lleva una sección «Amenazas», que revisa el subagente de seguridad.
- Al cerrar una spec sensible, `/security-review` sobre todo el módulo, no solo sobre el diff.

## Cadena de suministro
Spec siguiente a la 015 y a la /sdd-change de la 009.
- Dependabot, `pip-audit` y `npm audit`.
- pip con `--require-hashes`.
- Actions de GitHub fijadas por SHA.
- gitleaks en pre-commit y en la CI.
- Protección de ramas y aprobación de los workflows de forks.

## Despliegue (011)
- `check --deploy` en la CI y `DEBUG=False` fijado por un test.
- `ALLOWED_HOSTS`.
- Servidor de producción: gunicorn síncrono y solo WSGI; valorar borrar `config/asgi.py`. Hoy no hay ninguno: Compose usa `runserver` y gunicorn no está en requirements.
- HTTPS, HSTS, `SECURE_SSL_REDIRECT`, `SECURE_PROXY_SSL_HEADER` y `CSRF_TRUSTED_ORIGINS`, con un test sobre el módulo de producción.
- Cookies `Secure` y con el prefijo `__Host-`. Obliga a cambiar el nombre de la cookie CSRF que lee `session.ts`.
- CSP y cabeceras. `img-src` necesita `data:` por los 39 iconos SVG del CSS de maplibre-gl y por un png de 1 × 1 de maplibre-gl; comprobar si también hace falta `blob:`, o sustituirlos por ficheros propios.
- `NUM_PROXIES` y el proxy de confianza.
- Contadores de los límites en Redis, compartidos entre procesos. Hoy son LocMem, por proceso.
- PostgreSQL con los mínimos privilegios, sin exponer y con un log sin valores.
- `DB_PASSWORD` de 16 caracteres o más, con una /sdd-change.
- Contenedores sin root y con el sistema de ficheros de solo lectura.
- Servidor: SSH solo con clave, cortafuegos, actualizaciones y fail2ban.
- Cloudflare: WAF, gestión de bots y límites.
- Rotación de `SECRET_KEY` y de las claves. Rotar `SECRET_KEY` reinicia los contadores del par de la entrada, porque su clave no usa `SECRET_KEY_FALLBACKS`.
- Las claves reales nunca están en el portátil.

## Correo y cuenta (013 y 014)
- Verificación del email.
- Restablecer la contraseña con tokens de un solo uso.
- Aviso de un nuevo inicio de sesión.
- Contraseñas filtradas: valorar HIBP.
- 2FA para el staff.
- El admin de Django, no expuesto a internet.
- Salir de todas las sesiones.

## Publicar bienes (010)
- Quitar los EXIF de las fotos (GPS incluido) y recodificarlas.
- Límites de tamaño y de número.
- Sin SVG.
- Imágenes en R2, servidas desde otro dominio.
- Antispam y canal de denuncias (DSA).

## Pagos
- Formulario alojado por el proveedor.
- Webhooks con firma verificada e idempotencia.

## Antes de lanzar
- Sentry sin datos personales: `include_local_variables=False`, con un test que lo fije.
- Si algún día se configura `ADMINS`, revisar el riesgo de los marcos sin tapar en el informe de error (spec 015, «Riesgos aceptados»).
- Alertas de 5xx, de fallos de entrada y de 429.
- Monitor de disponibilidad.
- `security.txt`.
- Runbook de incidentes.
- Copias de seguridad cifradas, con prueba de restauración.
- Auditoría con la skill de Cloudflare.
- OWASP ZAP con sesión y sin ella.
- Checklist de ASVS 2, anotada.
- Pentest cuando haya ingresos.

## Cadencia
- En cada PR: la CI.
- Cada mes: dependencias y alertas.
- Cada trimestre: prueba de restauración, rotación de claves y OWASP ZAP.

## Riesgo conocido: IP compartida
Con `NUM_PROXIES=0`, detrás de un proxy todas las peticiones llegan con la IP del proxy, así que los límites por IP la comparten todos los usuarios. Hoy solo lo acota no desplegar antes de la 011.

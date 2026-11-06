# Notas para la spec 015 — Entrada
Estado: notas previas. La spec todavía no existe: se escribe con `/feature` cuando la 009 esté implementada.
Depende de: spec 009 (registro, sesión y salida). Orden: 009 → 015 → 013 → 014 → 011.

## Alcance previsto (9 RF, unas 7 tareas)
1. Entrada correcta: abre sesión y responde con el email de la cuenta; el email se compara normalizado.
2. Credenciales incorrectas: un único error, con el mismo código, cuerpo y estado, para email desconocido o mal formado, contraseña errónea y cuenta desactivada.
3. Límite de entrada por IP: 20 peticiones por minuto, con IPv6 por prefijo /64.
4. Límite por IP y email: 5 intentos fallidos en 15 minutos, con el email en una huella HMAC con secreto del servidor.
5. Sesión nueva al entrar, con el mismo mecanismo que el registro.
6. Forma, tamaño y contenido de la petición de entrada.
7. «Entrar» en la barra superior.
8. Formulario de entrada: envío, errores y «Mostrar contraseña».
9. `/login` con sesión lleva al mapa sin añadir historial.

## Lo que hereda de la 009
- Sesión de Django con CSRF de doble envío; el error es `csrf_failed` y el cliente reintenta una vez tras volver a preguntar «quién soy».
- Orden de comprobaciones: límite por IP → método → CSRF → tamaño y forma → (límite por IP y email) → validación → comprobación de credenciales. Con el límite superado, cualquier método recibe el error de límite, como en la 006 y en el registro de la 009.
- Tiempo máximo de 10 s en las peticiones que cambian el estado: el error general permite reintentar. Antes de dar por fallida una petición vencida, el cliente pregunta «quién soy».
- Códigos `invalid_request` y `payload_too_large`, formato único de errores y `no-store`.
- La sesión anterior se vacía siempre al abrir una nueva. Si la entrada falla, la sesión actual no se toca.
- Respuestas mínimas (solo el email propio), barra superior sin email, `/login/` normalizado a `/login`, navegación entre páginas con historial.
- Cuenta desactivada: no entra, y su sesión abierta cuenta como sin sesión.
- Los intentos rechazados por el propio límite no cuentan. El mensaje de espera redondea a minutos, como mínimo 1.

## Hallazgos de la clarificación de la 009 que se resuelven aquí
- **Límite por IP y email**:
  - Deben contar todos los fallos de credenciales incorrectas: email desconocido, mal formado, cuenta desactivada y contraseña de más de 128 caracteres. Si solo contaran los de cuentas existentes, el límite revelaría qué emails existen.
  - La huella se calcula sobre el email normalizado, no sobre el recibido, para que mayúsculas, espacios o formas NFKC no lo evadan.
  - Fijar si la ventana es fija o deslizante y desde cuándo corre. Una entrada correcta reinicia el contador del par.
  - Fijar el secreto del HMAC (si es `SECRET_KEY` u otro; en test es fija) y añadirlo a la redacción de logs.
  - El par IP y email necesita leer el email: va después de CSRF y de la forma del cuerpo.
- **IP compartida**: detrás de un proxy o un NAT, 5 fallos de cualquiera bloquean esa cuenta para todos 15 minutos, y 20 entradas por minuto agotan la entrada de todos. Decidir si se prohíbe desplegar tras un proxy antes de la 011 o se acepta como riesgo.
- **Ataque desde muchas IP contra una cuenta**: el límite no lo frena. Se acepta porque un límite global por email permitiría bloquear la cuenta de otra persona; lo mitigan la longitud mínima y la lista de contraseñas comunes.
- **Estado de credenciales incorrectas**: un 401 añade `WWW-Authenticate` y un 403 se confunde con `csrf_failed`; el plan lo fija. Un cuerpo no JSON es `invalid_request`.
- **Contenido que provoca un error del servidor**:
  - Una contraseña de más de 128 caracteres da credenciales incorrectas sin calcular el hash.
  - Un email con un carácter nulo da credenciales incorrectas: la entrada no tiene la validación `control_char` de la 004 y psycopg rechaza el nulo en la consulta.
  - Una contraseña con un sustituto suelto da credenciales incorrectas y no un error del servidor.
- **Concurrencia**: si el contador solo suma fallos tras comprobar la contraseña, N peticiones en paralelo pueden superar los 5. Decidir cuándo cuenta.
- **Coste del hash**: la entrada con un email inexistente calcula un hash igualmente (igualación de tiempos de Django). Queda como riesgo hasta el tope global de la 011.
- **Diferencias de tiempo residuales** entre un email existente y otro que no: riesgo a aceptar.
- **Estados de `/login`** mientras se resuelve «quién soy»: el mismo criterio que `/register`.

## Para la 011
Proxy de confianza, almacén compartido y atómico de los contadores, tope global del coste del hash, `Origin` y `Referer` tras un proxy HTTPS.

## Criterios previstos
- Pruebas de mecanismo: uniformidad del error en las cuatro causas, cada límite y el reinicio, contraseña de más de 128 caracteres sin hash, y clave del contador sin el email y dependiente del secreto.
- Navegador a 1280 y 375 px: entrar con una cuenta creada en la 009, y comprobar credenciales incorrectas y límite superado.
- Relaciones: el enlace «¿Has olvidado tu contraseña?» llega con la 013 y los textos legales con la 014.

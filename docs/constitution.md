# Constitución — RentRadar
Principios innegociables. Si una spec, un plan o un commit contradice alguno, se corrige antes de seguir.

1. **Stack mínimo.** Django, DRF, PostGIS, React y TypeScript. Ninguna dependencia nueva sin aprobación explícita.
2. **La spec manda.** No se implementa nada que no esté en una spec aprobada. Cada RF tiene un test automático o, si es de interfaz, una verificación en navegador registrada en la validación. Un cambio de requisitos empieza por la spec y termina en el código.
3. **Lógica, datos e interfaz separados.** Las reglas de negocio van en funciones puras o servicios. Vistas, serializers y componentes solo traducen. Lo externo (hora, red, almacenamiento) entra como parámetro.
4. **Los tests son la puerta.** No se hace ningún commit con pytest, vitest, build o eslint en rojo. El test se escribe primero y debe fallar por la razón esperada.
5. **Autorización por objeto.** Cada endpoint declara qué pueden hacer el anónimo, el usuario y el propietario. Cada recurso ajeno tiene un test que intenta acceder a él y espera 404 si no puede verlo y 403 si puede verlo pero no modificarlo.
6. **Desconfianza de toda entrada.** El backend valida tipo, rango y tamaño de todo lo que llega del usuario o de un servicio externo; la validación del frontend solo ayuda. El frontend valida la forma de toda respuesta de la API antes de usarla. Los secretos van solo en variables de entorno.
7. **Accesible y móvil primero.** Se diseña a 375 px y se amplía. Controles de 44 px como mínimo, uso completo con teclado, foco visible y etiquetas accesibles. Se verifica en navegador a 375 y 1280 px, sin errores en consola.
8. **Idioma.** Código, identificadores, rutas y commits en inglés. Interfaz, mensajes al usuario, comentarios y documentación en castellano.

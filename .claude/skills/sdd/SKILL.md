---
name: sdd
description: Úsala siempre que trabajes con Spec-Driven Development en RentRadar, es decir, con docs/constitution.md o con cualquier archivo de specs/. Cubre redactar, revisar o cambiar specs, planes y tareas, e implementar o validar una tarea de una spec, aunque el usuario no mencione "SDD" de forma explícita.
---

# Spec-Driven Development en RentRadar

## Flujo
Constitución → Spec (/feature) → Clarificación → Plan → Tareas → Implementación → Validación → Cambio.

- Nunca pases a la siguiente fase sin la aprobación explícita del usuario.
- La spec manda: lo que no está en la spec no se implementa. Si falta una decisión, para y pregunta.
- Un cambio de requisitos se hace primero en la spec, después en el plan y las tareas, y por último en el código (/sdd-change).
- Cada spec vive en `specs/NNN-slug/` con `spec.md`, `plan.md` y `tasks.md`. NNN tiene tres cifras y es correlativo; el slug va en inglés y en kebab-case.
- Estados de la spec: borrador → aprobada → en curso → implementada. Solo el usuario aprueba.
- Al cerrar cada fase, actualiza MEMORY.md (estado y spec activa). Nunca lo escribe un subagente.

## spec.md
```
# Spec NNN — <Nombre>
Estado: borrador | aprobada | en curso | implementada

## Contexto y objetivo
## Usuarios
## Historias de usuario
- HU-1. Como <rol>, quiero <acción> para <beneficio>.
## Definiciones (solo si hay términos que admitan varias lecturas)
## Requisitos funcionales
## Requisitos no funcionales (seguridad, permisos, accesibilidad, móvil, rendimiento)
## Casos límite
## Fuera de alcance
## Criterios de finalización
## Dudas abiertas
- [NECESITA ACLARACIÓN] <duda>
```
La spec describe el QUÉ y el POR QUÉ: nada de stack, arquitectura, nombres de archivos ni endpoints.

## Requisitos en EARS (en español)
- RF-x: CUANDO <evento>, EL SISTEMA <respuesta>.
- RF-x: SI <condición no deseada>, ENTONCES EL SISTEMA <respuesta>.
- RF-x: MIENTRAS <estado>, EL SISTEMA <respuesta>.
- RF-x: EL SISTEMA <comportamiento permanente>.

Un RF describe un solo comportamiento y debe ser verificable: nada de "rápido", "bonito" o "intuitivo" sin un criterio medible. Cada entrada del usuario y cada servicio externo necesita al menos un RF de error (SI … ENTONCES).

## plan.md
```
# Plan NNN — <Nombre>
Spec: specs/NNN-slug/spec.md (aprobada)

## Resumen
## Archivos y responsabilidades
| Archivo | Crea/Modifica | Responsabilidad | RF |
## Modelo de datos y migraciones
## Contrato de API
Método, ruta, permisos, cuerpo y respuestas con sus códigos de error.
## Lógica
Funciones puras y servicios. Lo externo ("ahora", red, almacenamiento) entra como parámetro.
## Interfaz
Estados de carga, vacío, error y éxito. Foco, anuncios accesibles, controles de 44 px. Móvil primero.
## Decisiones
| Decisión | Opciones | Elegida | Qué evita | Coste |
## Blast radius
Código existente que se toca y tests que pueden romperse.
## Riesgos
| Riesgo | Mitigación |
## Estrategia de tests
| RF | Cómo se verifica (pytest / vitest / Chrome DevTools) |
## Afirmaciones no verificadas
Lo que el plan supone sin haberlo comprobado en el código o en la documentación.
## Skills que aplican
```
Ningún RF puede quedar huérfano: si un RF no aparece en la estrategia de tests, el plan no está listo. Consulta las APIs de librerías con Context7 en vez de fiarte de lo que recuerdes.

## tasks.md
```
- [ ] **Tn. <Descripción>.** RF-x, RF-y
  - Commit: `type(scope): short message`
  - Hecho cuando: <comprobación verificable>.
```
Como máximo 10 tareas de 20-30 min, en orden de dependencia. Cada tarea es un commit atómico que deja build y tests en verde. Si salen más de 10, propón dividir la spec.

## Implementación
Una tarea cada vez:
1. Escribe primero los tests y comprueba que fallan por la razón esperada.
2. Escribe el código mínimo para que pasen.
3. Verifica. Backend: `pytest -q`, más `manage.py check` y `makemigrations --check --dry-run` si tocas modelos. Frontend: `npx vitest run`, `npm run build` y `npx eslint <ficheros tocados>`.
4. Si el test protege un mecanismo (permiso, omisión de un campo, foco, limpieza), rompe el código a propósito, comprueba que el test falla y restáuralo.
5. Muestra el resultado y el mensaje de commit propuesto. Con la aprobación: commit, `git log --oneline -3` y marca la tarea.
6. Para. No empieces la siguiente.

## Validación
Recorre la spec RF por RF: qué test lo cubre y su resultado. Los RF de interfaz se comprueban con el MCP de Chrome DevTools a 1280 y 375 px, con la consola sin errores y un recorrido solo con teclado. Termina con un veredicto: la spec se cumple o no, y qué falta.

## Checklist de revisión de una spec
- [ ] ¿Cada RF es un solo comportamiento y verificable?
- [ ] ¿Cada entrada y cada servicio externo tiene su RF de error?
- [ ] ¿Están claros los permisos: anónimo, usuario y propietario del recurso?
- [ ] ¿Se ha pensado en vacío, duplicado, límite máximo, concurrencia y datos ajenos?
- [ ] ¿"Fuera de alcance" cierra las ampliaciones obvias?
- [ ] ¿Algún requisito contradice docs/constitution.md?

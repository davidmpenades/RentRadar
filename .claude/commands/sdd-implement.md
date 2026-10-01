---
description: SDD · Implementa UNA tarea, tests primero
argument-hint: <NNN-slug> <Tn>
---
Implementa SOLO la tarea $2 de specs/$1/tasks.md, siguiendo specs/$1/plan.md, docs/constitution.md y la skill sdd.

1. Si la spec está "aprobada", pásala a "en curso".
2. Escribe primero los tests y comprueba que fallan por la razón esperada.
3. Escribe el código mínimo hasta que pasen.
4. Ejecuta la verificación de la skill (backend y/o frontend según lo que toques) y muéstrame el resultado.
5. Si el test protege un mecanismo, haz la prueba de mutación y restaura.
6. Propón el mensaje de commit y espera mi aprobación. Después: commit, `git log --oneline -3`, marca $2 en tasks.md e indica qué RF cubre.

Después PÁRATE. No empieces la siguiente tarea.

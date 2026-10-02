---
description: SDD · Implementa UNA tarea con el implementer y la commitea con tu aprobación
argument-hint: <NNN-slug> <Tn>
arguments: [spec, task]
---
1. Si no estás en la rama feature/$spec, cámbiate a ella si existe o créala desde dev.
2. Si specs/$spec/spec.md está "aprobada", pásala a "en curso".
3. Pide a implementer la tarea $task de specs/$spec/tasks.md. Pásale la ruta de la spec, el plan, la tarea y las decisiones relevantes de esta conversación.
4. Cuando termine, enséñame: el resumen del implementer, `git diff --stat` y el resultado de los tests. Si los tests no están en verde o el implementer se ha parado, explícame por qué y PARA.
5. Propón el mensaje de commit y espera mi aprobación. Después: marca $task en tasks.md, haz commit con los cambios y tasks.md, y ejecuta `git log --oneline -3`.
6. Si era la última tarea, actualiza MEMORY.md.

PÁRATE. No empieces la siguiente tarea.

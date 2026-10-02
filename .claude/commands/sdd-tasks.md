---
description: SDD · Divide el plan en tareas pequeñas y verificables
argument-hint: <NNN-slug>
arguments: [spec]
---
A partir de specs/$spec/spec.md y specs/$spec/plan.md, genera specs/$spec/tasks.md con el formato de la skill sdd:
- Tareas de 20-30 min, en orden de dependencia, como máximo 10.
- Cada una con los RF que cubre, su mensaje de commit y una línea "Hecho cuando:" verificable.
- Cada tarea deja build y tests en verde por sí sola.
Si salen más de 10, no las escribas: propón cómo dividir la spec.

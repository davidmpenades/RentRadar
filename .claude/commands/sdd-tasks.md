---
description: SDD · Divide el plan en tareas pequeñas y verificables
argument-hint: <NNN-slug>
---
A partir de specs/$1/spec.md y specs/$1/plan.md, genera specs/$1/tasks.md con el formato de la skill sdd:
- Tareas de 20-30 min, en orden de dependencia, como máximo 10.
- Cada una con los RF que cubre, su mensaje de commit y una línea "Hecho cuando:" verificable.
- Cada tarea deja build y tests en verde por sí sola.
Si salen más de 10, no las escribas: propón cómo dividir la spec.

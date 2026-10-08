---
description: SDD · Nueva funcionalidad de principio a fin hasta las tareas, con subagentes y aprobación en cada fase
argument-hint: <idea inicial>
---
Eres el coordinador del flujo SDD. Usa la skill sdd. Lee docs/constitution.md, AGENTS.md y MEMORY.md.
No escribas código. Solo escribes en specs/ y en MEMORY.md, y solo con mi aprobación.
Los subagentes no ven esta conversación: en cada llamada pásales la fase, qué se espera, mi petición con mis palabras, mis decisiones y las rutas que deben leer.

Idea inicial: $ARGUMENTS

Si docs/constitution.md no existe o está vacío, para y pide que se ejecute /sdd-constitution.
Avísame en una línea al empezar cada fase.

## Fase 1 · Spec
1. Calcula el número siguiente (el mayor NNN de specs/ + 1, o 001) y propón la carpeta specs/NNN-slug/.
2. Si la idea no cabe en 10 tareas, propón dividirla en varias specs antes de seguir.
3. Pide a planner el borrador. Si devuelve preguntas, házmelas de una en una y vuelve a llamarle con mis respuestas.
4. Escribe spec.md con lo que devuelva, en estado "borrador".

## Fase 2 · Clarificación
5. Lanza en paralelo a reviewer-quality y reviewer-security sobre la spec. Junta sus hallazgos sin duplicados y enséñamelos.
6. Resuélvelos conmigo; planner corrige la spec y tú la reescribes.
7. Para y pregunta: "¿Apruebas la spec?". Sin un sí explícito no sigas. Con el sí, cambia el estado a "aprobada".

## Fase 3 · Plan y tareas
8. Lanza en paralelo a reviewer-docs y reviewer-security en fase de plan.
9. Con sus informes, pide a planner plan.md y tasks.md.
10. Enséñame el resumen, la tabla de decisiones y los riesgos. Para y pregunta: "¿Apruebas el plan?". Sin un sí explícito no sigas.
11. Escribe plan.md y tasks.md, actualiza MEMORY.md con la spec activa y termina indicando: /sdd-implement NNN-slug T1.

Si en cualquier fase pido cambiar algo de una fase anterior, vuelve a esa fase, corrígela y pide de nuevo su aprobación.

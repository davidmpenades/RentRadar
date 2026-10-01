---
description: SDD · Nueva funcionalidad de principio a fin hasta las tareas, con aprobación en cada fase
argument-hint: <idea inicial>
---
Vamos a llevar esta funcionalidad por el flujo SDD hasta dejar listas sus tareas. Usa la skill sdd. Lee docs/constitution.md, AGENTS.md y MEMORY.md.
NO escribas código en ningún momento ni modifiques nada fuera de specs/.

Idea inicial: $ARGUMENTS

Si docs/constitution.md no existe o está vacío, para y pide que se ejecute /sdd-constitution.

## Fase 1 · Spec
1. Calcula el número siguiente (el mayor NNN de specs/ + 1, o 001 si no hay ninguno) y propón la carpeta specs/NNN-slug/.
2. Si la idea no cabe en 10 tareas, propón dividirla en varias specs antes de seguir.
3. Hazme preguntas de UNA en UNA, como máximo 5: casos límite, errores, permisos y qué queda fuera.
4. Genera spec.md con la plantilla de la skill y "Estado: borrador". Solo el QUÉ y el POR QUÉ.

## Fase 2 · Clarificación
5. Revisa tu propia spec con el checklist de la skill, como un QA exigente: ambigüedades, contradicciones, casos límite, permisos, errores y conflictos con la constitución. Lístalos numerados.
6. Resuélvelos conmigo y actualiza la spec.
7. PARA y pregunta: "¿Apruebas la spec?". Sin un sí explícito no sigas. Con el sí, cambia el estado a "aprobada".

## Fase 3 · Plan
8. Lee el código afectado y consulta con Context7 las librerías que intervengan.
9. Genera plan.md con la plantilla de la skill, con la tabla de decisiones (opciones, elegida, qué evita, coste) y la estrategia de tests por RF.
10. PARA y pregunta: "¿Apruebas el plan?". Sin un sí explícito no sigas.

## Fase 4 · Tareas
11. Genera tasks.md: como máximo 10 tareas, cada una con sus RF, su mensaje de commit y "Hecho cuando:".
12. Actualiza MEMORY.md con la spec activa y termina indicando: /sdd-implement NNN-slug T1.

Si en cualquier fase te pido cambiar algo de una fase anterior, vuelve a esa fase, corrígela y pide de nuevo su aprobación.

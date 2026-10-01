---
description: SDD · Genera el plan técnico de una spec aprobada
argument-hint: <NNN-slug>
---
Lee docs/constitution.md, AGENTS.md y specs/$1/spec.md. Usa la skill sdd. NO escribas código.

Si la spec no está en estado "aprobada" o tiene dudas abiertas, para y avísame.

Lee el código existente que vaya a verse afectado antes de planificar: cada afirmación sobre el código tiene que estar comprobada o figurar en "Afirmaciones no verificadas". Consulta con Context7 las APIs de las librerías que intervengan.

Genera specs/$1/plan.md con la plantilla de la skill. En "Decisiones", para cada decisión con compromisos reales, da 2-3 opciones, la elegida, qué evita y su coste. Marca qué RF cubre cada parte. Todo debe respetar la constitución.

---
description: SDD · Valida la spec RF por RF (tests + Chrome DevTools)
argument-hint: <NNN-slug>
---
Recorre specs/$1/spec.md requisito por requisito. Para cada RF indica qué test lo cubre y el resultado de ejecutarlo.

Verifica los RF de interfaz con el MCP de Chrome DevTools a 1280 y 375 px: consola sin errores, sin desbordamiento horizontal y recorrido solo con teclado.

Si algún RF no está cubierto o falla, dilo claramente. NO arregles nada todavía. Comprueba los criterios de finalización y dame un veredicto: ¿la spec se cumple?

Si se cumple y lo apruebo: pasa la spec a "implementada" y actualiza MEMORY.md.

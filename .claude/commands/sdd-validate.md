---
description: SDD · Valida la spec con tres revisores en paralelo y verificación en navegador
argument-hint: <NNN-slug> [rama base]
---
1. Si no estás en la rama feature/$1, PARA y avísame.
2. Lanza EN PARALELO a reviewer-quality, reviewer-security y reviewer-docs en fase de validación sobre specs/$1/. Pásales la ruta, el diff de la rama feature/$1 contra la rama base ($2, o dev si no se indica) y qué se espera de cada uno.
3. Mientras tanto, verifica tú los RF de interfaz con el MCP de Chrome DevTools a 375 y 1280 px: consola sin errores, sin desbordamiento horizontal y recorrido solo con teclado.
4. Junta los tres informes y tu verificación en uno solo, sin duplicados: lo bloqueante primero, después "Opcional". Termina con un veredicto final.
5. NO arregles nada. Si hay cambios necesarios, propón cómo corregirlos (vuelta al implementer con la lista exacta) y espera mi decisión. Máximo 2 vueltas de corrección; si sigue fallando, para y explícamelo.
6. Si la spec se cumple y lo apruebo: pasa la spec a "implementada" y actualiza MEMORY.md.

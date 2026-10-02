# Producto — RentRadar
Borrador. Decisiones de producto que alimentan las specs; lo pendiente se marca como tal.

## Ubicación y privacidad

### Decidido
- **Ubicación pública según el anunciante.** Los particulares muestran una ubicación aproximada; los profesionales pueden mostrar la exacta.
- **Dirección exacta guardada en privado.** La ubicación pública aproximada se deriva de ella y se guarda aparte, para que la exacta nunca salga de la API por accidente.
- **La búsqueda usa la ubicación pública.** Para los particulares, la búsqueda por radio y la distancia mostrada usan la ubicación aproximada, nunca la exacta. Así, cruzar varias búsquedas no permite deducir la dirección.
- **Ubicación aproximada estable.** Es fija para cada bien y no cambia en cada petición.
- **Distancia redondeada y radio mínimo de búsqueda.** Los valores se fijan cuando se confirme el tamaño de celda.

### Pendiente de confirmar (con recomendación)
- **Cálculo de la aproximada.** Recomendación: ajustar el punto al centro de una celda de una cuadrícula fija de unos 500 m. Es determinista, no hay que guardar ninguna semilla, y aunque la dirección cambie dentro de la misma celda no se revela nada nuevo. El mapa tendrá que agrupar los bienes que caen en el mismo punto.
- **Ubicación exacta de los profesionales.** Recomendación: cada profesional elige si la muestra, y por defecto se muestra la aproximada.
- **Representación en el mapa.** Recomendación: la ubicación aproximada se dibuja como un círculo o zona sin marcador central, para no dar a entender que es exacta.

### Abierto
- **Cuándo se revela la dirección exacta.** Depende de si habrá reservas dentro de la plataforma. Si las hay, la recomendación es revelarla solo al arrendatario cuando la reserva esté confirmada.
- **Valores del redondeo y del radio mínimo.** Dependen del tamaño de celda.

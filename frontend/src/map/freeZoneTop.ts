const GAP_PX = 8;

// Dónde empieza la zona libre del aviso: bajo los controles del mapa, con un hueco; sin controles, desde arriba
export function freeZoneTop(controlsBottom: number | null, zoneTop: number): number {
  if (controlsBottom === null) return 0;
  return Math.ceil(controlsBottom - zoneTop) + GAP_PX;
}

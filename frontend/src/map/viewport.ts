import type { VisibleBounds } from "./requestBox";

export type Viewport = { bounds: VisibleBounds; latitude: number; longitude: number; zoom: number };

export const INITIAL_CENTER = { latitude: 39.4699, longitude: -0.3763 };
export const INITIAL_ZOOM = 11;

const CENTER_TOLERANCE_DEGREES = 1e-6;
const ZOOM_TOLERANCE = 0.01;

// El mapa guarda el centro en coma flotante: se compara con tolerancia y no con igualdad
export function atInitialView(view: Pick<Viewport, "latitude" | "longitude" | "zoom">): boolean {
  return (
    Math.abs(view.latitude - INITIAL_CENTER.latitude) <= CENTER_TOLERANCE_DEGREES &&
    Math.abs(view.longitude - INITIAL_CENTER.longitude) <= CENTER_TOLERANCE_DEGREES &&
    Math.abs(view.zoom - INITIAL_ZOOM) <= ZOOM_TOLERANCE
  );
}

export type VisibleBounds = { south: number; west: number; north: number; east: number };

// Límites del cuadro como índices enteros de celdas de 0,05 grados
export type RequestBox = { south: number; west: number; north: number; east: number };

export type RequestBoxResult =
  | { kind: "ok"; box: RequestBox }
  | { kind: "outOfRange" }
  | { kind: "tooLarge" };

const EARTH_RADIUS_METERS = 6_371_008.8;
const PRIVACY_MARGIN_METERS = 2000;
const CELLS_PER_DEGREE = 20;
const HUNDREDTHS_PER_CELL = 5;
const MAX_LATITUDE_INDEX = 85 * CELLS_PER_DEGREE;
const MAX_LONGITUDE_INDEX = 180 * CELLS_PER_DEGREE;
// 5,5 grados cuadrados: el máximo del servidor (6) menos el margen del cliente (0,5)
const MAX_CELLS = 2200;

const latitudeMarginDegrees = ((PRIVACY_MARGIN_METERS / EARTH_RADIUS_METERS) * 180) / Math.PI;

const OUT_OF_RANGE: RequestBoxResult = { kind: "outOfRange" };
const TOO_LARGE: RequestBoxResult = { kind: "tooLarge" };

// Amplía la zona visible lo que mide el mayor radio de privacidad y la redondea hacia fuera, sin recortar nunca
export function requestBox(visible: VisibleBounds): RequestBoxResult {
  const { south, west, north, east } = visible;
  if (![south, west, north, east].every(Number.isFinite) || south > north || west > east) {
    return OUT_OF_RANGE;
  }

  const southIndex = Math.floor((south - latitudeMarginDegrees) * CELLS_PER_DEGREE);
  const northIndex = Math.ceil((north + latitudeMarginDegrees) * CELLS_PER_DEGREE);
  // La latitud va antes que la longitud: así el cuadro ampliado queda dentro de ±85 y el coseno nunca se anula
  if (southIndex < -MAX_LATITUDE_INDEX || northIndex > MAX_LATITUDE_INDEX) return OUT_OF_RANGE;

  // Un grado de longitud mide menos cuanto más lejos del ecuador: el margen usa la latitud más alejada del cuadro ya ampliado
  const farthestLatitude = Math.max(
    Math.abs(south - latitudeMarginDegrees),
    Math.abs(north + latitudeMarginDegrees),
  );
  const longitudeMarginDegrees = latitudeMarginDegrees / Math.cos((farthestLatitude * Math.PI) / 180);
  const westIndex = Math.floor((west - longitudeMarginDegrees) * CELLS_PER_DEGREE);
  const eastIndex = Math.ceil((east + longitudeMarginDegrees) * CELLS_PER_DEGREE);
  if (westIndex < -MAX_LONGITUDE_INDEX || eastIndex > MAX_LONGITUDE_INDEX) return OUT_OF_RANGE;

  // Aritmética entera: el área no depende de redondeos de coma flotante
  if ((northIndex - southIndex) * (eastIndex - westIndex) > MAX_CELLS) return TOO_LARGE;

  return { kind: "ok", box: { south: southIndex, west: westIndex, north: northIndex, east: eastIndex } };
}

// Se escribe desde el entero y no con toFixed, para que el mismo cuadro dé siempre la misma cadena
function formatIndex(index: number): string {
  const hundredths = Math.abs(index) * HUNDREDTHS_PER_CELL;
  const whole = Math.floor(hundredths / 100);
  const fraction = String(hundredths % 100).padStart(2, "0");
  return `${index < 0 ? "-" : ""}${whole}.${fraction}`;
}

export function boxToQuery(box: RequestBox): string {
  return [
    `south=${formatIndex(box.south)}`,
    `west=${formatIndex(box.west)}`,
    `north=${formatIndex(box.north)}`,
    `east=${formatIndex(box.east)}`,
  ].join("&");
}

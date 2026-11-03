// Atribución escrita aquí: la del TileJSON la pone un tercero y sus enlaces no llevan rel
export const MAP_ATTRIBUTION_HTML =
  '<a href="https://openfreemap.org" target="_blank" rel="noopener noreferrer">OpenFreeMap</a> ' +
  '<a href="https://www.openmaptiles.org/" target="_blank" rel="noopener noreferrer">© OpenMapTiles</a> ' +
  'Data from <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a>';

export type StyleJson = {
  version: 8;
  sources: Record<string, unknown>;
  layers: unknown[];
  [key: string]: unknown;
};

// Error propio con mensaje fijo: la dirección bloqueada no debe llegar a la consola
export class BlockedUrlError extends Error {
  constructor() {
    super("Petición del mapa bloqueada");
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function validateStyleUrl(raw: string): URL | undefined {
  let url: URL;
  try {
    url = new URL(raw);
  } catch {
    return undefined;
  }
  if (url.protocol !== "https:" || url.username !== "" || url.password !== "") return undefined;
  return url;
}

// Los orígenes permitidos se pasan con su forma canónica (`URL.origin`)
export function isAllowedMapUrl(raw: string, allowedOrigins: readonly string[]): boolean {
  let url: URL;
  try {
    url = new URL(raw);
  } catch {
    return false;
  }
  return url.protocol === "https:" && allowedOrigins.includes(url.origin);
}

// Solo lo mínimo para no pasar a MapLibre algo que no sea un estilo; el resto lo valida él
export function validateStyleJson(json: unknown): StyleJson | undefined {
  if (!isRecord(json) || json.version !== 8 || !isRecord(json.sources) || !Array.isArray(json.layers)) {
    return undefined;
  }
  return json as StyleJson;
}

// MapLibre mezcla las opciones de la fuente sobre el TileJSON: así gana esta atribución y no la del tercero
export function withFixedAttribution(style: StyleJson): StyleJson {
  const sources = Object.fromEntries(
    Object.entries(style.sources).map(([id, source]) => [
      id,
      isRecord(source) ? { ...source, attribution: MAP_ATTRIBUTION_HTML } : source,
    ]),
  );
  return { ...style, sources };
}

export function createTransformRequest(allowedOrigins: readonly string[]) {
  return (url: string): undefined => {
    if (!isAllowedMapUrl(url, allowedOrigins)) throw new BlockedUrlError();
    return undefined;
  };
}

// Al registrar un listener, MapLibre deja de escribir los errores en consola: lo hace este
export function createMapErrorListener(logError: (error: unknown) => void) {
  return (event: { error: unknown }): void => {
    if (event.error instanceof BlockedUrlError) return;
    logError(event.error);
  };
}

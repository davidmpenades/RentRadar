import { hasJsonContentType } from "../api/http";
import { runWithTimeout } from "../api/timeout";
import { validateStyleJson, withFixedAttribution, type StyleJson } from "./style";

type StyleLoaderOptions<Handle> = {
  fetch: (input: string, init: { credentials: "omit"; signal: AbortSignal }) => Promise<Response>;
  setTimer: (callback: () => void, ms: number) => Handle;
  clearTimer: (handle: Handle) => void;
  timeoutMs: number;
};

const STYLE_TIMEOUT_MS = 10_000;
const MAX_STYLE_CHARS = 1_048_576;

// Mensaje fijo: no lleva la dirección ni nada del cuerpo
export class StyleLoadError extends Error {
  constructor() {
    super("No se pudo cargar el estilo del mapa");
  }
}

export function createStyleLoader<Handle>(options: StyleLoaderOptions<Handle>) {
  const { fetch, setTimer, clearTimer, timeoutMs } = options;

  return function loadStyle(url: string, signal: AbortSignal): Promise<StyleJson> {
    return runWithTimeout(
      { signal, timeoutMs, setTimer, clearTimer, onTimeout: () => new StyleLoadError() },
      async (inner) => {
        const response = await fetch(url, { credentials: "omit", signal: inner });
        if (response.status !== 200) throw new StyleLoadError();
        if (!hasJsonContentType(response)) throw new StyleLoadError();
        const text = await response.text();
        if (text.length > MAX_STYLE_CHARS) throw new StyleLoadError();

        let json: unknown;
        try {
          json = JSON.parse(text);
        } catch {
          throw new StyleLoadError();
        }
        const style = validateStyleJson(json);
        if (!style) throw new StyleLoadError();
        return withFixedAttribution(style);
      },
    );
  };
}

export const loadStyle = createStyleLoader({
  fetch: (input, init) => fetch(input, init),
  setTimer: (callback, ms) => setTimeout(callback, ms),
  clearTimer: (handle) => clearTimeout(handle),
  timeoutMs: STYLE_TIMEOUT_MS,
});

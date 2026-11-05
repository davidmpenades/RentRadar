import { hasJsonContentType } from "../api/http";
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

  return async function loadStyle(url: string, signal: AbortSignal): Promise<StyleJson> {
    signal.throwIfAborted();

    // Controlador propio para enlazar a mano la señal externa y el tiempo máximo
    const controller = new AbortController();
    let timedOut = false;
    const abortWithExternal = () => controller.abort(signal.reason);
    signal.addEventListener("abort", abortWithExternal, { once: true });
    const timer = setTimer(() => {
      timedOut = true;
      controller.abort();
    }, timeoutMs);

    try {
      const response = await fetch(url, { credentials: "omit", signal: controller.signal });
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
    } catch (error) {
      if (timedOut) throw new StyleLoadError();
      throw error;
    } finally {
      // Se cancela al terminar de leer, no al llegar las cabeceras: cubre un cuerpo colgado
      clearTimer(timer);
      signal.removeEventListener("abort", abortWithExternal);
    }
  };
}

export const loadStyle = createStyleLoader({
  fetch: (input, init) => fetch(input, init),
  setTimer: (callback, ms) => setTimeout(callback, ms),
  clearTimer: (handle) => clearTimeout(handle),
  timeoutMs: STYLE_TIMEOUT_MS,
});

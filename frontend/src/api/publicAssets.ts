import { boxToQuery, type RequestBox } from "../map/requestBox";
import { hasJsonContentType } from "./http";
import { InvalidResponseError, validateResponse } from "./validate";

type PublicAssetList = ReturnType<typeof validateResponse>;

export type FailureKind = "network" | "timeout" | "server" | "throttled" | "invalid";

export type FetchInit = { credentials: "omit"; signal: AbortSignal };

type FetcherOptions<Handle> = {
  fetch: (input: string, init: FetchInit) => Promise<Response>;
  setTimer: (callback: () => void, ms: number) => Handle;
  clearTimer: (handle: Handle) => void;
  timeoutMs: number;
};

const PUBLIC_ASSETS_URL = "/api/v1/public/assets/";
const REQUEST_TIMEOUT_MS = 10_000;

// Los errores solo llevan la causa: ni el cuerpo ni la dirección pedida
export class HttpStatusError extends Error {
  readonly status: number;

  constructor(status: number) {
    super("La API respondió con un estado no admitido");
    this.status = status;
  }
}

export class NetworkError extends Error {
  constructor() {
    super("No se pudo conectar con la API");
  }
}

export class RequestTimeoutError extends Error {
  constructor() {
    super("La API tardó demasiado en responder");
  }
}

async function readJson(response: Response): Promise<unknown> {
  // Vite devuelve index.html con un 200 para las rutas que no conoce
  if (!hasJsonContentType(response)) {
    throw new InvalidResponseError();
  }
  try {
    return await response.json();
  } catch (error) {
    if (error instanceof SyntaxError) throw new InvalidResponseError();
    throw error;
  }
}

// Solo el TypeError de fetch es un fallo de red; el de cualquier otra parte es un error del código
async function requestAssets(
  fetch: FetcherOptions<unknown>["fetch"],
  url: string,
  init: FetchInit,
): Promise<Response> {
  try {
    return await fetch(url, init);
  } catch (error) {
    if (error instanceof TypeError) throw new NetworkError();
    throw error;
  }
}

export function createPublicAssetsFetcher<Handle>(options: FetcherOptions<Handle>) {
  const { fetch, setTimer, clearTimer, timeoutMs } = options;

  return async function fetchAssets(box: RequestBox, signal: AbortSignal): Promise<PublicAssetList> {
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
      const response = await requestAssets(fetch, `${PUBLIC_ASSETS_URL}?${boxToQuery(box)}`, {
        credentials: "omit",
        signal: controller.signal,
      });
      // El cuerpo de un error no se lee: nunca llega a la pantalla
      if (response.status !== 200) throw new HttpStatusError(response.status);
      return validateResponse(await readJson(response));
    } catch (error) {
      if (timedOut) throw new RequestTimeoutError();
      // Si abortó la señal externa, el AbortError sale tal cual y quien pidió lo descarta
      throw error;
    } finally {
      // Se cancela al terminar de validar, no al llegar las cabeceras: cubre un cuerpo colgado
      clearTimer(timer);
      signal.removeEventListener("abort", abortWithExternal);
    }
  };
}

export const fetchPublicAssets = createPublicAssetsFetcher({
  fetch: (input, init) => fetch(input, init),
  setTimer: (callback, ms) => setTimeout(callback, ms),
  clearTimer: (handle) => clearTimeout(handle),
  timeoutMs: REQUEST_TIMEOUT_MS,
});

// Solo clasifica causas conocidas; un error inesperado se propaga para no esconder un fallo del código
export function classifyFailure(error: unknown): FailureKind {
  if (error instanceof HttpStatusError) return error.status === 429 ? "throttled" : "server";
  if (error instanceof RequestTimeoutError) return "timeout";
  if (error instanceof InvalidResponseError) return "invalid";
  if (error instanceof NetworkError) return "network";
  throw error;
}

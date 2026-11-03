import { afterEach, describe, expect, it, vi } from "vitest";

import openapi from "../../../backend/openapi.json";
import type { RequestBox } from "../map/requestBox";
import {
  classifyFailure,
  createPublicAssetsFetcher,
  fetchPublicAssets,
  HttpStatusError,
  NetworkError,
  RequestTimeoutError,
  type FetchInit,
} from "./publicAssets";
import { InvalidResponseError } from "./validate";

const BOX: RequestBox = { south: 9, west: -1, north: 21, east: 211 };
const BOX_QUERY = "south=0.45&west=-0.05&north=1.05&east=10.55";
const TIMEOUT_MS = 10_000;

// Reloj a mano: los temporizadores pendientes se ven y solo vencen con advance
function createFakeClock() {
  let now = 0;
  let nextHandle = 1;
  let started = 0;
  const timers = new Map<number, { dueAt: number; callback: () => void }>();
  return {
    setTimer(callback: () => void, ms: number): number {
      const handle = nextHandle++;
      started += 1;
      timers.set(handle, { dueAt: now + ms, callback });
      return handle;
    },
    clearTimer(handle: number): void {
      timers.delete(handle);
    },
    advance(ms: number): void {
      const target = now + ms;
      for (;;) {
        const due = [...timers.entries()]
          .filter(([, timer]) => timer.dueAt <= target)
          .sort(([, a], [, b]) => a.dueAt - b.dueAt)[0];
        if (!due) break;
        const [handle, timer] = due;
        timers.delete(handle);
        now = timer.dueAt;
        timer.callback();
      }
      now = target;
    },
    get pending(): number {
      return timers.size;
    },
    get started(): number {
      return started;
    },
  };
}

function asset() {
  return {
    public_id: crypto.randomUUID(),
    title: "Kayak doble",
    category_slug: "kayak",
    category_name: "Kayak",
    price: "12.50",
    currency: "EUR",
    price_unit: "day",
    privacy_radius: 1000,
    latitude: 39.469912,
    longitude: -0.376288,
  };
}

function jsonResponse(body: unknown, init: ResponseInit = {}): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
    ...init,
  });
}

// Deja pasar las tareas pendientes de la plataforma (flujos del cuerpo de Response incluidos)
function tick(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, 0));
}

type Call = { url: string; init: FetchInit };

function setup(respond: (init: FetchInit, url: string) => Promise<Response>) {
  const clock = createFakeClock();
  const calls: Call[] = [];
  const fetchAssets = createPublicAssetsFetcher({
    fetch: (url, init) => {
      calls.push({ url, init });
      return respond(init, url);
    },
    setTimer: clock.setTimer,
    clearTimer: clock.clearTimer,
    timeoutMs: TIMEOUT_MS,
  });
  return { clock, calls, fetchAssets };
}

// Un fetch que respeta la señal: se rechaza con su motivo cuando se aborta
function neverResponds(init: FetchInit): Promise<Response> {
  return new Promise((_resolve, reject) => {
    init.signal.addEventListener("abort", () => reject(init.signal.reason), { once: true });
  });
}

// Llegan las cabeceras pero el cuerpo no termina; el flujo falla al abortar la señal
function bodyThatNeverArrives(init: FetchInit): Promise<Response> {
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      init.signal.addEventListener("abort", () => controller.error(init.signal.reason), {
        once: true,
      });
    },
  });
  return Promise.resolve(
    new Response(body, { status: 200, headers: { "Content-Type": "application/json" } }),
  );
}

async function rejection(promise: Promise<unknown>): Promise<unknown> {
  try {
    await promise;
  } catch (error) {
    return error;
  }
  throw new Error("La promesa se esperaba rechazada");
}

// Ejecuta la función y devuelve lo que lanza: permite comparar la misma instancia, no solo el mensaje
function thrownBy(run: () => unknown): unknown {
  try {
    run();
  } catch (error) {
    return error;
  }
  throw new Error("La función se esperaba que lanzase");
}

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("fetchPublicAssets: la petición", () => {
  it("pide la ruta con los cuatro límites, sin credenciales", async () => {
    const { calls, fetchAssets } = setup(() => Promise.resolve(jsonResponse({ results: [], incomplete: false })));
    await fetchAssets(BOX, new AbortController().signal);
    expect(calls).toHaveLength(1);
    expect(calls[0]?.url).toBe(`/api/v1/public/assets/?${BOX_QUERY}`);
    expect(calls[0]?.init.credentials).toBe("omit");
    expect(Object.keys(calls[0]?.init ?? {}).sort()).toEqual(["credentials", "signal"]);
  });

  it("la ruta y los cuatro nombres de parámetro son los de la descripción OpenAPI", async () => {
    const { calls, fetchAssets } = setup(() => Promise.resolve(jsonResponse({ results: [], incomplete: false })));
    await fetchAssets(BOX, new AbortController().signal);
    const requested = new URL(calls[0]?.url ?? "", "http://localhost");

    expect(Object.keys(openapi.paths)).toContain(requested.pathname);
    const operation = openapi.paths["/api/v1/public/assets/"].get;
    const declared = operation.parameters.map((parameter) => parameter.name).sort();
    expect(declared).toEqual(["east", "north", "south", "west"]);
    expect(operation.parameters.every((parameter) => parameter.in === "query")).toBe(true);
    expect([...requested.searchParams.keys()].sort()).toEqual(declared);
  });

  it("devuelve la respuesta validada", async () => {
    const body = { results: [asset(), asset()], incomplete: true };
    const { fetchAssets } = setup(() => Promise.resolve(jsonResponse(body)));
    expect(await fetchAssets(BOX, new AbortController().signal)).toEqual(body);
  });

  it("la instancia real usa fetch sin credenciales y un tiempo máximo de 10 s", async () => {
    const realFetch = vi.fn(() => Promise.resolve(jsonResponse({ results: [], incomplete: false })));
    vi.stubGlobal("fetch", realFetch);
    const setTimeoutSpy = vi.spyOn(globalThis, "setTimeout");
    const clearTimeoutSpy = vi.spyOn(globalThis, "clearTimeout");

    await fetchPublicAssets(BOX, new AbortController().signal);

    expect(realFetch).toHaveBeenCalledTimes(1);
    const [url, init] = realFetch.mock.calls[0] as unknown as [string, FetchInit];
    expect(url).toBe(`/api/v1/public/assets/?${BOX_QUERY}`);
    expect(init.credentials).toBe("omit");
    const timeoutCalls = setTimeoutSpy.mock.calls
      .map((call, index) => ({ ms: call[1], handle: setTimeoutSpy.mock.results[index]?.value }))
      .filter(({ ms }) => ms === TIMEOUT_MS);
    expect(timeoutCalls).toHaveLength(1);
    expect(clearTimeoutSpy).toHaveBeenCalledWith(timeoutCalls[0]?.handle);
  });
});

describe("fetchPublicAssets: tiempo máximo", () => {
  it("a 9999 ms sigue esperando y a 10000 ms falla por tiempo con la petición abortada", async () => {
    const { clock, calls, fetchAssets } = setup(neverResponds);
    const result = rejection(fetchAssets(BOX, new AbortController().signal));
    let settled = false;
    void result.then(() => (settled = true));

    clock.advance(TIMEOUT_MS - 1);
    await tick();
    expect(settled).toBe(false);
    expect(calls[0]?.init.signal.aborted).toBe(false);
    expect(clock.pending).toBe(1);

    clock.advance(1);
    const error = await result;
    expect(error).toBeInstanceOf(RequestTimeoutError);
    expect(calls[0]?.init.signal.aborted).toBe(true);
    expect(clock.pending).toBe(0);
    expect(classifyFailure(error)).toBe("timeout");
  });

  it("un cuerpo que nunca llega también es un fallo por tiempo", async () => {
    const { clock, fetchAssets } = setup(bodyThatNeverArrives);
    const result = rejection(fetchAssets(BOX, new AbortController().signal));
    await tick();
    clock.advance(TIMEOUT_MS);
    expect(await result).toBeInstanceOf(RequestTimeoutError);
    expect(clock.pending).toBe(0);
  });

  it("el temporizador sigue vivo al llegar las cabeceras y se cancela al validar", async () => {
    let bodyController: ReadableStreamDefaultController<Uint8Array> | undefined;
    const { clock, fetchAssets } = setup(() => {
      const body = new ReadableStream<Uint8Array>({
        start(controller) {
          bodyController = controller;
        },
      });
      return Promise.resolve(
        new Response(body, { status: 200, headers: { "Content-Type": "application/json" } }),
      );
    });
    const result = fetchAssets(BOX, new AbortController().signal);
    await tick();
    expect(clock.pending).toBe(1);

    bodyController?.enqueue(new TextEncoder().encode(JSON.stringify({ results: [], incomplete: false })));
    bodyController?.close();
    await result;
    expect(clock.pending).toBe(0);
  });

  it("tras un éxito el temporizador está cancelado y el tiempo ya no aborta nada", async () => {
    const { clock, calls, fetchAssets } = setup(() =>
      Promise.resolve(jsonResponse({ results: [], incomplete: false })),
    );
    await fetchAssets(BOX, new AbortController().signal);
    expect(clock.started).toBe(1);
    expect(clock.pending).toBe(0);
    clock.advance(TIMEOUT_MS * 3);
    expect(calls[0]?.init.signal.aborted).toBe(false);
  });
});

describe("fetchPublicAssets: cancelación externa", () => {
  it("con la señal ya abortada relanza el AbortError sin pedir ni arrancar temporizadores", async () => {
    const { clock, calls, fetchAssets } = setup(neverResponds);
    const controller = new AbortController();
    controller.abort();

    const error = await rejection(fetchAssets(BOX, controller.signal));
    expect(error).toBe(controller.signal.reason);
    expect((error as DOMException).name).toBe("AbortError");
    expect(calls).toHaveLength(0);
    expect(clock.started).toBe(0);
  });

  it("abortada durante la petición relanza el AbortError, sin temporizadores vivos", async () => {
    const { clock, calls, fetchAssets } = setup(neverResponds);
    const controller = new AbortController();
    const result = rejection(fetchAssets(BOX, controller.signal));
    await tick();
    controller.abort();

    const error = await result;
    expect((error as DOMException).name).toBe("AbortError");
    expect(calls[0]?.init.signal.aborted).toBe(true);
    expect(clock.pending).toBe(0);
  });

  it("abortada mientras llega el cuerpo relanza el AbortError", async () => {
    const { clock, fetchAssets } = setup(bodyThatNeverArrives);
    const controller = new AbortController();
    const result = rejection(fetchAssets(BOX, controller.signal));
    await tick();
    controller.abort();

    const error = await result;
    expect((error as DOMException).name).toBe("AbortError");
    expect(clock.pending).toBe(0);
  });

  it("un AbortError no es un fallo clasificable: se propaga", async () => {
    const { fetchAssets } = setup(neverResponds);
    const controller = new AbortController();
    const result = rejection(fetchAssets(BOX, controller.signal));
    await tick();
    controller.abort();
    const error = await result;
    expect(thrownBy(() => classifyFailure(error))).toBe(error);
  });

  it.each([
    ["con éxito", () => Promise.resolve(jsonResponse({ results: [], incomplete: false }))],
    ["con un error de estado", () => Promise.resolve(jsonResponse({}, { status: 500 }))],
  ])("quita de la señal externa el listener que añadió, %s", async (_name, respond) => {
    const { fetchAssets } = setup(respond);
    const controller = new AbortController();
    const add = vi.spyOn(controller.signal, "addEventListener");
    const remove = vi.spyOn(controller.signal, "removeEventListener");

    await fetchAssets(BOX, controller.signal).catch(() => undefined);

    expect(add).toHaveBeenCalledTimes(1);
    const [type, listener, options] = add.mock.calls[0] ?? [];
    expect(type).toBe("abort");
    expect(options).toEqual({ once: true });
    expect(remove).toHaveBeenCalledWith("abort", listener);
  });

  it("abortar la señal externa después de terminar no toca la petición ya hecha", async () => {
    const { calls, fetchAssets } = setup(() => Promise.resolve(jsonResponse({ results: [], incomplete: false })));
    const controller = new AbortController();
    await fetchAssets(BOX, controller.signal);
    controller.abort();
    expect(calls[0]?.init.signal.aborted).toBe(false);
  });
});

describe("fetchPublicAssets: errores", () => {
  it.each([201, 204, 206, 301, 400, 403, 404, 500, 502, 503])(
    "el estado %i falla con HttpStatusError, sin leer el cuerpo",
    async (status) => {
      const response =
        status === 204
          ? new Response(null, { status })
          : new Response("cuerpo-secreto", { status, headers: { "Content-Type": "application/json" } });
      const { clock, fetchAssets } = setup(() => Promise.resolve(response));

      const error = await rejection(fetchAssets(BOX, new AbortController().signal));
      expect(error).toBeInstanceOf(HttpStatusError);
      expect((error as HttpStatusError).status).toBe(status);
      expect(classifyFailure(error)).toBe("server");
      expect(response.bodyUsed).toBe(false);
      expect(clock.pending).toBe(0);
    },
  );

  it("el estado 429 se clasifica como límite y no lee el cuerpo", async () => {
    const response = new Response('{"code":"throttled","retry_after":30}', {
      status: 429,
      headers: { "Content-Type": "application/json" },
    });
    const { fetchAssets } = setup(() => Promise.resolve(response));

    const error = await rejection(fetchAssets(BOX, new AbortController().signal));
    expect((error as HttpStatusError).status).toBe(429);
    expect(classifyFailure(error)).toBe("throttled");
    expect(response.bodyUsed).toBe(false);
  });

  it("el error de estado solo lleva el estado", async () => {
    const { fetchAssets } = setup(() =>
      Promise.resolve(new Response("cuerpo-secreto", { status: 500 })),
    );
    const error = (await rejection(fetchAssets(BOX, new AbortController().signal))) as HttpStatusError;
    expect(Object.getOwnPropertyNames(error).sort()).toEqual(["message", "stack", "status"]);
    expect(error.message).not.toContain("cuerpo-secreto");
  });

  it("un TypeError de fetch pasa a NetworkError, sin la dirección ni el mensaje original", async () => {
    const { clock, fetchAssets } = setup(() =>
      Promise.reject(new TypeError(`Failed to fetch /api/v1/public/assets/?${BOX_QUERY}`)),
    );

    const error = await rejection(fetchAssets(BOX, new AbortController().signal));
    expect(error).toBeInstanceOf(NetworkError);
    expect(classifyFailure(error)).toBe("network");
    expect(Object.getOwnPropertyNames(error).sort()).toEqual(["message", "stack"]);
    expect((error as NetworkError).cause).toBeUndefined();
    const everything = `${(error as Error).message}\n${(error as Error).stack ?? ""}`;
    expect(everything).not.toContain("Failed to fetch");
    expect(everything).not.toContain("south=");
    expect(clock.pending).toBe(0);
  });

  it("un TypeError de fetch con el temporizador ya disparado sigue siendo un fallo por tiempo", async () => {
    const { clock, fetchAssets } = setup(
      (init) =>
        new Promise((_resolve, reject) => {
          init.signal.addEventListener("abort", () => reject(new TypeError("Failed to fetch")), {
            once: true,
          });
        }),
    );
    const result = rejection(fetchAssets(BOX, new AbortController().signal));
    await tick();
    clock.advance(TIMEOUT_MS);

    const error = await result;
    expect(error).toBeInstanceOf(RequestTimeoutError);
    expect(classifyFailure(error)).toBe("timeout");
  });

  it("un TypeError que no viene de fetch (response.json) se propaga: no es un fallo de red", async () => {
    const used = jsonResponse({ results: [], incomplete: false });
    await used.text();
    const { clock, fetchAssets } = setup(() => Promise.resolve(used));

    const error = await rejection(fetchAssets(BOX, new AbortController().signal));
    expect(error).toBeInstanceOf(TypeError);
    expect(error).not.toBeInstanceOf(NetworkError);
    expect(thrownBy(() => classifyFailure(error))).toBe(error);
    expect(clock.pending).toBe(0);
  });

  it("un TypeError que no viene de fetch (cabeceras) se propaga: no es un fallo de red", async () => {
    const failure = new TypeError("cabeceras rotas");
    const broken = {
      status: 200,
      headers: {
        get: () => {
          throw failure;
        },
      },
    } as unknown as Response;
    const { fetchAssets } = setup(() => Promise.resolve(broken));

    const error = await rejection(fetchAssets(BOX, new AbortController().signal));
    expect(error).toBe(failure);
    expect(thrownBy(() => classifyFailure(error))).toBe(failure);
  });

  it("un error inesperado de fetch se propaga sin clasificar", async () => {
    const failure = new RangeError("inesperado");
    const { fetchAssets } = setup(() => Promise.reject(failure));

    const error = await rejection(fetchAssets(BOX, new AbortController().signal));
    expect(error).toBe(failure);
    expect(thrownBy(() => classifyFailure(error))).toBe(failure);
  });
});

describe("fetchPublicAssets: Content-Type y cuerpo", () => {
  it.each([
    "application/json",
    "application/json; charset=utf-8",
    "application/json;charset=UTF-8",
    "application/json ; charset=utf-8",
    "APPLICATION/JSON",
    "Application/Json",
  ])("acepta el tipo %s", async (contentType) => {
    const { fetchAssets } = setup(() =>
      Promise.resolve(jsonResponse({ results: [], incomplete: false }, { headers: { "Content-Type": contentType } })),
    );
    await expect(fetchAssets(BOX, new AbortController().signal)).resolves.toEqual({
      results: [],
      incomplete: false,
    });
  });

  it.each([
    "text/html",
    "text/html; charset=utf-8",
    "text/plain",
    "application/jsonp",
    "application/jsonx",
    "application/json-patch+json",
    "application/vnd.api+json",
    "application/x-json",
    "xapplication/json",
    "json",
    "",
  ])("rechaza el tipo %j con un 200, sin leer el cuerpo", async (contentType) => {
    const response = new Response('{"results":[],"incomplete":false}', {
      status: 200,
      headers: { "Content-Type": contentType },
    });
    const { fetchAssets } = setup(() => Promise.resolve(response));

    const error = await rejection(fetchAssets(BOX, new AbortController().signal));
    expect(error).toBeInstanceOf(InvalidResponseError);
    expect(classifyFailure(error)).toBe("invalid");
    expect(response.bodyUsed).toBe(false);
  });

  it("rechaza un 200 sin Content-Type", async () => {
    const response = new Response(new TextEncoder().encode('{"results":[],"incomplete":false}'), {
      status: 200,
    });
    expect(response.headers.get("Content-Type")).toBeNull();
    const { fetchAssets } = setup(() => Promise.resolve(response));

    const error = await rejection(fetchAssets(BOX, new AbortController().signal));
    expect(error).toBeInstanceOf(InvalidResponseError);
    expect(response.bodyUsed).toBe(false);
  });

  it("el index.html de Vite con un 200 es una respuesta no válida", async () => {
    const response = new Response("<!doctype html><html></html>", {
      status: 200,
      headers: { "Content-Type": "text/html" },
    });
    const { fetchAssets } = setup(() => Promise.resolve(response));
    const error = await rejection(fetchAssets(BOX, new AbortController().signal));
    expect(classifyFailure(error)).toBe("invalid");
  });

  it.each(["{", "", "<html>", '{"results":'])("un JSON roto (%j) es una respuesta no válida", async (text) => {
    const { clock, fetchAssets } = setup(() =>
      Promise.resolve(new Response(text, { status: 200, headers: { "Content-Type": "application/json" } })),
    );
    const error = await rejection(fetchAssets(BOX, new AbortController().signal));
    expect(error).toBeInstanceOf(InvalidResponseError);
    expect(classifyFailure(error)).toBe("invalid");
    expect(clock.pending).toBe(0);
  });

  it.each([
    ["null", null],
    ["campo de más", { results: [], incomplete: false, total: 0 }],
    ["un bien con otro radio", { results: [{ ...asset(), privacy_radius: 1500 }], incomplete: false }],
  ])("un JSON con forma incorrecta (%s) es una respuesta no válida", async (_name, body) => {
    const { clock, fetchAssets } = setup(() => Promise.resolve(jsonResponse(body)));
    const error = await rejection(fetchAssets(BOX, new AbortController().signal));
    expect(error).toBeInstanceOf(InvalidResponseError);
    expect(clock.pending).toBe(0);
  });
});

describe("classifyFailure", () => {
  it("clasifica cada causa conocida", () => {
    expect(classifyFailure(new HttpStatusError(429))).toBe("throttled");
    expect(classifyFailure(new HttpStatusError(500))).toBe("server");
    expect(classifyFailure(new HttpStatusError(404))).toBe("server");
    expect(classifyFailure(new HttpStatusError(204))).toBe("server");
    expect(classifyFailure(new RequestTimeoutError())).toBe("timeout");
    expect(classifyFailure(new NetworkError())).toBe("network");
    expect(classifyFailure(new InvalidResponseError())).toBe("invalid");
  });

  it.each([
    ["un Error cualquiera", new Error("x")],
    ["un SyntaxError", new SyntaxError("x")],
    ["un TypeError", new TypeError("x")],
    ["un valor que no es Error", "texto"],
    ["undefined", undefined],
  ])("propaga %s sin clasificarlo", (_name, error) => {
    let thrown: unknown;
    try {
      classifyFailure(error);
    } catch (caught) {
      thrown = caught;
    }
    expect(thrown).toBe(error);
  });
});

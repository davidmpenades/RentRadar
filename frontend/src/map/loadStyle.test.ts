import { describe, expect, it, vi } from "vitest";

import { createStyleLoader, StyleLoadError } from "./loadStyle";
import { MAP_ATTRIBUTION_HTML } from "./style";

const STYLE_URL = "https://tiles.openfreemap.org/styles/positron";
const TIMEOUT_MS = 10_000;
const MAX_CHARS = 1_048_576;

const STYLE = {
  version: 8,
  sources: { vector: { type: "vector", url: "https://tiles.openfreemap.org/planet", attribution: "<b>x</b>" } },
  layers: [{ id: "background", type: "background" }],
};

function jsonResponse(body: string, init: ResponseInit = {}): Response {
  return new Response(body, { status: 200, headers: { "Content-Type": "application/json" }, ...init });
}

// Un solo temporizador: basta para ver si se arma, se cancela y qué espera
function createTimer() {
  let callback: (() => void) | undefined;
  const timer = {
    armedWith: [] as number[],
    cleared: 0,
    setTimer(cb: () => void, ms: number): number {
      callback = cb;
      timer.armedWith.push(ms);
      return 1;
    },
    clearTimer(): void {
      timer.cleared += 1;
      callback = undefined;
    },
    fire(): void {
      callback?.();
    },
  };
  return timer;
}

// Un fetch que respeta la señal: sin respuesta hasta que se aborta
function hangingFetch() {
  return vi.fn((_input: string, init: { signal: AbortSignal }) => {
    return new Promise<Response>((_resolve, reject) => {
      init.signal.addEventListener("abort", () => reject(init.signal.reason), { once: true });
    });
  });
}

function setup(fetch: (input: string, init: { credentials: "omit"; signal: AbortSignal }) => Promise<Response>) {
  const timer = createTimer();
  const load = createStyleLoader({ fetch, setTimer: timer.setTimer, clearTimer: timer.clearTimer, timeoutMs: TIMEOUT_MS });
  return { load, timer };
}

describe("createStyleLoader", () => {
  it("descarga el estilo sin credenciales y fija la atribución", async () => {
    const fetch = vi.fn(async () => jsonResponse(JSON.stringify(STYLE)));
    const { load, timer } = setup(fetch);
    const signal = new AbortController().signal;

    const style = await load(STYLE_URL, signal);

    expect(fetch).toHaveBeenCalledTimes(1);
    const [url, init] = fetch.mock.calls[0] as unknown as [string, { credentials: string; signal: AbortSignal }];
    expect(url).toBe(STYLE_URL);
    expect(init.credentials).toBe("omit");
    expect(init.signal).toBeInstanceOf(AbortSignal);
    expect((style.sources.vector as { attribution: string }).attribution).toBe(MAP_ATTRIBUTION_HTML);
    expect(timer.armedWith).toEqual([TIMEOUT_MS]);
    expect(timer.cleared).toBe(1);
  });

  it.each(["application/json", "application/json; charset=utf-8", "Application/JSON;charset=UTF-8"])(
    "acepta el Content-Type %j",
    async (contentType) => {
      const { load } = setup(async () => jsonResponse(JSON.stringify(STYLE), { headers: { "Content-Type": contentType } }));
      await expect(load(STYLE_URL, new AbortController().signal)).resolves.toBeDefined();
    },
  );

  it.each([
    ["text/html", new Response(JSON.stringify(STYLE), { headers: { "Content-Type": "text/html" } })],
    ["application/jsonp", new Response(JSON.stringify(STYLE), { headers: { "Content-Type": "application/jsonp" } })],
    ["sin Content-Type", new Response(new TextEncoder().encode(JSON.stringify(STYLE)))],
  ])("rechaza %s", async (_name, response) => {
    const { load } = setup(async () => response);
    await expect(load(STYLE_URL, new AbortController().signal)).rejects.toBeInstanceOf(StyleLoadError);
  });

  it.each([404, 500, 429, 204])("rechaza el estado %d", async (status) => {
    const { load } = setup(async () => new Response(status === 204 ? null : JSON.stringify(STYLE), { status, headers: { "Content-Type": "application/json" } }));
    await expect(load(STYLE_URL, new AbortController().signal)).rejects.toBeInstanceOf(StyleLoadError);
  });

  it("rechaza un JSON roto", async () => {
    const { load } = setup(async () => jsonResponse("{\"version\": 8,"));
    await expect(load(STYLE_URL, new AbortController().signal)).rejects.toBeInstanceOf(StyleLoadError);
  });

  it.each([
    ["una versión distinta", { ...STYLE, version: 7 }],
    ["sin capas", { version: 8, sources: {} }],
    ["una lista", []],
  ])("rechaza un estilo con %s", async (_name, style) => {
    const { load } = setup(async () => jsonResponse(JSON.stringify(style)));
    await expect(load(STYLE_URL, new AbortController().signal)).rejects.toBeInstanceOf(StyleLoadError);
  });

  function styleOfLength(length: number): string {
    const base = JSON.stringify({ ...STYLE, metadata: "" });
    return JSON.stringify({ ...STYLE, metadata: "a".repeat(length - base.length) });
  }

  it("acepta un texto de exactamente 1 MiB", async () => {
    const body = styleOfLength(MAX_CHARS);
    expect(body.length).toBe(MAX_CHARS);
    const { load } = setup(async () => jsonResponse(body));
    await expect(load(STYLE_URL, new AbortController().signal)).resolves.toBeDefined();
  });

  it("rechaza un texto que pasa de 1 MiB", async () => {
    const body = styleOfLength(MAX_CHARS + 1);
    expect(body.length).toBe(MAX_CHARS + 1);
    const { load, timer } = setup(async () => jsonResponse(body));
    await expect(load(STYLE_URL, new AbortController().signal)).rejects.toBeInstanceOf(StyleLoadError);
    expect(timer.cleared).toBe(1);
  });

  it("agota el tiempo a los 10 s aunque la respuesta no llegue", async () => {
    const fetch = hangingFetch();
    const { load, timer } = setup(fetch);

    const result = load(STYLE_URL, new AbortController().signal);
    const outcome = expect(result).rejects.toBeInstanceOf(StyleLoadError);
    timer.fire();

    await outcome;
    expect(timer.armedWith).toEqual([TIMEOUT_MS]);
    const init = fetch.mock.calls[0]![1];
    expect(init.signal.aborted).toBe(true);
    expect(timer.cleared).toBe(1);
  });

  it("agota el tiempo si el cuerpo nunca llega", async () => {
    const { load, timer } = setup(async (_url, init) => {
      const body = new ReadableStream<Uint8Array>({
        start(controller) {
          init.signal.addEventListener("abort", () => controller.error(init.signal.reason), { once: true });
        },
      });
      return new Response(body, { status: 200, headers: { "Content-Type": "application/json" } });
    });

    const outcome = expect(load(STYLE_URL, new AbortController().signal)).rejects.toBeInstanceOf(StyleLoadError);
    await Promise.resolve();
    timer.fire();

    await outcome;
  });

  it("propaga un fallo de red sin esconderlo", async () => {
    const { load, timer } = setup(async () => {
      throw new TypeError("Failed to fetch");
    });
    await expect(load(STYLE_URL, new AbortController().signal)).rejects.toBeInstanceOf(TypeError);
    expect(timer.cleared).toBe(1);
  });

  it("no pide nada si la señal ya está abortada", async () => {
    const fetch = vi.fn(async () => jsonResponse(JSON.stringify(STYLE)));
    const { load, timer } = setup(fetch);
    const controller = new AbortController();
    controller.abort();

    await expect(load(STYLE_URL, controller.signal)).rejects.toMatchObject({ name: "AbortError" });
    expect(fetch).not.toHaveBeenCalled();
    expect(timer.armedWith).toEqual([]);
  });

  it("aborta la petición y no la da por tiempo agotado si cancela quien pide", async () => {
    const fetch = hangingFetch();
    const { load, timer } = setup(fetch);
    const controller = new AbortController();

    const outcome = expect(load(STYLE_URL, controller.signal)).rejects.toMatchObject({ name: "AbortError" });
    controller.abort();

    await outcome;
    expect(timer.cleared).toBe(1);
  });

  it("el error propio lleva un mensaje fijo sin la dirección", async () => {
    const { load } = setup(async () => jsonResponse("no es json"));
    const error = await load(STYLE_URL, new AbortController().signal).catch((e: unknown) => e);
    expect((error as StyleLoadError).message).not.toContain("openfreemap");
  });
});

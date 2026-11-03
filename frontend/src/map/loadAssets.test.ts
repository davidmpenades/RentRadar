import { describe, expect, it, vi } from "vitest";

import {
  HttpStatusError,
  NetworkError,
  RequestTimeoutError,
} from "../api/publicAssets";
import { InvalidResponseError } from "../api/validate";
import { loadAssetsForView } from "./loadAssets";
import { requestBox, type RequestBox } from "./requestBox";

const VALENCIA = { south: 39.35, west: -0.6, north: 39.6, east: -0.15 };

const ASSET = {
  public_id: "3f0c1f2e-5b7a-4c1d-9e8f-0a1b2c3d4e5f",
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
const LIST = { results: [ASSET], incomplete: false };

type Fetch = (box: RequestBox, signal: AbortSignal) => Promise<typeof LIST>;

function setup(options: { fetch?: Fetch } = {}) {
  const controller = new AbortController();
  const state = { current: true };
  const fetchAssets = vi.fn(options.fetch ?? (async () => LIST));
  const show = vi.fn();
  const clear = vi.fn();
  const logError = vi.fn();
  const run = (bounds = VALENCIA) =>
    loadAssetsForView({
      bounds,
      request: { signal: controller.signal, isCurrent: () => state.current },
      fetchAssets,
      show,
      clear,
      logError,
    });
  return { run, state, controller, fetchAssets, show, clear, logError };
}

describe("loadAssetsForView", () => {
  it("pide el cuadro calculado con la señal de la petición y pinta lo que llega", async () => {
    const { run, fetchAssets, show, clear, controller } = setup();

    await run();

    const result = requestBox(VALENCIA);
    expect(result.kind).toBe("ok");
    expect(fetchAssets).toHaveBeenCalledExactlyOnceWith(result.kind === "ok" ? result.box : null, controller.signal);
    expect(show).toHaveBeenCalledExactlyOnceWith([ASSET]);
    expect(clear).not.toHaveBeenCalled();
  });

  it("pinta una lista vacía como lista vacía, sin vaciar", async () => {
    const { run, show, clear } = setup({ fetch: async () => ({ results: [], incomplete: false }) });
    await run();
    expect(show).toHaveBeenCalledExactlyOnceWith([]);
    expect(clear).not.toHaveBeenCalled();
  });

  it("no pinta la respuesta de una petición que ya no es la actual", async () => {
    const { run, state, show, clear, logError } = setup();
    state.current = false;

    await run();

    expect(show).not.toHaveBeenCalled();
    expect(clear).not.toHaveBeenCalled();
    expect(logError).not.toHaveBeenCalled();
  });

  it("comprueba la vigencia al llegar la respuesta, no al pedir", async () => {
    let resolve: (list: typeof LIST) => void = () => {};
    const { run, state, show } = setup({ fetch: () => new Promise((r) => (resolve = r)) });

    const pending = run();
    state.current = false;
    resolve(LIST);
    await pending;

    expect(show).not.toHaveBeenCalled();
  });

  it.each([
    ["demasiado grande", { south: 30, west: -10, north: 50, east: 10 }],
    ["fuera de rango en latitud", { south: 84, west: 0, north: 85, east: 0.5 }],
    ["fuera de rango en longitud", { south: 0, west: 179.9, north: 0.5, east: 180 }],
  ])("vacía los círculos y no pide si el cuadro es %s", async (_name, bounds) => {
    const { run, fetchAssets, show, clear } = setup();
    await run(bounds);
    expect(fetchAssets).not.toHaveBeenCalled();
    expect(show).not.toHaveBeenCalled();
    expect(clear).toHaveBeenCalledTimes(1);
  });

  it.each([
    ["servidor", new HttpStatusError(500)],
    ["límite", new HttpStatusError(429)],
    ["red", new NetworkError()],
    ["tiempo agotado", new RequestTimeoutError()],
    ["respuesta no válida", new InvalidResponseError()],
  ])("vacía los círculos, sin registrar nada, si falla por %s", async (_name, error) => {
    const { run, show, clear, logError } = setup({ fetch: async () => Promise.reject(error) });
    await run();
    expect(clear).toHaveBeenCalledTimes(1);
    expect(show).not.toHaveBeenCalled();
    expect(logError).not.toHaveBeenCalled();
  });

  it("vacía los círculos y registra un error que classifyFailure no clasifica", async () => {
    const bug = new TypeError("fallo del código");
    const { run, show, clear, logError } = setup({ fetch: async () => Promise.reject(bug) });
    await run();
    expect(clear).toHaveBeenCalledTimes(1);
    expect(logError).toHaveBeenCalledExactlyOnceWith(bug);
    expect(show).not.toHaveBeenCalled();
  });

  it("no hace nada al cancelar la petición", async () => {
    const abort = new DOMException("Aborted", "AbortError");
    const { run, show, clear, logError } = setup({ fetch: async () => Promise.reject(abort) });
    await run();
    expect(show).not.toHaveBeenCalled();
    expect(clear).not.toHaveBeenCalled();
    expect(logError).not.toHaveBeenCalled();
  });

  it("ignora el fallo de una petición que ya no es la actual", async () => {
    const { run, state, show, clear, logError } = setup({ fetch: async () => Promise.reject(new NetworkError()) });
    state.current = false;
    await run();
    expect(show).not.toHaveBeenCalled();
    expect(clear).not.toHaveBeenCalled();
    expect(logError).not.toHaveBeenCalled();
  });

  it("ignora también un error inesperado de una petición que ya no es la actual", async () => {
    const { run, state, clear, logError } = setup({ fetch: async () => Promise.reject(new TypeError("bug")) });
    state.current = false;
    await run();
    expect(clear).not.toHaveBeenCalled();
    expect(logError).not.toHaveBeenCalled();
  });
});

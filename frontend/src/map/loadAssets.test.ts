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
  const report = vi.fn();
  const logError = vi.fn();
  const run = (bounds = VALENCIA) =>
    loadAssetsForView({
      bounds,
      request: { signal: controller.signal, isCurrent: () => state.current },
      fetchAssets,
      report,
      logError,
    });
  return { run, state, controller, fetchAssets, report, logError };
}

describe("loadAssetsForView", () => {
  it("pide el cuadro calculado con la señal de la petición y reporta la lista con la zona visible", async () => {
    const { run, fetchAssets, report, controller } = setup();

    await run();

    const result = requestBox(VALENCIA);
    expect(result.kind).toBe("ok");
    expect(fetchAssets).toHaveBeenCalledExactlyOnceWith(result.kind === "ok" ? result.box : null, controller.signal);
    expect(report).toHaveBeenCalledExactlyOnceWith({ kind: "loaded", list: LIST, visibleBounds: VALENCIA });
  });

  it("guarda la zona visible que recibe y no el cuadro pedido", async () => {
    const { run, report } = setup();
    await run();
    const reported = report.mock.calls[0]![0];
    expect(reported.visibleBounds).toEqual(VALENCIA);
  });

  it("reporta una lista vacía como cargada", async () => {
    const empty = { results: [], incomplete: false };
    const { run, report } = setup({ fetch: async () => empty });
    await run();
    expect(report).toHaveBeenCalledExactlyOnceWith({ kind: "loaded", list: empty, visibleBounds: VALENCIA });
  });

  it("no reporta la respuesta de una petición que ya no es la actual", async () => {
    const { run, state, report, logError } = setup();
    state.current = false;

    await run();

    expect(report).not.toHaveBeenCalled();
    expect(logError).not.toHaveBeenCalled();
  });

  it("comprueba la vigencia al llegar la respuesta, no al pedir", async () => {
    let resolve: (list: typeof LIST) => void = () => {};
    const { run, state, report } = setup({ fetch: () => new Promise((r) => (resolve = r)) });

    const pending = run();
    state.current = false;
    resolve(LIST);
    await pending;

    expect(report).not.toHaveBeenCalled();
  });

  it.each([
    ["demasiado grande", { south: 30, west: -10, north: 50, east: 10 }, "tooLarge"],
    ["fuera de rango en latitud", { south: 84, west: 0, north: 85, east: 0.5 }, "outOfRange"],
    ["fuera de rango en longitud", { south: 0, west: 179.9, north: 0.5, east: 180 }, "outOfRange"],
  ])("no pide y reporta notRequested si el cuadro es %s", async (_name, bounds, reason) => {
    const { run, fetchAssets, report } = setup();
    await run(bounds);
    expect(fetchAssets).not.toHaveBeenCalled();
    expect(report).toHaveBeenCalledExactlyOnceWith({ kind: "notRequested", reason });
  });

  it("reporta notRequested antes de ceder el control, sin pasar por una espera", async () => {
    const { run, report } = setup();
    const pending = run({ south: 30, west: -10, north: 50, east: 10 });
    expect(report).toHaveBeenCalledTimes(1);
    await pending;
  });

  it.each([
    ["servidor", new HttpStatusError(500), "server"],
    ["límite", new HttpStatusError(429), "throttled"],
    ["red", new NetworkError(), "network"],
    ["tiempo agotado", new RequestTimeoutError(), "timeout"],
    ["respuesta no válida", new InvalidResponseError(), "invalid"],
  ])("reporta el fallo, sin registrar nada, si falla por %s", async (_name, error, failure) => {
    const { run, report, logError } = setup({ fetch: async () => Promise.reject(error) });
    await run();
    expect(report).toHaveBeenCalledExactlyOnceWith({ kind: "failed", failure });
    expect(logError).not.toHaveBeenCalled();
  });

  it("reporta unexpected y registra un error que classifyFailure no clasifica", async () => {
    const bug = new TypeError("fallo del código");
    const { run, report, logError } = setup({ fetch: async () => Promise.reject(bug) });
    await run();
    expect(report).toHaveBeenCalledExactlyOnceWith({ kind: "failed", failure: "unexpected" });
    expect(logError).toHaveBeenCalledExactlyOnceWith(bug);
  });

  it("no hace nada al cancelar la petición", async () => {
    const abort = new DOMException("Aborted", "AbortError");
    const { run, report, logError } = setup({ fetch: async () => Promise.reject(abort) });
    await run();
    expect(report).not.toHaveBeenCalled();
    expect(logError).not.toHaveBeenCalled();
  });

  it("ignora el fallo de una petición que ya no es la actual", async () => {
    const { run, state, report, logError } = setup({ fetch: async () => Promise.reject(new NetworkError()) });
    state.current = false;
    await run();
    expect(report).not.toHaveBeenCalled();
    expect(logError).not.toHaveBeenCalled();
  });

  it("ignora también un error inesperado de una petición que ya no es la actual", async () => {
    const { run, state, report, logError } = setup({ fetch: async () => Promise.reject(new TypeError("bug")) });
    state.current = false;
    await run();
    expect(report).not.toHaveBeenCalled();
    expect(logError).not.toHaveBeenCalled();
  });
});

import { describe, expect, it } from "vitest";

import type { FailureKind } from "../api/publicAssets";
import type { components } from "../api/schema.gen";
import { INITIAL_REQUEST, requestCircles, startLoading, viewState, type RequestState } from "./viewState";

type PublicAsset = components["schemas"]["PublicAsset"];

const VISIBLE = { south: 39.4, north: 39.5, west: -0.45, east: -0.3 };

function asset(n: number, overrides: Partial<PublicAsset> = {}): PublicAsset {
  return {
    public_id: `3f0c1f2e-5b7a-4c1d-9e8f-0a1b2c3d4e${String(n).padStart(2, "0")}`,
    title: `Bien ${n}`,
    category_slug: "kayak",
    category_name: "Kayak",
    price: "12.50",
    currency: "EUR",
    price_unit: "day",
    privacy_radius: 500,
    latitude: 39.45,
    longitude: -0.37,
    ...overrides,
  };
}

// Un círculo de 500 m a unos 5 km al norte de la zona visible: no se ve
const FAR = { latitude: 39.55, longitude: -0.37 };

function loaded(results: PublicAsset[], incomplete = false) {
  return { kind: "loaded", list: { results, incomplete }, visibleBounds: VISIBLE } as const;
}

const view = (request: RequestState, options: { styleFailed?: boolean; atInitialView?: boolean } = {}) =>
  viewState({ styleFailed: false, atInitialView: false, request, ...options });

describe("viewState", () => {
  it("es loading mientras se espera la respuesta", () => {
    expect(view(INITIAL_REQUEST)).toEqual({ kind: "loading" });
  });

  it("en loading no deriva tarjetas de la respuesta anterior", () => {
    const request = startLoading(loaded([asset(1), asset(2)]));
    expect(view(request)).toEqual({ kind: "loading" });
  });

  it("es results con las tarjetas en el orden de la respuesta", () => {
    const first = asset(1);
    const second = asset(2, { latitude: 39.41 });
    expect(view(loaded([second, first]))).toEqual({ kind: "results", cards: [second, first], incomplete: false });
  });

  it("conserva el indicador de lista incompleta", () => {
    expect(view(loaded([asset(1)], true))).toMatchObject({ kind: "results", incomplete: true });
  });

  it("deja fuera de las tarjetas el bien cuyo círculo no toca la zona visible", () => {
    const visible = asset(1);
    const hidden = asset(2, FAR);
    expect(view(loaded([hidden, visible]))).toMatchObject({ kind: "results", cards: [visible] });
  });

  it("es empty con una respuesta válida sin bienes", () => {
    expect(view(loaded([]))).toEqual({ kind: "empty", canReset: true });
  });

  it("es empty si hay bienes pero ninguno se ve en la zona visible", () => {
    expect(view(loaded([asset(1, FAR), asset(2, FAR)]))).toEqual({ kind: "empty", canReset: true });
  });

  it.each(["tooLarge", "outOfRange"] as const)("es zoomIn si el cuadro no se pide (%s)", (reason) => {
    expect(view({ kind: "notRequested", reason })).toEqual({ kind: "zoomIn", canReset: true });
  });

  it("no ofrece volver a la zona inicial si ya está en ella, ni en vacío ni en zoomIn", () => {
    expect(view(loaded([]), { atInitialView: true })).toEqual({ kind: "empty", canReset: false });
    expect(view({ kind: "notRequested", reason: "tooLarge" }, { atInitialView: true })).toEqual({
      kind: "zoomIn",
      canReset: false,
    });
  });

  it.each<FailureKind | "unexpected">(["network", "timeout", "server", "throttled", "invalid", "unexpected"])(
    "es error con el tipo %s",
    (failure) => {
      expect(view({ kind: "failed", failure })).toEqual({ kind: "error", failure });
    },
  );

  it("con el estilo fallido solo es styleError, sea cual sea la petición", () => {
    const requests: RequestState[] = [
      INITIAL_REQUEST,
      startLoading(loaded([asset(1)])),
      loaded([asset(1)]),
      loaded([]),
      { kind: "notRequested", reason: "tooLarge" },
      { kind: "failed", failure: "network" },
    ];
    for (const request of requests) {
      expect(view(request, { styleFailed: true })).toEqual({ kind: "styleError" });
    }
  });
});

describe("requestCircles", () => {
  it("dibuja todos los bienes de la respuesta, también los que no tienen tarjeta, y junta los de la misma celda", () => {
    const circles = requestCircles(loaded([asset(1), asset(2), asset(3, FAR)]));
    expect(circles).toHaveLength(2);
  });

  it("mientras se espera una respuesta nueva conserva los círculos de la última cargada", () => {
    const previous = loaded([asset(1), asset(3, FAR)]);
    expect(requestCircles(startLoading(previous))).toEqual(requestCircles(previous));
    expect(requestCircles(startLoading(previous))).toHaveLength(2);
  });

  it.each<[string, RequestState]>([
    ["loading sin respuesta previa", INITIAL_REQUEST],
    ["notRequested", { kind: "notRequested", reason: "outOfRange" }],
    ["failed", { kind: "failed", failure: "server" }],
  ])("no dibuja nada en %s", (_name, request) => {
    expect(requestCircles(request)).toEqual([]);
  });
});

describe("startLoading", () => {
  const previous = loaded([asset(1)]);

  it("guarda la respuesta cargada al empezar una petición", () => {
    expect(startLoading(previous)).toEqual({ kind: "loading", previous });
  });

  it("no pierde la última respuesta cargada si empieza otra petición mientras se espera", () => {
    const second = startLoading(startLoading(previous));
    expect(second).toEqual({ kind: "loading", previous });
    expect(startLoading(second)).toEqual({ kind: "loading", previous });
  });

  it("no inventa una respuesta previa sin ninguna cargada", () => {
    expect(startLoading(INITIAL_REQUEST)).toEqual({ kind: "loading", previous: null });
  });

  it.each<[string, RequestState]>([
    ["failed", { kind: "failed", failure: "network" }],
    ["notRequested", { kind: "notRequested", reason: "tooLarge" }],
  ])("tras %s no hay respuesta previa que conservar", (_name, request) => {
    expect(startLoading(request)).toEqual({ kind: "loading", previous: null });
    expect(requestCircles(startLoading(request))).toEqual([]);
  });

  it("tras un fallo con una respuesta cargada antes, la anterior ya se perdió", () => {
    const failed: RequestState = { kind: "failed", failure: "timeout" };
    expect(startLoading(failed)).toEqual({ kind: "loading", previous: null });
  });
});

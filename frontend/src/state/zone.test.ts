import { describe, expect, it } from "vitest";

import { loadAssetsForView, type RequestOutcome } from "../map/loadAssets";
import { requestBox } from "../map/requestBox";
import { circleKey } from "../map/circles";
import { requestCircles, viewState } from "./viewState";

const VISIBLE = { south: 39.4, west: -0.45, north: 39.5, east: -0.3 };
const METERS_PER_DEGREE = 111_195.08;

const base = {
  category_slug: "kayak",
  category_name: "Kayak",
  price: "12.50",
  currency: "EUR",
  price_unit: "day",
  privacy_radius: 500,
  longitude: -0.375,
} as const;
const INSIDE = { ...base, public_id: "3f0c1f2e-5b7a-4c1d-9e8f-0a1b2c3d4e01", title: "Dentro", latitude: 39.45 };
// 1,5 km al norte del borde visible, con un círculo de 500 m: cabe en el cuadro pedido y no toca la zona visible
const OUTSIDE = {
  ...base,
  public_id: "3f0c1f2e-5b7a-4c1d-9e8f-0a1b2c3d4e02",
  title: "Fuera",
  latitude: 39.5 + 1500 / METERS_PER_DEGREE,
};

describe("la zona de las tarjetas y la de los círculos", () => {
  it("un bien dentro del cuadro pedido con el círculo fuera de la zona visible tiene círculo y no tarjeta", async () => {
    const box = requestBox(VISIBLE);
    if (box.kind !== "ok") throw new Error("el cuadro debería pedirse");
    // El bien está de verdad dentro del cuadro pedido, que se amplía 2 km
    expect(OUTSIDE.latitude).toBeLessThanOrEqual(box.box.north / 20);

    let outcome: RequestOutcome | undefined;
    await loadAssetsForView({
      bounds: VISIBLE,
      request: { signal: new AbortController().signal, isCurrent: () => true },
      fetchAssets: async () => ({ results: [INSIDE, OUTSIDE], incomplete: false }),
      report: (reported) => {
        outcome = reported;
      },
      logError: () => {},
    });
    if (!outcome) throw new Error("no se ha reportado nada");

    const view = viewState({ styleFailed: false, request: outcome, atInitialView: true });
    expect(view.kind).toBe("results");
    expect(view.kind === "results" ? view.cards.map((card) => card.title) : []).toEqual(["Dentro"]);

    const circleKeys = requestCircles(outcome).map((circle) => circle.key);
    expect(circleKeys).toEqual([circleKey(INSIDE), circleKey(OUTSIDE)]);
  });
});

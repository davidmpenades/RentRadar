import { describe, expect, it } from "vitest";

import { atInitialView, INITIAL_CENTER, INITIAL_ZOOM } from "./viewport";

const initial = { ...INITIAL_CENTER, zoom: INITIAL_ZOOM };

describe("atInitialView", () => {
  it("es verdad en la vista inicial exacta", () => {
    expect(atInitialView(initial)).toBe(true);
  });

  it("tolera 1e-6 grados de centro y 0,01 de zoom", () => {
    expect(atInitialView({ ...initial, latitude: initial.latitude + 9e-7 })).toBe(true);
    expect(atInitialView({ ...initial, longitude: initial.longitude - 9e-7 })).toBe(true);
    expect(atInitialView({ ...initial, zoom: initial.zoom + 0.009 })).toBe(true);
    expect(atInitialView({ ...initial, zoom: initial.zoom - 0.009 })).toBe(true);
  });

  it("es falsa si se mueve más que la tolerancia en cada eje", () => {
    expect(atInitialView({ ...initial, latitude: initial.latitude + 2e-6 })).toBe(false);
    expect(atInitialView({ ...initial, longitude: initial.longitude + 2e-6 })).toBe(false);
    expect(atInitialView({ ...initial, zoom: initial.zoom + 0.02 })).toBe(false);
    expect(atInitialView({ ...initial, zoom: initial.zoom - 0.02 })).toBe(false);
  });
});

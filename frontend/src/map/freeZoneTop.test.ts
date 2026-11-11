import { describe, expect, it } from "vitest";

import { freeZoneTop } from "./freeZoneTop";

describe("freeZoneTop", () => {
  it("sin controles no reserva nada", () => {
    expect(freeZoneTop(null, 56)).toBe(0);
  });

  it("deja 8 px bajo los controles, contados desde el borde superior de la zona", () => {
    expect(freeZoneTop(160, 56)).toBe(112);
  });

  it("sube al píxel entero siguiente: un decimal sobrante no deja el aviso pegado a los controles", () => {
    expect(freeZoneTop(160.2, 56)).toBe(113);
  });

  it("un decimal en el borde superior de la zona también sube al entero siguiente", () => {
    expect(freeZoneTop(160, 56.5)).toBe(112);
    expect(freeZoneTop(160, 55.5)).toBe(113);
  });

  it("un valor ya entero no suma otro píxel", () => {
    expect(freeZoneTop(100, 0)).toBe(108);
  });
});

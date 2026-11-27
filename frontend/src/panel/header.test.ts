import { describe, expect, it } from "vitest";

import { headerText, statusText } from "./header";

describe("headerText", () => {
  it("dice «1 bien» en singular con la lista completa", () => {
    expect(headerText(1, false, false)).toBe("1 bien en esta zona");
  });

  it.each([2, 24, 200])("dice «%d bienes» con la lista completa", (count) => {
    expect(headerText(count, false, false)).toBe(`${count} bienes en esta zona`);
  });

  it("avisa de que puede haber más con la lista incompleta", () => {
    expect(headerText(40, true, false)).toBe("Mostrando 40 bienes. Puede haber más: acerca el mapa para verlos todos");
  });

  it("usa el singular también con la lista incompleta y una sola tarjeta", () => {
    expect(headerText(1, true, false)).toBe("Mostrando 1 bien. Puede haber más: acerca el mapa para verlos todos");
  });

  // Rojo si: headerText ignora filtered y el número o el aviso de lista incompleta salen sin «con estos filtros»
  it.each([
    [1, false, "1 bien en esta zona con estos filtros"],
    [24, false, "24 bienes en esta zona con estos filtros"],
    [1, true, "Mostrando 1 bien con estos filtros. Puede haber más: acerca el mapa para verlos todos"],
    [40, true, "Mostrando 40 bienes con estos filtros. Puede haber más: acerca el mapa para verlos todos"],
  ])("con filtros, %d con la lista incompleta %s dice «%s»", (count, incomplete, expected) => {
    expect(headerText(count, incomplete, true)).toBe(expected);
  });
});

describe("statusText", () => {
  const card = {
    public_id: "3f0c1f2e-5b7a-4c1d-9e8f-0a1b2c3d4e5f",
    title: "Kayak",
    category_slug: "kayak",
    category_name: "Kayak",
    price: "9.00",
    currency: "EUR",
    price_unit: "hour",
    privacy_radius: 500,
    latitude: 39.46,
    longitude: -0.37,
  } as const;

  it.each([
    [{ kind: "loading" }, "Buscando bienes…"],
    [{ kind: "results", cards: [card], incomplete: false, filtered: false }, "1 bien en esta zona"],
    [{ kind: "results", cards: [card], incomplete: true, filtered: false }, "Mostrando 1 bien. Puede haber más: acerca el mapa para verlos todos"],
    [{ kind: "empty", canReset: true, filtered: false }, "No hay bienes en esta zona"],
    [{ kind: "zoomIn", canReset: false }, "Acerca el mapa para ver los bienes"],
    [{ kind: "error", failure: "network" }, "No hay conexión. Comprueba tu red y vuelve a intentarlo."],
    [{ kind: "error", failure: "timeout" }, "El servidor tarda demasiado en responder."],
    [{ kind: "error", failure: "server" }, "Ha habido un problema en el servidor."],
    [{ kind: "error", failure: "throttled" }, "Has hecho muchas búsquedas seguidas. Espera un momento y vuelve a intentarlo."],
    [{ kind: "error", failure: "invalid" }, "No se han podido leer los bienes."],
    [{ kind: "error", failure: "unexpected" }, "Ha ocurrido un error inesperado. Vuelve a intentarlo."],
    [{ kind: "styleError" }, ""],
  ] as const)("%j dice «%s»", (view, expected) => {
    expect(statusText(view)).toBe(expected);
  });

  // Rojo si: statusText ignora filtered y el vacío o los resultados salen con el texto de sin filtros
  it.each([
    ["el vacío", "No hay bienes en esta zona con estos filtros", { kind: "empty", canReset: true, filtered: true }],
    [
      "los resultados",
      "1 bien en esta zona con estos filtros",
      { kind: "results", cards: [card], incomplete: false, filtered: true },
    ],
  ] as const)("con filtros, %s dice «%s»", (_name, expected, view) => {
    expect(statusText(view)).toBe(expected);
  });
});

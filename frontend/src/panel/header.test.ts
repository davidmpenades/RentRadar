import { describe, expect, it } from "vitest";

import { headerText, statusText } from "./header";

describe("headerText", () => {
  it("dice «1 bien» en singular con la lista completa", () => {
    expect(headerText(1, false)).toBe("1 bien en esta zona");
  });

  it.each([2, 24, 200])("dice «%d bienes» con la lista completa", (count) => {
    expect(headerText(count, false)).toBe(`${count} bienes en esta zona`);
  });

  it("avisa de que puede haber más con la lista incompleta", () => {
    expect(headerText(40, true)).toBe("Mostrando 40 bienes. Puede haber más: acerca el mapa para verlos todos");
  });

  it("usa el singular también con la lista incompleta y una sola tarjeta", () => {
    expect(headerText(1, true)).toBe("Mostrando 1 bien. Puede haber más: acerca el mapa para verlos todos");
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
    [{ kind: "results", cards: [card], incomplete: false }, "1 bien en esta zona"],
    [{ kind: "results", cards: [card], incomplete: true }, "Mostrando 1 bien. Puede haber más: acerca el mapa para verlos todos"],
    [{ kind: "empty", canReset: true }, "No hay bienes en esta zona"],
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
});

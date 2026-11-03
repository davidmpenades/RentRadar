import { describe, expect, it } from "vitest";

import { boxToQuery, requestBox, type VisibleBounds } from "./requestBox";

function bounds(south: number, west: number, north: number, east: number): VisibleBounds {
  return { south, west, north, east };
}

// Zona con esquinas a mitad de celda: la ampliación (0,36 celdas) las redondea hacia fuera de forma limpia
function halfCellZone(latitudeCells: number, longitudeCells: number): VisibleBounds {
  return bounds(0.025, 0.025, 0.025 + (latitudeCells - 1) * 0.05, 0.025 + (longitudeCells - 1) * 0.05);
}

function cells(latitudeCells: number, longitudeCells: number) {
  return requestBox(halfCellZone(latitudeCells, longitudeCells));
}

describe("requestBox: ampliación y redondeo", () => {
  it("amplía en latitud 2 km y redondea hacia fuera a celdas de 0,05 grados", () => {
    // 0,5 - 0,017986 = 0,482014 -> 9,64 celdas; 1 + 0,017986 = 1,017986 -> 20,36 celdas
    // 10,036 - 0,017987 = 10,018 -> 200,36; 10,514 + 0,017987 = 10,532 -> 210,64 (cerca del ecuador)
    expect(requestBox(bounds(0.5, 10.036, 1, 10.514))).toEqual({
      kind: "ok",
      box: { south: 9, west: 200, north: 21, east: 211 },
    });
  });

  it("a 60 grados de latitud la ampliación en longitud se duplica (2 km / cos 60)", () => {
    // Latitud más alejada del cuadro ampliado: 61,018 (cos = 0,4845); 2 km son 0,03712 grados de longitud
    // 10,036 - 0,03712 = 9,99888 -> 199,98 celdas; 10,514 + 0,03712 = 10,55112 -> 211,02 celdas
    expect(requestBox(bounds(59, 10.036, 61, 10.514))).toEqual({
      kind: "ok",
      box: { south: 1179, west: 199, north: 1221, east: 212 },
    });
  });

  it("usa la latitud más alejada del ecuador, también en el hemisferio sur", () => {
    expect(requestBox(bounds(-61, 10.036, -59, 10.514))).toEqual({
      kind: "ok",
      box: { south: -1221, west: 199, north: -1179, east: 212 },
    });
  });

  it("usa la latitud más alejada cuando la zona cruza el ecuador", () => {
    // La más alejada es la norte ya ampliada (2,018 grados): 0,018 de margen en longitud
    expect(requestBox(bounds(-1, 5.04, 2, 5.46))).toEqual({
      kind: "ok",
      box: { south: -21, west: 100, north: 41, east: 110 },
    });
  });
});

describe("requestBox: el margen en longitud usa la latitud del cuadro ya ampliado", () => {
  it("a 80 grados el borde ampliado (80,018) mueve el índice oeste y el este", () => {
    // Margen en longitud con 80,018: 0,017986 / 0,17334 = 0,103764 grados = 2,07529 celdas
    // oeste: 5,103665 * 20 = 102,0733 celdas; 102,0733 - 2,07529 = 99,998 -> 99
    // este: 7,39633 * 20 = 147,9266 celdas; 147,9266 + 2,07529 = 150,002 -> 151
    // Con la latitud de la zona visible (80) el margen sería 2,07159 celdas: 100,002 -> 100 y 149,998 -> 150
    expect(requestBox(bounds(79.5, 5.103665, 80, 7.39633))).toEqual({
      kind: "ok",
      box: { south: 1589, west: 99, north: 1601, east: 151 },
    });
  });

  it("a 85 grados el borde ampliado (84,978) mueve el índice oeste y el este", () => {
    // Margen en longitud con 84,978: 0,017986 / 0,087538 = 0,205469 grados = 4,10937 celdas
    // oeste: 0,7051 * 20 = 14,102 celdas; 14,102 - 4,10937 = 9,9926 -> 9
    // este: 0,7949 * 20 = 15,898 celdas; 15,898 + 4,10937 = 20,0074 -> 21
    // Con la latitud de la zona visible (84,96) el margen sería 4,09474 celdas: 10,0073 -> 10 y 19,9927 -> 20
    expect(requestBox(bounds(84.5, 0.7051, 84.96, 0.7949))).toEqual({
      kind: "ok",
      box: { south: 1689, west: 9, north: 1700, east: 21 },
    });
  });
});

describe("requestBox: tamaño máximo en celdas", () => {
  it("acepta 2200 celdas (5,5 grados cuadrados)", () => {
    expect(cells(40, 55)).toEqual({ kind: "ok", box: { south: 0, west: 0, north: 40, east: 55 } });
  });

  it("acepta una sola celda de alto con 2200 de ancho y rechaza 2201", () => {
    expect(cells(1, 2200)).toEqual({ kind: "ok", box: { south: 0, west: 0, north: 1, east: 2200 } });
    expect(cells(1, 2201)).toEqual({ kind: "tooLarge" });
  });

  it("rechaza 2201 celdas con una forma más cuadrada (31 por 71)", () => {
    expect(cells(31, 71)).toEqual({ kind: "tooLarge" });
  });

  it("rechaza 6 grados cuadrados (2400 celdas): el margen del cliente", () => {
    expect(cells(48, 50)).toEqual({ kind: "tooLarge" });
  });

  it("rechaza 6,3 grados cuadrados (2520 celdas)", () => {
    expect(cells(42, 60)).toEqual({ kind: "tooLarge" });
  });
});

describe("requestBox: fuera de rango", () => {
  it("acepta el borde de 85 grados de latitud: el índice 1700 es el último", () => {
    expect(requestBox(bounds(84.5, 0, 84.96, 1))).toEqual({
      kind: "ok",
      box: { south: 1689, west: -5, north: 1700, east: 25 },
    });
    expect(requestBox(bounds(-84.96, 0, -84.5, 1))).toEqual({
      kind: "ok",
      box: { south: -1700, west: -5, north: -1689, east: 25 },
    });
  });

  it("no pide si el cuadro ampliado pasa de 85 grados de latitud", () => {
    expect(requestBox(bounds(84.5, 0, 84.99, 1))).toEqual({ kind: "outOfRange" });
    expect(requestBox(bounds(-84.99, 0, -84.5, 1))).toEqual({ kind: "outOfRange" });
  });

  it("acepta el borde de 180 grados de longitud: el índice 3600 es el último", () => {
    expect(requestBox(bounds(0, 179, 1, 179.96))).toEqual({
      kind: "ok",
      box: { south: -1, west: 3579, north: 21, east: 3600 },
    });
    expect(requestBox(bounds(0, -179.96, 1, -179))).toEqual({
      kind: "ok",
      box: { south: -1, west: -3600, north: 21, east: -3579 },
    });
  });

  it("no pide si el cuadro ampliado pasa de 180 grados de longitud", () => {
    expect(requestBox(bounds(0, 179, 1, 179.99))).toEqual({ kind: "outOfRange" });
    expect(requestBox(bounds(0, -179.99, 1, -179))).toEqual({ kind: "outOfRange" });
  });

  it("no pide si el mapa muestra más de una vuelta al mundo", () => {
    expect(requestBox(bounds(0, -181, 1, 0))).toEqual({ kind: "outOfRange" });
    expect(requestBox(bounds(0, 0, 1, 181))).toEqual({ kind: "outOfRange" });
  });

  it("no pide si la zona cruza el antimeridiano (oeste mayor que este)", () => {
    expect(requestBox(bounds(0, 179, 1, -179))).toEqual({ kind: "outOfRange" });
  });

  it("no pide con la zona invertida en latitud", () => {
    expect(requestBox(bounds(2, 0, 1, 1))).toEqual({ kind: "outOfRange" });
  });

  it("no pide cerca de los polos y no calcula la longitud con coseno cero", () => {
    expect(requestBox(bounds(89, 0, 90, 1))).toEqual({ kind: "outOfRange" });
    expect(requestBox(bounds(89, 0, 91, 1))).toEqual({ kind: "outOfRange" });
    expect(requestBox(bounds(-90, 0, -89, 1))).toEqual({ kind: "outOfRange" });
  });

  it.each([
    ["sur NaN", bounds(Number.NaN, 0, 1, 1)],
    ["oeste NaN", bounds(0, Number.NaN, 1, 1)],
    ["norte infinito", bounds(0, 0, Number.POSITIVE_INFINITY, 1)],
    ["este infinito negativo", bounds(0, 0, 1, Number.NEGATIVE_INFINITY)],
  ])("no pide con un valor no finito: %s", (_name, visible) => {
    expect(requestBox(visible)).toEqual({ kind: "outOfRange" });
  });

  it("acepta una zona de altura y anchura cero", () => {
    expect(requestBox(bounds(40, 3, 40, 3)).kind).toBe("ok");
  });
});

describe("boxToQuery", () => {
  it("da south, west, north y east, en ese orden, con dos decimales", () => {
    expect(boxToQuery({ south: 9, west: 200, north: 21, east: 211 })).toBe(
      "south=0.45&west=10.00&north=1.05&east=10.55",
    );
  });

  it("escribe el signo y la parte entera desde el entero", () => {
    expect(boxToQuery({ south: -1221, west: -1, north: 1, east: 3600 })).toBe(
      "south=-61.05&west=-0.05&north=0.05&east=180.00",
    );
  });

  it.each([
    [0, "0.00"],
    [1, "0.05"],
    [2, "0.10"],
    [19, "0.95"],
    [20, "1.00"],
    [33, "1.65"],
    [-1, "-0.05"],
    [-20, "-1.00"],
    [-1700, "-85.00"],
    [1700, "85.00"],
    [-3600, "-180.00"],
  ])("el índice %i sale como %s", (index, text) => {
    expect(boxToQuery({ south: index, west: 0, north: 0, east: 0 })).toBe(
      `south=${text}&west=0.00&north=0.00&east=0.00`,
    );
  });

  it("el índice cero sale como 0.00, nunca -0.00, también con cero negativo", () => {
    expect(boxToQuery({ south: -0, west: -0, north: -0, east: -0 })).toBe(
      "south=0.00&west=0.00&north=0.00&east=0.00",
    );
  });

  it("un cuadro que sale de un redondeo a cero negativo se escribe sin signo", () => {
    // 0,03 al sur del ecuador más 2 km es 0,24 celdas bajo cero: ceil da -0
    const result = requestBox(bounds(-0.5, 0, -0.03, 0.5));
    expect(result.kind).toBe("ok");
    if (result.kind !== "ok") return;
    expect(boxToQuery(result.box)).toBe("south=-0.55&west=-0.05&north=0.00&east=0.55");
  });

  it("una zona real da la cadena esperada, calculada a mano", () => {
    // 39,3 - 0,018 = 39,282 -> 785 (39.25); 39,6 + 0,018 = 39,618 -> 792,36 -> 793 (39.65)
    // Margen en longitud con 39,618 (cos = 0,7703): 0,02335; -0,5 - 0,02335 -> -10,47 -> -11; -0,2 + 0,02335 -> -3,53 -> -3
    const result = requestBox(bounds(39.3, -0.5, 39.6, -0.2));
    expect(result.kind).toBe("ok");
    if (result.kind !== "ok") return;
    expect(boxToQuery(result.box)).toBe("south=39.25&west=-0.55&north=39.65&east=-0.15");
  });
});

import { describe, expect, it } from "vitest";

import openapi from "../../../backend/openapi.json";
import {
  InvalidResponseError,
  publicAssetListSchema,
  publicAssetSchema,
  validateResponse,
} from "./validate";

type Json = Record<string, unknown>;

function asset(overrides: Json = {}): Json {
  return {
    public_id: crypto.randomUUID(),
    title: "Kayak doble",
    category_slug: "kayak",
    category_name: "Kayak",
    price: "12.50",
    currency: "EUR",
    price_unit: "day",
    privacy_radius: 1000,
    latitude: 39.469912,
    longitude: -0.376288,
    ...overrides,
  };
}

function withoutKey(item: Json, key: string): Json {
  return Object.fromEntries(Object.entries(item).filter(([name]) => name !== key));
}

function list(results: unknown[], extra: Json = {}): Json {
  return { results, incomplete: false, ...extra };
}

function assets(count: number): Json[] {
  return Array.from({ length: count }, () => asset());
}

describe("validateResponse: respuestas válidas", () => {
  it.each([0, 1, 200])("acepta %i bienes", (count) => {
    const body = list(assets(count));
    expect(validateResponse(body)).toEqual(body);
  });

  it("acepta incomplete verdadero", () => {
    expect(validateResponse(list(assets(1), { incomplete: true })).incomplete).toBe(true);
  });

  it("conserva el orden de la respuesta", () => {
    const first = asset({ title: "Primero" });
    const second = asset({ title: "Segundo" });
    const third = asset({ title: "Tercero" });
    const titles = validateResponse(list([second, third, first])).results.map(
      (item) => item.title,
    );
    expect(titles).toEqual(["Segundo", "Tercero", "Primero"]);
  });

  it("acepta una categoría desconocida", () => {
    expect(() =>
      validateResponse(list([asset({ category_slug: "nueva", category_name: "Nueva" })])),
    ).not.toThrow();
  });

  it.each(["hour", "day", "week", "month"])("acepta la unidad %s", (unit) => {
    expect(() => validateResponse(list([asset({ price_unit: unit })]))).not.toThrow();
  });

  it.each([500, 1000, 2000])("acepta el radio %i", (radius) => {
    expect(() => validateResponse(list([asset({ privacy_radius: radius })]))).not.toThrow();
  });

  it.each(["0.01", "99999.99", "5.00"])("acepta el precio %s", (price) => {
    expect(() => validateResponse(list([asset({ price })]))).not.toThrow();
  });

  it.each([
    [90, 180],
    [-90, -180],
    [0, 0],
  ])("acepta las coordenadas %f, %f", (latitude, longitude) => {
    expect(() => validateResponse(list([asset({ latitude, longitude })]))).not.toThrow();
  });

  it("acepta un título de 200 caracteres", () => {
    expect(() => validateResponse(list([asset({ title: "a".repeat(200) })]))).not.toThrow();
  });

  it("no reescribe el título", () => {
    const title = "  con espacios  ";
    expect(validateResponse(list([asset({ title })])).results[0]?.title).toBe(title);
  });
});

describe("validateResponse: respuestas inválidas", () => {
  const invalid: [string, unknown][] = [
    ["null", null],
    ["una cadena", "texto"],
    ["un número", 7],
    ["una lista", []],
    ["un objeto vacío", {}],
    ["sin results", { incomplete: false }],
    ["sin incomplete", { results: [] }],
    ["results que no es lista", { results: {}, incomplete: false }],
    ["campo de más en la raíz", list([], { total: 0 })],
    ["campo de más en un bien", list([asset({ owner: 1 })])],
    ["bien sin un campo", list([withoutKey(asset(), "price")])],
    ["bien que no es objeto", list(["x"])],
    ["radio 1500", list([asset({ privacy_radius: 1500 })])],
    ["radio como cadena", list([asset({ privacy_radius: "1000" })])],
    ["latitud nula", list([asset({ latitude: null })])],
    ["longitud nula", list([asset({ longitude: null })])],
    ["latitud como cadena", list([asset({ latitude: "39.4" })])],
    ["latitud 90,000001", list([asset({ latitude: 90.000001 })])],
    ["latitud -91", list([asset({ latitude: -91 })])],
    ["longitud 180,5", list([asset({ longitude: 180.5 })])],
    ["longitud -180,5", list([asset({ longitude: -180.5 })])],
    ["latitud NaN", list([asset({ latitude: Number.NaN })])],
    ["latitud infinita", list([asset({ latitude: Number.POSITIVE_INFINITY })])],
    ["longitud infinita negativa", list([asset({ longitude: Number.NEGATIVE_INFINITY })])],
    ["otra moneda", list([asset({ currency: "USD" })])],
    ["moneda en minúsculas", list([asset({ currency: "eur" })])],
    ["unidad desconocida", list([asset({ price_unit: "year" })])],
    ["precio sin decimales", list([asset({ price: "12" })])],
    ["precio con un decimal", list([asset({ price: "12.5" })])],
    ["precio con tres decimales", list([asset({ price: "12.500" })])],
    ["precio con seis cifras enteras", list([asset({ price: "100000.00" })])],
    ["precio con coma", list([asset({ price: "12,50" })])],
    ["precio negativo", list([asset({ price: "-1.00" })])],
    ["precio con espacio", list([asset({ price: " 12.50" })])],
    ["precio con salto de línea final", list([asset({ price: "12.50\n" })])],
    ["precio con dígitos no ASCII", list([asset({ price: "１２.５０" })])],
    ["precio numérico", list([asset({ price: 12.5 })])],
    ["incomplete como cadena", list([], { incomplete: "false" })],
    ["incomplete como número", list([], { incomplete: 0 })],
    ["incomplete nulo", list([], { incomplete: null })],
    ["201 bienes", list(assets(201))],
    ["ids repetidos", list([asset({ public_id: "3f0c9d6a-1b2e-4c8f-9a7d-5e4b3c2a1f00" }), asset({ public_id: "3f0c9d6a-1b2e-4c8f-9a7d-5e4b3c2a1f00" })])],
    ["id que no es UUID", list([asset({ public_id: "123" })])],
    ["id UUID v1", list([asset({ public_id: "c232ab00-9414-11ec-b3c8-9f6bdeced846" })])],
    ["id UUID v7", list([asset({ public_id: "018f4a6e-7b1c-7c3d-8e5f-0a1b2c3d4e5f" })])],
    ["id nulo", list([asset({ public_id: null })])],
    ["título vacío", list([asset({ title: "" })])],
    ["título de solo espacios", list([asset({ title: "   \t " })])],
    ["título de 201 caracteres", list([asset({ title: "a".repeat(201) })])],
    ["título numérico", list([asset({ title: 5 })])],
    ["slug vacío", list([asset({ category_slug: "" })])],
    ["slug de 65 caracteres", list([asset({ category_slug: "a".repeat(65) })])],
    ["nombre de categoría vacío", list([asset({ category_name: "" })])],
    ["nombre de categoría de 101 caracteres", list([asset({ category_name: "a".repeat(101) })])],
  ];

  it.each(invalid)("rechaza %s", (_name, body) => {
    expect(() => validateResponse(body)).toThrow(InvalidResponseError);
  });

  it("un solo bien inválido invalida la respuesta entera", () => {
    const body = list([...assets(5), asset({ privacy_radius: 1500 }), ...assets(5)]);
    expect(() => validateResponse(body)).toThrow(InvalidResponseError);
  });

  it("acepta los máximos exactos de categoría", () => {
    const item = asset({ category_slug: "a".repeat(64), category_name: "a".repeat(100) });
    expect(() => validateResponse(list([item]))).not.toThrow();
  });

  it("el error no revela los valores recibidos ni los problemas de Zod", () => {
    const sentinelLongitude = -0.37628812345;
    const sentinelTitle = "titulo-centinela";
    const body = list([
      asset({ title: sentinelTitle, longitude: sentinelLongitude, privacy_radius: 1500 }),
    ]);
    let caught: unknown;
    try {
      validateResponse(body);
    } catch (error) {
      caught = error;
    }
    expect(caught).toBeInstanceOf(InvalidResponseError);
    const error = caught as InvalidResponseError;
    expect(error.cause).toBeUndefined();
    expect(Object.getOwnPropertyNames(error).sort()).toEqual(["message", "stack"]);
    const everything = [
      error.message,
      error.stack ?? "",
      JSON.stringify(error, Object.getOwnPropertyNames(error)),
    ].join("\n");
    expect(everything).not.toContain("37628812");
    expect(everything).not.toContain(sentinelTitle);
    expect(everything).not.toContain("1500");
    expect(everything).not.toContain("privacy_radius");
  });

  it("el mensaje del error es fijo", () => {
    const messages = [
      captureMessage(list([asset({ privacy_radius: 1500 })])),
      captureMessage(null),
      captureMessage(list([], { total: 3 })),
    ];
    expect(new Set(messages).size).toBe(1);
  });
});

function captureMessage(body: unknown): string {
  try {
    validateResponse(body);
  } catch (error) {
    if (error instanceof Error) return error.message;
  }
  return "no ha lanzado";
}

describe("esquema Zod frente a openapi.json", () => {
  const schemas = openapi.components.schemas;

  function keysOf(shape: object): string[] {
    return Object.keys(shape).sort();
  }

  it("la raíz tiene las mismas claves que PublicAssetList", () => {
    const component = schemas.PublicAssetList;
    expect(keysOf(publicAssetListSchema.shape)).toEqual(keysOf(component.properties));
    expect(keysOf(publicAssetListSchema.shape)).toEqual([...component.required].sort());
  });

  it("cada bien tiene las mismas claves que PublicAsset", () => {
    const component = schemas.PublicAsset;
    expect(keysOf(publicAssetSchema.shape)).toEqual(keysOf(component.properties));
    expect(keysOf(publicAssetSchema.shape)).toEqual([...component.required].sort());
  });
});

import { describe, expect, it, vi } from "vitest";

import {
  BlockedUrlError,
  createMapErrorListener,
  createTransformRequest,
  isAllowedMapUrl,
  MAP_ATTRIBUTION_HTML,
  validateStyleJson,
  validateStyleUrl,
  withFixedAttribution,
} from "./style";

const ALLOWED = ["https://tiles.openfreemap.org", "https://rentradar.example"];

describe("validateStyleUrl", () => {
  it("acepta una dirección https", () => {
    expect(validateStyleUrl("https://tiles.openfreemap.org/styles/positron")?.href).toBe(
      "https://tiles.openfreemap.org/styles/positron",
    );
  });

  it.each([
    "http://tiles.openfreemap.org/styles/positron",
    "https://user:secret@tiles.openfreemap.org/styles/positron",
    "https://user@tiles.openfreemap.org/styles/positron",
    "https://:secret@tiles.openfreemap.org/styles/positron",
    "//tiles.openfreemap.org/styles/positron",
    "/styles/positron",
    "javascript:alert(1)",
    "data:application/json,{}",
    "not a url",
    "",
  ])("rechaza %j", (url) => {
    expect(validateStyleUrl(url)).toBeUndefined();
  });
});

describe("isAllowedMapUrl", () => {
  it.each([
    "https://tiles.openfreemap.org/planet/20261101_080013_pt/11/1/2.pbf",
    "https://tiles.openfreemap.org/styles/positron",
    "https://rentradar.example/api/x",
    "HTTPS://TILES.OPENFREEMAP.ORG/fonts/a/0-255.pbf",
  ])("permite %j", (url) => {
    expect(isAllowedMapUrl(url, ALLOWED)).toBe(true);
  });

  it.each([
    ["http en un origen permitido", "http://tiles.openfreemap.org/planet/1.pbf"],
    ["http en el origen propio", "http://rentradar.example/api/x"],
    ["otro host", "https://evil.example/planet/1.pbf"],
    ["subdominio parecido", "https://tiles.openfreemap.org.evil.example/planet/1.pbf"],
    ["prefijo parecido", "https://eviltiles.openfreemap.org/planet/1.pbf"],
    ["subdominio del permitido", "https://a.tiles.openfreemap.org/planet/1.pbf"],
    ["otro puerto", "https://tiles.openfreemap.org:8443/planet/1.pbf"],
    ["host tras una arroba", "https://tiles.openfreemap.org@evil.example/planet/1.pbf"],
    ["ruta relativa", "/planet/1.pbf"],
    ["esquema data", "data:image/png;base64,AAAA"],
    ["esquema blob", "blob:https://rentradar.example/1234"],
    ["no es una dirección", "no es una url"],
    ["vacía", ""],
  ])("rechaza %s", (_name, url) => {
    expect(isAllowedMapUrl(url, ALLOWED)).toBe(false);
  });

  it("rechaza http aunque su origen esté en la lista, como el origen propio en desarrollo", () => {
    expect(isAllowedMapUrl("http://localhost:5173/x", ["http://localhost:5173"])).toBe(false);
  });

  it("rechaza todo si no hay orígenes permitidos", () => {
    expect(isAllowedMapUrl("https://tiles.openfreemap.org/x", [])).toBe(false);
  });
});

describe("validateStyleJson", () => {
  const style = { version: 8, sources: {}, layers: [] };

  it("acepta un estilo mínimo", () => {
    expect(validateStyleJson(style)).toEqual(style);
  });

  it.each([
    ["versión 7", { ...style, version: 7 }],
    ["versión como texto", { ...style, version: "8" }],
    ["sin versión", { sources: {}, layers: [] }],
    ["sin fuentes", { version: 8, layers: [] }],
    ["fuentes nulas", { ...style, sources: null }],
    ["fuentes como lista", { ...style, sources: [] }],
    ["sin capas", { version: 8, sources: {} }],
    ["capas como objeto", { ...style, layers: {} }],
    ["nulo", null],
    ["lista", []],
    ["texto", "style"],
    ["número", 8],
  ])("rechaza %s", (_name, json) => {
    expect(validateStyleJson(json)).toBeUndefined();
  });
});

describe("MAP_ATTRIBUTION_HTML", () => {
  const anchors = [...MAP_ATTRIBUTION_HTML.matchAll(/<a\s[^>]*>/g)].map((match) => match[0]);

  it("enlaza a los tres proveedores y a nadie más", () => {
    const hrefs = anchors.map((anchor) => /href="([^"]*)"/.exec(anchor)?.[1]);
    expect(hrefs).toEqual([
      "https://openfreemap.org",
      "https://www.openmaptiles.org/",
      "https://www.openstreetmap.org/copyright",
    ]);
  });

  it("abre cada enlace en otra pestaña sin dar acceso a la página", () => {
    for (const anchor of anchors) {
      expect(anchor).toContain('target="_blank"');
      expect(anchor).toContain('rel="noopener noreferrer"');
    }
  });

  it("dice lo que fija el plan", () => {
    expect(MAP_ATTRIBUTION_HTML.replace(/<[^>]*>/g, "")).toBe(
      "OpenFreeMap © OpenMapTiles Data from OpenStreetMap",
    );
  });
});

describe("withFixedAttribution", () => {
  const hostile = '<script>alert(1)</script><a href="https://evil.example">gratis</a>';

  function styleWith(sources: Record<string, unknown>) {
    return { version: 8 as const, sources, layers: [{ id: "background", type: "background" }], sprite: "s" };
  }

  it("sustituye la atribución hostil de cada fuente", () => {
    const style = styleWith({
      vector: { type: "vector", url: "https://tiles.openfreemap.org/planet", attribution: hostile },
      raster: { type: "raster", tiles: ["https://tiles.openfreemap.org/r/{z}/{x}/{y}.png"], attribution: hostile },
    });
    const fixed = withFixedAttribution(style);
    for (const source of Object.values(fixed.sources) as { attribution: string }[]) {
      expect(source.attribution).toBe(MAP_ATTRIBUTION_HTML);
      expect(source.attribution).not.toContain("script");
      expect(source.attribution).not.toContain("evil");
    }
  });

  it("pone la atribución propia a una fuente que no traía ninguna", () => {
    const fixed = withFixedAttribution(styleWith({ vector: { type: "vector", url: "https://tiles.openfreemap.org/planet" } }));
    expect((fixed.sources.vector as { attribution: string }).attribution).toBe(MAP_ATTRIBUTION_HTML);
  });

  it("conserva la url del TileJSON y el resto del estilo", () => {
    const fixed = withFixedAttribution(
      styleWith({ vector: { type: "vector", url: "https://tiles.openfreemap.org/planet", attribution: hostile } }),
    );
    expect(fixed.sources.vector).toMatchObject({ type: "vector", url: "https://tiles.openfreemap.org/planet" });
    expect(fixed.layers).toEqual([{ id: "background", type: "background" }]);
    expect(fixed).toMatchObject({ version: 8, sprite: "s" });
  });

  it("no muta el estilo original", () => {
    const style = styleWith({ vector: { type: "vector", attribution: hostile } });
    const frozen = JSON.parse(JSON.stringify(style)) as typeof style;
    const fixed = withFixedAttribution(style);
    expect(style).toEqual(frozen);
    expect(fixed).not.toBe(style);
    expect(fixed.sources).not.toBe(style.sources);
    expect(fixed.sources.vector).not.toBe(style.sources.vector);
  });

  it("deja tal cual una fuente que no es un objeto", () => {
    const fixed = withFixedAttribution(styleWith({ broken: "texto" }));
    expect(fixed.sources.broken).toBe("texto");
  });
});

describe("createTransformRequest", () => {
  const transformRequest = createTransformRequest(ALLOWED);

  it("deja pasar una dirección permitida sin cambiarla", () => {
    expect(transformRequest("https://tiles.openfreemap.org/planet/1/2/3.pbf")).toBeUndefined();
  });

  it("lanza BlockedUrlError con un mensaje fijo que no lleva la dirección", () => {
    const url = "http://evil.example/secret?token=abc123";
    let thrown: unknown;
    try {
      transformRequest(url);
    } catch (error) {
      thrown = error;
    }
    expect(thrown).toBeInstanceOf(BlockedUrlError);
    const message = (thrown as BlockedUrlError).message;
    expect(message).toBe(new BlockedUrlError().message);
    expect(message).not.toContain("evil");
    expect(message).not.toContain("abc123");
    expect(message).not.toContain("http");
  });

  it("lanza también con una dirección https de otro host", () => {
    expect(() => transformRequest("https://evil.example/x.pbf")).toThrow(BlockedUrlError);
  });
});

describe("createMapErrorListener", () => {
  it("silencia BlockedUrlError", () => {
    const logError = vi.fn();
    createMapErrorListener(logError)({ error: new BlockedUrlError() });
    expect(logError).not.toHaveBeenCalled();
  });

  it("no silencia cualquier otro error", () => {
    const logError = vi.fn();
    const error = new Error("fallo de la tesela");
    createMapErrorListener(logError)({ error });
    expect(logError).toHaveBeenCalledExactlyOnceWith(error);
  });

  it("no silencia algo que parece un BlockedUrlError sin serlo", () => {
    const logError = vi.fn();
    const lookalike = Object.assign(new Error(new BlockedUrlError().message), { name: "BlockedUrlError" });
    createMapErrorListener(logError)({ error: lookalike });
    expect(logError).toHaveBeenCalledExactlyOnceWith(lookalike);
  });

  it("registra un valor que no es un Error", () => {
    const logError = vi.fn();
    createMapErrorListener(logError)({ error: "texto" });
    expect(logError).toHaveBeenCalledExactlyOnceWith("texto");
  });
});

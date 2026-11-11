import { describe, expect, it } from "vitest";
import {
  expectNoExternalReferencesOrScripts,
  expectOnlyAllowedAttributes,
  expectOnlyAllowedTags,
  expectSvgNamespaceOnlyAtRoot,
} from "../testing/svgWhitelist";

const files = import.meta.glob<string>("../assets/categories/*.svg", { eager: true, query: "?raw", import: "default" });

describe("las imágenes de categoría", () => {
  it("son las 11 de la semilla", () => {
    const names = Object.keys(files).map((path) => path.slice(path.lastIndexOf("/") + 1));
    expect(names.sort()).toEqual(
      ["barbecue", "boat", "canoe", "caravan", "ebike", "kayak", "motorhome", "other", "pool", "sports-area", "van"].map(
        (slug) => `${slug}.svg`,
      ),
    );
  });

  describe.each(Object.entries(files))("%s", (path, source) => {
    it("solo contiene etiquetas de la lista blanca, sin texto, comentarios ni entidades", () => {
      expectOnlyAllowedTags(path, source);
    });

    it("solo usa atributos de la lista blanca con el valor esperado", () => {
      expectOnlyAllowedAttributes(path, source);
    });

    it("no tiene referencias externas ni scripts", () => {
      expectNoExternalReferencesOrScripts(path, source);
    });

    it("lleva el espacio de nombres svg una sola vez, en la raíz", () => {
      expectSvgNamespaceOnlyAtRoot(source);
    });
  });
});

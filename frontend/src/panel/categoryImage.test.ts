import { describe, expect, it } from "vitest";

import { categoryImage } from "./categoryImage";

const SLUGS = ["ebike", "caravan", "motorhome", "van", "pool", "barbecue", "sports-area", "boat", "kayak", "canoe", "other"];

describe("categoryImage", () => {
  it.each(SLUGS)("la categoría %s resuelve a su propia imagen", (slug) => {
    // En dev la dirección lleva la consulta ?no-inline; en el build, un hash antes de .svg
    expect(categoryImage(slug)).toMatch(new RegExp(`/${slug}(-[\\w-]+)?\\.svg(\\?no-inline)?$`));
  });

  it("da una imagen distinta a cada una de las 11 categorías", () => {
    expect(new Set(SLUGS.map(categoryImage)).size).toBe(SLUGS.length);
  });

  it.each(["desconocido", "", "EBIKE", "ebike ", "../ebike", "ebike.svg"])("un slug desconocido (%j) da la imagen de other", (slug) => {
    expect(categoryImage(slug)).toBe(categoryImage("other"));
  });

  // Un objeto normal respondería a estos nombres con lo que hereda de Object.prototype
  it.each(["__proto__", "constructor", "toString", "hasOwnProperty", "valueOf", "prototype", "__defineGetter__"])(
    "un slug hostil (%s) da la imagen de other y siempre una cadena",
    (slug) => {
      const image = categoryImage(slug);
      expect(typeof image).toBe("string");
      expect(image).toBe(categoryImage("other"));
    },
  );
});

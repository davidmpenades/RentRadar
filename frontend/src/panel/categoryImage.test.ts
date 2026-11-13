import { describe, expect, it } from "vitest";

import { CATEGORY_KEYS } from "../testing/categoryKeys";
import { categoryImage } from "./categoryImage";

describe("categoryImage", () => {
  it.each(CATEGORY_KEYS)("la categoría %s resuelve a su propia imagen", (slug) => {
    // En dev la dirección lleva la consulta ?no-inline; en el build, un hash antes de .webp
    expect(categoryImage(slug)).toMatch(new RegExp(`/${slug}(-[\\w-]+)?\\.webp(\\?no-inline)?$`));
  });

  it("da una imagen distinta a cada una de las 12 categorías", () => {
    expect(new Set(CATEGORY_KEYS.map(categoryImage)).size).toBe(12);
  });

  it.each(["desconocido", "", "EBIKE", "ebike ", "../ebike", "ebike.webp", "snow", "SKI", "ski ", "ski.webp", "../ski"])("un slug desconocido (%j) da la imagen de other", (slug) => {
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

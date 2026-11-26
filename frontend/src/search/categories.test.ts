import { describe, expect, it } from "vitest";

import { es } from "../i18n/es";
import { CATEGORY_KEYS } from "../testing/categoryKeys";
import { CATEGORY_CHIPS } from "./categories";

// Un identificador sin nombre da undefined en lugar de romper la compilación
const names: Record<string, string | undefined> = es.categories;

describe("CATEGORY_CHIPS", () => {
  it("tiene exactamente los identificadores de las categorías con imagen", () => {
    expect([...CATEGORY_CHIPS].sort()).toEqual([...CATEGORY_KEYS].sort());
  });

  it("deja «Otros» como último chip", () => {
    expect(CATEGORY_CHIPS.at(-1)).toBe("other");
  });

  it("da a cada chip un nombre que no está vacío", () => {
    for (const slug of CATEGORY_CHIPS) expect(names[slug]?.trim(), slug).toBeTruthy();
  });

  it("no repite el nombre de ningún chip", () => {
    expect(new Set(CATEGORY_CHIPS.map((slug) => names[slug])).size).toBe(CATEGORY_CHIPS.length);
  });
});

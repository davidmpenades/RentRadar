import { describe, expect, it } from "vitest";

import { categoryFileProblems, type CategoryFileProblems } from "../testing/categoryFiles";
import { CATEGORY_KEYS } from "../testing/categoryKeys";

const EXACT = CATEGORY_KEYS.map((key) => `${key}.webp`);

const withExtra = (name: string) => [...EXACT, name];
const without = (name: string) => EXACT.filter((one) => one !== name);
const renamed = (from: string, to: string) => EXACT.map((one) => (one === from ? to : one));

const CASES: [string, string[], CategoryFileProblems][] = [
  ["exacto", EXACT, { missing: [], extra: [] }],
  ["falta una", without("ski.webp"), { missing: ["ski"], extra: [] }],
  ["un fichero oculto", withExtra(".oculto"), { missing: [], extra: [".oculto"] }],
  ["otro formato", withExtra("ski.png"), { missing: [], extra: ["ski.png"] }],
  ["una SVG heredada", withExtra("other.svg"), { missing: [], extra: ["other.svg"] }],
  ["una clave que no existe", withExtra("snow.webp"), { missing: [], extra: ["snow.webp"] }],
  ["una subcarpeta", withExtra("sub/x.webp"), { missing: [], extra: ["sub/x.webp"] }],
  ["mayúsculas en el nombre", renamed("ski.webp", "Ski.webp"), { missing: ["ski"], extra: ["Ski.webp"] }],
  ["guion bajo en vez de guion", renamed("sports-area.webp", "sports_area.webp"), { missing: ["sports-area"], extra: ["sports_area.webp"] }],
  ["ninguna", [], { missing: [...CATEGORY_KEYS], extra: [] }],
];

describe("categoryFileProblems: cada caso por su causa", () => {
  it.each(CASES)("%s", (_name, names, expected) => {
    expect(categoryFileProblems(names, CATEGORY_KEYS)).toEqual(expected);
  });
});

// Sin eager: solo se listan los nombres, no se carga ninguna imagen
const FOLDER = "../assets/categories/";
const folder = import.meta.glob("../assets/categories/**/*", { query: "?url", exhaustive: true });
const realNames = Object.keys(folder)
  .map((path) => path.slice(FOLDER.length))
  .sort();

describe("la carpeta real de las imágenes de categoría", () => {
  const problems = categoryFileProblems(realNames, CATEGORY_KEYS);

  it("tiene una imagen por cada clave", () => {
    expect(problems.missing).toEqual([]);
  });

  it("no tiene ningún fichero de más", () => {
    expect(problems.extra).toEqual([]);
  });
});

import { describe, expect, it } from "vitest";

import {
  appliedFilters,
  clearFilters,
  filtersQuery,
  hasActiveFilters,
  setText,
  toggleCategory,
  type FilterState,
} from "./filters";

const EMPTY: FilterState = { category: null, text: "" };

describe("toggleCategory", () => {
  it("activa la categoría pulsada", () => {
    expect(toggleCategory(EMPTY, "ski")).toEqual({ category: "ski", text: "" });
  });

  it("quita la categoría al pulsar la misma", () => {
    expect(toggleCategory({ category: "ski", text: "" }, "ski")).toEqual(EMPTY);
  });

  it("sustituye la categoría activa al pulsar otra", () => {
    expect(toggleCategory({ category: "ski", text: "" }, "kayak")).toEqual({ category: "kayak", text: "" });
  });

  it("conserva el texto al cambiar de categoría", () => {
    expect(toggleCategory({ category: "ski", text: "botas" }, "kayak")).toEqual({ category: "kayak", text: "botas" });
  });
});

describe("setText", () => {
  it("guarda lo escrito tal cual, sin recortar", () => {
    expect(setText({ category: "ski", text: "" }, "  bici ")).toEqual({ category: "ski", text: "  bici " });
  });
});

describe("clearFilters", () => {
  it("devuelve un estado sin categoría y con el texto vacío", () => {
    expect(clearFilters()).toEqual(EMPTY);
  });
});

describe("los cambios de estado", () => {
  it("devuelven un estado nuevo y no modifican el anterior", () => {
    const before: FilterState = { category: "ski", text: "botas" };

    const states = [toggleCategory(before, "kayak"), setText(before, "otra cosa")];

    expect(before).toEqual({ category: "ski", text: "botas" });
    for (const state of states) expect(state).not.toBe(before);
  });
});

describe("appliedFilters", () => {
  it("no envía nada sin categoría ni texto", () => {
    expect(appliedFilters(EMPTY)).toEqual({});
  });

  it("no genera q con un texto de solo espacios o caracteres de control", () => {
    expect(appliedFilters({ category: null, text: "  \t \n" })).toEqual({});
  });

  it("recorta el texto por los extremos y respeta los espacios de dentro", () => {
    expect(appliedFilters({ category: null, text: "  bici   eléctrica " })).toEqual({ q: "bici   eléctrica" });
  });

  it("sustituye los caracteres de control por un espacio", () => {
    expect(appliedFilters({ category: null, text: "bi\tci\n" })).toEqual({ q: "bi ci" });
  });
});

describe("hasActiveFilters", () => {
  it("está activo solo con una categoría", () => {
    expect(hasActiveFilters({ category: "ski", text: "" })).toBe(true);
  });

  it("está activo solo con un texto", () => {
    expect(hasActiveFilters({ category: null, text: "bici" })).toBe(true);
  });

  it("no está activo con un texto de solo espacios o caracteres de control", () => {
    expect(hasActiveFilters({ category: null, text: " \t\n " })).toBe(false);
  });
});

describe("filtersQuery", () => {
  it("devuelve una cadena vacía sin filtros", () => {
    expect(filtersQuery({})).toBe("");
  });

  it("pone category antes que q aunque el objeto traiga q primero", () => {
    expect(filtersQuery({ q: "bici", category: "ski" })).toBe("category=ski&q=bici");
  });

  it("codifica un texto con espacio, &, %, #, ñ y un emoji", () => {
    const text = "esquí & botas 50% #1 ñandú 🚲";

    const params = new URLSearchParams(filtersQuery({ category: "ski", q: text }));

    expect(params.get("q")).toBe(text);
    expect(params.get("category")).toBe("ski");
    expect([...params.keys()]).toEqual(["category", "q"]);
  });
});

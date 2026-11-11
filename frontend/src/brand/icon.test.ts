import { describe, expect, it } from "vitest";
import icon from "../../public/icon.svg?raw";
import {
  ATTRIBUTE,
  TAG,
  expectNoExternalReferencesOrScripts,
  expectOnlyAllowedAttributes,
  expectOnlyAllowedTags,
  expectSvgNamespaceOnlyAtRoot,
} from "../testing/svgWhitelist";

const LEMON = "#F5D547";

type Whitelist = (source: string) => void;

const whitelist = {
  tags: (source) => expectOnlyAllowedTags("icon.svg", source),
  attributes: (source) => expectOnlyAllowedAttributes("icon.svg", source),
  references: (source) => expectNoExternalReferencesOrScripts("icon.svg", source),
  namespace: (source) => expectSvgNamespaceOnlyAtRoot(source),
} satisfies Record<string, Whitelist>;

// Rellenos en orden de dibujo, sin contar la raíz <svg>
function fillsInDrawingOrder(source: string): (string | undefined)[] {
  return [...source.matchAll(TAG)]
    .filter((tag) => tag[1] === "" && tag[2] !== "svg")
    .map((tag) => [...(tag[3] ?? "").matchAll(ATTRIBUTE)].find((attribute) => attribute[1] === "fill")?.[2]?.toUpperCase());
}

function layerFill(layer: number): string {
  const fill = fillsInDrawingOrder(icon)[layer];
  expect(fill, `capa ${layer} del dibujo`).toBeDefined();
  return fill!;
}

function luminance(color: string): number {
  const [red, green, blue] = [1, 3, 5].map((start) => {
    const channel = parseInt(color.slice(start, start + 2), 16) / 255;
    return channel <= 0.03928 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
  }) as [number, number, number];
  return 0.2126 * red + 0.7152 * green + 0.0722 * blue;
}

function contrast(first: string, second: string): number {
  const [lighter, darker] = [luminance(first), luminance(second)].sort((a, b) => b - a) as [number, number];
  return (lighter + 0.05) / (darker + 0.05);
}

describe("el icono de RentRadar", () => {
  describe("lista blanca de SVG", () => {
    it("solo contiene etiquetas de la lista blanca, sin texto, comentarios ni entidades", () => {
      whitelist.tags(icon);
    });

    it("solo usa atributos de la lista blanca con el valor esperado", () => {
      whitelist.attributes(icon);
    });

    it("no tiene referencias externas ni scripts", () => {
      whitelist.references(icon);
    });

    it("lleva el espacio de nombres svg una sola vez, en la raíz", () => {
      whitelist.namespace(icon);
    });
  });

  describe("capas", () => {
    it("usa al menos tres rellenos distintos", () => {
      const fills = fillsInDrawingOrder(icon).filter((fill) => fill !== undefined);
      expect(new Set(fills).size).toBeGreaterThanOrEqual(3);
    });

    it("ninguna capa usa el limón de la marca", () => {
      for (const fill of fillsInDrawingOrder(icon)) expect(fill).not.toBe(LEMON);
    });

    it("la sombra es más oscura que la base y el brillo más claro", () => {
      const [base, highlight, shadow] = [layerFill(0), layerFill(1), layerFill(2)];
      expect(luminance(shadow)).toBeLessThan(luminance(base));
      expect(luminance(base)).toBeLessThan(luminance(highlight));
    });

    it("la base se distingue de la sombra y del brillo al menos 1,5:1", () => {
      const [base, highlight, shadow] = [layerFill(0), layerFill(1), layerFill(2)];
      expect(contrast(base, shadow)).toBeGreaterThanOrEqual(1.5);
      expect(contrast(base, highlight)).toBeGreaterThanOrEqual(1.5);
    });

    it("la silueta, que es la base, se distingue del blanco al menos 3:1", () => {
      expect(contrast(layerFill(0), "#FFFFFF")).toBeGreaterThanOrEqual(3);
    });
  });

  describe("cada rasgo prohibido hace fallar su regla de la lista blanca", () => {
    const base = '<path d="M32 61 C22 51 10 40 10 26 A22 22 0 0 1 54 26 C54 40 42 51 32 61 Z" fill="#4A82EE"/>';
    const wrap = (content: string) =>
      `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" aria-hidden="true" width="64" height="64">${content}</svg>`;

    // Cada caso cambia un solo rasgo de un icono válido y lista las reglas que deben fallar; las demás, no
    const cases: { name: string; svg: string; failing: (keyof typeof whitelist)[] }[] = [
      {
        name: "un degradado",
        svg: wrap(
          '<linearGradient id="g"><stop offset="0" stop-color="#4A82EE"/></linearGradient>' + base.replace("#4A82EE", "url(#g)"),
        ),
        failing: ["tags", "attributes", "references"],
      },
      { name: "una escala en transform", svg: wrap(base.replace("/>", ' transform="scale(2)"/>')), failing: ["attributes"] },
      { name: "un color de tres cifras", svg: wrap(base.replace("#4A82EE", "#48E")), failing: ["attributes"] },
      { name: "una etiqueta <g>", svg: wrap(`<g>${base}</g>`), failing: ["tags"] },
    ];

    it("el icono de referencia pasa las cuatro reglas", () => {
      for (const rule of Object.values(whitelist)) expect(() => rule(wrap(base))).not.toThrow();
    });

    describe.each(cases)("$name", ({ svg, failing }) => {
      it.each(Object.entries(whitelist))("regla %s", (rule, check) => {
        if (failing.includes(rule as keyof typeof whitelist)) expect(() => check(svg)).toThrow();
        else expect(() => check(svg)).not.toThrow();
      });
    });
  });
});

import { describe, expect, it } from "vitest";

import css from "./surfaces.css?raw";

const FALLBACKS = [
  ["no hay desenfoque", "@supports not ((backdrop-filter: blur(1px)) or (-webkit-backdrop-filter: blur(1px)))"],
  ["se pide menos transparencia", "@media (prefers-reduced-transparency: reduce)"],
  ["se pide más contraste", "@media (prefers-contrast: more)"],
] as const;

// Cada respaldo se cierra con la llave de dos espacios que lo abre dentro de la capa
const blockOf = (header: string) => {
  const start = css.indexOf(header);
  if (start === -1) return "";
  const end = css.indexOf("\n  }\n", start);
  return css.slice(start, end === -1 ? undefined : end);
};

describe("superficies de cristal", () => {
  it("el tinte del cristal tiene al menos el 80 % de opacidad", () => {
    const alpha = css.match(/--glass-bg:\s*rgb\(\s*\d+\s+\d+\s+\d+\s*\/\s*([\d.]+)\s*\)/)?.[1];
    expect(alpha).toBeDefined();
    expect(Number(alpha)).toBeGreaterThanOrEqual(0.8);
  });

  it("el cristal desenfoca lo que hay detrás con el filtro por defecto", () => {
    expect(css).toMatch(/--glass-filter:\s*blur\(\d+px\)/);
    expect(css).toMatch(/backdrop-filter:\s*var\(--glass-filter\)/);
  });

  it.each(FALLBACKS)("cuando %s la superficie pasa a sólida y sin filtro", (_when, header) => {
    const block = blockOf(header);
    expect(block).not.toBe("");
    expect(block).toMatch(/--glass-bg:\s*#[0-9a-f]{6}\s*;/i);
    expect(block).toMatch(/--glass-filter:\s*none\s*;/);
    expect(block).toMatch(/--btn-secondary-bg:\s*#[0-9a-f]{6}\s*;/i);
  });

  it("en colores forzados la superficie usa los colores del sistema y no lleva sombra ni filtro", () => {
    const block = blockOf("@media (forced-colors: active)");
    expect(block).toContain("Canvas");
    expect(block).toContain("CanvasText");
    expect(block).toMatch(/box-shadow:\s*none/);
    expect(block).toMatch(/backdrop-filter:\s*none/);
  });
});

import { expect } from "vitest";

const ALLOWED_TAGS = new Set(["svg", "rect", "circle", "ellipse", "path"]);

const NUMBER = "-?\\d+(?:\\.\\d+)?";
const COLOR = "#[0-9A-Fa-f]{6}";
// Cada atributo admitido con la forma exacta de su valor
const ALLOWED_ATTRIBUTES: Record<string, RegExp> = {
  xmlns: /^http:\/\/www\.w3\.org\/2000\/svg$/,
  viewBox: new RegExp(`^0 0 ${NUMBER} ${NUMBER}$`),
  role: /^img$/,
  "aria-hidden": /^true$/,
  width: new RegExp(`^${NUMBER}$`),
  height: new RegExp(`^${NUMBER}$`),
  x: new RegExp(`^${NUMBER}$`),
  y: new RegExp(`^${NUMBER}$`),
  cx: new RegExp(`^${NUMBER}$`),
  cy: new RegExp(`^${NUMBER}$`),
  r: new RegExp(`^${NUMBER}$`),
  rx: new RegExp(`^${NUMBER}$`),
  ry: new RegExp(`^${NUMBER}$`),
  d: /^[MmLlHhVvCcSsQqTtAaZz0-9\s.,-]+$/,
  fill: new RegExp(`^(?:none|${COLOR})$`),
  stroke: new RegExp(`^${COLOR}$`),
  "stroke-width": new RegExp(`^${NUMBER}$`),
  "stroke-linecap": /^round$/,
  "stroke-linejoin": /^round$/,
  opacity: /^(?:0|1|0?\.\d+)$/,
  transform: new RegExp(`^(?:rotate\\(${NUMBER} ${NUMBER} ${NUMBER}\\)|translate\\(${NUMBER} ${NUMBER}\\))$`),
};

export const TAG = /<(\/?)([A-Za-z][\w:-]*)((?:\s+[^\s=<>/"']+="[^"<>&]*")*)\s*(\/?)>/g;
export const ATTRIBUTE = /\s+([^\s=]+)="([^"]*)"/g;

export function expectOnlyAllowedTags(path: string, source: string) {
  // Lo que queda al quitar todas las etiquetas bien formadas debe ser solo espacio en blanco
  expect(source.replace(TAG, "").trim()).toBe("");
  const tags = [...source.matchAll(TAG)].map((match) => match[2]!);
  expect(tags.length).toBeGreaterThan(0);
  for (const tag of tags) expect(ALLOWED_TAGS.has(tag), `${path}: etiqueta <${tag}>`).toBe(true);
}

export function expectOnlyAllowedAttributes(path: string, source: string) {
  for (const tag of source.matchAll(TAG)) {
    for (const attribute of (tag[3] ?? "").matchAll(ATTRIBUTE)) {
      const [, name, value] = attribute as unknown as [string, string, string];
      const allowed = Object.hasOwn(ALLOWED_ATTRIBUTES, name) ? ALLOWED_ATTRIBUTES[name] : undefined;
      expect(allowed, `${path}: atributo ${name}`).toBeDefined();
      expect(allowed!.test(value), `${path}: ${name}="${value}"`).toBe(true);
    }
  }
}

export function expectNoExternalReferencesOrScripts(path: string, source: string) {
  const lower = source.toLowerCase();
  for (const forbidden of ["href", "xlink", "url(", "style", "script", "data:", "javascript:", "<image", "foreignobject", "<!"]) {
    expect(lower.includes(forbidden), `${path}: ${forbidden}`).toBe(false);
  }
  expect(/\son[a-z]+\s*=/i.test(source)).toBe(false);
}

export function expectSvgNamespaceOnlyAtRoot(source: string) {
  expect(source.match(/xmlns=/g)).toHaveLength(1);
  expect(source.startsWith('<svg xmlns="http://www.w3.org/2000/svg" ')).toBe(true);
}

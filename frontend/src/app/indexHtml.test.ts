import { describe, expect, it } from "vitest";
import html from "../../index.html?raw";

// Un atributo sin valor (crossorigin) sale con la cadena vacía
function tagsOf(name: string): Record<string, string>[] {
  return [...html.matchAll(new RegExp(`<${name}\\b[^>]*>`, "g"))].map(([tag]) =>
    Object.fromEntries([...tag.matchAll(/\s([\w-]+)(?:="([^"]*)")?/g)].map((match): [string, string] => [match[1]!, match[2] ?? ""])),
  );
}

const links = (rel: string) => tagsOf("link").filter((attributes) => attributes.rel === rel);
const metas = (name: string) => tagsOf("meta").filter((attributes) => attributes.name === name);

describe("index.html", () => {
  it("declara el icono del sitio: el SVG de public/, una sola vez", () => {
    expect(links("icon")).toEqual([{ rel: "icon", href: "/icon.svg", type: "image/svg+xml" }]);
  });

  it("ya no declara el icono vacío", () => {
    expect(html).not.toContain("data:,");
  });

  it("declara el color de tema del navegador: el de la barra, blanco", () => {
    expect(metas("theme-color")).toEqual([{ name: "theme-color", content: "#FFFFFF" }]);
  });

  it("declara el esquema de color claro, porque no hay modo oscuro", () => {
    expect(metas("color-scheme")).toEqual([{ name: "color-scheme", content: "light" }]);
  });

  it("se preconecta al servidor de teselas con crossorigin, porque MapLibre pide en modo CORS", () => {
    expect(links("preconnect")).toEqual([{ rel: "preconnect", href: "https://tiles.openfreemap.org", crossorigin: "" }]);
  });
});

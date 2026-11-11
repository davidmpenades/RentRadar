import { describe, expect, it } from "vitest";
import html from "../../index.html?raw";

const iconLinks = [...html.matchAll(/<link\b[^>]*>/g)]
  .map(([tag]) => Object.fromEntries([...tag.matchAll(/\s([\w-]+)="([^"]*)"/g)].map((match): [string, string] => [match[1]!, match[2]!])))
  .filter((attributes) => attributes.rel === "icon");

describe("index.html", () => {
  it("declara el icono del sitio: el SVG de public/, una sola vez", () => {
    expect(iconLinks).toEqual([{ rel: "icon", href: "/icon.svg", type: "image/svg+xml" }]);
  });

  it("ya no declara el icono vacío", () => {
    expect(html).not.toContain("data:,");
  });
});

import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { components } from "../api/schema.gen";
import { es } from "../i18n/es";
import type { ViewState } from "../state/viewState";
import { AssetCard } from "./AssetCard";
import { ResultsPanel } from "./ResultsPanel";

type PublicAsset = components["schemas"]["PublicAsset"];

function asset(n: number, overrides: Partial<PublicAsset> = {}): PublicAsset {
  return {
    public_id: `3f0c1f2e-5b7a-4c1d-9e8f-0a1b2c3d4e${String(n).padStart(2, "0")}`,
    title: `Bien ${n}`,
    category_slug: "kayak",
    category_name: "Kayak",
    price: "12.50",
    currency: "EUR",
    price_unit: "day",
    privacy_radius: 500,
    latitude: 39.45,
    longitude: -0.37,
    ...overrides,
  };
}

const escape = (text: string) =>
  text.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
const HOSTILE = ["<img src=x onerror=alert(1)>", "<script>alert(1)</script>", '"><svg onload=alert(1)>', "&lt;b&gt;"];
const noop = () => {};
const NBSP = String.fromCharCode(160);
const panel = (view: ViewState) => renderToStaticMarkup(createElement(ResultsPanel, { view, onRetry: noop, onReset: noop }));
const card = (item: PublicAsset) => renderToStaticMarkup(createElement("ul", null, createElement(AssetCard, { asset: item })));
const imgTags = (html: string) => html.match(/<img\b[^>]*>/g) ?? [];

describe("AssetCard: el texto del anuncio es texto", () => {
  it.each(HOSTILE)("el título %s sale escapado y dentro de <bdi>", (title) => {
    const html = card(asset(1, { title }));
    expect(html).toContain(`<bdi>${escape(title)}</bdi>`);
    expect(html).not.toContain("<img src=x");
    expect(html).not.toContain("<script");
    expect(html).not.toContain("<svg onload");
    expect(html).not.toMatch(/<b>/);
  });

  it.each(HOSTILE)("el nombre de la categoría %s sale escapado", (category_name) => {
    const html = card(asset(1, { category_name }));
    expect(html).not.toContain("<img src=x");
    expect(html).not.toContain("<script");
    expect(html).not.toContain("<svg onload");
    expect(html).toContain(escape(category_name));
  });

  it("no es interactiva: sin enlaces, botones ni tabindex", () => {
    const html = card(asset(1));
    expect(html).not.toMatch(/<(a|button|input|select|textarea)\b/);
    expect(html).not.toContain("tabindex");
  });

  it("lleva una sola imagen decorativa, con alt vacío", () => {
    const tags = imgTags(card(asset(1)));
    expect(tags).toHaveLength(1);
    expect(tags[0]).toContain('alt=""');
  });

  it("enseña el nombre de la categoría, la zona y el precio", () => {
    const html = card(asset(1, { privacy_radius: 2000, price: "30.00", price_unit: "week" })).replaceAll(String.fromCharCode(160), " ");
    expect(html).toContain("Kayak");
    expect(html).toContain("Zona de unos 2 km");
    expect(html).toContain("30 €");
    expect(html).toContain("semana");
  });

  it("une el importe y la unidad con un espacio duro, para que no se parta antes de la barra", () => {
    const html = card(asset(1, { price: "12.50", price_unit: "day" }));
    expect(html).toContain(`</span>${NBSP}/ día`);
    expect(html).not.toContain("</span> / día");
  });

  it("usa la imagen de other si el slug es hostil", () => {
    const hostile = imgTags(card(asset(1, { category_slug: "__proto__" })))[0];
    const other = imgTags(card(asset(1, { category_slug: "other" })))[0];
    expect(hostile).toBe(other);
  });
});

describe("ResultsPanel", () => {
  it("pinta una tarjeta y una imagen por bien, todas con alt vacío", () => {
    const cards = [1, 2, 3, 4, 5].map((n) => asset(n, { title: HOSTILE[n % HOSTILE.length]! }));
    const html = panel({ kind: "results", cards, incomplete: false });
    expect(html.match(/<li\b/g)).toHaveLength(cards.length);
    const images = imgTags(html);
    expect(images).toHaveLength(cards.length);
    for (const image of images) expect(image).toContain('alt=""');
    expect(html).toContain("5 bienes en esta zona");
  });

  it("lleva siempre la región de estado y el aviso de ubicación aproximada", () => {
    const views: ViewState[] = [
      { kind: "loading" },
      { kind: "results", cards: [asset(1)], incomplete: false },
      { kind: "empty", canReset: true },
      { kind: "zoomIn", canReset: false },
      { kind: "error", failure: "network" },
      { kind: "styleError" },
    ];
    for (const view of views) {
      const html = panel(view);
      expect(html).toMatch(/role="status"/);
      expect(html).toContain('aria-live="polite"');
      expect(html).toContain(es.map.notice);
    }
  });

  it("con el estilo fallido solo enseña el aviso: ni cabecera, ni lista, ni botones", () => {
    const html = panel({ kind: "styleError" });
    expect(html).not.toContain("<ul");
    expect(html).not.toContain("<button");
    expect(html).not.toContain("<img");
    expect(html).toContain(es.map.notice);
  });

  it("anuncia la carga en la región de estado", () => {
    expect(panel({ kind: "loading" })).toContain("Buscando bienes…");
  });

  it("ofrece volver a la zona inicial solo si se puede", () => {
    expect(panel({ kind: "empty", canReset: true })).toContain("Volver a la zona inicial");
    expect(panel({ kind: "empty", canReset: false })).not.toContain("Volver a la zona inicial");
    expect(panel({ kind: "zoomIn", canReset: true })).toContain("Volver a la zona inicial");
    expect(panel({ kind: "zoomIn", canReset: false })).not.toContain("Volver a la zona inicial");
  });

  it.each(["network", "timeout", "server", "throttled", "invalid", "unexpected"] as const)(
    "el error %s lleva su mensaje y el botón Reintentar, sin lista",
    (failure) => {
      const html = panel({ kind: "error", failure });
      expect(html).toContain(es.panel.errors[failure]);
      expect(html).toContain(">Reintentar<");
      expect(html).not.toContain("<ul");
    },
  );

  it.each<[string, ViewState]>([
    ["resultados", { kind: "results", cards: [asset(1)], incomplete: false }],
    ["error", { kind: "error", failure: "network" }],
    ["vacío", { kind: "empty", canReset: true }],
    ["estilo fallido", { kind: "styleError" }],
  ])("la cabecera (%s) es enfocable por código y contiene la región de estado y los botones, no el aviso", (_name, view) => {
    const html = panel(view);
    expect(html.match(/tabindex="-1"/g)).toHaveLength(1);
    const header = html.indexOf('tabindex="-1"');
    const status = html.indexOf('role="status"');
    const notice = html.indexOf(es.map.notice);
    expect(header).toBeLessThan(status);
    expect(status).toBeLessThan(notice);
    const button = html.indexOf("<button");
    if (button !== -1) {
      expect(button).toBeGreaterThan(status);
      expect(button).toBeLessThan(notice);
    }
    // El div de la cabecera se cierra antes del aviso: lo que va entre ambos es su cierre
    expect(html.slice(html.lastIndexOf("</div>", notice), notice)).toMatch(/^<\/div><p /);
  });

  it("los botones miden al menos 44 px", () => {
    expect(panel({ kind: "error", failure: "network" })).toContain("min-h-11");
    expect(panel({ kind: "empty", canReset: true })).toContain("min-h-11");
  });
});

import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { es } from "../i18n/es";
import { CATEGORY_CHIPS } from "./categories";
import { FilterBar } from "./FilterBar";
import type { FilterState } from "./filters";

const noop = () => {};
const NBSP = String.fromCharCode(160);
const EMPTY: FilterState = { category: null, text: "" };

const bar = (filters: FilterState) =>
  renderToStaticMarkup(
    createElement(FilterBar, {
      filters,
      onToggleCategory: noop,
      onTextChange: noop,
      onSubmit: noop,
      onClearText: noop,
      onClearAll: noop,
    }),
  );
const tagOf = (html: string, tag: string) => html.match(new RegExp(`<${tag}\\b[^>]*>`))?.[0] ?? "";
const groupOf = (html: string) => html.match(/<div\b[^>]*role="group"[^>]*>[\s\S]*?<\/div>/)?.[0] ?? "";
const buttonsOf = (html: string) => html.match(/<button\b[^>]*>[\s\S]*?<\/button>/g) ?? [];
const textOf = (html: string) => html.replace(/<[^>]*>/g, "");

describe("FilterBar", () => {
  // Rojo si: el formulario pierde role="search" o pasa a ser un div
  it("marca el formulario como búsqueda", () => {
    expect(tagOf(bar(EMPTY), "form")).toMatch(/\srole="search"/);
  });

  // Rojo si: el label no apunta al input y el campo se queda sin nombre accesible
  it("asocia al campo su etiqueta «Buscar por título»", () => {
    const html = bar(EMPTY);
    const label = html.match(/<label\b[^>]*\sfor="([^"]*)"[^>]*>([^<]*)<\/label>/);
    const fieldId = tagOf(html, "input").match(/\sid="([^"]*)"/)?.[1];
    expect(fieldId).toBeTruthy();
    expect(label?.[1]).toBe(fieldId);
    expect(label?.[2]).toBe(es.search.label);
  });

  // Rojo si: falta maxLength=64 y el servidor respondería 400 por texto demasiado largo
  it("limita el texto del campo a 64 caracteres", () => {
    expect(tagOf(bar(EMPTY), "input")).toMatch(/\smaxlength="64"/i);
  });

  // Rojo si: falta autoComplete="off" y el navegador guarda la búsqueda en el historial de formularios
  it("desactiva el autocompletado del campo", () => {
    expect(tagOf(bar(EMPTY), "input")).toMatch(/\sautocomplete="off"/i);
  });

  // Rojo si: falta spellCheck={false} y la corrección mejorada del navegador envía lo escrito fuera
  it("desactiva la corrección ortográfica del campo", () => {
    expect(tagOf(bar(EMPTY), "input")).toMatch(/\sspellcheck="false"/i);
  });

  // Rojo si: un control lleva name o el formulario lleva action, y el texto podría acabar en la dirección
  it("no pone name a ningún control ni action al formulario", () => {
    const html = bar({ category: "ski", text: "esqui" });
    expect(tagOf(html, "form")).not.toBe("");
    expect(tagOf(html, "input")).not.toBe("");
    expect(html).not.toMatch(/\sname=/i);
    expect(tagOf(html, "form")).not.toMatch(/\saction=/i);
  });

  // Rojo si: el grupo de chips pierde role="group" o su etiqueta «Categorías»
  it("agrupa los chips bajo la etiqueta «Categorías»", () => {
    expect(groupOf(bar(EMPTY))).toMatch(/\saria-label="Categorías"/);
  });

  // Rojo si: falta un chip, cambia el orden o el nombre no sale de es.ts
  it("pinta un chip por categoría, en orden y con su nombre", () => {
    const chips = buttonsOf(groupOf(bar(EMPTY))).map(textOf);
    expect(chips).toEqual(CATEGORY_CHIPS.map((slug) => es.categories[slug]));
  });

  // Rojo si: algún botón no es type="button" y al pulsarlo envía el formulario
  it("pone type=button a todos los botones", () => {
    const buttons = buttonsOf(bar({ category: "ski", text: "esqui" }));
    // Doce chips, «Borrar texto» y «Quitar filtros»
    expect(buttons).toHaveLength(CATEGORY_CHIPS.length + 2);
    for (const button of buttons) expect(tagOf(button, "button")).toMatch(/\stype="button"/);
  });

  // Rojo si: algún chip no lleva aria-pressed y no anuncia si está activo
  it("pone aria-pressed a cada chip", () => {
    const chips = buttonsOf(groupOf(bar(EMPTY)));
    expect(chips).toHaveLength(CATEGORY_CHIPS.length);
    for (const chip of chips) expect(tagOf(chip, "button")).toMatch(/\saria-pressed="false"/);
  });

  // Rojo si: hay dos chips pulsados o ninguno con una categoría activa
  it("pulsa solo el chip de la categoría activa", () => {
    const chips = buttonsOf(groupOf(bar({ category: "kayak", text: "" })));
    const pressed = chips.filter((chip) => /\saria-pressed="true"/.test(tagOf(chip, "button")));
    expect(pressed.map(textOf)).toEqual([es.categories.kayak]);
  });

  // Rojo si: el chip activo se distingue solo por el color, o todos llevan la marca
  it("pone la marca de verificación solo en el chip activo", () => {
    const chips = buttonsOf(groupOf(bar({ category: "kayak", text: "" })));
    const marked = chips.filter((chip) => chip.includes("<svg"));
    expect(marked.map(textOf)).toEqual([es.categories.kayak]);
    expect(buttonsOf(groupOf(bar(EMPTY))).some((chip) => chip.includes("<svg"))).toBe(false);
  });

  // Rojo si: «Quitar filtros» sale sin filtro aplicado; un texto de solo espacios no lo es
  it.each([
    ["vacío", ""],
    ["solo espacios", ` ${NBSP} `],
  ])("no ofrece «Quitar filtros» sin filtro activo (%s)", (_name, text) => {
    expect(bar({ category: null, text })).not.toContain(es.search.clearAll);
  });

  // Rojo si: «Quitar filtros» no sale con un filtro activo
  it.each([
    ["una categoría", { category: "ski", text: "" }],
    ["un texto", { category: null, text: "esqui" }],
  ])("ofrece «Quitar filtros» con %s", (_name, filters) => {
    expect(bar(filters)).toContain(es.search.clearAll);
  });

  // Rojo si: «Borrar texto» sale con el campo vacío
  it("no ofrece «Borrar texto» con el campo vacío", () => {
    expect(bar({ category: "ski", text: "" })).not.toContain(es.search.clearText);
  });

  // Rojo si: «Borrar texto» falta con texto escrito
  it("ofrece «Borrar texto» con texto escrito", () => {
    expect(bar({ category: null, text: "esqui" })).toContain(`aria-label="${es.search.clearText}"`);
  });

  // Rojo si: el campo no lleva el texto del estado y «Quitar filtros» lo deja escrito
  it("muestra en el campo el texto del estado", () => {
    expect(tagOf(bar({ category: null, text: "kayak doble" }), "input")).toMatch(/\svalue="kayak doble"/);
  });
});

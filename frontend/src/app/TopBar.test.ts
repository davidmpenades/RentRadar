import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { es } from "../i18n/es";
import type { TopBarAction } from "../session/sessionState";
import { classesOf } from "../testing/classesOf";
import { TopBar } from "./TopBar";

const noop = () => {};
const ACTIONS: TopBarAction[] = ["none", "register", "logout"];

const bar = (action: TopBarAction, logoutPending = false) =>
  renderToStaticMarkup(createElement(TopBar, { action, logoutPending, onNavigate: noop, onLogout: noop }));

const links = (html: string) => html.match(/<a\b[^>]*>.*?<\/a>/g) ?? [];
const buttons = (html: string) => html.match(/<button\b[^>]*>.*?<\/button>/g) ?? [];
const attributesOf = (tag: string) =>
  Object.fromEntries([...tag.matchAll(/\s([\w-]+)="([^"]*)"/g)].map((match): [string, string] => [match[1]!, match[2]!]));

describe("TopBar", () => {
  it.each(ACTIONS)("con %s la marca es un enlace a /map de al menos 44 px", (action) => {
    const brand = links(bar(action)).find((tag) => tag.includes(es.topBar.brand));
    expect(brand).toBeDefined();
    expect(brand).toMatch(/href="\/map"/);
    expect(classesOf(brand ?? "")).toContain("min-h-11");
  });

  describe("la marca", () => {
    const brand = () => links(bar("none")).find((tag) => tag.includes(es.topBar.brand)) ?? "";

    it("también mide 44 px de ancho: el icono solo ocupa 36", () => {
      expect(classesOf(brand())).toEqual(expect.arrayContaining(["min-h-11", "min-w-11"]));
    });

    it("lleva el icono del sitio como imagen decorativa de 36 × 36 px", () => {
      const image = brand().match(/<img\b[^>]*>/)?.[0] ?? "";
      expect(attributesOf(image)).toEqual({ src: "/icon.svg", alt: "", width: "36", height: "36" });
    });

    it("lleva el nombre en un span que el traductor no toca, dentro del enlace", () => {
      const name = brand().match(/<span\b[^>]*>RentRadar<\/span>/)?.[0] ?? "";
      expect(attributesOf(name).translate).toBe("no");
    });

    it("oculta el nombre a la vista por debajo de 900 px sin quitarlo del nombre accesible", () => {
      const name = brand().match(/<span\b[^>]*>RentRadar<\/span>/)?.[0] ?? "";
      const classes = classesOf(name);
      expect(classes).toEqual(expect.arrayContaining(["sr-only", "min-[900px]:not-sr-only"]));
      expect(classes).not.toContain("hidden");
    });
  });

  it.each(ACTIONS)("con %s la barra mide siempre 56 px y no se encoge: aparecer una acción no la mueve", (action) => {
    const header = bar(action).match(/<header\b[^>]*>/)?.[0] ?? "";
    expect(classesOf(header)).toEqual(expect.arrayContaining(["h-14", "shrink-0"]));
  });

  it("mientras no se sabe si hay sesión no hay acciones de sesión", () => {
    const html = bar("none");
    expect(links(html)).toHaveLength(1);
    expect(buttons(html)).toHaveLength(0);
    expect(html).not.toContain(es.topBar.register);
    expect(html).not.toContain(es.topBar.logout);
  });

  it("sin sesión muestra el enlace «Registrarse» a /register, como botón principal, y no «Salir»", () => {
    const html = bar("register");
    const register = links(html).find((tag) => tag.includes(es.topBar.register));
    expect(register).toMatch(/href="\/register"/);
    expect(classesOf(register ?? "")).toEqual(expect.arrayContaining(["btn", "btn-primary"]));
    expect(buttons(html)).toHaveLength(0);
    expect(es.topBar.register).toBe("Registrarse");
  });

  it("con sesión muestra el botón «Salir», como botón secundario, y no «Registrarse»", () => {
    const html = bar("logout");
    const [logout] = buttons(html);
    expect(buttons(html)).toHaveLength(1);
    expect(logout).toContain(es.topBar.logout);
    expect(logout).toMatch(/type="button"/);
    expect(classesOf(logout ?? "")).toEqual(expect.arrayContaining(["btn", "btn-secondary"]));
    expect(logout).not.toMatch(/\saria-disabled=/);
    expect(html).not.toContain("/register");
    expect(es.topBar.logout).toBe("Salir");
  });

  it("«Salir» en curso usa aria-disabled y no disabled, para conservar el foco", () => {
    const [logout] = buttons(bar("logout", true));
    expect(logout).toMatch(/aria-disabled="true"/);
    expect(logout).not.toMatch(/\sdisabled(=|\s|>)/);
  });

  it.each(ACTIONS)("con %s nunca hay un email en la barra", (action) => {
    expect(bar(action)).not.toContain("@");
  });
});

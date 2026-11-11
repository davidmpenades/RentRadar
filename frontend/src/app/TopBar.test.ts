import { createElement, isValidElement, type ReactElement, type ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { es } from "../i18n/es";
import type { TopBarAction } from "../session/sessionState";
import { LogoutNotice } from "./LogoutNotice";
import { TopBar } from "./TopBar";

const noop = () => {};
const ACTIONS: TopBarAction[] = ["none", "register", "logout"];

const bar = (action: TopBarAction, logoutPending = false) =>
  renderToStaticMarkup(createElement(TopBar, { action, logoutPending, onNavigate: noop, onLogout: noop }));
const notice = (value: "logout_failed" | null) =>
  renderToStaticMarkup(createElement(LogoutNotice, { notice: value, onRetry: noop, onDismiss: noop }));
const regionOf = (html: string) => html.match(/<div\b[^>]*role="status"[^>]*>(.*?)<\/div>/s)?.[1];

type ButtonProps = { children?: ReactNode; onClick?: () => void };

function childrenOf(node: ReactNode): ReactNode[] {
  if (!isValidElement<{ children?: ReactNode }>(node)) return [];
  return [node.props.children].flat();
}

function buttonElements(node: ReactNode): ReactElement<ButtonProps>[] {
  if (!isValidElement<ButtonProps>(node)) return [];
  const own = node.type === "button" ? [node] : [];
  return [...own, ...childrenOf(node).flatMap(buttonElements)];
}

const textOf = (node: ReactNode) => [node].flat().join("");

const links = (html: string) => html.match(/<a\b[^>]*>.*?<\/a>/g) ?? [];
const buttons = (html: string) => html.match(/<button\b[^>]*>.*?<\/button>/g) ?? [];
const classesOf = (tag: string) => (tag.match(/class="([^"]*)"/)?.[1] ?? "").split(" ");

describe("TopBar", () => {
  it.each(ACTIONS)("con %s la marca es un enlace a /map de al menos 44 px", (action) => {
    const brand = links(bar(action)).find((tag) => tag.includes(es.topBar.brand));
    expect(brand).toBeDefined();
    expect(brand).toMatch(/href="\/map"/);
    expect(classesOf(brand ?? "")).toContain("min-h-11");
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

describe("LogoutNotice", () => {
  it("sin aviso deja montada la región de estado, vacía", () => {
    expect(regionOf(notice(null))).toBe("");
  });

  it("el contenedor va superpuesto bajo la barra: no cambia el alto de la zona de contenido", () => {
    const container = notice(null).match(/<div\b[^>]*>/)?.[0] ?? "";
    expect(classesOf(container)).toEqual(expect.arrayContaining(["absolute", "inset-x-0", "top-0"]));
  });

  it("la región solo contiene el mensaje de la 009", () => {
    const region = regionOf(notice("logout_failed")) ?? "";
    expect(region.replace(/<[^>]*>/g, "")).toBe(es.session.logoutFailed);
  });

  it("ningún botón queda dentro de la región: el anuncio no incluye sus nombres", () => {
    expect(regionOf(notice("logout_failed"))).not.toContain("<button");
  });

  it("con el fallo de salida muestra «Reintentar» como principal y «Cerrar aviso» como secundario", () => {
    const [retry, dismiss, ...rest] = buttons(notice("logout_failed"));
    expect(rest).toHaveLength(0);
    expect(dismiss).toBeDefined();
    expect(retry).toContain(es.session.retry);
    expect(retry).toMatch(/type="button"/);
    expect(classesOf(retry ?? "")).toEqual(expect.arrayContaining(["btn", "btn-primary"]));
    expect(dismiss).toContain(es.session.dismiss);
    expect(dismiss).toMatch(/type="button"/);
    expect(classesOf(dismiss ?? "")).toEqual(expect.arrayContaining(["btn", "btn-secondary"]));
  });

  // renderToStaticMarkup no muestra a qué función va cada onClick: se llama al componente y se recorre su árbol
  it("cada botón llama a su función: «Reintentar» a onRetry y «Cerrar aviso» a onDismiss", () => {
    const onRetry = vi.fn();
    const onDismiss = vi.fn();
    const tree = LogoutNotice({ notice: "logout_failed", onRetry, onDismiss });
    const clickButton = (label: string) => {
      const button = buttonElements(tree).find((element) => textOf(element.props.children) === label);
      expect(button, label).toBeDefined();
      (button?.props.onClick as () => void)();
    };

    clickButton(es.session.retry);
    expect(onRetry).toHaveBeenCalledTimes(1);
    expect(onDismiss).not.toHaveBeenCalled();

    clickButton(es.session.dismiss);
    expect(onDismiss).toHaveBeenCalledTimes(1);
    expect(onRetry).toHaveBeenCalledTimes(1);
  });
});

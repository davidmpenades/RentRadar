import { createElement, isValidElement, type ReactElement, type ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { es } from "../i18n/es";
import css from "../styles/notice.css?raw";
import { classesOf } from "../testing/classesOf";
import { LogoutNotice } from "./LogoutNotice";

const noop = () => {};

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

const cardTags = (html: string) => html.match(/<div\b[^>]*\bclass="[^"]*\bnotice-card\b[^"]*"[^>]*>/g) ?? [];

// Las declaraciones de la regla cuyo selector es exactamente este, sin contar las que lo llevan dentro de otro selector
const declarationsOf = (selector: string) => {
  const escaped = selector.replace(/[.[\]]/g, "\\$&");
  return css.match(new RegExp(`(?:^|\\n)\\s*${escaped}\\s*\\{([^}]*)\\}`))?.[1] ?? "";
};

const buttons = (html: string) => html.match(/<button\b[^>]*>.*?<\/button>/g) ?? [];

describe("LogoutNotice", () => {
  it("sin aviso deja montada la región de estado, vacía", () => {
    expect(regionOf(notice(null))).toBe("");
  });

  it("la zona va fuera del flujo y sin eventos de puntero: no cambia el alto de la zona de contenido", () => {
    const zone = notice(null).match(/<div\b[^>]*>/)?.[0] ?? "";
    expect(classesOf(zone)).toContain("notice-zone");
    const declarations = declarationsOf(".notice-zone");
    expect(declarations).toMatch(/position:\s*absolute/);
    expect(declarations).toMatch(/z-index:\s*20\b/);
    expect(declarations).toMatch(/pointer-events:\s*none/);
  });

  it("la región de estado va oculta a la vista, con aviso y sin él", () => {
    for (const value of ["logout_failed", null] as const) {
      const region = notice(value).match(/<div\b[^>]*role="status"[^>]*>/)?.[0] ?? "";
      expect(classesOf(region), String(value)).toContain("sr-only");
    }
  });

  // En un contenedor flex alineado al final, una región absoluta sin anclar cae en el borde inferior y desborda la página
  it("la región oculta se ancla arriba a la izquierda de la zona", () => {
    const region = notice(null).match(/<div\b[^>]*role="status"[^>]*>/)?.[0] ?? "";
    expect(classesOf(region)).toEqual(expect.arrayContaining(["top-0", "left-0"]));
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

  // Un data-* con false se pinta como data-open="false" y el selector [data-open] lo daría por abierto: sin aviso, el atributo no existe
  it("data-open aparece una sola vez con aviso y nunca sin él", () => {
    expect(notice("logout_failed").match(/\sdata-open(?==|\s|>)/g) ?? []).toHaveLength(1);
    expect(notice(null)).not.toContain("data-open");
  });

  it("la tarjeta notice-card es de cristal, está siempre montada y solo lleva data-open con aviso", () => {
    const closed = cardTags(notice(null));
    expect(closed, "sin aviso la tarjeta sigue montada").toHaveLength(1);
    expect(classesOf(closed[0] ?? "")).toContain("glass");
    expect(closed[0]).not.toContain("data-open");

    const open = cardTags(notice("logout_failed"));
    expect(open, "con aviso hay una sola tarjeta").toHaveLength(1);
    expect(open[0]).toMatch(/\sdata-open(?==|\s|>)/);
  });

  // Durante los 240 ms de la salida animada la tarjeta sigue pintada: inert evita que sus botones reciban clic o teclado
  it("la tarjeta lleva inert mientras no hay aviso y no lo lleva con aviso", () => {
    expect(cardTags(notice(null))[0]).toMatch(/\sinert(?==|\s|>)/);
    expect(cardTags(notice("logout_failed"))[0]).not.toMatch(/\sinert(?==|\s|>)/);
  });

  it("notice.css abre la tarjeta con el mismo selector .notice-card[data-open] que el marcado", () => {
    expect(css).toMatch(/\.notice-card\[data-open\]/);
  });

  it("el aviso lleva el indicador de error, decorativo", () => {
    const icons = notice("logout_failed").match(/<svg\b[^>]*>/g) ?? [];
    expect(icons).toHaveLength(1);
    expect(icons[0]).toMatch(/aria-hidden="true"/);
  });

  it("el párrafo visible del mensaje lleva aria-hidden: solo la región lo anuncia", () => {
    const paragraphs = (notice("logout_failed").match(/<p\b[^>]*>[^<]*<\/p>/g) ?? []).filter((paragraph) =>
      paragraph.includes(es.session.logoutFailed),
    );
    expect(paragraphs.length, "el mensaje visible va en un párrafo").toBeGreaterThan(0);
    for (const paragraph of paragraphs) expect(paragraph).toMatch(/aria-hidden="true"/);
  });
});

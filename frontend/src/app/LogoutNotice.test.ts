import { createElement, isValidElement, type ReactElement, type ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { es } from "../i18n/es";
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

const buttons = (html: string) => html.match(/<button\b[^>]*>.*?<\/button>/g) ?? [];
const classesOf = (tag: string) => (tag.match(/class="([^"]*)"/)?.[1] ?? "").split(" ");

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

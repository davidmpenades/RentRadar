import { createElement, type ComponentProps } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { es } from "../i18n/es";
import { classesOf } from "../testing/classesOf";
import { LoginForm } from "./LoginForm";

type Props = ComponentProps<typeof LoginForm>;

const noop = () => {};
const BASE: Props = {
  email: "",
  onEmailChange: noop,
  emailMessages: [],
  passwordMessages: [],
  general: null,
  submitting: false,
  passwordVisible: false,
  onTogglePasswordVisible: noop,
  onSubmit: noop,
};

const render = (props: Partial<Props> = {}) => renderToStaticMarkup(createElement(LoginForm, { ...BASE, ...props }));
const tag = (html: string, pattern: RegExp) => html.match(pattern)?.[0] ?? "";
const inputOf = (html: string, id: string) => tag(html, new RegExp(`<input\\b[^>]*\\bid="${id}"[^>]*>`));
const buttonWith = (html: string, text: string) =>
  tag(html, new RegExp(`<button\\b[^>]*>[^<]*${text}[^<]*</button>`));
const attr = (element: string, name: string) => element.match(new RegExp(`\\s${name}="([^"]*)"`, "i"))?.[1];
const eyeOf = (html: string) =>
  tag(html, new RegExp(`<button\\b[^>]*\\baria-label="${es.register.showPassword}"[^>]*>.*?</button>`, "s"));
const statusOf = (html: string) => tag(html, /<div\b[^>]*\brole="status"[^>]*>.*?<\/div>/s);
const textOf = (html: string) => html.replace(/<[^>]*>/g, "");
const listItems = (html: string) => html.match(/<li\b[^>]*>.*?<\/li>/gs) ?? [];

const EMPTY_FIELDS: Partial<Props> = {
  emailMessages: [es.register.email.email_empty],
  passwordMessages: [es.register.password.password_required],
  general: es.register.summary,
};

describe("LoginForm: estructura", () => {
  it("lleva el h1 «Entrar» y un formulario sin validación del navegador que no envía por GET", () => {
    const html = render();
    expect(tag(html, /<h1\b[^>]*>.*?<\/h1>/s)).toContain(es.login.title);
    expect(es.login.title).toBe("Entrar");
    const form = tag(html, /<form\b[^>]*>/);
    expect(form).toMatch(/\snovalidate=""/i);
    expect(attr(form, "method")).toBe("post");
  });

  it.each([
    ["login-email", es.register.emailLabel],
    ["login-password", es.register.passwordLabel],
  ])("el campo %s tiene su etiqueta asociada", (id, text) => {
    expect(render()).toMatch(new RegExp(`<label\\b[^>]*\\bfor="${id}"[^>]*>${text}</label>`));
  });

  it("el email es de tipo email con autocompletado, teclado y sin mayúsculas ni corrector", () => {
    const email = inputOf(render(), "login-email");
    expect(attr(email, "type")).toBe("email");
    expect(attr(email, "autocomplete")).toBe("email");
    expect(attr(email, "inputmode")).toBe("email");
    expect(attr(email, "autocapitalize")).toBe("none");
    expect(attr(email, "spellcheck")).toBe("false");
  });

  it("la contraseña es la actual, sin pista de longitud y sin bloquear el pegado", () => {
    const html = render();
    const password = inputOf(html, "login-password");
    expect(attr(password, "type")).toBe("password");
    expect(attr(password, "autocomplete")).toBe("current-password");
    expect(attr(password, "aria-describedby")).toBeUndefined();
    expect(html).not.toContain("Al menos");
    expect(html).not.toMatch(/onpaste/i);
  });

  it.each(["login-email", "login-password"])("%s es un campo con su clase de tipo", (id) => {
    expect(classesOf(inputOf(render(), id))).toContain("field");
  });

  it("«Entrar» es el botón principal de formulario y envía", () => {
    const submit = buttonWith(render(), es.login.submit);
    expect(submit).not.toBe("");
    expect(es.login.submit).toBe("Entrar");
    expect(attr(submit, "type")).toBe("submit");
    expect(classesOf(submit)).toEqual(expect.arrayContaining(["btn", "btn-primary", "btn-form"]));
  });

  it("la región de estado está siempre montada, es role=status y se puede enfocar por código", () => {
    const region = tag(render(), /<div\b[^>]*\brole="status"[^>]*>/);
    expect(region).not.toBe("");
    expect(attr(region, "tabindex")).toBe("-1");
  });

  it("«¿No tienes cuenta? Regístrate» enlaza con /register bajo el envío y mide al menos 44 px", () => {
    const html = render();
    const link = tag(html, /<a\b[^>]*\bhref="\/register"[^>]*>[^<]*<\/a>/);
    expect(textOf(link)).toBe(es.login.toRegister);
    expect(es.login.toRegister).toBe("¿No tienes cuenta? Regístrate");
    expect(classesOf(link)).toEqual(expect.arrayContaining(["inline-flex", "min-h-11"]));
    expect(html.indexOf('type="submit"')).toBeLessThan(html.indexOf('href="/register"'));
  });
});

describe("LoginForm: la contraseña nunca llega al HTML", () => {
  const STATES: [string, Partial<Props>][] = [
    ["vacío", {}],
    ["con errores", { ...EMPTY_FIELDS, email: "ana@example.com" }],
    ["con el error general", { general: es.login.credentialsInvalid, email: "ana@example.com" }],
    ["enviando", { submitting: true, email: "ana@example.com" }],
    ["visible", { passwordVisible: true }],
    ["visible y enviando", { passwordVisible: true, submitting: true }],
  ];

  it.each(STATES)("con el formulario %s la contraseña no lleva value ni defaultValue", (_name, props) => {
    const password = inputOf(render(props), "login-password");
    expect(password).not.toBe("");
    expect(password).not.toMatch(/\svalue=/);
    expect(password).not.toMatch(/\sdefaultvalue=/i);
  });

  it("el componente no recibe la contraseña: no hay propiedad para ella", () => {
    expect(Object.keys(BASE)).not.toContain("password");
  });

  it("el email sí es un campo controlado y lleva su valor", () => {
    expect(attr(inputOf(render({ email: "ana@example.com" }), "login-email"), "value")).toBe("ana@example.com");
  });
});

describe("LoginForm: campos vacíos", () => {
  it("cada campo vacío es inválido y apunta a su mensaje", () => {
    const html = render(EMPTY_FIELDS);
    for (const [id, message] of [
      ["login-email", es.register.email.email_empty],
      ["login-password", es.register.password.password_required],
    ] as const) {
      const input = inputOf(html, id);
      expect(attr(input, "aria-invalid")).toBe("true");
      const listId = attr(input, "aria-describedby");
      const list = tag(html, new RegExp(`<ul\\b[^>]*\\bid="${listId}"[^>]*>.*?</ul>`, "s"));
      expect(listItems(list).map(textOf)).toEqual([message]);
    }
  });

  it("sin errores no hay aria-invalid ni listas", () => {
    const html = render();
    expect(inputOf(html, "login-email")).not.toMatch(/\saria-invalid=/);
    expect(inputOf(html, "login-password")).not.toMatch(/\saria-invalid=/);
    expect(html).not.toContain("<ul");
  });
});

describe("LoginForm: envío en curso", () => {
  const html = render({ submitting: true, email: "ana@example.com" });

  it("anuncia «Entrando…» en la región de estado, sin indicador", () => {
    const region = statusOf(html);
    expect(textOf(region)).toBe(es.login.submitting);
    expect(es.login.submitting).toBe("Entrando…");
    expect(region).not.toContain("<svg");
    expect(classesOf(tag(html, /<div\b[^>]*\brole="status"[^>]*>/))).toContain("text-muted");
  });

  it("el envío usa aria-disabled y no disabled, para conservar el foco", () => {
    const submit = buttonWith(html, es.login.submit);
    expect(attr(submit, "aria-disabled")).toBe("true");
    expect(html).not.toMatch(/\sdisabled(=|\s|>)/);
  });

  it("los dos campos pasan a solo lectura para que no cambien durante la operación", () => {
    expect(inputOf(html, "login-email")).toMatch(/\sreadonly=""/i);
    expect(inputOf(html, "login-password")).toMatch(/\sreadonly=""/i);
  });

  it("sin envío en curso no hay aria-disabled ni solo lectura y no se anuncia nada", () => {
    const idle = render();
    expect(buttonWith(idle, es.login.submit)).not.toMatch(/\saria-disabled=/);
    expect(inputOf(idle, "login-email")).not.toMatch(/\sreadonly=/i);
    expect(inputOf(idle, "login-password")).not.toMatch(/\sreadonly=/i);
    expect(textOf(statusOf(idle))).toBe("");
  });

  it("mientras se envía no se muestra el error general anterior", () => {
    expect(render({ submitting: true, general: es.login.credentialsInvalid })).not.toContain(es.login.credentialsInvalid);
  });
});

describe("LoginForm: región de estado", () => {
  it("el error general lleva el indicador oculto y el texto, que es lo único que se anuncia", () => {
    const region = statusOf(render({ general: es.login.credentialsInvalid }));
    const svg = tag(region, /<svg\b[^>]*>/);
    expect(attr(svg, "aria-hidden")).toBe("true");
    expect(textOf(region)).toBe(es.login.credentialsInvalid);
  });
});

describe("LoginForm: el ojo", () => {
  it("«Mostrar contraseña» no envía el formulario, controla la contraseña y no tiene texto visible", () => {
    const eye = eyeOf(render());
    expect(eye).not.toBe("");
    expect(attr(eye, "type")).toBe("button");
    expect(attr(eye, "aria-controls")).toBe("login-password");
    expect(attr(eye, "aria-pressed")).toBe("false");
    expect(textOf(eye)).toBe("");
  });

  it("al mostrar la contraseña cambia aria-pressed y el tipo, pero no el nombre", () => {
    const html = render({ passwordVisible: true });
    expect(attr(eyeOf(html), "aria-pressed")).toBe("true");
    expect(attr(eyeOf(html), "aria-label")).toBe(es.register.showPassword);
    expect(attr(inputOf(html, "login-password"), "type")).toBe("text");
  });
});

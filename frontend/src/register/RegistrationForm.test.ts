import { createElement, type ComponentProps } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { es } from "../i18n/es";
import { RegistrationForm } from "./RegistrationForm";
import { PASSWORD_MIN_LENGTH } from "./registerForm";

type Props = ComponentProps<typeof RegistrationForm>;

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

const render = (props: Partial<Props> = {}) => renderToStaticMarkup(createElement(RegistrationForm, { ...BASE, ...props }));
const tag = (html: string, pattern: RegExp) => html.match(pattern)?.[0] ?? "";
const inputOf = (html: string, id: string) => tag(html, new RegExp(`<input\\b[^>]*\\bid="${id}"[^>]*>`));
const buttonWith = (html: string, text: string) =>
  tag(html, new RegExp(`<button\\b[^>]*>[^<]*${text}[^<]*</button>`));
const classesOf = (element: string) => (element.match(/class="([^"]*)"/)?.[1] ?? "").split(" ");
const attr = (element: string, name: string) => element.match(new RegExp(`\\s${name}="([^"]*)"`, "i"))?.[1];
const eyeOf = (html: string) =>
  tag(html, new RegExp(`<button\\b[^>]*\\baria-label="${es.register.showPassword}"[^>]*>.*?</button>`, "s"));
const statusOf = (html: string) => tag(html, /<div\b[^>]*\brole="status"[^>]*>.*?<\/div>/s);
const statusTagOf = (html: string) => tag(html, /<div\b[^>]*\brole="status"[^>]*>/);
const svgTags = (html: string) => html.match(/<svg\b[^>]*>/g) ?? [];
const textOf = (html: string) => html.replace(/<[^>]*>/g, "");
const listItems = (html: string) => html.match(/<li\b[^>]*>.*?<\/li>/gs) ?? [];

const WITH_ERRORS: Partial<Props> = {
  email: "ana@example.com",
  emailMessages: ["Ya existe una cuenta con este email."],
  passwordMessages: ["Esa contraseña es demasiado común.", "La contraseña no puede tener solo números."],
  general: es.register.summary,
};

describe("RegistrationForm: estructura", () => {
  it("lleva un h1 y un formulario sin validación del navegador que no envía por GET", () => {
    const html = render();
    expect(html).toContain(`<h1`);
    expect(html).toContain(es.register.title);
    const form = tag(html, /<form\b[^>]*>/);
    expect(form).toMatch(/\snovalidate=""/i);
    expect(attr(form, "method")).toBe("post");
  });

  it.each([
    ["register-email", es.register.emailLabel],
    ["register-password", es.register.passwordLabel],
  ])("el campo %s tiene su etiqueta asociada", (id, text) => {
    expect(render()).toMatch(new RegExp(`<label\\b[^>]*\\bfor="${id}"[^>]*>${text}</label>`));
  });

  it("el email es de tipo email con autocompletado, teclado y sin mayúsculas ni corrector", () => {
    const email = inputOf(render(), "register-email");
    expect(attr(email, "type")).toBe("email");
    expect(attr(email, "autocomplete")).toBe("email");
    expect(attr(email, "inputmode")).toBe("email");
    expect(attr(email, "autocapitalize")).toBe("none");
    expect(attr(email, "spellcheck")).toBe("false");
  });

  it("la contraseña es de contraseña nueva y no se bloquea el pegado", () => {
    const html = render();
    const password = inputOf(html, "register-password");
    expect(attr(password, "type")).toBe("password");
    expect(attr(password, "autocomplete")).toBe("new-password");
    expect(html).not.toMatch(/onpaste/i);
  });

  it("la pista usa la constante de longitud mínima y está enlazada a la contraseña", () => {
    const html = render();
    expect(html).toContain(`Al menos ${PASSWORD_MIN_LENGTH} caracteres.`);
    const hintId = html.match(/<p\b[^>]*\bid="([^"]*)"[^>]*>Al menos/)?.[1];
    expect(hintId).toBeDefined();
    expect(attr(inputOf(html, "register-password"), "aria-describedby")).toContain(hintId);
  });

  it.each([
    ["el email", (html: string) => inputOf(html, "register-email")],
    ["la contraseña", (html: string) => inputOf(html, "register-password")],
  ])("%s es un campo con su clase de tipo", (_name, find) => {
    const element = find(render());
    expect(element).not.toBe("");
    expect(classesOf(element)).toContain("field");
  });

  it("«Crear cuenta» es el botón principal de formulario", () => {
    const submit = buttonWith(render(), es.register.submit);
    expect(submit).not.toBe("");
    expect(classesOf(submit)).toEqual(expect.arrayContaining(["btn", "btn-primary", "btn-form"]));
  });

  it("la región de estado está siempre montada, es role=status y se puede enfocar por código", () => {
    const region = tag(render(), /<div\b[^>]*\brole="status"[^>]*>/);
    expect(region).not.toBe("");
    expect(attr(region, "tabindex")).toBe("-1");
  });
});

describe("RegistrationForm: la contraseña nunca llega al HTML", () => {
  const STATES: [string, Partial<Props>][] = [
    ["vacío", {}],
    ["con errores", WITH_ERRORS],
    ["enviando", { submitting: true, email: "ana@example.com" }],
    ["visible", { passwordVisible: true }],
    ["visible y enviando", { passwordVisible: true, submitting: true }],
  ];

  it.each(STATES)("con el formulario %s el campo no lleva value ni defaultValue", (_name, props) => {
    const password = inputOf(render(props), "register-password");
    expect(password).not.toBe("");
    expect(password).not.toMatch(/\svalue=/);
    expect(password).not.toMatch(/\sdefaultvalue=/i);
  });

  it("el componente no recibe la contraseña: no hay propiedad para ella", () => {
    expect(Object.keys(BASE)).not.toContain("password");
  });

  it("el email sí es un campo controlado y lleva su valor", () => {
    expect(attr(inputOf(render({ email: "ana@example.com" }), "register-email"), "value")).toBe("ana@example.com");
  });
});

describe("RegistrationForm: errores enlazados a su campo", () => {
  it("sin errores no hay aria-invalid y la contraseña solo se describe con la pista", () => {
    const html = render();
    expect(inputOf(html, "register-email")).not.toMatch(/\saria-invalid=/);
    expect(inputOf(html, "register-password")).not.toMatch(/\saria-invalid=/);
    expect(attr(inputOf(html, "register-email"), "aria-describedby")).toBeUndefined();
  });

  it("con errores en el email, solo el email es inválido y apunta a su lista", () => {
    const html = render({ emailMessages: ["Ya existe una cuenta con este email."] });
    const email = inputOf(html, "register-email");
    expect(attr(email, "aria-invalid")).toBe("true");
    expect(inputOf(html, "register-password")).not.toMatch(/\saria-invalid=/);
    const listId = attr(email, "aria-describedby");
    expect(listId).toBeDefined();
    const list = tag(html, new RegExp(`<ul\\b[^>]*\\bid="${listId}"[^>]*>.*?</ul>`, "s"));
    expect(list).not.toBe("");
    expect(listItems(list).map(textOf)).toEqual(["Ya existe una cuenta con este email."]);
  });

  it("con varios errores de contraseña, un elemento por mensaje, y la lista junto a la pista", () => {
    const html = render(WITH_ERRORS);
    const password = inputOf(html, "register-password");
    expect(attr(password, "aria-invalid")).toBe("true");
    const ids = (attr(password, "aria-describedby") ?? "").split(" ");
    expect(ids).toHaveLength(2);
    for (const id of ids) expect(html).toMatch(new RegExp(`\\bid="${id}"`));
    expect(listItems(html).map(textOf)).toEqual(
      expect.arrayContaining(["Esa contraseña es demasiado común.", "La contraseña no puede tener solo números."]),
    );
  });

  it("el error de cada campo va en el token de error y con su indicador, no solo en color", () => {
    const html = render(WITH_ERRORS);
    expect(html).toContain("text-danger");
    expect(inputOf(html, "register-email")).toMatch(/\saria-invalid=/);
    const items = listItems(html);
    expect(items).toHaveLength(3);
    for (const item of items) expect(item).toContain("<svg");
  });

  it("el error general y el resumen van en la región de estado", () => {
    const html = render({ general: es.register.errors.network });
    const region = html.slice(html.indexOf('role="status"'));
    expect(region).toContain(es.register.errors.network);
  });
});

describe("RegistrationForm: envío en curso", () => {
  const html = render({ submitting: true, email: "ana@example.com" });

  it("anuncia «Creando la cuenta…» en la región de estado", () => {
    expect(html.slice(html.indexOf('role="status"'))).toContain(es.register.submitting);
  });

  it("el envío usa aria-disabled y no disabled, para conservar el foco", () => {
    const submit = buttonWith(html, es.register.submit);
    expect(attr(submit, "aria-disabled")).toBe("true");
    expect(html).not.toMatch(/\sdisabled(=|\s|>)/);
    expect(attr(submit, "type")).toBe("submit");
  });

  it("los dos campos pasan a solo lectura para que no cambien durante la operación", () => {
    expect(inputOf(html, "register-email")).toMatch(/\sreadonly=""/i);
    expect(inputOf(html, "register-password")).toMatch(/\sreadonly=""/i);
  });

  it("sin envío en curso no hay aria-disabled ni solo lectura y no se anuncia nada", () => {
    const idle = render();
    expect(buttonWith(idle, es.register.submit)).not.toMatch(/\saria-disabled=/);
    expect(inputOf(idle, "register-email")).not.toMatch(/\sreadonly=/i);
    expect(inputOf(idle, "register-password")).not.toMatch(/\sreadonly=/i);
    expect(idle).not.toContain(es.register.submitting);
  });

  it("mientras se envía no se muestra el error general anterior", () => {
    expect(render({ submitting: true, general: es.register.errors.network })).not.toContain(es.register.errors.network);
  });
});

describe("RegistrationForm: el ojo", () => {
  it("tiene nombre fijo, sin texto visible, no envía el formulario y controla la contraseña", () => {
    const eye = eyeOf(render());
    expect(eye).not.toBe("");
    expect(attr(eye, "type")).toBe("button");
    expect(attr(eye, "aria-controls")).toBe("register-password");
    expect(attr(eye, "aria-pressed")).toBe("false");
    expect(textOf(eye)).toBe("");
  });

  it("es un control del campo, no un botón con relieve", () => {
    const classes = classesOf(eyeOf(render()));
    expect(classes).toContain("eye");
    expect(classes).not.toContain("btn");
  });

  it("al mostrar la contraseña cambia aria-pressed y el tipo, pero no el nombre", () => {
    const html = render({ passwordVisible: true });
    expect(attr(eyeOf(html), "aria-pressed")).toBe("true");
    expect(attr(eyeOf(html), "aria-label")).toBe(es.register.showPassword);
    expect(attr(inputOf(html, "register-password"), "type")).toBe("text");
    expect(html).not.toContain("Ocultar");
  });

  it("dibuja el ojo abierto con la contraseña oculta y el tachado solo con ella visible", () => {
    const hidden = eyeOf(render());
    const visible = eyeOf(render({ passwordVisible: true }));
    expect(hidden).toContain("<svg");
    expect(hidden).toContain("M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12Z");
    expect(hidden).not.toContain("M3 3l18 18");
    expect(visible).toContain("M3 3l18 18");
    expect(visible).not.toContain("M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12Z");
  });

  it("va dentro de la caja del campo, tras la entrada y antes de la ayuda", () => {
    const html = render();
    const input = html.indexOf('id="register-password"');
    const eye = html.indexOf(`aria-label="${es.register.showPassword}"`);
    const hint = html.indexOf('id="register-password-hint"');
    expect(input).toBeGreaterThan(-1);
    expect(input).toBeLessThan(eye);
    expect(eye).toBeLessThan(hint);
    const box = tag(html, /<div\b[^>]*\bclass="[^"]*\bfield-box\b[^"]*"[^>]*>.*?<\/div>/s);
    expect(box).toContain('id="register-password"');
    expect(box).toContain(`aria-label="${es.register.showPassword}"`);
  });
});

describe("RegistrationForm: región de estado", () => {
  it("el error general lleva el indicador y el texto en tinta, sin fondo ni limón", () => {
    const html = render({ general: es.register.errors.network });
    const region = statusOf(html);
    expect(region).toContain("<svg");
    expect(textOf(region)).toBe(es.register.errors.network);
    const openTag = statusTagOf(html);
    expect(openTag).not.toMatch(/\bbg-/);
    expect(openTag).not.toMatch(/\btext-(danger|muted)\b/);
    expect(html).not.toContain("lemon");
  });

  it("el envío en curso va sin indicador, sin fondo y en el gris secundario", () => {
    const html = render({ submitting: true });
    const region = statusOf(html);
    expect(region).not.toContain("<svg");
    expect(textOf(region)).toBe(es.register.submitting);
    expect(classesOf(statusTagOf(html))).toContain("text-muted");
    expect(statusTagOf(html)).not.toMatch(/\bbg-/);
    expect(html).not.toContain("lemon");
  });

  it("sin estado la región está vacía y sin indicador", () => {
    const region = statusOf(render());
    expect(region).not.toContain("<svg");
    expect(textOf(region)).toBe("");
  });
});

describe("RegistrationForm: iconos decorativos", () => {
  const STATES: [string, Partial<Props>][] = [
    ["con errores y la contraseña oculta", WITH_ERRORS],
    ["con la contraseña visible", { passwordVisible: true, general: es.register.errors.network }],
  ];

  it.each(STATES)("%s, todos los SVG van ocultos a la tecnología de apoyo y sin foco", (_name, props) => {
    const svgs = svgTags(render(props));
    expect(svgs.length).toBeGreaterThanOrEqual(2);
    for (const svg of svgs) {
      expect(attr(svg, "aria-hidden")).toBe("true");
      expect(attr(svg, "focusable")).toBe("false");
    }
  });

  it("el indicador de la región de estado no se anuncia: el anuncio es solo el texto", () => {
    const region = statusOf(render({ general: es.register.summary }));
    const svgs = svgTags(region);
    expect(svgs).toHaveLength(1);
    expect(attr(svgs[0] ?? "", "aria-hidden")).toBe("true");
    expect(attr(svgs[0] ?? "", "focusable")).toBe("false");
    expect(textOf(region)).toBe(es.register.summary);
  });
});

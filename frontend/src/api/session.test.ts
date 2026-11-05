import { afterEach, describe, expect, expectTypeOf, it, vi } from "vitest";

import type { FetchInit } from "./publicAssets";
import {
  createSessionClient,
  readCsrfToken,
  sessionClient,
  type SessionFetchInit,
} from "./session";

const SESSION_URL = "/api/v1/auth/session/";
const REGISTER_URL = "/api/v1/auth/register/";
const LOGOUT_URL = "/api/v1/auth/logout/";

const WHO_AM_I_MS = 5_000;
const WRITE_MS = 10_000;

const TOKEN_A = "A1b2".repeat(8);
const TOKEN_B = "Z9y8".repeat(8);
const TOKEN_LONG = "Q7w3".repeat(16);
const COOKIE_A = `csrftoken=${TOKEN_A}`;
const COOKIE_B = `csrftoken=${TOKEN_B}`;

const CREDENTIALS = { email: "ana@example.com", password: "una contraseña larga" };

// Cada intento arma su temporizador: se ve cuántos, con qué espera y si se cancelan todos
function createTimers() {
  const entries: { ms: number; callback: () => void; active: boolean }[] = [];
  const timers = {
    get armedWith(): number[] {
      return entries.map((entry) => entry.ms);
    },
    clearCalls: 0,
    setTimer(callback: () => void, ms: number): number {
      entries.push({ ms, callback, active: true });
      return entries.length - 1;
    },
    clearTimer(handle: number): void {
      timers.clearCalls += 1;
      const entry = entries[handle];
      if (entry) entry.active = false;
    },
    // Vence el último temporizador que sigue armado
    fire(): void {
      const entry = [...entries].reverse().find((candidate) => candidate.active);
      if (!entry) throw new Error("No hay ningún temporizador armado");
      entry.active = false;
      entry.callback();
    },
  };
  return timers;
}

function tick(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, 0));
}

// Espera a que el cliente haya armado `count` temporizadores
async function armed(timers: ReturnType<typeof createTimers>, count: number): Promise<void> {
  for (let attempt = 0; attempt < 50 && timers.armedWith.length < count; attempt += 1) {
    await tick();
  }
  if (timers.armedWith.length < count) throw new Error("El cliente no armó el temporizador esperado");
}

type Responder = (init: SessionFetchInit, url: string) => Response | Promise<Response>;
type Call = { url: string; init: SessionFetchInit };

function setup(script: Responder[], cookies: string[] = [COOKIE_A]) {
  const timers = createTimers();
  const calls: Call[] = [];
  let next = 0;
  let reads = 0;
  const readCookies = vi.fn(() => cookies[Math.min(reads++, cookies.length - 1)] ?? "");
  const client = createSessionClient({
    fetch: (url, init) => {
      calls.push({ url, init });
      const responder = script[next++];
      if (!responder) return Promise.reject(new Error(`Petición no prevista a ${url}`));
      return Promise.resolve().then(() => responder(init, url));
    },
    readCookies,
    setTimer: timers.setTimer,
    clearTimer: timers.clearTimer,
    whoAmITimeoutMs: WHO_AM_I_MS,
    writeTimeoutMs: WRITE_MS,
  });
  return { client, timers, calls, readCookies };
}

function json(body: unknown, status = 200, headers: Record<string, string> = {}): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...headers },
  });
}

const registered = () => json({ user: { email: "ana@example.com" } }, 201);
const authenticated = () => json({ user: { email: "ana@example.com" } });
const anonymous = () => json({ user: null });
const csrfFailed = () => json({ code: "csrf_failed" }, 403);
const loggedOut = () => new Response(null, { status: 204 });

// Un fetch que respeta la señal: no responde hasta que se aborta
const hang: Responder = (init) =>
  new Promise<Response>((_resolve, reject) => {
    if (init.signal.aborted) {
      reject(init.signal.reason);
      return;
    }
    init.signal.addEventListener("abort", () => reject(init.signal.reason), { once: true });
  });

// Llegan las cabeceras pero el cuerpo no termina; el flujo falla al abortar la señal
const bodyThatNeverArrives =
  (status: number): Responder =>
  (init) => {
    const body = new ReadableStream<Uint8Array>({
      start(controller) {
        init.signal.addEventListener("abort", () => controller.error(init.signal.reason), { once: true });
      },
    });
    return new Response(body, { status, headers: { "Content-Type": "application/json" } });
  };

// Llegan las cabeceras y el flujo del cuerpo se corta con un TypeError, como al caerse la conexión
const bodyThatIsCutOff =
  (status: number): Responder =>
  () => {
    const body = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.error(new TypeError("terminated"));
      },
    });
    return new Response(body, { status, headers: { "Content-Type": "application/json" } });
  };

// El cuerpo se corta con un TypeError justo cuando se aborta la señal, es decir, cuando vence el temporizador
const bodyThatIsCutOffWhenAborted =
  (status: number): Responder =>
  (init) => {
    const body = new ReadableStream<Uint8Array>({
      start(controller) {
        init.signal.addEventListener("abort", () => controller.error(new TypeError("terminated")), { once: true });
      },
    });
    return new Response(body, { status, headers: { "Content-Type": "application/json" } });
  };

// La lectura del cuerpo falla con un error que no es de red: es del código y no se esconde
function bodyThatFailsInTheCode(status: number, failure: Error): Responder {
  return () => {
    const response = new Response("{}", { status, headers: { "Content-Type": "application/json" } });
    vi.spyOn(response, "json").mockRejectedValue(failure);
    return response;
  };
}

const networkDown: Responder = () => {
  throw new TypeError("Failed to fetch");
};

async function rejection(promise: Promise<unknown>): Promise<unknown> {
  try {
    await promise;
  } catch (error) {
    return error;
  }
  throw new Error("La promesa se esperaba rechazada");
}

function headersOf(call: Call | undefined): Record<string, string> {
  return (call?.init.headers ?? {}) as Record<string, string>;
}

function watchConsole() {
  return (["log", "info", "warn", "error", "debug"] as const).map((method) =>
    vi.spyOn(console, method).mockImplementation(() => undefined),
  );
}

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("readCsrfToken", () => {
  it.each([
    ["32 caracteres", `csrftoken=${TOKEN_A}`, TOKEN_A],
    ["64 caracteres", `csrftoken=${TOKEN_LONG}`, TOKEN_LONG],
    ["entre otras cookies", `a=1; csrftoken=${TOKEN_A}; b=2`, TOKEN_A],
    ["con espacios alrededor", `  csrftoken=${TOKEN_A}  `, TOKEN_A],
    ["el primero válido de varios", `csrftoken=${TOKEN_A}; csrftoken=${TOKEN_B}`, TOKEN_A],
    ["salta uno corto", `csrftoken=corto; csrftoken=${TOKEN_B}`, TOKEN_B],
    ["salta uno vacío", `csrftoken=; csrftoken=${TOKEN_B}`, TOKEN_B],
    ["salta uno de 33", `csrftoken=${TOKEN_A}x; csrftoken=${TOKEN_B}`, TOKEN_B],
    ["salta uno de 63", `csrftoken=${TOKEN_LONG.slice(1)}; csrftoken=${TOKEN_B}`, TOKEN_B],
    ["salta uno de 65", `csrftoken=${TOKEN_LONG}x; csrftoken=${TOKEN_B}`, TOKEN_B],
    ["salta uno con símbolos", `csrftoken=${TOKEN_A.slice(1)}-; csrftoken=${TOKEN_B}`, TOKEN_B],
    ["salta uno con guion bajo", `csrftoken=${TOKEN_A.slice(1)}_; csrftoken=${TOKEN_B}`, TOKEN_B],
  ])("%s", (_name, cookies, expected) => {
    expect(readCsrfToken(cookies)).toBe(expected);
  });

  it.each([
    ["cadena vacía", ""],
    ["sin la cookie", "sessionid=abc; theme=dark"],
    ["solo mal formadas", `csrftoken=corto; csrftoken=${TOKEN_A}x`],
    ["otro nombre con el mismo sufijo", `xcsrftoken=${TOKEN_A}`],
    ["otro nombre con el mismo prefijo", `csrftoken2=${TOKEN_A}`],
    ["mayúsculas en el nombre", `CSRFTOKEN=${TOKEN_A}`],
    ["el token como nombre", `${TOKEN_A}=csrftoken`],
    ["sin igual", `csrftoken${TOKEN_A}`],
    ["de 31 caracteres", `csrftoken=${TOKEN_A.slice(1)}`],
  ])("devuelve null: %s", (_name, cookies) => {
    expect(readCsrfToken(cookies)).toBeNull();
  });
});

describe("el cliente de sesión: tipos de la petición", () => {
  it("el cliente de sesión envía las cookies del mismo origen y el público sigue en omit", () => {
    expectTypeOf<SessionFetchInit["credentials"]>().toEqualTypeOf<"same-origin">();
    expectTypeOf<FetchInit["credentials"]>().toEqualTypeOf<"omit">();
  });
});

describe("whoAmI", () => {
  it("hace un GET a la ruta con barra final, con las cookies del mismo origen y sin cuerpo", async () => {
    const { client, calls, timers } = setup([authenticated]);

    expect(await client.whoAmI()).toBe("authenticated");

    expect(calls).toHaveLength(1);
    expect(calls[0]?.url).toBe(SESSION_URL);
    expect(calls[0]?.init.method).toBe("GET");
    expect(calls[0]?.init.credentials).toBe("same-origin");
    expect(calls[0]?.init.signal).toBeInstanceOf(AbortSignal);
    expect(Object.keys(calls[0]?.init ?? {}).sort()).toEqual(["credentials", "method", "signal"]);
    expect(timers.armedWith).toEqual([WHO_AM_I_MS]);
    expect(timers.clearCalls).toBe(1);
  });

  it("no lee la cookie del token: un GET no lo necesita", async () => {
    const { client, readCookies } = setup([authenticated]);
    await client.whoAmI();
    expect(readCookies).not.toHaveBeenCalled();
  });

  it("responde anonymous cuando el servidor dice que no hay sesión", async () => {
    const { client } = setup([anonymous]);
    expect(await client.whoAmI()).toBe("anonymous");
  });

  it.each([
    ["500 con JSON", () => json({ code: "x" }, 500)],
    ["503 vacío", () => new Response(null, { status: 503 })],
    ["404", () => json({ code: "not_found" }, 404)],
    ["204", () => new Response(null, { status: 204 })],
    ["201 con una sesión válida", () => json({ user: { email: "ana@example.com" } }, 201)],
    ["un Content-Type ajeno", () => new Response('{"user":null}', { headers: { "Content-Type": "text/html" } })],
    ["application/jsonp", () => new Response('{"user":null}', { headers: { "Content-Type": "application/jsonp" } })],
    ["sin Content-Type", () => new Response(new TextEncoder().encode('{"user":{"email":"a@b.c"}}'))],
    ["JSON roto", () => new Response('{"user":', { headers: { "Content-Type": "application/json" } })],
    ["sin la clave user", () => json({})],
    ["user sin email", () => json({ user: {} })],
    ["email vacío", () => json({ user: { email: "" } })],
    ["email que no es texto", () => json({ user: { email: 5 } })],
    ["user que no es objeto", () => json({ user: "ana@example.com" })],
    ["campo desconocido en user", () => json({ user: { email: "ana@example.com", id: 1 } })],
    ["campo desconocido en la raíz", () => json({ user: null, extra: true })],
    ["una lista", () => json([])],
    ["un texto", () => json("sesión")],
    ["null", () => json(null)],
  ])("responde anonymous ante %s, sin escribir en la consola", async (_name, respond) => {
    const spies = watchConsole();
    const { client } = setup([respond]);

    expect(await client.whoAmI()).toBe("anonymous");

    for (const spy of spies) expect(spy).not.toHaveBeenCalled();
  });

  it("responde anonymous ante un fallo de red, sin escribir en la consola", async () => {
    const spies = watchConsole();
    const { client, timers } = setup([networkDown]);

    expect(await client.whoAmI()).toBe("anonymous");

    expect(timers.clearCalls).toBe(1);
    for (const spy of spies) expect(spy).not.toHaveBeenCalled();
  });

  it("a 5 s sin respuesta responde anonymous y aborta la petición", async () => {
    const spies = watchConsole();
    const { client, timers, calls } = setup([hang]);

    const pending = client.whoAmI();
    timers.fire();

    expect(await pending).toBe("anonymous");
    expect(timers.armedWith).toEqual([WHO_AM_I_MS]);
    expect(calls[0]?.init.signal.aborted).toBe(true);
    expect(timers.clearCalls).toBe(1);
    for (const spy of spies) expect(spy).not.toHaveBeenCalled();
  });

  it("un cuerpo que nunca llega también vence a los 5 s", async () => {
    const { client, timers } = setup([bodyThatNeverArrives(200)]);

    const pending = client.whoAmI();
    await tick();
    expect(timers.clearCalls).toBe(0);
    timers.fire();

    expect(await pending).toBe("anonymous");
  });

  it("cancelado por quien lo pide relanza el AbortError tal cual, sin responder anonymous", async () => {
    const controller = new AbortController();
    const { client, timers, calls } = setup([hang]);

    const pending = client.whoAmI(controller.signal);
    await tick();
    controller.abort();

    const error = await rejection(pending);
    expect(error).toBe(controller.signal.reason);
    expect((error as DOMException).name).toBe("AbortError");
    expect(calls[0]?.init.signal.aborted).toBe(true);
    expect(timers.clearCalls).toBe(1);
  });

  it("con la señal ya abortada relanza el AbortError sin pedir nada ni armar el temporizador", async () => {
    const controller = new AbortController();
    controller.abort();
    const { client, timers, calls } = setup([authenticated]);

    const error = await rejection(client.whoAmI(controller.signal));

    expect(error).toBe(controller.signal.reason);
    expect(calls).toEqual([]);
    expect(timers.armedWith).toEqual([]);
  });

  it("un cuerpo cortado a medias (TypeError al leerlo) responde anonymous, sin escribir en la consola", async () => {
    const spies = watchConsole();
    const { client, timers } = setup([bodyThatIsCutOff(200)]);

    expect(await client.whoAmI()).toBe("anonymous");

    expect(timers.clearCalls).toBe(1);
    for (const spy of spies) expect(spy).not.toHaveBeenCalled();
  });

  it("un error que no es un TypeError al leer el cuerpo se propaga", async () => {
    const failure = new RangeError("fallo propio");
    const { client } = setup([bodyThatFailsInTheCode(200, failure)]);

    expect(await rejection(client.whoAmI())).toBe(failure);
  });

  it("un error inesperado de fetch se propaga: no se esconde un fallo del código", async () => {
    const failure = new RangeError("fallo propio");
    const { client } = setup([
      () => {
        throw failure;
      },
    ]);
    expect(await rejection(client.whoAmI())).toBe(failure);
  });
});

describe("register: la petición", () => {
  it("hace un POST JSON a la ruta con barra final, con el token y las cookies del mismo origen", async () => {
    const { client, calls, timers } = setup([registered]);

    expect(await client.register(CREDENTIALS)).toEqual({ kind: "registered" });

    expect(calls).toHaveLength(1);
    expect(calls[0]?.url).toBe(REGISTER_URL);
    expect(calls[0]?.init.method).toBe("POST");
    expect(calls[0]?.init.credentials).toBe("same-origin");
    expect(calls[0]?.init.signal).toBeInstanceOf(AbortSignal);
    expect(headersOf(calls[0])).toEqual({ "Content-Type": "application/json", "X-CSRFToken": TOKEN_A });
    expect(JSON.parse(calls[0]?.init.body ?? "null")).toEqual(CREDENTIALS);
    expect(Object.keys(JSON.parse(calls[0]?.init.body ?? "{}")).sort()).toEqual(["email", "password"]);
    expect(timers.armedWith).toEqual([WRITE_MS]);
    expect(timers.clearCalls).toBe(1);
  });

  it("envía el token de 64 caracteres tal cual", async () => {
    const { client, calls } = setup([registered], [`csrftoken=${TOKEN_LONG}`]);
    await client.register(CREDENTIALS);
    expect(headersOf(calls[0])["X-CSRFToken"]).toBe(TOKEN_LONG);
  });

  it.each([
    ["sin cookies", ""],
    ["sin la cookie del token", "sessionid=abc"],
    ["con un token corto", "csrftoken=corto"],
    ["con un token de 33 caracteres", `csrftoken=${TOKEN_A}x`],
    ["con símbolos", `csrftoken=${TOKEN_A.slice(1)}!`],
  ])("%s: no envía la cabecera X-CSRFToken (el servidor responderá csrf_failed)", async (_name, cookies) => {
    const { client, calls } = setup([registered], [cookies]);

    await client.register(CREDENTIALS);

    expect(headersOf(calls[0])).toEqual({ "Content-Type": "application/json" });
    expect(Object.keys(headersOf(calls[0]))).not.toContain("X-CSRFToken");
  });

  it("lee la cookie en cada envío, sin guardar el token: dos registros seguidos usan cada uno el suyo", async () => {
    const { client, calls, readCookies } = setup([registered, registered], [COOKIE_A, COOKIE_B]);

    await client.register(CREDENTIALS);
    await client.register(CREDENTIALS);

    expect(readCookies).toHaveBeenCalledTimes(2);
    expect(headersOf(calls[0])["X-CSRFToken"]).toBe(TOKEN_A);
    expect(headersOf(calls[1])["X-CSRFToken"]).toBe(TOKEN_B);
  });

  it("no lee la cookie hasta que se envía: el valor del momento del envío es el que viaja", async () => {
    const { client, calls, readCookies } = setup([registered], [COOKIE_B]);
    expect(readCookies).not.toHaveBeenCalled();
    await client.register(CREDENTIALS);
    expect(headersOf(calls[0])["X-CSRFToken"]).toBe(TOKEN_B);
  });
});

describe("register: el reintento ante csrf_failed", () => {
  it("pregunta quién soy y reintenta una sola vez, releyendo el token en el reintento", async () => {
    const { client, calls, readCookies, timers } = setup(
      [csrfFailed, anonymous, registered],
      [COOKIE_A, COOKIE_B],
    );

    expect(await client.register(CREDENTIALS)).toEqual({ kind: "registered" });

    expect(calls.map((call) => call.url)).toEqual([REGISTER_URL, SESSION_URL, REGISTER_URL]);
    expect(readCookies).toHaveBeenCalledTimes(2);
    expect(headersOf(calls[0])["X-CSRFToken"]).toBe(TOKEN_A);
    expect(headersOf(calls[2])["X-CSRFToken"]).toBe(TOKEN_B);
    expect(JSON.parse(calls[2]?.init.body ?? "null")).toEqual(CREDENTIALS);
    expect(timers.armedWith).toEqual([WRITE_MS, WHO_AM_I_MS, WRITE_MS]);
    expect(timers.clearCalls).toBe(3);
  });

  it("si el segundo intento vuelve a dar csrf_failed, es el error general y no hay un tercer envío", async () => {
    const { client, calls } = setup([csrfFailed, anonymous, csrfFailed, authenticated, registered]);

    expect(await client.register(CREDENTIALS)).toEqual({ kind: "failed", reason: "csrf" });

    expect(calls.map((call) => call.url)).toEqual([REGISTER_URL, SESSION_URL, REGISTER_URL]);
  });

  it.each([
    ["con sesión", authenticated],
    ["con un error del servidor", () => json({ code: "x" }, 500)],
    ["con la red caída", networkDown],
  ] as const)("reintenta igualmente cuando quién soy responde %s", async (_name, whoAmI) => {
    const { client, calls } = setup([csrfFailed, whoAmI, registered]);

    expect(await client.register(CREDENTIALS)).toEqual({ kind: "registered" });

    expect(calls.map((call) => call.url)).toEqual([REGISTER_URL, SESSION_URL, REGISTER_URL]);
  });

  it("el resultado del reintento se trata como el de cualquier envío", async () => {
    const taken = () => json({ code: "invalid_fields", params: { email: ["email_taken"] } }, 400);
    const { client } = setup([csrfFailed, anonymous, taken]);

    expect(await client.register(CREDENTIALS)).toEqual({
      kind: "fieldErrors",
      email: ["email_taken"],
      password: [],
      other: [],
    });
  });

  it("si el reintento vence, pregunta quién soy (sin sesión es failed timeout) y no reintenta más", async () => {
    const { client, calls, timers } = setup([csrfFailed, anonymous, hang, anonymous]);

    const pending = client.register(CREDENTIALS);
    await armed(timers, 3);
    timers.fire();

    expect(await pending).toEqual({ kind: "failed", reason: "timeout" });
    expect(calls.map((call) => call.url)).toEqual([REGISTER_URL, SESSION_URL, REGISTER_URL, SESSION_URL]);
  });

  it("un 403 con otro código no se reintenta", async () => {
    const { client, calls } = setup([() => json({ code: "forbidden" }, 403), anonymous, registered]);

    expect(await client.register(CREDENTIALS)).toEqual({ kind: "failed", reason: "request" });

    expect(calls).toHaveLength(1);
  });

  it("csrf_failed con otro estado no se reintenta", async () => {
    const { client, calls } = setup([() => json({ code: "csrf_failed" }, 400), anonymous, registered]);

    expect(await client.register(CREDENTIALS)).toEqual({ kind: "failed", reason: "request" });

    expect(calls).toHaveLength(1);
  });
});

describe("register: el tiempo máximo", () => {
  it("espera 10 s, aborta la petición y, con sesión, es un éxito", async () => {
    const { client, calls, timers } = setup([hang, authenticated]);

    const pending = client.register(CREDENTIALS);
    timers.fire();

    expect(await pending).toEqual({ kind: "registered" });
    expect(timers.armedWith).toEqual([WRITE_MS, WHO_AM_I_MS]);
    expect(calls[0]?.init.signal.aborted).toBe(true);
    expect(calls.map((call) => call.url)).toEqual([REGISTER_URL, SESSION_URL]);
    expect(timers.clearCalls).toBe(2);
  });

  it("vencido y sin sesión es failed timeout", async () => {
    const { client, timers } = setup([hang, anonymous]);

    const pending = client.register(CREDENTIALS);
    timers.fire();

    expect(await pending).toEqual({ kind: "failed", reason: "timeout" });
  });

  it.each([
    ["con un error del servidor", () => json({ code: "x" }, 500)],
    ["con la red caída", networkDown],
    ["con una forma inválida", () => json({ user: "x" })],
  ] as const)("vencido y con quién soy %s es failed timeout", async (_name, whoAmI) => {
    const { client, timers } = setup([hang, whoAmI]);

    const pending = client.register(CREDENTIALS);
    timers.fire();

    expect(await pending).toEqual({ kind: "failed", reason: "timeout" });
  });

  it("un cuerpo que llegó a medias también vence a los 10 s", async () => {
    const { client, timers } = setup([bodyThatNeverArrives(201), authenticated]);

    const pending = client.register(CREDENTIALS);
    await tick();
    expect(timers.clearCalls).toBe(0);
    timers.fire();

    expect(await pending).toEqual({ kind: "registered" });
  });

  it.each([
    ["con sesión", authenticated, { kind: "registered" }],
    ["sin sesión", anonymous, { kind: "failed", reason: "network" }],
  ] as const)(
    "un 201 cuyo cuerpo se corta con un TypeError al vencer el temporizador pregunta quién soy y, %s, gana la etiqueta del valor devuelto",
    async (_name, whoAmI, expected) => {
      const spies = watchConsole();
      const { client, calls, timers } = setup([bodyThatIsCutOffWhenAborted(201), whoAmI]);

      const pending = client.register(CREDENTIALS);
      await tick();
      expect(timers.clearCalls).toBe(0);
      timers.fire();

      expect(await pending).toEqual(expected);
      expect(calls.map((call) => call.url)).toEqual([REGISTER_URL, SESSION_URL]);
      expect(calls[0]?.init.signal.aborted).toBe(true);
      expect(timers.armedWith).toEqual([WRITE_MS, WHO_AM_I_MS]);
      expect(timers.clearCalls).toBe(2);
      for (const spy of spies) expect(spy).not.toHaveBeenCalled();
    },
  );

  it("un fallo de red que llega con el temporizador ya disparado sigue siendo un tiempo vencido", async () => {
    const { client, timers } = setup([
      (init) =>
        new Promise<Response>((_resolve, reject) => {
          if (init.signal.aborted) {
            reject(new TypeError("Failed to fetch"));
            return;
          }
          init.signal.addEventListener("abort", () => reject(new TypeError("Failed to fetch")), { once: true });
        }),
      anonymous,
    ]);

    const pending = client.register(CREDENTIALS);
    timers.fire();

    expect(await pending).toEqual({ kind: "failed", reason: "timeout" });
  });

  it("la pregunta de quién soy tras vencer tiene su propio temporizador de 5 s", async () => {
    const { client, timers, calls } = setup([hang, hang]);

    const pending = client.register(CREDENTIALS);
    timers.fire();
    await armed(timers, 2);
    expect(timers.armedWith).toEqual([WRITE_MS, WHO_AM_I_MS]);
    timers.fire();

    expect(await pending).toEqual({ kind: "failed", reason: "timeout" });
    expect(calls[1]?.init.signal.aborted).toBe(true);
  });
});

describe("register: la respuesta", () => {
  it("un 201 válido es registered y no pregunta quién soy", async () => {
    const { client, calls } = setup([registered, authenticated]);

    expect(await client.register(CREDENTIALS)).toEqual({ kind: "registered" });

    expect(calls).toHaveLength(1);
  });

  it.each([
    ["user nulo", () => json({ user: null }, 201)],
    ["sin user", () => json({}, 201)],
    ["user sin email", () => json({ user: {} }, 201)],
    ["email vacío", () => json({ user: { email: "" } }, 201)],
    ["email que no es texto", () => json({ user: { email: 3 } }, 201)],
    ["campo desconocido en user", () => json({ user: { email: "ana@example.com", id: 1 } }, 201)],
    ["campo desconocido en la raíz", () => json({ user: { email: "ana@example.com" }, extra: 1 }, 201)],
    ["una lista", () => json([], 201)],
    ["un Content-Type ajeno", () => new Response('{"user":{"email":"a@b.c"}}', { status: 201, headers: { "Content-Type": "text/html" } })],
    ["sin Content-Type", () => new Response(new TextEncoder().encode('{"user":{"email":"a@b.c"}}'), { status: 201 })],
    ["JSON roto", () => new Response('{"user":', { status: 201, headers: { "Content-Type": "application/json" } })],
  ])("un 201 con %s pregunta quién soy: con sesión es registered", async (_name, respond) => {
    const { client, calls } = setup([respond, authenticated]);

    expect(await client.register(CREDENTIALS)).toEqual({ kind: "registered" });

    expect(calls.map((call) => call.url)).toEqual([REGISTER_URL, SESSION_URL]);
  });

  it.each([
    ["user nulo", () => json({ user: null }, 201)],
    ["sin user", () => json({}, 201)],
    ["un Content-Type ajeno", () => new Response('{"user":{"email":"a@b.c"}}', { status: 201, headers: { "Content-Type": "text/html" } })],
    ["JSON roto", () => new Response('{"user":', { status: 201, headers: { "Content-Type": "application/json" } })],
  ])("un 201 con %s y sin sesión es failed invalid", async (_name, respond) => {
    const { client, calls } = setup([respond, anonymous]);

    expect(await client.register(CREDENTIALS)).toEqual({ kind: "failed", reason: "invalid" });

    expect(calls.map((call) => call.url)).toEqual([REGISTER_URL, SESSION_URL]);
  });

  it.each([
    [400, "invalid_request"],
    [405, "method_not_allowed"],
    [413, "payload_too_large"],
    [403, "forbidden"],
    [404, "not_found"],
    [401, "unauthorized"],
    [422, "algo_nuevo"],
  ])("un %d con el código %s es failed request, sin reintento ni quién soy", async (status, code) => {
    const { client, calls } = setup([() => json({ code }, status), anonymous, registered]);

    expect(await client.register(CREDENTIALS)).toEqual({ kind: "failed", reason: "request" });

    expect(calls).toHaveLength(1);
  });

  it.each([
    ["HTML", () => new Response("<html></html>", { status: 400, headers: { "Content-Type": "text/html" } })],
    ["sin Content-Type", () => new Response(new TextEncoder().encode('{"code":"x"}'), { status: 400 })],
    ["JSON roto", () => new Response('{"code":', { status: 400, headers: { "Content-Type": "application/json" } })],
    ["sin code", () => json({}, 400)],
    ["code que no es texto", () => json({ code: 5 }, 400)],
    ["campo desconocido", () => json({ code: "invalid_request", detail: "x" }, 400)],
    ["retry_after cero", () => json({ code: "invalid_request", retry_after: 0 }, 400)],
    ["params con valores de otro tipo", () => json({ code: "invalid_request", params: { a: 1 } }, 400)],
    ["una lista", () => json([], 400)],
  ])("un 4xx con un cuerpo que es %s es failed invalid", async (_name, respond) => {
    const { client, calls } = setup([respond]);

    expect(await client.register(CREDENTIALS)).toEqual({ kind: "failed", reason: "invalid" });

    expect(calls).toHaveLength(1);
  });

  it("un 403 sin cuerpo válido tampoco se reintenta", async () => {
    const { client, calls } = setup([() => new Response("Forbidden", { status: 403 }), anonymous, registered]);

    expect(await client.register(CREDENTIALS)).toEqual({ kind: "failed", reason: "invalid" });

    expect(calls).toHaveLength(1);
  });

  it.each([1, 59, 60, 61, 3600, 86400])("un 429 con retry_after %d es throttled con ese valor", async (seconds) => {
    const { client, calls } = setup([() => json({ code: "throttled", retry_after: seconds }, 429)]);

    expect(await client.register(CREDENTIALS)).toEqual({ kind: "throttled", retryAfterSeconds: seconds });

    expect(calls).toHaveLength(1);
  });

  it("un 429 toma retry_after del cuerpo e ignora la cabecera Retry-After", async () => {
    const { client } = setup([() => json({ code: "throttled", retry_after: 120 }, 429, { "Retry-After": "5" })]);

    expect(await client.register(CREDENTIALS)).toEqual({ kind: "throttled", retryAfterSeconds: 120 });
  });

  it.each(["algo_nuevo", "rate_limited"])("un 429 con el code %s también es throttled: no se exige el code", async (code) => {
    const { client, calls } = setup([() => json({ code, retry_after: 120 }, 429)]);

    expect(await client.register(CREDENTIALS)).toEqual({ kind: "throttled", retryAfterSeconds: 120 });

    expect(calls).toHaveLength(1);
  });

  it.each([
    ["sin retry_after pero con la cabecera", () => json({ code: "throttled" }, 429, { "Retry-After": "30" })],
    ["con retry_after cero", () => json({ code: "throttled", retry_after: 0 }, 429, { "Retry-After": "30" })],
    ["con retry_after negativo", () => json({ code: "throttled", retry_after: -5 }, 429)],
    ["con retry_after por encima de un día", () => json({ code: "throttled", retry_after: 86401 }, 429)],
    ["con retry_after decimal", () => json({ code: "throttled", retry_after: 1.5 }, 429)],
    ["con retry_after como texto", () => json({ code: "throttled", retry_after: "60" }, 429)],
    ["con retry_after nulo", () => json({ code: "throttled", retry_after: null }, 429)],
    ["con un cuerpo que no es JSON", () => new Response("Too Many Requests", { status: 429, headers: { "Retry-After": "30" } })],
    ["con un cuerpo vacío", () => new Response(null, { status: 429 })],
  ])("un 429 %s es failed invalid", async (_name, respond) => {
    const { client } = setup([respond]);

    expect(await client.register(CREDENTIALS)).toEqual({ kind: "failed", reason: "invalid" });
  });

  it.each([500, 502, 503, 504, 599])("un %d es failed server y no lee el cuerpo", async (status) => {
    const response = new Response('{"code":"cualquier cosa', { status, headers: { "Content-Type": "application/json" } });
    const { client, calls } = setup([() => response, anonymous]);

    expect(await client.register(CREDENTIALS)).toEqual({ kind: "failed", reason: "server" });

    expect(response.bodyUsed).toBe(false);
    expect(calls).toHaveLength(1);
  });

  it.each([200, 202, 204, 301, 304])("un estado %d inesperado es failed invalid, sin preguntar quién soy", async (status) => {
    const { client, calls } = setup([
      () => new Response(status === 204 || status === 304 ? null : "{}", { status }),
      authenticated,
    ]);

    expect(await client.register(CREDENTIALS)).toEqual({ kind: "failed", reason: "invalid" });

    expect(calls).toHaveLength(1);
  });

  it("un estado informativo (1xx) es failed invalid, sin preguntar quién soy", async () => {
    const informational = { status: 101, headers: new Headers() } as unknown as Response;
    const { client, calls } = setup([() => informational, authenticated]);

    expect(await client.register(CREDENTIALS)).toEqual({ kind: "failed", reason: "invalid" });

    expect(calls).toHaveLength(1);
  });

  it("un TypeError de fetch es failed network, sin preguntar quién soy ni reintentar", async () => {
    const spies = watchConsole();
    const { client, calls, timers } = setup([networkDown, authenticated, registered]);

    expect(await client.register(CREDENTIALS)).toEqual({ kind: "failed", reason: "network" });

    expect(calls).toHaveLength(1);
    expect(timers.clearCalls).toBe(1);
    for (const spy of spies) expect(spy).not.toHaveBeenCalled();
  });

  it.each([400, 404, 413, 429])(
    "un %d con el cuerpo cortado es failed network, sin preguntar quién soy y sin escribir en la consola",
    async (status) => {
      const spies = watchConsole();
      const { client, calls, timers } = setup([bodyThatIsCutOff(status), authenticated, registered]);

      expect(await client.register(CREDENTIALS)).toEqual({ kind: "failed", reason: "network" });

      expect(calls).toHaveLength(1);
      expect(timers.armedWith).toEqual([WRITE_MS]);
      expect(timers.clearCalls).toBe(1);
      for (const spy of spies) expect(spy).not.toHaveBeenCalled();
    },
  );

  it("un 403 con el cuerpo cortado no se reintenta ni pregunta quién soy: no se puede saber si era csrf_failed", async () => {
    const { client, calls, readCookies } = setup([bodyThatIsCutOff(403), anonymous, registered], [COOKIE_A, COOKIE_B]);

    expect(await client.register(CREDENTIALS)).toEqual({ kind: "failed", reason: "network" });

    expect(calls.map((call) => call.url)).toEqual([REGISTER_URL]);
    expect(readCookies).toHaveBeenCalledTimes(1);
  });

  it("un 201 con el cuerpo cortado pregunta quién soy: con sesión es registered", async () => {
    const spies = watchConsole();
    const { client, calls, timers } = setup([bodyThatIsCutOff(201), authenticated]);

    expect(await client.register(CREDENTIALS)).toEqual({ kind: "registered" });

    expect(calls.map((call) => call.url)).toEqual([REGISTER_URL, SESSION_URL]);
    expect(timers.armedWith).toEqual([WRITE_MS, WHO_AM_I_MS]);
    expect(timers.clearCalls).toBe(2);
    for (const spy of spies) expect(spy).not.toHaveBeenCalled();
  });

  it.each([
    ["sin sesión", anonymous],
    ["con un error del servidor", () => json({ code: "x" }, 500)],
    ["con la red caída", networkDown],
  ] as const)("un 201 con el cuerpo cortado y quién soy %s es failed network", async (_name, whoAmI) => {
    const { client, calls } = setup([bodyThatIsCutOff(201), whoAmI]);

    expect(await client.register(CREDENTIALS)).toEqual({ kind: "failed", reason: "network" });

    expect(calls.map((call) => call.url)).toEqual([REGISTER_URL, SESSION_URL]);
  });

  it.each([201, 400, 403, 429])("un error que no es un TypeError al leer el cuerpo de un %d se propaga", async (status) => {
    const failure = new RangeError("fallo propio");
    const { client, calls } = setup([bodyThatFailsInTheCode(status, failure), anonymous]);

    expect(await rejection(client.register(CREDENTIALS))).toBe(failure);

    expect(calls).toHaveLength(1);
  });

  it("un error inesperado de fetch se propaga sin clasificar", async () => {
    const failure = new RangeError("fallo propio");
    const { client } = setup([
      () => {
        throw failure;
      },
    ]);

    expect(await rejection(client.register(CREDENTIALS))).toBe(failure);
  });
});

describe("register: errores por campo", () => {
  const invalidFields = (params: unknown) => () => json({ code: "invalid_fields", params }, 400);

  async function fieldErrors(params: unknown) {
    const { client, calls } = setup([invalidFields(params)]);
    const outcome = await client.register(CREDENTIALS);
    expect(calls).toHaveLength(1);
    return outcome;
  }

  it.each(["email_empty", "email_invalid", "email_control_char", "email_too_long", "email_taken"])(
    "reconoce el código de email %s",
    async (code) => {
      expect(await fieldErrors({ email: [code] })).toEqual({ kind: "fieldErrors", email: [code], password: [], other: [] });
    },
  );

  it.each([
    "password_required",
    "password_invalid",
    "password_too_long",
    "password_too_short",
    "password_too_common",
    "password_entirely_numeric",
    "password_too_similar",
  ])("reconoce el código de contraseña %s", async (code) => {
    expect(await fieldErrors({ password: [code] })).toEqual({ kind: "fieldErrors", email: [], password: [code], other: [] });
  });

  it.each(["constraint_violated", "validation_failed"])("reconoce el código general %s de non_field", async (code) => {
    expect(await fieldErrors({ non_field: [code] })).toEqual({ kind: "fieldErrors", email: [], password: [], other: [code] });
  });

  it("conserva el orden de los códigos de cada campo", async () => {
    expect(
      await fieldErrors({
        email: ["email_taken", "email_invalid", "email_empty"],
        password: ["password_too_short", "password_too_common", "password_entirely_numeric", "password_too_similar"],
      }),
    ).toEqual({
      kind: "fieldErrors",
      email: ["email_taken", "email_invalid", "email_empty"],
      password: ["password_too_short", "password_too_common", "password_entirely_numeric", "password_too_similar"],
      other: [],
    });
  });

  it("reparte los tres campos a la vez", async () => {
    expect(
      await fieldErrors({
        email: ["email_taken"],
        password: ["password_too_short"],
        non_field: ["constraint_violated"],
      }),
    ).toEqual({
      kind: "fieldErrors",
      email: ["email_taken"],
      password: ["password_too_short"],
      other: ["constraint_violated"],
    });
  });

  it.each([
    ["email", { email: ["email_taken", "codigo_nuevo"] }, { email: ["email_taken", "unknown"], password: [], other: [] }],
    ["email", { email: ["codigo_nuevo"] }, { email: ["unknown"], password: [], other: [] }],
    ["password", { password: ["codigo_nuevo", "password_too_short"] }, { email: [], password: ["unknown", "password_too_short"], other: [] }],
    ["non_field", { non_field: ["codigo_nuevo"] }, { email: [], password: [], other: ["unknown"] }],
    ["email con un código de otro campo", { email: ["password_too_short"] }, { email: ["unknown"], password: [], other: [] }],
    ["email con otra capitalización", { email: ["EMAIL_TAKEN"] }, { email: ["unknown"], password: [], other: [] }],
    ["email con un nombre heredado de Object", { email: ["constructor", "toString", "__proto__"] }, { email: ["unknown", "unknown", "unknown"], password: [], other: [] }],
  ])("un código desconocido en %s se queda en su campo como unknown, sin ser un error de forma", async (_name, params, fields) => {
    expect(await fieldErrors(params)).toEqual({ kind: "fieldErrors", ...fields });
  });

  it("un campo desconocido da unknown en other, sin perder los demás errores", async () => {
    expect(await fieldErrors({ email: ["email_taken"], telefono: ["x"] })).toEqual({
      kind: "fieldErrors",
      email: ["email_taken"],
      password: [],
      other: ["unknown"],
    });
  });

  it("un campo desconocido y non_field comparten other y conservan el orden del servidor", async () => {
    expect(await fieldErrors({ non_field: ["constraint_violated"], telefono: ["x"] })).toEqual({
      kind: "fieldErrors",
      email: [],
      password: [],
      other: ["constraint_violated", "unknown"],
    });
    expect(await fieldErrors({ telefono: ["x"], non_field: ["constraint_violated"] })).toEqual({
      kind: "fieldErrors",
      email: [],
      password: [],
      other: ["unknown", "constraint_violated"],
    });
  });

  it("un nombre de campo heredado de Object es un campo desconocido y __proto__ no entra en el resultado", async () => {
    const body = '{"code":"invalid_fields","params":{"__proto__":["x"],"constructor":["y"],"email":["email_taken"]}}';
    const { client } = setup([
      () => new Response(body, { status: 400, headers: { "Content-Type": "application/json" } }),
    ]);

    expect(await client.register(CREDENTIALS)).toEqual({
      kind: "fieldErrors",
      email: ["email_taken"],
      password: [],
      other: ["unknown"],
    });
  });

  it("un código o un campo desconocido nunca da failed invalid", async () => {
    const outcome = await fieldErrors({ campo_nuevo: ["codigo_nuevo"] });
    expect(outcome).toEqual({ kind: "fieldErrors", email: [], password: [], other: ["unknown"] });
  });

  it.each([
    ["sin params", undefined],
    ["params nulo", null],
    ["params como lista", []],
    ["params como texto", "email_taken"],
    ["valores de campo como texto", { email: "email_taken" }],
    ["códigos que no son texto", { email: [1] }],
    ["códigos anidados", { email: [["email_taken"]] }],
    ["un campo bueno y otro mal formado", { email: ["email_taken"], password: "password_too_short" }],
    ["un valor nulo", { email: null }],
    ["un valor objeto", { email: { 0: "email_taken" } }],
  ])("params mal formado (%s) es failed invalid", async (_name, params) => {
    const { client } = setup([() => json({ code: "invalid_fields", ...(params === undefined ? {} : { params }) }, 400)]);

    expect(await client.register(CREDENTIALS)).toEqual({ kind: "failed", reason: "invalid" });
  });

  it.each([
    ["params vacío", {}],
    ["campos conocidos sin códigos", { email: [], password: [], non_field: [] }],
    ["un campo desconocido sin códigos", { telefono: [] }],
  ])("invalid_fields sin ninguna entrada (%s) es failed invalid", async (_name, params) => {
    const { client } = setup([invalidFields(params)]);

    expect(await client.register(CREDENTIALS)).toEqual({ kind: "failed", reason: "invalid" });
  });

  it("un invalid_fields que no es un 400 no es de campos", async () => {
    const { client } = setup([() => json({ code: "invalid_fields", params: { email: ["email_taken"] } }, 403)]);

    expect(await client.register(CREDENTIALS)).toEqual({ kind: "failed", reason: "request" });
  });

  it("invalid_request con params tampoco es de campos", async () => {
    const { client } = setup([() => json({ code: "invalid_request", params: { email: ["email_taken"] } }, 400)]);

    expect(await client.register(CREDENTIALS)).toEqual({ kind: "failed", reason: "request" });
  });
});

describe("logout", () => {
  it("hace un POST a la ruta con barra final, sin cuerpo ni Content-Type, con el token y las cookies del mismo origen", async () => {
    const { client, calls, timers } = setup([loggedOut]);

    expect(await client.logout()).toEqual({ kind: "loggedOut" });

    expect(calls).toHaveLength(1);
    expect(calls[0]?.url).toBe(LOGOUT_URL);
    expect(calls[0]?.init.method).toBe("POST");
    expect(calls[0]?.init.credentials).toBe("same-origin");
    expect(calls[0]?.init.body).toBeUndefined();
    expect(headersOf(calls[0])).toEqual({ "X-CSRFToken": TOKEN_A });
    expect(timers.armedWith).toEqual([WRITE_MS]);
    expect(timers.clearCalls).toBe(1);
  });

  it.each([
    ["sin cookies", ""],
    ["con un token corto", "csrftoken=corto"],
    ["con un token de 65 caracteres", `csrftoken=${TOKEN_LONG}x`],
  ])("%s: no envía la cabecera X-CSRFToken", async (_name, cookies) => {
    const { client, calls } = setup([loggedOut], [cookies]);

    await client.logout();

    expect(headersOf(calls[0])).toEqual({});
  });

  it("lee la cookie en cada envío, sin guardar el token", async () => {
    const { client, calls, readCookies } = setup([loggedOut, loggedOut], [COOKIE_A, COOKIE_B]);

    await client.logout();
    await client.logout();

    expect(readCookies).toHaveBeenCalledTimes(2);
    expect(headersOf(calls[0])["X-CSRFToken"]).toBe(TOKEN_A);
    expect(headersOf(calls[1])["X-CSRFToken"]).toBe(TOKEN_B);
  });

  it("un 204 es loggedOut y no lee el cuerpo", async () => {
    const response = loggedOut();
    const { client } = setup([() => response]);

    expect(await client.logout()).toEqual({ kind: "loggedOut" });

    expect(response.bodyUsed).toBe(false);
  });

  it("ante csrf_failed pregunta quién soy y reintenta una vez, releyendo el token", async () => {
    const { client, calls, readCookies, timers } = setup([csrfFailed, authenticated, loggedOut], [COOKIE_A, COOKIE_B]);

    expect(await client.logout()).toEqual({ kind: "loggedOut" });

    expect(calls.map((call) => call.url)).toEqual([LOGOUT_URL, SESSION_URL, LOGOUT_URL]);
    expect(readCookies).toHaveBeenCalledTimes(2);
    expect(headersOf(calls[0])["X-CSRFToken"]).toBe(TOKEN_A);
    expect(headersOf(calls[2])["X-CSRFToken"]).toBe(TOKEN_B);
    expect(timers.armedWith).toEqual([WRITE_MS, WHO_AM_I_MS, WRITE_MS]);
    expect(timers.clearCalls).toBe(3);
  });

  it.each([
    ["sin sesión", anonymous],
    ["con un error del servidor", () => json({ code: "x" }, 500)],
    ["con la red caída", networkDown],
  ] as const)("reintenta aunque quién soy responda %s", async (_name, whoAmI) => {
    const { client, calls } = setup([csrfFailed, whoAmI, loggedOut]);

    expect(await client.logout()).toEqual({ kind: "loggedOut" });

    expect(calls.map((call) => call.url)).toEqual([LOGOUT_URL, SESSION_URL, LOGOUT_URL]);
  });

  it("si el segundo intento vuelve a dar csrf_failed, es el error general y no hay un tercer envío", async () => {
    const { client, calls } = setup([csrfFailed, anonymous, csrfFailed, authenticated, loggedOut]);

    expect(await client.logout()).toEqual({ kind: "failed", reason: "csrf" });

    expect(calls.map((call) => call.url)).toEqual([LOGOUT_URL, SESSION_URL, LOGOUT_URL]);
  });

  it("vencido a los 10 s es failed timeout, aborta la petición y no pregunta quién soy", async () => {
    const { client, calls, timers } = setup([hang, authenticated]);

    const pending = client.logout();
    timers.fire();

    expect(await pending).toEqual({ kind: "failed", reason: "timeout" });
    expect(timers.armedWith).toEqual([WRITE_MS]);
    expect(calls).toHaveLength(1);
    expect(calls[0]?.init.signal.aborted).toBe(true);
    expect(timers.clearCalls).toBe(1);
  });

  it("si el reintento vence, es failed timeout sin una segunda pregunta de quién soy", async () => {
    const { client, calls, timers } = setup([csrfFailed, anonymous, hang, authenticated]);

    const pending = client.logout();
    await armed(timers, 3);
    timers.fire();

    expect(await pending).toEqual({ kind: "failed", reason: "timeout" });
    expect(calls.map((call) => call.url)).toEqual([LOGOUT_URL, SESSION_URL, LOGOUT_URL]);
  });

  it("un TypeError de fetch es failed network, sin preguntar quién soy", async () => {
    const { client, calls } = setup([networkDown, authenticated, loggedOut]);

    expect(await client.logout()).toEqual({ kind: "failed", reason: "network" });

    expect(calls).toHaveLength(1);
  });

  it.each([500, 502, 503])("un %d es failed server y no lee el cuerpo", async (status) => {
    const response = new Response("{", { status, headers: { "Content-Type": "application/json" } });
    const { client } = setup([() => response]);

    expect(await client.logout()).toEqual({ kind: "failed", reason: "server" });

    expect(response.bodyUsed).toBe(false);
  });

  it.each([
    [400, "invalid_request"],
    [403, "forbidden"],
    [404, "not_found"],
    [405, "method_not_allowed"],
    [429, "throttled"],
  ])("un %d con el código %s es failed request, sin reintento", async (status, code) => {
    const { client, calls } = setup([() => json({ code }, status), anonymous, loggedOut]);

    expect(await client.logout()).toEqual({ kind: "failed", reason: "request" });

    expect(calls).toHaveLength(1);
  });

  it.each([
    ["HTML", () => new Response("<html></html>", { status: 400, headers: { "Content-Type": "text/html" } })],
    ["sin code", () => json({}, 400)],
    ["JSON roto", () => new Response("{", { status: 403, headers: { "Content-Type": "application/json" } })],
    ["campo desconocido", () => json({ code: "x", extra: 1 }, 400)],
  ])("un 4xx con un cuerpo que es %s es failed invalid", async (_name, respond) => {
    const { client } = setup([respond]);

    expect(await client.logout()).toEqual({ kind: "failed", reason: "invalid" });
  });

  it.each([200, 201, 202, 301, 304])("un estado %d inesperado es failed invalid", async (status) => {
    const { client, calls } = setup([
      () => new Response(status === 304 ? null : "{}", { status }),
      authenticated,
    ]);

    expect(await client.logout()).toEqual({ kind: "failed", reason: "invalid" });

    expect(calls).toHaveLength(1);
  });

  it.each([400, 403, 404, 429])(
    "un %d con el cuerpo cortado es failed network, sin reintento ni quién soy y sin escribir en la consola",
    async (status) => {
      const spies = watchConsole();
      const { client, calls, timers } = setup([bodyThatIsCutOff(status), anonymous, loggedOut]);

      expect(await client.logout()).toEqual({ kind: "failed", reason: "network" });

      expect(calls.map((call) => call.url)).toEqual([LOGOUT_URL]);
      expect(timers.clearCalls).toBe(1);
      for (const spy of spies) expect(spy).not.toHaveBeenCalled();
    },
  );

  it.each([400, 403])("un error que no es un TypeError al leer el cuerpo de un %d se propaga", async (status) => {
    const failure = new RangeError("fallo propio");
    const { client, calls } = setup([bodyThatFailsInTheCode(status, failure), anonymous]);

    expect(await rejection(client.logout())).toBe(failure);

    expect(calls).toHaveLength(1);
  });

  it("un error inesperado de fetch se propaga sin clasificar", async () => {
    const failure = new RangeError("fallo propio");
    const { client } = setup([
      () => {
        throw failure;
      },
    ]);

    expect(await rejection(client.logout())).toBe(failure);
  });
});

describe("las credenciales de todas las llamadas", () => {
  it("whoAmI, registro, salida y sus reintentos usan same-origin", async () => {
    const { client, calls } = setup([
      anonymous,
      csrfFailed,
      anonymous,
      registered,
      csrfFailed,
      anonymous,
      loggedOut,
      () => json({ user: "x" }, 201),
      authenticated,
    ]);

    await client.whoAmI();
    await client.register(CREDENTIALS);
    await client.logout();
    await client.register(CREDENTIALS);

    expect(calls.map((call) => call.url)).toEqual([
      SESSION_URL,
      REGISTER_URL,
      SESSION_URL,
      REGISTER_URL,
      LOGOUT_URL,
      SESSION_URL,
      LOGOUT_URL,
      REGISTER_URL,
      SESSION_URL,
    ]);
    expect(calls.map((call) => call.init.credentials)).toEqual(Array(9).fill("same-origin"));
  });
});

describe("sessionClient: la instancia real", () => {
  it("usa fetch con las cookies del mismo origen y un tiempo máximo de 5 s para quién soy", async () => {
    const realFetch = vi.fn(() => Promise.resolve(authenticated()));
    vi.stubGlobal("fetch", realFetch);
    const setTimeoutSpy = vi.spyOn(globalThis, "setTimeout");
    const clearTimeoutSpy = vi.spyOn(globalThis, "clearTimeout");

    expect(await sessionClient.whoAmI()).toBe("authenticated");

    expect(realFetch).toHaveBeenCalledTimes(1);
    const [url, init] = realFetch.mock.calls[0] as unknown as [string, SessionFetchInit];
    expect(url).toBe(SESSION_URL);
    expect(init.credentials).toBe("same-origin");
    const timeoutCalls = setTimeoutSpy.mock.calls
      .map((call, index) => ({ ms: call[1], handle: setTimeoutSpy.mock.results[index]?.value }))
      .filter(({ ms }) => ms === WHO_AM_I_MS);
    expect(timeoutCalls).toHaveLength(1);
    expect(clearTimeoutSpy).toHaveBeenCalledWith(timeoutCalls[0]?.handle);
  });
});

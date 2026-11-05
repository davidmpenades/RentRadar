import { z } from "zod";

import { hasJsonContentType } from "./http";
import type { components } from "./schema.gen";
import { runWithTimeout } from "./timeout";

type Session = components["schemas"]["Session"];

const SESSION_URL = "/api/v1/auth/session/";
const REGISTER_URL = "/api/v1/auth/register/";
const LOGOUT_URL = "/api/v1/auth/logout/";
const WHO_AM_I_TIMEOUT_MS = 5_000;
const WRITE_TIMEOUT_MS = 10_000;
const MAX_RETRY_AFTER_SECONDS = 86_400;
const CSRF_TOKEN = /^[A-Za-z0-9]{32}([A-Za-z0-9]{32})?$/;

export const EMAIL_ERROR_CODES = [
  "email_empty",
  "email_invalid",
  "email_control_char",
  "email_too_long",
  "email_taken",
] as const;
export const PASSWORD_ERROR_CODES = [
  "password_required",
  "password_invalid",
  "password_too_long",
  "password_too_short",
  "password_too_common",
  "password_entirely_numeric",
  "password_too_similar",
] as const;
export const OTHER_ERROR_CODES = ["constraint_violated", "validation_failed"] as const;

// "unknown" conserva el campo cuando el servidor manda un código que este cliente aún no conoce
export type EmailError = (typeof EMAIL_ERROR_CODES)[number] | "unknown";
export type PasswordError = (typeof PASSWORD_ERROR_CODES)[number] | "unknown";
export type OtherError = (typeof OTHER_ERROR_CODES)[number] | "unknown";

export type FailureReason = "csrf" | "request" | "network" | "server" | "invalid" | "timeout";

export type RegisterOutcome =
  | { kind: "registered" }
  | { kind: "fieldErrors"; email: EmailError[]; password: PasswordError[]; other: OtherError[] }
  | { kind: "throttled"; retryAfterSeconds: number }
  | { kind: "failed"; reason: FailureReason };

export type LogoutOutcome = { kind: "loggedOut" } | { kind: "failed"; reason: FailureReason };

export type WhoAmIResult = "authenticated" | "anonymous";

export type SessionClient = {
  whoAmI(signal?: AbortSignal): Promise<WhoAmIResult>;
  register(credentials: { email: string; password: string }): Promise<RegisterOutcome>;
  logout(): Promise<LogoutOutcome>;
};

// El cliente de sesión envía las cookies del mismo origen; el de la lista pública sigue en "omit"
export type SessionFetchInit = {
  method: "GET" | "POST";
  credentials: "same-origin";
  signal: AbortSignal;
  headers?: Record<string, string>;
  body?: string;
};

type SessionClientOptions<Handle> = {
  fetch: (input: string, init: SessionFetchInit) => Promise<Response>;
  readCookies: () => string;
  setTimer: (callback: () => void, ms: number) => Handle;
  clearTimer: (handle: Handle) => void;
  whoAmITimeoutMs: number;
  writeTimeoutMs: number;
};

const sessionUserSchema = z.strictObject({ email: z.string().min(1) });
const sessionSchema = z.strictObject({ user: sessionUserSchema.nullable() });
// El 201 del registro exige la cuenta: un user nulo no es un registro correcto
const registeredSchema = z.strictObject({ user: sessionUserSchema });
const apiErrorSchema = z.strictObject({
  code: z.string(),
  params: z.record(z.string(), z.union([z.string(), z.array(z.string())])).optional(),
  retry_after: z.int().min(1).optional(),
});
const fieldParamsSchema = z.record(z.string(), z.array(z.string()));

// Los errores propios llevan solo la causa: ni el cuerpo ni la dirección pedida
class SessionTimeoutError extends Error {
  constructor() {
    super("La API tardó demasiado en responder");
  }
}

class SessionNetworkError extends Error {
  constructor() {
    super("No se pudo conectar con la API");
  }
}

// Comprueba en compilación que el esquema cabe en el tipo generado
function parseSession(json: unknown): Session | null {
  const parsed = sessionSchema.safeParse(json);
  return parsed.success ? parsed.data : null;
}

export function readCsrfToken(cookies: string): string | null {
  for (const cookie of cookies.split(";")) {
    const separator = cookie.indexOf("=");
    if (separator === -1) continue;
    if (cookie.slice(0, separator).trim() !== "csrftoken") continue;
    const value = cookie.slice(separator + 1).trim();
    if (CSRF_TOKEN.test(value)) return value;
  }
  return null;
}

// Devuelve undefined si el cuerpo no es JSON: ningún esquema acepta undefined
async function readJson(response: Response): Promise<unknown> {
  if (!hasJsonContentType(response)) return undefined;
  try {
    return await response.json();
  } catch (error) {
    if (error instanceof SyntaxError) return undefined;
    // Un TypeError del flujo es una conexión cortada a mitad del cuerpo; cualquier otro error es del código
    if (error instanceof TypeError) throw new SessionNetworkError();
    throw error;
  }
}

async function readApiError(response: Response) {
  const parsed = apiErrorSchema.safeParse(await readJson(response));
  return parsed.success ? parsed.data : null;
}

const isServerError = (status: number) => status >= 500 && status < 600;
const isClientError = (status: number) => status >= 400 && status < 500;

function classifyCodes<Known extends string>(known: readonly Known[], codes: string[]): (Known | "unknown")[] {
  return codes.map((code) => known.find((candidate) => candidate === code) ?? "unknown");
}

function fieldErrorsFrom(params: unknown): RegisterOutcome {
  const parsed = fieldParamsSchema.safeParse(params);
  if (!parsed.success) return { kind: "failed", reason: "invalid" };

  const email: EmailError[] = [];
  const password: PasswordError[] = [];
  const other: OtherError[] = [];
  for (const [field, codes] of Object.entries(parsed.data)) {
    if (field === "email") email.push(...classifyCodes(EMAIL_ERROR_CODES, codes));
    else if (field === "password") password.push(...classifyCodes(PASSWORD_ERROR_CODES, codes));
    else if (field === "non_field") other.push(...classifyCodes(OTHER_ERROR_CODES, codes));
    else if (codes.length > 0) other.push("unknown");
  }
  // Sin ninguna entrada no hay nada que mostrar junto a un campo
  if (email.length + password.length + other.length === 0) return { kind: "failed", reason: "invalid" };
  return { kind: "fieldErrors", email, password, other };
}

// Solo el vencimiento y la red son fallos conocidos; cualquier otro error es del código y se propaga
function failureReason(error: unknown): "timeout" | "network" {
  if (error instanceof SessionTimeoutError) return "timeout";
  if (error instanceof SessionNetworkError) return "network";
  throw error;
}

type Attempt<Outcome> = Outcome | { kind: "csrf" };
type RegisterAttempt =
  | Attempt<RegisterOutcome>
  | { kind: "askWhoAmI"; failure: "invalid" | "timeout" | "network" };

export function createSessionClient<Handle>(options: SessionClientOptions<Handle>): SessionClient {
  const { fetch, readCookies, setTimer, clearTimer, whoAmITimeoutMs, writeTimeoutMs } = options;

  // Solo el TypeError de fetch es un fallo de red; el de cualquier otra parte es un error del código
  async function send(url: string, init: SessionFetchInit): Promise<Response> {
    try {
      return await fetch(url, init);
    } catch (error) {
      if (error instanceof TypeError) throw new SessionNetworkError();
      throw error;
    }
  }

  function withTimeout<T>(
    timeoutMs: number,
    task: (signal: AbortSignal) => Promise<T>,
    signal?: AbortSignal,
  ): Promise<T> {
    return runWithTimeout(
      { signal, timeoutMs, setTimer, clearTimer, onTimeout: () => new SessionTimeoutError() },
      task,
    );
  }

  // El token se lee de la cookie en cada envío y solo viaja si tiene la forma correcta
  function postHeaders(hasJsonBody: boolean): Record<string, string> {
    const token = readCsrfToken(readCookies());
    return {
      ...(hasJsonBody ? { "Content-Type": "application/json" } : {}),
      ...(token ? { "X-CSRFToken": token } : {}),
    };
  }

  async function whoAmI(signal?: AbortSignal): Promise<WhoAmIResult> {
    try {
      return await withTimeout(
        whoAmITimeoutMs,
        async (inner): Promise<WhoAmIResult> => {
          const response = await send(SESSION_URL, { method: "GET", credentials: "same-origin", signal: inner });
          if (response.status !== 200) return "anonymous";
          return parseSession(await readJson(response))?.user ? "authenticated" : "anonymous";
        },
        signal,
      );
    } catch (error) {
      // Cualquier fallo conocido es "sin sesión"; un AbortError de quien lo pidió sale tal cual
      failureReason(error);
      return "anonymous";
    }
  }

  async function interpretRegister(response: Response): Promise<RegisterAttempt> {
    const { status } = response;
    // El cuerpo de un error del servidor no se lee: nunca llega a la pantalla
    if (isServerError(status)) return { kind: "failed", reason: "server" };
    if (status === 201) {
      try {
        return registeredSchema.safeParse(await readJson(response)).success
          ? { kind: "registered" }
          : { kind: "askWhoAmI", failure: "invalid" };
      } catch (error) {
        // La cuenta pudo crearse aunque el cuerpo se cortase: se pregunta quién soy
        if (error instanceof SessionNetworkError) return { kind: "askWhoAmI", failure: "network" };
        throw error;
      }
    }
    if (!isClientError(status)) return { kind: "failed", reason: "invalid" };

    const error = await readApiError(response);
    if (!error) return { kind: "failed", reason: "invalid" };
    if (status === 403 && error.code === "csrf_failed") return { kind: "csrf" };
    if (status === 429) {
      // Cuenta el cuerpo; la cabecera Retry-After se ignora
      const seconds = error.retry_after;
      if (seconds === undefined || seconds > MAX_RETRY_AFTER_SECONDS) return { kind: "failed", reason: "invalid" };
      return { kind: "throttled", retryAfterSeconds: seconds };
    }
    if (status === 400 && error.code === "invalid_fields") return fieldErrorsFrom(error.params);
    return { kind: "failed", reason: "request" };
  }

  async function attemptRegister(credentials: { email: string; password: string }): Promise<RegisterAttempt> {
    try {
      return await withTimeout(writeTimeoutMs, async (inner) =>
        interpretRegister(
          await send(REGISTER_URL, {
            method: "POST",
            credentials: "same-origin",
            signal: inner,
            headers: postHeaders(true),
            body: JSON.stringify({ email: credentials.email, password: credentials.password }),
          }),
        ),
      );
    } catch (error) {
      // El servidor pudo completar el registro: antes de dar el error se pregunta quién soy
      return failureReason(error) === "timeout"
        ? { kind: "askWhoAmI", failure: "timeout" }
        : { kind: "failed", reason: "network" };
    }
  }

  async function register(credentials: { email: string; password: string }): Promise<RegisterOutcome> {
    let attempt = await attemptRegister(credentials);
    // Un solo reintento: quién soy deja una cookie nueva, que se relee al enviar
    if (attempt.kind === "csrf") {
      await whoAmI();
      attempt = await attemptRegister(credentials);
    }
    if (attempt.kind === "csrf") return { kind: "failed", reason: "csrf" };
    if (attempt.kind !== "askWhoAmI") return attempt;
    return (await whoAmI()) === "authenticated"
      ? { kind: "registered" }
      : { kind: "failed", reason: attempt.failure };
  }

  async function interpretLogout(response: Response): Promise<Attempt<LogoutOutcome>> {
    const { status } = response;
    if (status === 204) return { kind: "loggedOut" };
    if (isServerError(status)) return { kind: "failed", reason: "server" };
    if (!isClientError(status)) return { kind: "failed", reason: "invalid" };

    const error = await readApiError(response);
    if (!error) return { kind: "failed", reason: "invalid" };
    if (status === 403 && error.code === "csrf_failed") return { kind: "csrf" };
    return { kind: "failed", reason: "request" };
  }

  async function attemptLogout(): Promise<Attempt<LogoutOutcome>> {
    try {
      return await withTimeout(writeTimeoutMs, async (inner) =>
        interpretLogout(
          await send(LOGOUT_URL, {
            method: "POST",
            credentials: "same-origin",
            signal: inner,
            headers: postHeaders(false),
          }),
        ),
      );
    } catch (error) {
      return { kind: "failed", reason: failureReason(error) };
    }
  }

  async function logout(): Promise<LogoutOutcome> {
    let attempt = await attemptLogout();
    if (attempt.kind === "csrf") {
      await whoAmI();
      attempt = await attemptLogout();
    }
    return attempt.kind === "csrf" ? { kind: "failed", reason: "csrf" } : attempt;
  }

  return { whoAmI, register, logout };
}

export const sessionClient = createSessionClient({
  fetch: (input, init) => fetch(input, init),
  readCookies: () => document.cookie,
  setTimer: (callback, ms) => setTimeout(callback, ms),
  clearTimer: (handle) => clearTimeout(handle),
  whoAmITimeoutMs: WHO_AM_I_TIMEOUT_MS,
  writeTimeoutMs: WRITE_TIMEOUT_MS,
});

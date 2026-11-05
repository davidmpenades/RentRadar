import type { EmailError, PasswordError, RegisterOutcome } from "../api/session";
import { es } from "../i18n/es";
import { throttledMessage } from "../i18n/format";
import type { SessionStatus } from "../session/sessionState";

// Copia de MinimumLengthValidator en backend/config/settings/base.py: solo alimenta la pista y los textos, no valida
export const PASSWORD_MIN_LENGTH = 10;
// Copia de PASSWORD_MAX_LENGTH en backend/apps/users/services.py
export const PASSWORD_MAX_LENGTH = 128;

export type FocusTarget = "email" | "password" | "status";

export type FieldErrors = { email: EmailError[]; password: PasswordError[] };

export type SettledRegistration = RegisterOutcome | { kind: "failed"; reason: "unexpected" };

export type FormState = {
  emailMessages: string[];
  passwordMessages: string[];
  general: string | null;
  clearPassword: boolean;
  focus: FocusTarget | null;
  submitting: false;
};

type Credentials = { email: string; password: string };

const FIELD_CATALOG: Record<"email" | "password", Readonly<Record<string, string>>> = {
  email: es.register.email,
  password: es.register.password,
};

// El servidor recorta el email; la contraseña no se recorta, así que los espacios cuentan
export function emptyFieldErrors({ email, password }: Credentials): FieldErrors {
  return {
    email: email.trim() === "" ? ["email_empty"] : [],
    password: password === "" ? ["password_required"] : [],
  };
}

function withLengths(text: string): string {
  return text.replace("{min}", String(PASSWORD_MIN_LENGTH)).replace("{max}", String(PASSWORD_MAX_LENGTH));
}

// Un código que el catálogo no conoce cae en el texto genérico de su campo; un mismo texto no se repite
export function fieldMessages(field: "email" | "password", codes: readonly string[]): string[] {
  const catalog = FIELD_CATALOG[field];
  const fallback = field === "email" ? es.register.email.unknown : es.register.password.unknown;
  const messages = codes.map((code) => withLengths((Object.hasOwn(catalog, code) ? catalog[code] : undefined) ?? fallback));
  return [...new Set(messages)];
}

export function firstFocusTarget(
  errors: { email: readonly unknown[]; password: readonly unknown[] },
  hasGeneral: boolean,
): FocusTarget | null {
  if (errors.email.length > 0) return "email";
  if (errors.password.length > 0) return "password";
  return hasGeneral ? "status" : null;
}

function stateFromFieldCodes(email: readonly string[], password: readonly string[], hasOther: boolean): FormState {
  const hasFieldErrors = email.length + password.length > 0;
  const general = hasFieldErrors ? es.register.summary : hasOther ? es.register.errors.other : null;
  return {
    emailMessages: fieldMessages("email", email),
    passwordMessages: fieldMessages("password", password),
    general,
    // Solo se borra lo que el servidor ha señalado: un email repetido no obliga a reescribirla
    clearPassword: password.length > 0,
    focus: firstFocusTarget({ email, password }, general !== null),
    submitting: false,
  };
}

// Campos vacíos: se avisa sin enviar nada, así que no hay contraseña que borrar
export function formStateForEmpty(errors: FieldErrors): FormState {
  return { ...stateFromFieldCodes(errors.email, errors.password, false), clearPassword: false };
}

function generalMessage(reason: Extract<SettledRegistration, { kind: "failed" }>["reason"]): string {
  switch (reason) {
    case "csrf":
      return es.register.errors.csrf;
    case "timeout":
      return es.register.errors.timeout;
    case "network":
      return es.register.errors.network;
    case "server":
      return es.register.errors.server;
    case "request":
    case "invalid":
    case "unexpected":
      return es.register.errors.unexpected;
  }
}

export function formStateAfter(outcome: Exclude<SettledRegistration, { kind: "registered" }>): FormState {
  if (outcome.kind === "fieldErrors") {
    return stateFromFieldCodes(outcome.email, outcome.password, outcome.other.length > 0);
  }
  const general = outcome.kind === "throttled" ? throttledMessage(outcome.retryAfterSeconds) : generalMessage(outcome.reason);
  return {
    emailMessages: [],
    passwordMessages: [],
    general,
    clearPassword: false,
    focus: "status",
    submitting: false,
  };
}

type SettleRegistrationOptions = {
  register: (credentials: Credentials) => Promise<RegisterOutcome>;
  credentials: Credentials;
  logError: (error: unknown) => void;
};

// Un rechazo del cliente no puede dejar el envío bloqueado; lo que se registra es el error, nunca las credenciales
export async function settleRegistration({
  register,
  credentials,
  logError,
}: SettleRegistrationOptions): Promise<SettledRegistration> {
  try {
    return await register(credentials);
  } catch (error) {
    logError(error);
    return { kind: "failed", reason: "unexpected" };
  }
}

export function shouldLeaveRegister(status: SessionStatus): boolean {
  return status === "authenticated";
}

// El estado de React llega en el siguiente render: un doble clic o un doble Intro lo verían aún libre
export function createSubmitGuard() {
  let busy = false;
  return {
    tryStart(): boolean {
      if (busy) return false;
      busy = true;
      return true;
    },
    finish(): void {
      busy = false;
    },
  };
}

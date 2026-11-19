import { describe, expect, it } from "vitest";

import type { FailureReason } from "../api/session";
import { es } from "../i18n/es";
import { throttledMessage } from "../i18n/format";
import { formStateAfterLogin, type SettledLogin } from "./loginFormState";

type LoginFailure = Exclude<SettledLogin, { kind: "loggedIn" }>;

const GENERAL_BY_REASON: [FailureReason | "unexpected", string][] = [
  ["csrf", es.register.errors.csrf],
  ["timeout", es.register.errors.timeout],
  ["network", es.register.errors.network],
  ["server", es.register.errors.server],
  ["request", es.register.errors.unexpected],
  ["invalid", es.register.errors.unexpected],
  ["unexpected", es.register.errors.unexpected],
];

const ALL_OUTCOMES: LoginFailure[] = [
  { kind: "credentialsInvalid" },
  { kind: "throttled", retryAfterSeconds: 60 },
  ...GENERAL_BY_REASON.map(([reason]) => ({ kind: "failed" as const, reason })),
];

describe("formStateAfterLogin", () => {
  it("credenciales incorrectas: el texto de la spec, la contraseña borrada y el foco a la región de estado", () => {
    expect(formStateAfterLogin({ kind: "credentialsInvalid" })).toEqual({
      emailMessages: [],
      passwordMessages: [],
      general: es.login.credentialsInvalid,
      clearPassword: true,
      focus: "status",
      submitting: false,
    });
    expect(es.login.credentialsInvalid).toBe("El email o la contraseña no son correctos.");
  });

  it.each([1, 60, 61, 900, 86400])("límite superado con %d s: el texto de espera y los dos campos conservados", (seconds) => {
    expect(formStateAfterLogin({ kind: "throttled", retryAfterSeconds: seconds })).toEqual({
      emailMessages: [],
      passwordMessages: [],
      general: throttledMessage(seconds),
      clearPassword: false,
      focus: "status",
      submitting: false,
    });
  });

  it.each(GENERAL_BY_REASON)("failed(%s): el error general del registro y los dos campos conservados", (reason, general) => {
    expect(formStateAfterLogin({ kind: "failed", reason })).toEqual({
      emailMessages: [],
      passwordMessages: [],
      general,
      clearPassword: false,
      focus: "status",
      submitting: false,
    });
  });

  it.each(ALL_OUTCOMES)("con %o solo se borra la contraseña si las credenciales son incorrectas", (outcome) => {
    expect(formStateAfterLogin(outcome).clearPassword).toBe(outcome.kind === "credentialsInvalid");
  });

  it.each(ALL_OUTCOMES)(
    "con %o se conserva el email: sin errores por campo, foco a la región de estado y el envío libre",
    (outcome) => {
      const state = formStateAfterLogin(outcome);
      expect(Object.keys(state).sort()).toEqual([
        "clearPassword",
        "emailMessages",
        "focus",
        "general",
        "passwordMessages",
        "submitting",
      ]);
      expect(state.emailMessages).toEqual([]);
      expect(state.passwordMessages).toEqual([]);
      expect(state.focus).toBe("status");
      expect(state.submitting).toBe(false);
    },
  );
});

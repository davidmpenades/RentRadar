import type { LoginOutcome } from "../api/session";
import { es } from "../i18n/es";
import { throttledMessage } from "../i18n/format";
import { generalMessage, type FormState } from "../register/registerForm";

export type SettledLogin = LoginOutcome | { kind: "failed"; reason: "unexpected" };

type LoginFailure = Exclude<SettledLogin, { kind: "loggedIn" }>;

function loginMessage(outcome: LoginFailure): string {
  if (outcome.kind === "credentialsInvalid") return es.login.credentialsInvalid;
  if (outcome.kind === "throttled") return throttledMessage(outcome.retryAfterSeconds);
  return generalMessage(outcome.reason);
}

// Sin errores por campo y con el email intacto: la respuesta no dice cuál de los dos falla
export function formStateAfterLogin(outcome: LoginFailure): FormState {
  return {
    emailMessages: [],
    passwordMessages: [],
    general: loginMessage(outcome),
    clearPassword: outcome.kind === "credentialsInvalid",
    focus: "status",
    submitting: false,
  };
}

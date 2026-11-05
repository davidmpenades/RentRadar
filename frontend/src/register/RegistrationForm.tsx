import type { FormEvent, Ref } from "react";

import { es } from "../i18n/es";
import { PASSWORD_MIN_LENGTH } from "./registerForm";

type RegistrationFormProps = {
  email: string;
  onEmailChange: (value: string) => void;
  emailMessages: readonly string[];
  passwordMessages: readonly string[];
  general: string | null;
  submitting: boolean;
  passwordVisible: boolean;
  onTogglePasswordVisible: () => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  emailRef?: Ref<HTMLInputElement>;
  passwordRef?: Ref<HTMLInputElement>;
  statusRef?: Ref<HTMLDivElement>;
};

const FIELD =
  "min-h-11 w-full rounded-lg border-2 border-muted bg-white px-3 text-base read-only:opacity-70 aria-invalid:border-danger";
const BUTTON = "inline-flex min-h-11 min-w-11 items-center justify-center rounded-lg px-4 font-semibold";

function Messages({ id, messages }: { id: string; messages: readonly string[] }) {
  if (messages.length === 0) return null;
  return (
    <ul id={id} className="flex flex-col gap-1 text-sm font-semibold text-danger">
      {messages.map((message) => (
        <li key={message}>{message}</li>
      ))}
    </ul>
  );
}

// La contraseña no es un campo controlado: React copiaría cada valor al atributo value del DOM
export function RegistrationForm({
  email,
  onEmailChange,
  emailMessages,
  passwordMessages,
  general,
  submitting,
  passwordVisible,
  onTogglePasswordVisible,
  onSubmit,
  emailRef,
  passwordRef,
  statusRef,
}: RegistrationFormProps) {
  const status = submitting ? es.register.submitting : general;
  const emailInvalid = emailMessages.length > 0;
  const passwordInvalid = passwordMessages.length > 0;
  const hint = es.register.passwordHint.replace("{min}", String(PASSWORD_MIN_LENGTH));

  return (
    <main className="h-full overflow-y-auto px-4 py-8 sm:py-16">
      <div className="mx-auto w-full max-w-sm rounded-xl border border-ink/10 bg-white p-6">
        <h1 className="text-3xl font-bold">{es.register.title}</h1>
        <form noValidate method="post" onSubmit={onSubmit} className="mt-6 flex flex-col gap-5">
          <div className="flex flex-col gap-2">
            <label htmlFor="register-email" className="font-semibold">
              {es.register.emailLabel}
            </label>
            <input
              ref={emailRef}
              id="register-email"
              name="email"
              type="email"
              autoComplete="email"
              inputMode="email"
              autoCapitalize="none"
              spellCheck={false}
              value={email}
              onChange={(event) => onEmailChange(event.target.value)}
              readOnly={submitting}
              aria-invalid={emailInvalid || undefined}
              aria-describedby={emailInvalid ? "register-email-errors" : undefined}
              className={FIELD}
            />
            <Messages id="register-email-errors" messages={emailMessages} />
          </div>
          <div className="flex flex-col gap-2">
            <label htmlFor="register-password" className="font-semibold">
              {es.register.passwordLabel}
            </label>
            <input
              ref={passwordRef}
              id="register-password"
              name="password"
              type={passwordVisible ? "text" : "password"}
              autoComplete="new-password"
              readOnly={submitting}
              aria-invalid={passwordInvalid || undefined}
              aria-describedby={
                passwordInvalid ? "register-password-hint register-password-errors" : "register-password-hint"
              }
              className={FIELD}
            />
            <p id="register-password-hint" className="text-sm text-muted">
              {hint}
            </p>
            <Messages id="register-password-errors" messages={passwordMessages} />
            <button
              type="button"
              onClick={onTogglePasswordVisible}
              aria-pressed={passwordVisible}
              aria-controls="register-password"
              className={`${BUTTON} self-start border-2 border-ink`}
            >
              {es.register.showPassword}
            </button>
          </div>
          <div
            ref={statusRef}
            role="status"
            tabIndex={-1}
            className={status ? (submitting ? "text-muted" : "rounded-lg bg-lemon px-4 py-2 font-semibold") : undefined}
          >
            {status}
          </div>
          <button
            type="submit"
            aria-disabled={submitting || undefined}
            className={`${BUTTON} w-full bg-accent text-white aria-disabled:opacity-60`}
          >
            {es.register.submit}
          </button>
        </form>
      </div>
    </main>
  );
}

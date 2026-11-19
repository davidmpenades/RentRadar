import type { FormEvent, Ref } from "react";

import { es } from "../i18n/es";
import { EyeIcon, EyeOffIcon } from "../register/EyeIcons";
import { Messages } from "../register/RegistrationForm";
import { Indicator } from "../ui/Indicator";

type LoginFormProps = {
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

// La contraseña no es un campo controlado: React copiaría cada valor al atributo value del DOM
export function LoginForm({
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
}: LoginFormProps) {
  const status = submitting ? es.login.submitting : general;
  const emailInvalid = emailMessages.length > 0;
  const passwordInvalid = passwordMessages.length > 0;

  return (
    <main className="h-full overflow-y-auto px-4 py-8 sm:py-16">
      <div className="mx-auto w-full max-w-sm rounded-xl border border-ink/10 bg-white p-6">
        <h1 className="text-3xl font-bold text-balance">{es.login.title}</h1>
        <form noValidate method="post" onSubmit={onSubmit} className="mt-6 flex flex-col gap-5">
          <div className="flex flex-col gap-2">
            <label htmlFor="login-email" className="font-semibold">
              {es.register.emailLabel}
            </label>
            <input
              ref={emailRef}
              id="login-email"
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
              aria-describedby={emailInvalid ? "login-email-errors" : undefined}
              className="field"
            />
            <Messages id="login-email-errors" messages={emailMessages} />
          </div>
          <div className="flex flex-col gap-2">
            <label htmlFor="login-password" className="font-semibold">
              {es.register.passwordLabel}
            </label>
            <div className="field-box">
              <input
                ref={passwordRef}
                id="login-password"
                name="password"
                type={passwordVisible ? "text" : "password"}
                autoComplete="current-password"
                readOnly={submitting}
                aria-invalid={passwordInvalid || undefined}
                aria-describedby={passwordInvalid ? "login-password-errors" : undefined}
                className="field"
              />
              <button
                type="button"
                onClick={onTogglePasswordVisible}
                aria-label={es.register.showPassword}
                aria-pressed={passwordVisible}
                aria-controls="login-password"
                className="eye"
              >
                {passwordVisible ? <EyeOffIcon /> : <EyeIcon />}
              </button>
            </div>
            <Messages id="login-password-errors" messages={passwordMessages} />
          </div>
          <div
            ref={statusRef}
            role="status"
            tabIndex={-1}
            className={status ? (submitting ? "text-muted" : "flex items-start gap-2 font-semibold") : undefined}
          >
            {!submitting && general && <Indicator className="size-6" />}
            {status}
          </div>
          <button
            type="submit"
            aria-disabled={submitting || undefined}
            className="btn btn-primary btn-form w-full"
          >
            {es.login.submit}
          </button>
        </form>
        <a href="/register" className="mt-4 inline-flex min-h-11 items-center font-semibold underline underline-offset-4">
          {es.login.toRegister}
        </a>
      </div>
    </main>
  );
}

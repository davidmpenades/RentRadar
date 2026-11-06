import { useEffect, useRef, useState, type FormEvent } from "react";

import { sessionClient } from "../api/session";
import { RegistrationForm } from "../register/RegistrationForm";
import {
  createSubmitGuard,
  emptyFieldErrors,
  formStateAfter,
  formStateForEmpty,
  settleRegistration,
  shouldLeaveRegister,
  type FocusTarget,
  type FormState,
} from "../register/registerForm";
import { useSession } from "../session/SessionProvider";

type RegisterPageProps = {
  onLeave: () => void;
};

const NO_ERRORS: Pick<FormState, "emailMessages" | "passwordMessages" | "general"> = {
  emailMessages: [],
  passwordMessages: [],
  general: null,
};

const logError = (error: unknown) => console.error(error);

export function RegisterPage({ onLeave }: RegisterPageProps) {
  const session = useSession();
  const [email, setEmail] = useState("");
  const [errors, setErrors] = useState(NO_ERRORS);
  const [submitting, setSubmitting] = useState(false);
  const [passwordVisible, setPasswordVisible] = useState(false);
  // Un objeto nuevo por petición, para que el mismo destino vuelva a enfocarse
  const [focusRequest, setFocusRequest] = useState<{ target: FocusTarget } | null>(null);
  const guardRef = useRef<ReturnType<typeof createSubmitGuard> | null>(null);
  const emailRef = useRef<HTMLInputElement>(null);
  const passwordRef = useRef<HTMLInputElement>(null);
  const statusRef = useRef<HTMLDivElement>(null);

  // El formulario se pinta sin esperar a quién soy; si la sesión ya existe o llega después, se sale
  useEffect(() => {
    if (shouldLeaveRegister(session.status)) onLeave();
  }, [session.status, onLeave]);

  useEffect(() => {
    if (!focusRequest) return;
    const targets = { email: emailRef, password: passwordRef, status: statusRef };
    targets[focusRequest.target].current?.focus();
  }, [focusRequest]);

  const show = (state: FormState) => {
    setErrors({ emailMessages: state.emailMessages, passwordMessages: state.passwordMessages, general: state.general });
    if (state.focus) setFocusRequest({ target: state.focus });
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    guardRef.current ??= createSubmitGuard();
    const guard = guardRef.current;
    if (!guard.tryStart()) return;

    const passwordInput = passwordRef.current;
    // La contraseña solo vive en el campo y en esta variable: nunca en el estado de React
    const password = passwordInput?.value ?? "";
    const empty = emptyFieldErrors({ email, password });
    if (empty.email.length + empty.password.length > 0) {
      guard.finish();
      show(formStateForEmpty(empty));
      return;
    }

    setSubmitting(true);
    // Vaciar los errores al empezar hace que un segundo fallo igual vuelva a anunciarse
    setErrors(NO_ERRORS);
    void (async () => {
      try {
        const outcome = await settleRegistration({
          register: sessionClient.register,
          credentials: { email, password },
          logError,
        });
        if (outcome.kind === "registered") {
          if (passwordInput) passwordInput.value = "";
          session.markRegistered();
          return;
        }
        const state = formStateAfter(outcome);
        if (state.clearPassword && passwordInput) passwordInput.value = "";
        show(state);
      } finally {
        guard.finish();
        setSubmitting(false);
      }
    })();
  };

  if (shouldLeaveRegister(session.status)) return null;

  return (
    <RegistrationForm
      email={email}
      onEmailChange={setEmail}
      emailMessages={errors.emailMessages}
      passwordMessages={errors.passwordMessages}
      general={errors.general}
      submitting={submitting}
      passwordVisible={passwordVisible}
      onTogglePasswordVisible={() => setPasswordVisible((visible) => !visible)}
      onSubmit={handleSubmit}
      emailRef={emailRef}
      passwordRef={passwordRef}
      statusRef={statusRef}
    />
  );
}

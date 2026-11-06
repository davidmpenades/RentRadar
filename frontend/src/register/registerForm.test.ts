import { describe, expect, it, vi } from "vitest";

import {
  EMAIL_ERROR_CODES,
  OTHER_ERROR_CODES,
  PASSWORD_ERROR_CODES,
  type EmailError,
  type FailureReason,
  type OtherError,
  type PasswordError,
  type RegisterOutcome,
} from "../api/session";
import { es } from "../i18n/es";
import { throttledMessage } from "../i18n/format";
import {
  PASSWORD_MAX_LENGTH,
  PASSWORD_MIN_LENGTH,
  createSubmitGuard,
  emptyFieldErrors,
  fieldMessages,
  firstFocusTarget,
  formStateAfter,
  formStateForEmpty,
  settleRegistration,
  shouldLeaveRegister,
  type SettledRegistration,
} from "./registerForm";

const FAILURE_REASONS: FailureReason[] = ["csrf", "request", "network", "server", "invalid", "timeout"];

const fieldErrors = (
  email: EmailError[] = [],
  password: PasswordError[] = [],
  other: OtherError[] = [],
): Extract<RegisterOutcome, { kind: "fieldErrors" }> => ({ kind: "fieldErrors", email, password, other });

describe("longitudes de la contraseña", () => {
  it("copian las del backend: 10 de config/settings/base.py y 128 de apps/users/services.py", () => {
    expect(PASSWORD_MIN_LENGTH).toBe(10);
    expect(PASSWORD_MAX_LENGTH).toBe(128);
  });

  it("la pista del formulario sale de la constante", () => {
    expect(es.register.passwordHint.replace("{min}", String(PASSWORD_MIN_LENGTH))).toBe("Al menos 10 caracteres.");
  });
});

describe("emptyFieldErrors: el cliente solo comprueba que no estén vacíos", () => {
  it("con los dos campos escritos no hay errores", () => {
    expect(emptyFieldErrors({ email: "ana@example.com", password: "x" })).toEqual({ email: [], password: [] });
  });

  it.each(["", " ", "   ", "\t\n"])("el email %j está vacío: email_empty, como el servidor", (email) => {
    expect(emptyFieldErrors({ email, password: "contraseña-larga" })).toEqual({ email: ["email_empty"], password: [] });
  });

  it("la contraseña vacía da password_required", () => {
    expect(emptyFieldErrors({ email: "ana@example.com", password: "" })).toEqual({
      email: [],
      password: ["password_required"],
    });
  });

  it.each([" ", "          "])("la contraseña %j de solo espacios no está vacía: los espacios cuentan", (password) => {
    expect(emptyFieldErrors({ email: "ana@example.com", password }).password).toEqual([]);
  });

  it("con los dos vacíos da los dos códigos", () => {
    expect(emptyFieldErrors({ email: "", password: "" })).toEqual({
      email: ["email_empty"],
      password: ["password_required"],
    });
  });
});

describe("fieldMessages: un texto por código", () => {
  it.each(EMAIL_ERROR_CODES)("el código de email %s tiene su texto", (code) => {
    const [message] = fieldMessages("email", [code]);
    expect(message).toBeTruthy();
    expect(message).not.toContain("{");
  });

  it.each(PASSWORD_ERROR_CODES)("el código de contraseña %s tiene su texto", (code) => {
    const [message] = fieldMessages("password", [code]);
    expect(message).toBeTruthy();
    expect(message).not.toContain("{");
  });

  it("el catálogo no tiene textos de más ni de menos", () => {
    expect(Object.keys(es.register.email).sort()).toEqual([...EMAIL_ERROR_CODES, "unknown"].sort());
    expect(Object.keys(es.register.password).sort()).toEqual([...PASSWORD_ERROR_CODES, "unknown"].sort());
  });

  it("email_taken dice lo que fija la spec", () => {
    expect(fieldMessages("email", ["email_taken"])).toEqual(["Ya existe una cuenta con este email."]);
  });

  it("los textos de longitud llevan los números de las constantes", () => {
    expect(fieldMessages("password", ["password_too_short"])[0]).toContain(String(PASSWORD_MIN_LENGTH));
    expect(fieldMessages("password", ["password_too_long"])[0]).toContain(String(PASSWORD_MAX_LENGTH));
  });

  it("un código desconocido da el texto genérico de su campo", () => {
    expect(fieldMessages("email", ["unknown"])).toEqual([es.register.email.unknown]);
    expect(fieldMessages("password", ["unknown"])).toEqual([es.register.password.unknown]);
    expect(es.register.email.unknown).not.toBe(es.register.password.unknown);
  });

  it("conserva el orden de los códigos y no repite un mismo texto", () => {
    expect(fieldMessages("email", ["email_invalid", "unknown", "email_empty", "unknown", "email_invalid"])).toEqual([
      es.register.email.email_invalid,
      es.register.email.unknown,
      es.register.email.email_empty,
    ]);
  });

  it("sin códigos no hay textos", () => {
    expect(fieldMessages("email", [])).toEqual([]);
    expect(fieldMessages("password", [])).toEqual([]);
  });
});

describe("firstFocusTarget: email, contraseña y región de estado", () => {
  it("con error de email, el email, aunque haya también de contraseña", () => {
    expect(firstFocusTarget({ email: ["email_taken"], password: ["password_too_short"] }, true)).toBe("email");
  });

  it("solo con error de contraseña, la contraseña", () => {
    expect(firstFocusTarget({ email: [], password: ["password_too_common"] }, false)).toBe("password");
  });

  it("sin errores de campo y con error general, la región de estado", () => {
    expect(firstFocusTarget({ email: [], password: [] }, true)).toBe("status");
  });

  it("sin ningún error no hay a dónde llevar el foco", () => {
    expect(firstFocusTarget({ email: [], password: [] }, false)).toBeNull();
  });
});

describe("formStateAfter: el email se conserva y la contraseña solo se borra con un error de la contraseña", () => {
  describe("fieldErrors", () => {
    it("solo email_taken: conserva la contraseña, muestra el texto junto al email y lleva el foco al email", () => {
      const state = formStateAfter(fieldErrors(["email_taken"]));
      expect(state.clearPassword).toBe(false);
      expect(state.emailMessages).toEqual(["Ya existe una cuenta con este email."]);
      expect(state.passwordMessages).toEqual([]);
      expect(state.general).toBe(es.register.summary);
      expect(state.focus).toBe("email");
      expect(state.submitting).toBe(false);
    });

    it.each(EMAIL_ERROR_CODES)("solo el error de email %s: conserva la contraseña", (code) => {
      expect(formStateAfter(fieldErrors([code])).clearPassword).toBe(false);
    });

    it("un email desconocido: conserva la contraseña", () => {
      expect(formStateAfter(fieldErrors(["unknown"])).clearPassword).toBe(false);
    });

    it.each(PASSWORD_ERROR_CODES)("el error de contraseña %s: la borra y lleva el foco a la contraseña", (code) => {
      const state = formStateAfter(fieldErrors([], [code]));
      expect(state.clearPassword).toBe(true);
      expect(state.passwordMessages).toEqual(fieldMessages("password", [code]));
      expect(state.emailMessages).toEqual([]);
      expect(state.focus).toBe("password");
      expect(state.general).toBe(es.register.summary);
      expect(state.submitting).toBe(false);
    });

    it("una contraseña con código desconocido también la borra", () => {
      expect(formStateAfter(fieldErrors([], ["unknown"])).clearPassword).toBe(true);
    });

    it("errores en el email y en la contraseña: la borra, aunque haya también errores del email, y el foco va al email", () => {
      const state = formStateAfter(fieldErrors(["email_taken"], ["password_too_short"]));
      expect(state.clearPassword).toBe(true);
      expect(state.emailMessages).toHaveLength(1);
      expect(state.passwordMessages).toHaveLength(1);
      expect(state.focus).toBe("email");
    });

    it.each(OTHER_ERROR_CODES)("solo el error general %s: conserva la contraseña y el foco va a la región", (code) => {
      const state = formStateAfter(fieldErrors([], [], [code]));
      expect(state.clearPassword).toBe(false);
      expect(state.emailMessages).toEqual([]);
      expect(state.passwordMessages).toEqual([]);
      expect(state.general).toBe(es.register.errors.other);
      expect(state.focus).toBe("status");
      expect(state.submitting).toBe(false);
    });

    it("un error general desconocido: conserva la contraseña", () => {
      const state = formStateAfter(fieldErrors([], [], ["unknown"]));
      expect(state.clearPassword).toBe(false);
      expect(state.general).toBe(es.register.errors.other);
    });

    it("errores de campo y general a la vez: manda el resumen y el foco va al campo", () => {
      const state = formStateAfter(fieldErrors(["email_invalid"], [], ["validation_failed"]));
      expect(state.general).toBe(es.register.summary);
      expect(state.focus).toBe("email");
      expect(state.clearPassword).toBe(false);
    });
  });

  describe("throttled", () => {
    it.each([1, 59, 60])("con %s s espera 1 minuto: conserva la contraseña, texto de la spec y foco a la región", (seconds) => {
      const state = formStateAfter({ kind: "throttled", retryAfterSeconds: seconds });
      expect(state.clearPassword).toBe(false);
      expect(state.general).toBe("Demasiados intentos. Inténtalo de nuevo en 1 minuto.");
      expect(state.emailMessages).toEqual([]);
      expect(state.passwordMessages).toEqual([]);
      expect(state.focus).toBe("status");
      expect(state.submitting).toBe(false);
    });

    it("redondea los minutos hacia arriba", () => {
      expect(formStateAfter({ kind: "throttled", retryAfterSeconds: 3601 }).general).toBe(throttledMessage(3601));
      expect(formStateAfter({ kind: "throttled", retryAfterSeconds: 3601 }).general).toBe(
        "Demasiados intentos. Inténtalo de nuevo en 61 minutos.",
      );
    });
  });

  describe("failed", () => {
    const GENERAL: Record<FailureReason | "unexpected", string> = {
      csrf: es.register.errors.csrf,
      timeout: es.register.errors.timeout,
      network: es.register.errors.network,
      server: es.register.errors.server,
      request: es.register.errors.unexpected,
      invalid: es.register.errors.unexpected,
      unexpected: es.register.errors.unexpected,
    };

    it.each([...FAILURE_REASONS, "unexpected" as const])(
      "con %s conserva la contraseña, muestra el error general, vuelve a habilitar el envío y lleva el foco a la región",
      (reason) => {
        const state = formStateAfter({ kind: "failed", reason });
        expect(state.clearPassword).toBe(false);
        expect(state.general).toBe(GENERAL[reason]);
        expect(state.emailMessages).toEqual([]);
        expect(state.passwordMessages).toEqual([]);
        expect(state.focus).toBe("status");
        expect(state.submitting).toBe(false);
      },
    );

    it("los textos generales son distintos entre sí, salvo los que comparten el error inesperado", () => {
      const texts = new Set(["csrf", "timeout", "network", "server", "unexpected"].map((r) => GENERAL[r as FailureReason]));
      expect(texts.size).toBe(5);
    });

    it("el texto de recarga de csrf es el de la spec", () => {
      expect(es.register.errors.csrf).toBe("No se ha podido enviar el formulario. Recarga la página e inténtalo de nuevo.");
    });

    it("el tiempo vencido tiene su texto", () => {
      expect(es.register.errors.timeout).toBe("La petición ha tardado demasiado. Inténtalo de nuevo.");
    });
  });

  it("ningún estado lleva la contraseña escrita ni la pide de vuelta", () => {
    const outcomes: SettledRegistration[] = [
      fieldErrors(["email_taken"], ["password_too_short"]),
      { kind: "throttled", retryAfterSeconds: 30 },
      { kind: "failed", reason: "network" },
    ];
    for (const outcome of outcomes) {
      if (outcome.kind === "registered") continue;
      expect(Object.keys(formStateAfter(outcome)).sort()).toEqual(
        ["clearPassword", "emailMessages", "focus", "general", "passwordMessages", "submitting"].sort(),
      );
    }
  });
});

describe("formStateForEmpty: los campos vacíos se avisan sin enviar nada", () => {
  it("email vacío: texto junto al email, resumen y foco al email", () => {
    const state = formStateForEmpty(emptyFieldErrors({ email: "", password: "contraseña-larga" }));
    expect(state.emailMessages).toEqual([es.register.email.email_empty]);
    expect(state.passwordMessages).toEqual([]);
    expect(state.general).toBe(es.register.summary);
    expect(state.focus).toBe("email");
    expect(state.submitting).toBe(false);
  });

  it("contraseña vacía: texto junto a la contraseña y foco a la contraseña", () => {
    const state = formStateForEmpty(emptyFieldErrors({ email: "ana@example.com", password: "" }));
    expect(state.passwordMessages).toEqual([es.register.password.password_required]);
    expect(state.focus).toBe("password");
  });

  it("los dos vacíos: los dos textos y el foco al email; no hay nada que borrar", () => {
    const state = formStateForEmpty(emptyFieldErrors({ email: " ", password: "" }));
    expect(state.emailMessages).toHaveLength(1);
    expect(state.passwordMessages).toHaveLength(1);
    expect(state.focus).toBe("email");
    expect(state.clearPassword).toBe(false);
  });
});

describe("settleRegistration", () => {
  const credentials = { email: "ana@example.com", password: "secreto-muy-largo" };

  it("devuelve el resultado del cliente sin registrar nada", async () => {
    const logError = vi.fn();
    const register = vi.fn(async (): Promise<RegisterOutcome> => ({ kind: "registered" }));

    await expect(settleRegistration({ register, credentials, logError })).resolves.toEqual({ kind: "registered" });
    expect(register).toHaveBeenCalledExactlyOnceWith(credentials);
    expect(logError).not.toHaveBeenCalled();
  });

  it("un rechazo es un fallo inesperado: lo registra una vez y nunca lanza", async () => {
    const logError = vi.fn();
    const error = new RangeError("fallo del código");

    await expect(
      settleRegistration({ register: async () => Promise.reject(error), credentials, logError }),
    ).resolves.toEqual({ kind: "failed", reason: "unexpected" });
    expect(logError).toHaveBeenCalledTimes(1);
    expect(logError.mock.calls[0]).toEqual([error]);
  });

  it("lo que se registra no incluye el email ni la contraseña", async () => {
    const logError = vi.fn();

    await settleRegistration({ register: async () => Promise.reject(new Error("boom")), credentials, logError });

    const logged = JSON.stringify(logError.mock.calls, (_key, value: unknown) =>
      value instanceof Error ? { name: value.name, message: value.message } : value,
    );
    expect(logged).not.toContain(credentials.password);
    expect(logged).not.toContain(credentials.email);
  });

  it("un rechazo síncrono del cliente también se convierte en fallo", async () => {
    const register = vi.fn((): Promise<RegisterOutcome> => {
      throw new TypeError("síncrono");
    });

    await expect(settleRegistration({ register, credentials, logError: vi.fn() })).resolves.toEqual({
      kind: "failed",
      reason: "unexpected",
    });
  });
});

describe("createSubmitGuard: un envío a la vez", () => {
  it("el primer envío pasa y el segundo, con el primero en curso, no", () => {
    const guard = createSubmitGuard();
    expect(guard.tryStart()).toBe(true);
    expect(guard.tryStart()).toBe(false);
    expect(guard.tryStart()).toBe(false);
  });

  it("al terminar el primero se puede volver a enviar", () => {
    const guard = createSubmitGuard();
    guard.tryStart();
    guard.finish();
    expect(guard.tryStart()).toBe(true);
  });

  it("terminar dos veces no deja pasar dos envíos", () => {
    const guard = createSubmitGuard();
    guard.tryStart();
    guard.finish();
    guard.finish();
    expect(guard.tryStart()).toBe(true);
    expect(guard.tryStart()).toBe(false);
  });

  it("terminar sin haber empezado no estropea nada", () => {
    const guard = createSubmitGuard();
    guard.finish();
    expect(guard.tryStart()).toBe(true);
  });

  it("dos guardas son independientes", () => {
    const first = createSubmitGuard();
    const second = createSubmitGuard();
    first.tryStart();
    expect(second.tryStart()).toBe(true);
  });
});

describe("shouldLeaveRegister", () => {
  it("solo con sesión abierta se sale del registro", () => {
    expect(shouldLeaveRegister("authenticated")).toBe(true);
    expect(shouldLeaveRegister("anonymous")).toBe(false);
    expect(shouldLeaveRegister("unknown")).toBe(false);
  });
});

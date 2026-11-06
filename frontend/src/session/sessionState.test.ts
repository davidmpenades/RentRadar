import { describe, expect, it, vi } from "vitest";

import type { FailureReason, LogoutOutcome, WhoAmIResult } from "../api/session";
import { es } from "../i18n/es";
import {
  loadSessionStatus,
  logoutResult,
  registrationResult,
  settleLogout,
  statusAfterWhoAmI,
  topBarAction,
  type SessionStatus,
} from "./sessionState";

const FAILURE_REASONS: FailureReason[] = ["csrf", "request", "network", "server", "invalid", "timeout"];

function abortError() {
  return new DOMException("The operation was aborted.", "AbortError");
}

describe("topBarAction", () => {
  it.each<[SessionStatus, ReturnType<typeof topBarAction>]>([
    ["unknown", "none"],
    ["anonymous", "register"],
    ["authenticated", "logout"],
  ])("con el estado %s la barra muestra %s", (status, action) => {
    expect(topBarAction(status)).toBe(action);
  });
});

describe("statusAfterWhoAmI: la respuesta de quién soy solo decide el arranque", () => {
  it.each<WhoAmIResult>(["anonymous", "authenticated"])("en unknown se aplica %s", (result) => {
    expect(statusAfterWhoAmI("unknown", result)).toBe(result);
  });

  it("una respuesta sin sesión que llega tras registrarse no deshace el registro", () => {
    expect(statusAfterWhoAmI("authenticated", "anonymous")).toBe("authenticated");
  });

  it("una respuesta con sesión que llega tras salir no vuelve a mostrar Salir", () => {
    expect(statusAfterWhoAmI("anonymous", "authenticated")).toBe("anonymous");
  });

  it.each<[SessionStatus, WhoAmIResult]>([
    ["anonymous", "anonymous"],
    ["authenticated", "authenticated"],
  ])("con el estado %s y la respuesta %s no cambia nada", (current, result) => {
    expect(statusAfterWhoAmI(current, result)).toBe(current);
  });
});

describe("loadSessionStatus", () => {
  it.each<WhoAmIResult>(["anonymous", "authenticated"])("devuelve %s sin registrar nada", async (result) => {
    const logError = vi.fn();
    const whoAmI = vi.fn(async () => result);

    await expect(loadSessionStatus({ whoAmI, signal: new AbortController().signal, logError })).resolves.toBe(result);
    expect(logError).not.toHaveBeenCalled();
  });

  it("pasa a quién soy la señal que recibe", async () => {
    const controller = new AbortController();
    const whoAmI = vi.fn<(signal?: AbortSignal) => Promise<WhoAmIResult>>(async () => "anonymous");

    await loadSessionStatus({ whoAmI, signal: controller.signal, logError: vi.fn() });

    expect(whoAmI).toHaveBeenCalledExactlyOnceWith(controller.signal);
  });

  it("un rechazo que no es una cancelación es un fallo del código: sin sesión y registrado una vez", async () => {
    const failure = new RangeError("fallo del código");
    const logError = vi.fn();

    const result = await loadSessionStatus({
      whoAmI: async () => {
        throw failure;
      },
      signal: new AbortController().signal,
      logError,
    });

    expect(result).toBe("anonymous");
    expect(logError).toHaveBeenCalledExactlyOnceWith(failure);
  });

  it("un AbortError sin que la señal propia se haya cancelado tampoco se calla", async () => {
    const failure = abortError();
    const logError = vi.fn();

    const result = await loadSessionStatus({
      whoAmI: async () => {
        throw failure;
      },
      signal: new AbortController().signal,
      logError,
    });

    expect(result).toBe("anonymous");
    expect(logError).toHaveBeenCalledExactlyOnceWith(failure);
  });

  it("cancelada y rechazada con su AbortError: null y sin registrar nada", async () => {
    const controller = new AbortController();
    const logError = vi.fn();

    const result = await loadSessionStatus({
      whoAmI: async (signal) => {
        controller.abort();
        signal?.throwIfAborted();
        return "anonymous";
      },
      signal: controller.signal,
      logError,
    });

    expect(result).toBeNull();
    expect(logError).not.toHaveBeenCalled();
  });

  it("cancelada y rechazada con otro error: null y sin registrar nada", async () => {
    const controller = new AbortController();
    const logError = vi.fn();

    const result = await loadSessionStatus({
      whoAmI: async () => {
        controller.abort();
        throw new RangeError("después de cancelar");
      },
      signal: controller.signal,
      logError,
    });

    expect(result).toBeNull();
    expect(logError).not.toHaveBeenCalled();
  });

  it.each<WhoAmIResult>(["anonymous", "authenticated"])(
    "cancelada y resuelta después con %s: null, el resultado no se aplica",
    async (late) => {
      const controller = new AbortController();
      const logError = vi.fn();

      const result = await loadSessionStatus({
        whoAmI: async () => {
          controller.abort();
          return late;
        },
        signal: controller.signal,
        logError,
      });

      expect(result).toBeNull();
      expect(logError).not.toHaveBeenCalled();
    },
  );
});

describe("logoutResult", () => {
  it("al salir: sin sesión, anuncia «Has salido», foco en Registrarse y sin aviso", () => {
    expect(logoutResult({ kind: "loggedOut" })).toEqual({
      status: "anonymous",
      announcement: es.session.loggedOut,
      focus: "register",
      notice: null,
    });
    expect(es.session.loggedOut).toBe("Has salido");
  });

  it.each(FAILURE_REASONS)(
    "con failed(%s): la sesión sigue, foco en Salir y el aviso, que se anuncia solo",
    (reason) => {
      const outcome: LogoutOutcome = { kind: "failed", reason };
      expect(logoutResult(outcome)).toEqual({
        status: "authenticated",
        announcement: null,
        focus: "logout",
        notice: "logout_failed",
      });
    },
  );

  it("un fallo del código da el mismo resultado que cualquier otro fallo", () => {
    expect(logoutResult({ kind: "failed", reason: "unexpected" })).toEqual(
      logoutResult({ kind: "failed", reason: "network" }),
    );
  });

  it("el texto del aviso y el de su botón son los de la spec", () => {
    expect(es.session.logoutFailed).toBe("No se ha podido salir. Inténtalo de nuevo.");
    expect(es.session.retry).toBe("Reintentar");
  });
});

describe("settleLogout", () => {
  it.each<LogoutOutcome>([{ kind: "loggedOut" }, ...FAILURE_REASONS.map((reason) => ({ kind: "failed" as const, reason }))])(
    "devuelve tal cual %o sin registrar nada",
    async (outcome) => {
      const logError = vi.fn();
      await expect(settleLogout({ logout: async () => outcome, logError })).resolves.toEqual(outcome);
      expect(logError).not.toHaveBeenCalled();
    },
  );

  it("un rechazo es un fallo del código: failed(unexpected) y registrado una vez", async () => {
    const failure = new RangeError("fallo del código");
    const logError = vi.fn();

    const outcome = await settleLogout({
      logout: async () => {
        throw failure;
      },
      logError,
    });

    expect(outcome).toEqual({ kind: "failed", reason: "unexpected" });
    expect(logError).toHaveBeenCalledExactlyOnceWith(failure);
  });
});

describe("registrationResult: lo que hace markRegistered", () => {
  it("pasa a la sesión abierta y anuncia «Cuenta creada.»", () => {
    expect(registrationResult()).toEqual({ status: "authenticated", announcement: es.session.registered });
    expect(es.session.registered).toBe("Cuenta creada.");
  });

  it("la respuesta de quién soy del arranque que llega después no la deshace", () => {
    expect(statusAfterWhoAmI(registrationResult().status, "anonymous")).toBe("authenticated");
  });
});

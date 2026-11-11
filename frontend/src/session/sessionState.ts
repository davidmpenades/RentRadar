import type { LogoutOutcome, WhoAmIResult } from "../api/session";
import { es } from "../i18n/es";

// Sin email: lo que el cliente no guarda no puede pintarse por error
export type SessionStatus = "unknown" | "anonymous" | "authenticated";

export type TopBarAction = "none" | "register" | "logout";

export type LogoutNoticeKind = "logout_failed";

export type SettledLogout = LogoutOutcome | { kind: "failed"; reason: "unexpected" };

export type LogoutResult = {
  status: SessionStatus;
  // El fallo no va a la región global: lo anuncia la propia región del aviso
  announcement: string | null;
  focus: "register" | "logout";
  notice: LogoutNoticeKind | null;
};

export function topBarAction(status: SessionStatus): TopBarAction {
  if (status === "anonymous") return "register";
  if (status === "authenticated") return "logout";
  return "none";
}

// Un registro o una salida posteriores saben más que una respuesta que pudo salir antes que ellos
export function statusAfterWhoAmI(current: SessionStatus, result: WhoAmIResult): SessionStatus {
  return current === "unknown" ? result : current;
}

type LoadSessionStatusOptions = {
  whoAmI: (signal?: AbortSignal) => Promise<WhoAmIResult>;
  signal: AbortSignal;
  logError: (error: unknown) => void;
};

// null si se canceló: el resultado de una petición cancelada nunca se aplica, ni aunque llegue
export async function loadSessionStatus({ whoAmI, signal, logError }: LoadSessionStatusOptions) {
  try {
    const result = await whoAmI(signal);
    return signal.aborted ? null : result;
  } catch (error) {
    if (signal.aborted) return null;
    // whoAmI ya resuelve la red y el tiempo vencido: lo que rechaza es un fallo del código
    logError(error);
    return "anonymous";
  }
}

type SettleLogoutOptions = {
  logout: () => Promise<LogoutOutcome>;
  logError: (error: unknown) => void;
};

// Un rechazo de la salida no puede dejar «Salir» deshabilitado para siempre
export async function settleLogout({ logout, logError }: SettleLogoutOptions): Promise<SettledLogout> {
  try {
    return await logout();
  } catch (error) {
    logError(error);
    return { kind: "failed", reason: "unexpected" };
  }
}

// Tras un fallo o un tiempo vencido no se pregunta quién soy: reintentar sin sesión también sale bien
export function logoutResult(outcome: SettledLogout): LogoutResult {
  if (outcome.kind === "loggedOut") {
    return { status: "anonymous", announcement: es.session.loggedOut, focus: "register", notice: null };
  }
  return { status: "authenticated", announcement: null, focus: "logout", notice: "logout_failed" };
}

// Cerrar el aviso no cambia la sesión ni lo que se anuncia: solo lo retira y devuelve el foco a Salir
export function dismissResult(): { notice: null; focus: "logout" } {
  return { notice: null, focus: "logout" };
}

export function registrationResult(): { status: SessionStatus; announcement: string } {
  return { status: "authenticated", announcement: es.session.registered };
}

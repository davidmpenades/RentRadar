import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import type { SessionClient } from "../api/session";
import {
  loadSessionStatus,
  logoutResult,
  registrationResult,
  settleLogout,
  statusAfterWhoAmI,
  type LogoutNoticeKind,
  type SessionStatus,
} from "./sessionState";

type FocusRequest = { target: "register" | "logout" };

export type SessionContextValue = {
  status: SessionStatus;
  announcement: string;
  notice: LogoutNoticeKind | null;
  logoutPending: boolean;
  // Un objeto nuevo por petición, para que el mismo destino vuelva a enfocarse
  focusRequest: FocusRequest | null;
  logout: () => void;
  markRegistered: () => void;
};

const SessionContext = createContext<SessionContextValue | null>(null);

type SessionProviderProps = {
  client: SessionClient;
  logError: (error: unknown) => void;
  children: ReactNode;
};

export function SessionProvider({ client, logError, children }: SessionProviderProps) {
  const [status, setStatus] = useState<SessionStatus>("unknown");
  const [announcement, setAnnouncement] = useState("");
  const [notice, setNotice] = useState<LogoutNoticeKind | null>(null);
  const [logoutPending, setLogoutPending] = useState(false);
  const [focusRequest, setFocusRequest] = useState<FocusRequest | null>(null);
  // El estado llega en el siguiente render: un doble clic lo vería aún libre
  const logoutInFlight = useRef(false);

  useEffect(() => {
    const controller = new AbortController();
    void loadSessionStatus({ whoAmI: client.whoAmI, signal: controller.signal, logError }).then((result) => {
      if (result) setStatus((current) => statusAfterWhoAmI(current, result));
    });
    return () => controller.abort();
  }, [client, logError]);

  const logout = useCallback(() => {
    if (logoutInFlight.current) return;
    logoutInFlight.current = true;
    setLogoutPending(true);
    // Vaciar el aviso al empezar hace que un segundo fallo igual vuelva a anunciarse
    setNotice(null);
    setAnnouncement("");
    void settleLogout({ logout: client.logout, logError }).then((outcome) => {
      const result = logoutResult(outcome);
      logoutInFlight.current = false;
      setLogoutPending(false);
      setStatus(result.status);
      setNotice(result.notice);
      setAnnouncement(result.announcement ?? "");
      setFocusRequest({ target: result.focus });
    });
  }, [client, logError]);

  const markRegistered = useCallback(() => {
    const result = registrationResult();
    setStatus(result.status);
    setNotice(null);
    setAnnouncement(result.announcement);
  }, []);

  const value = useMemo(
    () => ({ status, announcement, notice, logoutPending, focusRequest, logout, markRegistered }),
    [status, announcement, notice, logoutPending, focusRequest, logout, markRegistered],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionContextValue {
  const value = useContext(SessionContext);
  if (!value) throw new Error("useSession necesita un SessionProvider");
  return value;
}

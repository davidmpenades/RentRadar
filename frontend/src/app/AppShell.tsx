import { useEffect, useRef, useSyncExternalStore } from "react";

import { MapPage } from "../pages/MapPage";
import { useSession } from "../session/SessionProvider";
import { topBarAction } from "../session/sessionState";
import { LogoutNotice } from "./LogoutNotice";
import type { AppNavigator } from "./navigation";
import { NotFoundPage } from "./NotFoundPage";
import { resolveRoute } from "./route";
import { TopBar } from "./TopBar";

type AppShellProps = {
  navigator: AppNavigator;
};

export function AppShell({ navigator }: AppShellProps) {
  const path = useSyncExternalStore(navigator.subscribe, navigator.getPath);
  const session = useSession();
  const registerRef = useRef<HTMLAnchorElement>(null);
  const logoutRef = useRef<HTMLButtonElement>(null);
  const zoneRef = useRef<HTMLDivElement>(null);
  const shownPath = useRef(path);

  // El destino del foco solo existe tras pintar el nuevo estado de la barra
  useEffect(() => {
    if (!session.focusRequest) return;
    const target = session.focusRequest.target === "register" ? registerRef : logoutRef;
    target.current?.focus();
  }, [session.focusRequest]);

  // Al cambiar de página el foco va a la zona, para no perderse en un elemento que ya no existe
  useEffect(() => {
    if (shownPath.current === path) return;
    shownPath.current = path;
    zoneRef.current?.focus();
  }, [path]);

  return (
    <div className="flex h-dvh flex-col">
      <TopBar
        action={topBarAction(session.status)}
        logoutPending={session.logoutPending}
        onNavigate={navigator.navigate}
        onLogout={session.logout}
        registerRef={registerRef}
        logoutRef={logoutRef}
      />
      <div ref={zoneRef} tabIndex={-1} className="relative min-h-0 flex-1">
        <LogoutNotice notice={session.notice} onRetry={session.logout} />
        {resolveRoute(path) === "notFound" ? <NotFoundPage /> : <MapPage />}
      </div>
      <div role="status" className="sr-only">
        {session.announcement}
      </div>
    </div>
  );
}

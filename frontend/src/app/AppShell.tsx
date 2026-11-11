import { useCallback, useEffect, useRef, useSyncExternalStore } from "react";

import { useFreeZoneTop } from "../map/useFreeZoneTop";
import { MapPage } from "../pages/MapPage";
import { RegisterPage } from "../pages/RegisterPage";
import { useSession } from "../session/SessionProvider";
import { topBarAction } from "../session/sessionState";
import { LogoutNotice } from "./LogoutNotice";
import type { AppNavigator } from "./navigation";
import { NotFoundPage } from "./NotFoundPage";
import { resolveRoute, type Route } from "./route";
import { TopBar } from "./TopBar";

type AppShellProps = {
  navigator: AppNavigator;
};

function Page({ route, onLeaveRegister }: { route: Route; onLeaveRegister: () => void }) {
  if (route === "notFound") return <NotFoundPage />;
  if (route === "register" || route === "redirectToRegister") return <RegisterPage onLeave={onLeaveRegister} />;
  return <MapPage />;
}

export function AppShell({ navigator }: AppShellProps) {
  const path = useSyncExternalStore(navigator.subscribe, navigator.getPath);
  const session = useSession();
  const registerRef = useRef<HTMLAnchorElement>(null);
  const logoutRef = useRef<HTMLButtonElement>(null);
  const zoneRef = useRef<HTMLDivElement>(null);
  const shownPath = useRef(path);
  // replace y no navigate: Atrás no debe volver al formulario
  const leaveRegister = useCallback(() => navigator.replace("/map"), [navigator]);
  useFreeZoneTop(zoneRef);

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
      {/* Recibe el foco por código y no es un control; el ! es necesario porque la regla global :focus-visible no va en una capa */}
      <div ref={zoneRef} tabIndex={-1} className="notice-host relative min-h-0 flex-1 outline-none!">
        <LogoutNotice notice={session.notice} onRetry={session.logout} onDismiss={session.dismissNotice} />
        <Page route={resolveRoute(path)} onLeaveRegister={leaveRegister} />
      </div>
      <div role="status" className="sr-only">
        {session.announcement}
      </div>
    </div>
  );
}

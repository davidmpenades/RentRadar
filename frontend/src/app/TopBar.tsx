import type { MouseEvent, Ref } from "react";

import { es } from "../i18n/es";
import type { TopBarAction } from "../session/sessionState";
import { isPlainLeftClick } from "./navigation";

type TopBarProps = {
  action: TopBarAction;
  logoutPending: boolean;
  onNavigate: (path: string) => void;
  onLogout: () => void;
  registerRef?: Ref<HTMLAnchorElement>;
  logoutRef?: Ref<HTMLButtonElement>;
};

const ACTION = "inline-flex min-h-11 min-w-11 items-center justify-center rounded-lg px-4 font-semibold";

export function TopBar({ action, logoutPending, onNavigate, onLogout, registerRef, logoutRef }: TopBarProps) {
  const followLink = (path: string) => (event: MouseEvent<HTMLAnchorElement>) => {
    if (!isPlainLeftClick(event)) return;
    event.preventDefault();
    onNavigate(path);
  };

  return (
    <header className="flex h-14 shrink-0 items-center justify-between gap-3 border-b border-ink/10 bg-white px-4">
      <a href="/map" onClick={followLink("/map")} className="inline-flex min-h-11 items-center text-xl font-bold">
        {es.topBar.brand}
      </a>
      {action === "register" && (
        <a ref={registerRef} href="/register" onClick={followLink("/register")} className={`${ACTION} bg-accent text-white`}>
          {es.topBar.register}
        </a>
      )}
      {action === "logout" && (
        <button
          ref={logoutRef}
          type="button"
          onClick={onLogout}
          aria-disabled={logoutPending || undefined}
          className={`${ACTION} border-2 border-ink aria-disabled:opacity-60`}
        >
          {es.topBar.logout}
        </button>
      )}
    </header>
  );
}

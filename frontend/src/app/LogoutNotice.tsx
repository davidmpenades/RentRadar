import { es } from "../i18n/es";
import type { LogoutNoticeKind } from "../session/sessionState";

type LogoutNoticeProps = {
  notice: LogoutNoticeKind | null;
  onRetry: () => void;
};

// La región está siempre montada para que cada fallo se anuncie; superpuesta, no cambia el alto del mapa
export function LogoutNotice({ notice, onRetry }: LogoutNoticeProps) {
  return (
    <div role="status" className="pointer-events-none absolute inset-x-0 top-0 z-20">
      {notice === "logout_failed" && (
        <div className="pointer-events-auto m-2 flex flex-wrap items-center justify-between gap-3 rounded-lg bg-lemon px-4 py-2 shadow-lg">
          <p className="font-semibold">{es.session.logoutFailed}</p>
          <button
            type="button"
            onClick={onRetry}
            className="inline-flex min-h-11 min-w-11 items-center justify-center rounded-lg bg-accent px-6 font-semibold text-white"
          >
            {es.session.retry}
          </button>
        </div>
      )}
    </div>
  );
}

import { es } from "../i18n/es";
import type { LogoutNoticeKind } from "../session/sessionState";

type LogoutNoticeProps = {
  notice: LogoutNoticeKind | null;
  onRetry: () => void;
  onDismiss: () => void;
};

const CARD = "pointer-events-auto flex flex-wrap items-center justify-between gap-3";
const CARD_OPEN = "m-2 rounded-lg bg-lemon px-4 py-2 shadow-lg";

// La región está siempre montada para que cada fallo se anuncie y solo lleva el mensaje; los botones van fuera para no entrar en el anuncio
export function LogoutNotice({ notice, onRetry, onDismiss }: LogoutNoticeProps) {
  return (
    <div className="pointer-events-none absolute inset-x-0 top-0 z-20">
      <div className={notice ? `${CARD} ${CARD_OPEN}` : CARD}>
        <div role="status">{notice === "logout_failed" && <p className="font-semibold">{es.session.logoutFailed}</p>}</div>
        {notice === "logout_failed" && (
          <div className="flex flex-wrap gap-2">
            <button type="button" onClick={onRetry} className="btn btn-primary">
              {es.session.retry}
            </button>
            <button type="button" onClick={onDismiss} className="btn btn-secondary">
              {es.session.dismiss}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

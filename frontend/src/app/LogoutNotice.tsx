import { es } from "../i18n/es";
import type { LogoutNoticeKind } from "../session/sessionState";
import { Indicator } from "../ui/Indicator";

type LogoutNoticeProps = {
  notice: LogoutNoticeKind | null;
  onRetry: () => void;
  onDismiss: () => void;
};

// La región está siempre montada para que cada fallo se anuncie y solo lleva el mensaje; la tarjeta conserva su contenido al cerrarse para que la salida pueda animarse y su párrafo se oculta para que el mensaje no se lea dos veces
export function LogoutNotice({ notice, onRetry, onDismiss }: LogoutNoticeProps) {
  return (
    <div className="notice-zone">
      <div role="status" className="sr-only top-0 left-0">
        {notice === "logout_failed" && es.session.logoutFailed}
      </div>
      <div className="notice-card glass" data-open={notice ? "" : undefined} inert={!notice}>
        <div className="notice-message">
          <Indicator className="size-6" />
          <p aria-hidden="true" className="font-semibold">
            {es.session.logoutFailed}
          </p>
        </div>
        <div className="notice-actions">
          <button type="button" onClick={onRetry} className="btn btn-primary">
            {es.session.retry}
          </button>
          <button type="button" onClick={onDismiss} className="btn btn-secondary">
            {es.session.dismiss}
          </button>
        </div>
      </div>
    </div>
  );
}

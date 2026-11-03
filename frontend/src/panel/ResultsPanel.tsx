import { useRef } from "react";

import { es } from "../i18n/es";
import type { ViewState } from "../state/viewState";
import { AssetCard } from "./AssetCard";
import { statusText } from "./header";

type ResultsPanelProps = {
  view: ViewState;
  onRetry: () => void;
  onReset: () => void;
};

const BUTTON =
  "mt-3 inline-flex min-h-11 items-center rounded-lg bg-accent px-6 font-semibold text-white motion-safe:transition-colors hover:bg-ink";

type PanelActionProps = ResultsPanelProps & { afterAction: () => void };

function PanelAction({ view, onRetry, onReset, afterAction }: PanelActionProps) {
  const run = (action: () => void) => () => {
    action();
    afterAction();
  };
  if (view.kind === "error") {
    return (
      <button type="button" onClick={run(onRetry)} className={BUTTON}>
        {es.map.retry}
      </button>
    );
  }
  if ((view.kind === "empty" || view.kind === "zoomIn") && view.canReset) {
    return (
      <button type="button" onClick={run(onReset)} className={BUTTON}>
        {es.panel.resetView}
      </button>
    );
  }
  return null;
}

export function ResultsPanel({ view, onRetry, onReset }: ResultsPanelProps) {
  const status = statusText(view);
  const headerRef = useRef<HTMLDivElement>(null);
  // El botón pulsado desaparece al cambiar el estado: el foco pasa antes a la cabecera, que no se anuncia por enfocarla
  const focusHeader = () => headerRef.current?.focus();
  return (
    <aside
      aria-label={es.panel.label}
      className="absolute inset-x-0 bottom-0 z-10 flex h-[40dvh] min-h-60 flex-col bg-sky shadow-lg min-[900px]:inset-y-0 min-[900px]:right-auto min-[900px]:h-auto min-[900px]:w-[400px]"
    >
      <div className="shrink-0 px-4 pt-3 pb-2">
        <div ref={headerRef} tabIndex={-1}>
          {/* Siempre presente: un anuncio solo se produce si cambia su texto */}
          <div role="status" aria-live="polite">
            {status && <p className="text-lg leading-snug font-semibold">{status}</p>}
          </div>
          <PanelAction view={view} onRetry={onRetry} onReset={onReset} afterAction={focusHeader} />
        </div>
        <p className="mt-1.5 text-sm leading-snug text-muted">{es.map.notice}</p>
      </div>
      {view.kind === "results" && (
        <ul className="min-h-0 flex-1 overflow-y-auto overscroll-contain border-t border-ink/10 px-4">
          {view.cards.map((asset) => (
            <AssetCard key={asset.public_id} asset={asset} />
          ))}
        </ul>
      )}
    </aside>
  );
}

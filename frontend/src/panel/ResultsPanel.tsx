import { useRef } from "react";

import { es } from "../i18n/es";
import type { ViewState } from "../state/viewState";
import { AssetCard } from "./AssetCard";
import { statusText } from "./header";

type ResultsPanelProps = {
  view: ViewState;
  onRetry: () => void;
  onReset: () => void;
  onClearFilters: () => void;
};

const BUTTON = "btn btn-primary mt-3";

type PanelActionProps = ResultsPanelProps & { afterAction: () => void };

function PanelAction({ view, onRetry, onReset, onClearFilters, afterAction }: PanelActionProps) {
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
  const canClearFilters = view.kind === "empty" && view.filtered;
  const canResetView = (view.kind === "empty" || view.kind === "zoomIn") && view.canReset;
  return (
    <>
      {canClearFilters && (
        <button type="button" onClick={run(onClearFilters)} className={BUTTON}>
          {es.search.clearAll}
        </button>
      )}
      {canResetView && (
        <button type="button" onClick={run(onReset)} className={BUTTON}>
          {es.panel.resetView}
        </button>
      )}
    </>
  );
}

export function ResultsPanel({ view, onRetry, onReset, onClearFilters }: ResultsPanelProps) {
  const status = statusText(view);
  const headerRef = useRef<HTMLDivElement>(null);
  // El botón pulsado desaparece al cambiar el estado: el foco pasa antes a la cabecera, que no se anuncia por enfocarla
  const focusHeader = () => headerRef.current?.focus();
  // Con el estilo fallido el mensaje y «Reintentar» ocupan el mapa: el panel no se pinta
  if (view.kind === "styleError") return null;
  return (
    <aside
      aria-label={es.panel.label}
      data-results-panel=""
      className="glass absolute inset-x-0 bottom-0 z-10 flex h-(--panel-height) flex-col rounded-t-surface min-[900px]:inset-y-0 min-[900px]:right-auto min-[900px]:h-auto min-[900px]:w-[400px] min-[900px]:rounded-t-none min-[900px]:rounded-r-surface"
    >
      <div className="shrink-0 px-4 py-3">
        <div ref={headerRef} tabIndex={-1}>
          {/* Siempre presente: un anuncio solo se produce si cambia su texto */}
          <div role="status" aria-live="polite">
            {status && <h2 className="text-lg leading-snug font-semibold">{status}</h2>}
          </div>
          <PanelAction
            view={view}
            onRetry={onRetry}
            onReset={onReset}
            onClearFilters={onClearFilters}
            afterAction={focusHeader}
          />
        </div>
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

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { fetchPublicAssets } from "../api/publicAssets";
import { circlesToFeatureCollection } from "../map/circles";
import { loadAssetsForView } from "../map/loadAssets";
import { MapView } from "../map/MapView";
import type { VisibleBounds } from "../map/requestBox";
import { createRequestScheduler, REQUEST_DELAY_MS } from "../map/scheduler";
import { atInitialView, type Viewport } from "../map/viewport";
import { ResultsPanel } from "../panel/ResultsPanel";
import { INITIAL_REQUEST, requestCircles, startLoading, viewState, type RequestState } from "../state/viewState";

export function MapPage() {
  const [request, setRequest] = useState<RequestState>(INITIAL_REQUEST);
  const [styleFailed, setStyleFailed] = useState(false);
  const [atInitial, setAtInitial] = useState(true);
  const [resetSignal, setResetSignal] = useState(0);
  const boundsRef = useRef<VisibleBounds | null>(null);
  const schedulerRef = useRef<ReturnType<typeof createRequestScheduler<number>> | null>(null);

  const view = viewState({ styleFailed, request, atInitialView: atInitial });
  const circles = useMemo(() => circlesToFeatureCollection(requestCircles(request)), [request]);

  useEffect(() => {
    const scheduler = createRequestScheduler({
      delayMs: REQUEST_DELAY_MS,
      setTimer: (callback, ms) => window.setTimeout(callback, ms),
      clearTimer: (handle) => window.clearTimeout(handle),
      run: (scheduled) => {
        const bounds = boundsRef.current;
        if (!bounds) return;
        // Si el cuadro no se pide, el aviso llega en el mismo lote y «Buscando» no llega a pintarse
        setRequest(startLoading);
        void loadAssetsForView({
          bounds,
          request: scheduled,
          fetchAssets: fetchPublicAssets,
          report: setRequest,
          logError: (error) => console.error(error),
        });
      },
    });
    schedulerRef.current = scheduler;
    return () => {
      scheduler.cancel();
      schedulerRef.current = null;
    };
  }, []);

  const handleReady = useCallback((viewport: Viewport) => {
    boundsRef.current = viewport.bounds;
    setAtInitial(atInitialView(viewport));
    schedulerRef.current?.runNow();
  }, []);

  const handleMoveStart = useCallback(() => {
    schedulerRef.current?.cancel();
  }, []);

  const handleMoveEnd = useCallback((viewport: Viewport) => {
    boundsRef.current = viewport.bounds;
    setAtInitial(atInitialView(viewport));
    schedulerRef.current?.schedule();
  }, []);

  const handleStyleFailed = useCallback(() => setStyleFailed(true), []);

  const handleStyleRetry = useCallback(() => {
    setStyleFailed(false);
    setRequest(INITIAL_REQUEST);
  }, []);

  const handleRetry = useCallback(() => schedulerRef.current?.runNow(), []);

  const handleReset = useCallback(() => setResetSignal((current) => current + 1), []);

  return (
    <main className="relative h-full overflow-hidden">
      <MapView
        circles={circles}
        styleFailed={styleFailed}
        resetSignal={resetSignal}
        onStyleFailed={handleStyleFailed}
        onStyleRetry={handleStyleRetry}
        onReady={handleReady}
        onMoveStart={handleMoveStart}
        onMoveEnd={handleMoveEnd}
      />
      <ResultsPanel view={view} onRetry={handleRetry} onReset={handleReset} />
    </main>
  );
}

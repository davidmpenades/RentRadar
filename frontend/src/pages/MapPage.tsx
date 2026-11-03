import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { fetchPublicAssets } from "../api/publicAssets";
import type { components } from "../api/schema.gen";
import { es } from "../i18n/es";
import { circlesToFeatureCollection, uniqueCircles } from "../map/circles";
import { loadAssetsForView } from "../map/loadAssets";
import { MapView } from "../map/MapView";
import type { VisibleBounds } from "../map/requestBox";
import { createRequestScheduler, REQUEST_DELAY_MS } from "../map/scheduler";

type PublicAsset = components["schemas"]["PublicAsset"];

export function MapPage() {
  const [assets, setAssets] = useState<readonly PublicAsset[]>([]);
  const circles = useMemo(() => circlesToFeatureCollection(uniqueCircles(assets)), [assets]);
  const boundsRef = useRef<VisibleBounds | null>(null);
  const schedulerRef = useRef<ReturnType<typeof createRequestScheduler<number>> | null>(null);

  useEffect(() => {
    const scheduler = createRequestScheduler({
      delayMs: REQUEST_DELAY_MS,
      setTimer: (callback, ms) => window.setTimeout(callback, ms),
      clearTimer: (handle) => window.clearTimeout(handle),
      run: (request) => {
        const bounds = boundsRef.current;
        if (!bounds) return;
        void loadAssetsForView({
          bounds,
          request,
          fetchAssets: fetchPublicAssets,
          show: setAssets,
          clear: () => setAssets([]),
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

  const handleReady = useCallback((bounds: VisibleBounds) => {
    boundsRef.current = bounds;
    schedulerRef.current?.runNow();
  }, []);

  const handleMoveStart = useCallback(() => {
    schedulerRef.current?.cancel();
  }, []);

  const handleMoveEnd = useCallback((bounds: VisibleBounds) => {
    boundsRef.current = bounds;
    schedulerRef.current?.schedule();
  }, []);

  return (
    <main className="relative h-dvh overflow-hidden">
      <MapView circles={circles} onReady={handleReady} onMoveStart={handleMoveStart} onMoveEnd={handleMoveEnd} />
      <aside className="absolute inset-x-0 bottom-0 z-10 h-[40dvh] min-h-60 overflow-y-auto bg-sky p-4 shadow-lg min-[900px]:inset-y-0 min-[900px]:right-auto min-[900px]:h-auto min-[900px]:w-[400px]">
        <p className="text-sm text-muted">{es.map.notice}</p>
      </aside>
    </main>
  );
}

import "maplibre-gl/dist/maplibre-gl.css";
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import {
  AttributionControl,
  GeoJSONSource,
  Map as MapLibreMap,
  NavigationControl,
  setWorkerUrl,
  type StyleSpecification,
} from "maplibre-gl";
import { useEffect, useRef, useState } from "react";

import { es } from "../i18n/es";
import type { CircleCollection } from "./circles";
import { loadStyle } from "./loadStyle";
import type { VisibleBounds } from "./requestBox";
import { createMapErrorListener, createTransformRequest, validateStyleUrl } from "./style";

// Sin esto MapLibre busca el worker junto al módulo, y tras empaquetar no existe
setWorkerUrl(workerUrl);

const DEFAULT_STYLE_URL = "https://tiles.openfreemap.org/styles/positron";
const INITIAL_CENTER: [number, number] = [-0.3763, 39.4699];
const INITIAL_ZOOM = 11;
const CIRCLES_SOURCE = "circles";
const ACCENT = "#1647b8";

const configuredStyleUrl: unknown = import.meta.env.VITE_MAP_STYLE_URL;
const styleUrl = validateStyleUrl(
  typeof configuredStyleUrl === "string" && configuredStyleUrl !== "" ? configuredStyleUrl : DEFAULT_STYLE_URL,
);

const EMPTY_CIRCLES: CircleCollection = { type: "FeatureCollection", features: [] };

type MapViewProps = {
  circles: CircleCollection;
  onReady: (bounds: VisibleBounds) => void;
  onMoveStart: () => void;
  onMoveEnd: (bounds: VisibleBounds) => void;
};

function visibleBounds(map: MapLibreMap): VisibleBounds {
  const bounds = map.getBounds();
  return { south: bounds.getSouth(), west: bounds.getWest(), north: bounds.getNorth(), east: bounds.getEast() };
}

function addCircleLayers(map: MapLibreMap): void {
  map.addSource(CIRCLES_SOURCE, { type: "geojson", data: EMPTY_CIRCLES });
  map.addLayer({
    id: "circles-fill",
    type: "fill",
    source: CIRCLES_SOURCE,
    paint: { "fill-color": ACCENT, "fill-opacity": 0.12 },
  });
  map.addLayer({
    id: "circles-line",
    type: "line",
    source: CIRCLES_SOURCE,
    paint: { "line-color": ACCENT, "line-width": 1.5 },
  });
}

function createMap(container: HTMLElement, style: StyleSpecification, allowedOrigins: string[]): MapLibreMap {
  const map = new MapLibreMap({
    container,
    style,
    center: INITIAL_CENTER,
    zoom: INITIAL_ZOOM,
    dragRotate: false,
    pitchWithRotate: false,
    maxPitch: 0,
    attributionControl: false,
    locale: es.map.locale,
    transformRequest: createTransformRequest(allowedOrigins),
  });
  map.touchZoomRotate.disableRotation();
  map.keyboard.disableRotation();
  map.on("error", createMapErrorListener((error) => console.error(error)));
  map.addControl(new AttributionControl({ compact: false }), "top-right");
  map.addControl(new NavigationControl({ showCompass: false }), "top-right");
  return map;
}

export function MapView({ circles, onReady, onMoveStart, onMoveEnd }: MapViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [failed, setFailed] = useState(styleUrl === undefined);
  const [attempt, setAttempt] = useState(0);
  const [loadedMap, setLoadedMap] = useState<MapLibreMap | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!styleUrl || !container) return;

    const controller = new AbortController();
    let map: MapLibreMap | undefined;

    async function start(url: URL, element: HTMLElement) {
      try {
        const style = await loadStyle(url.href, controller.signal);
        if (controller.signal.aborted) return;
        // new Map lanza si no hay WebGL2: se trata como un estilo que no carga
        map = createMap(element, style as unknown as StyleSpecification, [url.origin, window.location.origin]);
      } catch {
        if (!controller.signal.aborted) setFailed(true);
        return;
      }
      const created = map;
      created.once("load", () => {
        addCircleLayers(created);
        setLoadedMap(created);
        onReady(visibleBounds(created));
        // Una animación interrumpida emite moveend antes de la siguiente: no está quieto hasta que nadie la sigue
        created.on("movestart", onMoveStart);
        created.on("moveend", () => onMoveEnd(visibleBounds(created)));
      });
    }
    void start(styleUrl, container);

    return () => {
      controller.abort();
      map?.remove();
      setLoadedMap(null);
    };
  }, [attempt, onReady, onMoveStart, onMoveEnd]);

  useEffect(() => {
    loadedMap?.getSource<GeoJSONSource>(CIRCLES_SOURCE)?.setData(circles);
  }, [loadedMap, circles]);

  function retry() {
    // Con una dirección que no pasa la validación no hay nada que repetir
    setFailed(styleUrl === undefined);
    setAttempt((current) => current + 1);
  }

  if (failed) {
    return (
      <div role="alert" className="absolute inset-0 flex flex-col items-center justify-center gap-4 p-4 text-center">
        <p className="text-lg font-semibold">{es.map.styleError}</p>
        <button
          type="button"
          onClick={retry}
          className="inline-flex min-h-11 items-center rounded-lg bg-accent px-6 font-semibold text-white"
        >
          {es.map.retry}
        </button>
      </div>
    );
  }

  // MapLibre pone position: relative al contenedor y pisaría a absolute: el hueco lo da el envoltorio
  return (
    <div className="absolute inset-0">
      <div ref={containerRef} className="h-full w-full" />
    </div>
  );
}

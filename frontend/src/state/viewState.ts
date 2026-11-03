import type { FailureKind } from "../api/publicAssets";
import type { components } from "../api/schema.gen";
import { isCircleVisible, uniqueCircles, type Circle } from "../map/circles";
import type { RequestOutcome } from "../map/loadAssets";

type PublicAsset = components["schemas"]["PublicAsset"];

type LoadedRequest = Extract<RequestOutcome, { kind: "loaded" }>;

// Único estado de la petición: el panel y los círculos del mapa se derivan de él.
// loading conserva la última respuesta cargada solo para que los círculos no parpadeen al mover
export type RequestState = { kind: "loading"; previous: LoadedRequest | null } | RequestOutcome;

export const INITIAL_REQUEST: RequestState = { kind: "loading", previous: null };

// Un fallo o un cuadro sin pedir descartan la respuesta anterior: ahí no debe haber círculos
export function startLoading(current: RequestState): RequestState {
  if (current.kind === "loaded") return { kind: "loading", previous: current };
  return { kind: "loading", previous: current.kind === "loading" ? current.previous : null };
}

function loadedRequest(request: RequestState): LoadedRequest | null {
  if (request.kind === "loaded") return request;
  return request.kind === "loading" ? request.previous : null;
}

export type ViewState =
  | { kind: "loading" }
  | { kind: "results"; cards: readonly PublicAsset[]; incomplete: boolean }
  | { kind: "empty"; canReset: boolean }
  | { kind: "zoomIn"; canReset: boolean }
  | { kind: "error"; failure: FailureKind | "unexpected" }
  | { kind: "styleError" };

type ViewStateInput = { styleFailed: boolean; request: RequestState; atInitialView: boolean };

// Una tarjeta por cada bien de la respuesta, en su orden, cuyo círculo toca la zona visible del momento de pedir
function cardsOf(request: LoadedRequest): PublicAsset[] {
  const { list, visibleBounds } = request;
  return list.results.filter((asset) =>
    isCircleVisible(
      { latitude: asset.latitude, longitude: asset.longitude, radius: asset.privacy_radius },
      visibleBounds,
    ),
  );
}

export function viewState({ styleFailed, request, atInitialView }: ViewStateInput): ViewState {
  if (styleFailed) return { kind: "styleError" };
  const canReset = !atInitialView;
  switch (request.kind) {
    case "loading":
      return { kind: "loading" };
    case "notRequested":
      return { kind: "zoomIn", canReset };
    case "failed":
      return { kind: "error", failure: request.failure };
    case "loaded": {
      const cards = cardsOf(request);
      return cards.length === 0
        ? { kind: "empty", canReset }
        : { kind: "results", cards, incomplete: request.list.incomplete };
    }
  }
}

// Todos los bienes de la respuesta cargada, aunque no tengan tarjeta; durante loading, los de la última
export function requestCircles(request: RequestState): Circle[] {
  const loaded = loadedRequest(request);
  return loaded ? uniqueCircles(loaded.list.results) : [];
}

import { classifyFailure } from "../api/publicAssets";
import type { components } from "../api/schema.gen";
import type { ScheduledRequest } from "./scheduler";
import { requestBox, type RequestBox, type VisibleBounds } from "./requestBox";

type PublicAsset = components["schemas"]["PublicAsset"];
type PublicAssetList = components["schemas"]["PublicAssetList"];

type LoadAssetsOptions = {
  bounds: VisibleBounds;
  request: ScheduledRequest;
  fetchAssets: (box: RequestBox, signal: AbortSignal) => Promise<PublicAssetList>;
  show: (assets: readonly PublicAsset[]) => void;
  clear: () => void;
  logError: (error: unknown) => void;
};

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

// Decide qué hacen los círculos tras una petición: pintar la respuesta, vaciarlos o no tocarlos
export async function loadAssetsForView(options: LoadAssetsOptions): Promise<void> {
  const { bounds, request, fetchAssets, show, clear, logError } = options;

  const box = requestBox(bounds);
  if (box.kind !== "ok") {
    clear();
    return;
  }

  try {
    const list = await fetchAssets(box.box, request.signal);
    if (request.isCurrent()) show(list.results);
  } catch (error) {
    // Una petición vieja no decide nada: la nueva pinta o vacía por su cuenta
    if (isAbortError(error) || !request.isCurrent()) return;
    try {
      classifyFailure(error);
    } catch {
      logError(error);
    }
    clear();
  }
}

import { classifyFailure, type FailureKind } from "../api/publicAssets";
import type { components } from "../api/schema.gen";
import type { ScheduledRequest } from "./scheduler";
import { requestBox, type RequestBox, type VisibleBounds } from "./requestBox";

type PublicAssetList = components["schemas"]["PublicAssetList"];

export type RequestOutcome =
  // La zona visible es la del momento de pedir, no el cuadro pedido (que va 2 km más allá)
  | { kind: "loaded"; list: PublicAssetList; visibleBounds: VisibleBounds }
  | { kind: "notRequested"; reason: "tooLarge" | "outOfRange" }
  | { kind: "failed"; failure: FailureKind | "unexpected" };

type LoadAssetsOptions = {
  bounds: VisibleBounds;
  request: ScheduledRequest;
  fetchAssets: (box: RequestBox, signal: AbortSignal) => Promise<PublicAssetList>;
  report: (outcome: RequestOutcome) => void;
  logError: (error: unknown) => void;
};

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

// Un error que no es de una causa conocida es un fallo del código: se registra y se muestra como inesperado
function failureOf(error: unknown, logError: (error: unknown) => void): FailureKind | "unexpected" {
  try {
    return classifyFailure(error);
  } catch {
    logError(error);
    return "unexpected";
  }
}

// Pide los bienes de la zona y reporta cómo acabó, salvo si la petición se canceló o ya no es la actual
export async function loadAssetsForView(options: LoadAssetsOptions): Promise<void> {
  const { bounds, request, fetchAssets, report, logError } = options;

  const box = requestBox(bounds);
  if (box.kind !== "ok") {
    report({ kind: "notRequested", reason: box.kind });
    return;
  }

  try {
    const list = await fetchAssets(box.box, request.signal);
    if (request.isCurrent()) report({ kind: "loaded", list, visibleBounds: bounds });
  } catch (error) {
    // Una petición vieja no decide nada: la nueva reporta por su cuenta
    if (isAbortError(error) || !request.isCurrent()) return;
    report({ kind: "failed", failure: failureOf(error, logError) });
  }
}

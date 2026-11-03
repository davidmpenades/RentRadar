import { es } from "../i18n/es";
import type { ViewState } from "../state/viewState";

// El número es el de tarjetas, no el de la respuesta: un bien sin círculo a la vista no se cuenta
export function headerText(count: number, incomplete: boolean): string {
  const text = incomplete
    ? count === 1
      ? es.panel.incompleteOne
      : es.panel.incompleteMany
    : count === 1
      ? es.panel.countOne
      : es.panel.countMany;
  return text.replace("{count}", String(count));
}

// Lo que la región de estado anuncia; con el estilo fallido anuncia el mapa y no el panel
export function statusText(view: ViewState): string {
  switch (view.kind) {
    case "loading":
      return es.panel.searching;
    case "results":
      return headerText(view.cards.length, view.incomplete);
    case "empty":
      return es.panel.empty;
    case "zoomIn":
      return es.panel.zoomIn;
    case "error":
      return es.panel.errors[view.failure];
    case "styleError":
      return "";
  }
}

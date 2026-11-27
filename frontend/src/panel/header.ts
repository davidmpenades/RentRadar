import { es } from "../i18n/es";
import type { ViewState } from "../state/viewState";

// El número es el de tarjetas, no el de la respuesta: un bien sin círculo a la vista no se cuenta
export function headerText(count: number, incomplete: boolean, filtered: boolean): string {
  // Las ocho claves de es.panel siguen este nombre: el compilador avisa si falta alguna
  const key = `${incomplete ? "incomplete" : "count"}${count === 1 ? "One" : "Many"}${filtered ? "Filtered" : ""}` as const;
  return es.panel[key].replace("{count}", String(count));
}

// Lo que la región de estado anuncia; con el estilo fallido anuncia el mapa y no el panel
export function statusText(view: ViewState): string {
  switch (view.kind) {
    case "loading":
      return es.panel.searching;
    case "results":
      return headerText(view.cards.length, view.incomplete, view.filtered);
    case "empty":
      return view.filtered ? es.panel.emptyFiltered : es.panel.empty;
    case "zoomIn":
      return es.panel.zoomIn;
    case "error":
      return es.panel.errors[view.failure];
    case "styleError":
      return "";
  }
}

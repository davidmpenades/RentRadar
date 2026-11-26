export type FilterState = { category: string | null; text: string };

// Lo que se manda al servidor: un filtro está activo si aparece aquí
export type AppliedFilters = Readonly<{ category?: string; q?: string }>;

// Valor por defecto compartido de la petición: por eso está congelado
export const NO_FILTERS: AppliedFilters = Object.freeze({});

const CONTROL_CHARACTERS = /\p{Cc}/gu;

export function toggleCategory(state: FilterState, slug: string): FilterState {
  return { ...state, category: state.category === slug ? null : slug };
}

// Guarda lo escrito sin tocarlo: recortar aquí no dejaría teclear un espacio entre palabras
export function setText(state: FilterState, raw: string): FilterState {
  return { ...state, text: raw };
}

export function clearFilters(): FilterState {
  return { category: null, text: "" };
}

export function appliedFilters(state: FilterState): AppliedFilters {
  const text = state.text.replace(CONTROL_CHARACTERS, " ").trim();
  return {
    ...(state.category === null ? {} : { category: state.category }),
    ...(text === "" ? {} : { q: text }),
  };
}

export function hasActiveFilters(state: FilterState): boolean {
  const applied = appliedFilters(state);
  return applied.category !== undefined || applied.q !== undefined;
}

// Orden fijo: el mismo filtro da siempre la misma URL y aprovecha la caché de la lista
export function filtersQuery(applied: AppliedFilters): string {
  const params = new URLSearchParams();
  if (applied.category !== undefined) params.set("category", applied.category);
  if (applied.q !== undefined) params.set("q", applied.q);
  return params.toString();
}

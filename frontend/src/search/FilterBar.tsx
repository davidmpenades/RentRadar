import { useRef, type FormEvent } from "react";

import { es } from "../i18n/es";
import { CATEGORY_CHIPS } from "./categories";
import { hasActiveFilters, type FilterState } from "./filters";

type FilterBarProps = {
  filters: FilterState;
  onToggleCategory: (slug: string) => void;
  onTextChange: (raw: string) => void;
  onSubmit: () => void;
  onClearText: () => void;
  onClearAll: () => void;
};

const ICON = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeLinecap: "round",
  strokeLinejoin: "round",
  "aria-hidden": true,
  focusable: "false",
} as const;

function ClearIcon() {
  return (
    <svg {...ICON} strokeWidth={2} className="size-6">
      <path d="M6 6l12 12M18 6L6 18" />
    </svg>
  );
}

function SearchIcon() {
  return (
    <svg {...ICON} strokeWidth={2} className="pointer-events-none absolute start-3 top-1/2 size-5 -translate-y-1/2 text-muted">
      <circle cx="11" cy="11" r="7" />
      <path d="M20 20l-3.5-3.5" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg {...ICON} strokeWidth={3}>
      <path d="M5 12.5l4.5 4.5L19 7.5" />
    </svg>
  );
}

export function FilterBar({ filters, onToggleCategory, onTextChange, onSubmit, onClearText, onClearAll }: FilterBarProps) {
  const fieldRef = useRef<HTMLInputElement>(null);
  // El botón pulsado desaparece al cambiar el estado: el foco pasa antes al campo
  const thenFocusField = (action: () => void) => () => {
    action();
    fieldRef.current?.focus();
  };
  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSubmit();
  };

  return (
    <div className="flex h-27 shrink-0 flex-col py-1 min-[900px]:h-16 min-[900px]:flex-row min-[900px]:items-center min-[900px]:gap-3 min-[900px]:py-0">
      <form
        role="search"
        onSubmit={handleSubmit}
        className="flex shrink-0 items-center gap-2 px-3 min-[900px]:w-[400px]"
      >
        <label htmlFor="filter-text" className="sr-only">
          {es.search.label}
        </label>
        <div className="field-box min-w-0 flex-1">
          <SearchIcon />
          <input
            ref={fieldRef}
            id="filter-text"
            type="search"
            value={filters.text}
            onChange={(event) => onTextChange(event.target.value)}
            maxLength={64}
            autoComplete="off"
            spellCheck={false}
            enterKeyHint="search"
            placeholder={es.search.placeholder}
            className="field ps-11"
          />
          {filters.text !== "" && (
            <button type="button" onClick={thenFocusField(onClearText)} aria-label={es.search.clearText} className="eye">
              <ClearIcon />
            </button>
          )}
        </div>
        {hasActiveFilters(filters) && (
          <button type="button" onClick={thenFocusField(onClearAll)} className="btn btn-secondary shrink-0 px-3">
            {es.search.clearAll}
          </button>
        )}
      </form>
      {/* Con scroll-px-3, el chip enfocado con Tab queda a 12 px del borde del grupo */}
      <div
        role="group"
        aria-label={es.search.categories}
        className="flex min-w-0 flex-1 items-center gap-2 overflow-x-auto scroll-px-3 px-3 py-1 [scrollbar-width:none] min-[900px]:[scrollbar-width:thin]"
      >
        {CATEGORY_CHIPS.map((slug) => {
          const active = filters.category === slug;
          return (
            <button
              key={slug}
              type="button"
              aria-pressed={active}
              onClick={() => onToggleCategory(slug)}
              // Chrome no desplaza un chip que ya se ve en parte
              onFocus={(event) => event.currentTarget.scrollIntoView({ block: "nearest", inline: "nearest" })}
              className="chip"
            >
              {active && <CheckIcon />}
              {es.categories[slug]}
            </button>
          );
        })}
      </div>
    </div>
  );
}

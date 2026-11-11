type IndicatorProps = { className: string };

// Icono de error decorativo: el texto que lo acompaña es lo que se lee
export function Indicator({ className }: IndicatorProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      className={`shrink-0 text-danger ${className}`}
    >
      <circle cx="12" cy="12" r="10" />
      <path d="M12 7v6M12 16.5v.5" />
    </svg>
  );
}

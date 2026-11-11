import { es } from "./es";

const PRICE = /^(\d{1,5})\.(\d{2})$/;

// Los céntimos salen del texto del servidor, sin pasar por un float
export function parsePriceCents(price: string): number {
  const match = PRICE.exec(price);
  if (!match) throw new RangeError("Precio con un formato no válido");
  return Number(match[1]) * 100 + Number(match[2]);
}

// La unidad llega como texto del tipo generado; la respuesta ya se validó contra las cuatro conocidas
function unitLabel(unit: string): string {
  if (!Object.hasOwn(es.panel.priceUnit, unit)) throw new RangeError("Unidad de precio no válida");
  return es.panel.priceUnit[unit as keyof typeof es.panel.priceUnit];
}

export function formatPrice(price: string, unit: string): { amount: string; unit: string } {
  const cents = parsePriceCents(price);
  const amount = new Intl.NumberFormat("es-ES", {
    style: "currency",
    currency: "EUR",
    minimumFractionDigits: cents % 100 === 0 ? 0 : 2,
    maximumFractionDigits: 2,
  }).format(cents / 100);
  return { amount, unit: unitLabel(unit) };
}

// Con espacio duro, para que la cifra y la unidad no se partan entre dos líneas
export function formatRadius(meters: number): string {
  return meters % 1000 === 0 ? `${meters / 1000}\u00A0km` : `${meters}\u00A0m`;
}

export function waitMinutes(seconds: number): number {
  return Math.max(1, Math.ceil(seconds / 60));
}

export function throttledMessage(seconds: number): string {
  const minutes = waitMinutes(seconds);
  return minutes === 1
    ? es.auth.throttledOne
    : es.auth.throttledMany.replace("{minutes}", String(minutes));
}

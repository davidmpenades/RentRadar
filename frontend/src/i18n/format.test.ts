import { describe, expect, it } from "vitest";

import { formatPrice, formatRadius, parsePriceCents } from "./format";

// Intl separa el número del símbolo con un espacio duro: se normaliza para comparar con texto visible
const NBSP = String.fromCharCode(160);
const visible = (text: string) => text.replaceAll(NBSP, " ").replaceAll(String.fromCharCode(8239), " ");
const shown = (price: string, unit: string) => {
  const parts = formatPrice(price, unit);
  return visible(`${parts.amount} / ${parts.unit}`);
};

describe("parsePriceCents", () => {
  it.each([
    ["12.50", 1250],
    ["30.00", 3000],
    ["0.01", 1],
    ["0.10", 10],
    ["0.00", 0],
    ["99999.99", 9_999_999],
    ["8.05", 805],
  ])("lee %s como %d céntimos enteros", (price, cents) => {
    expect(parsePriceCents(price)).toBe(cents);
  });

  it("devuelve siempre un entero, también donde el float falla", () => {
    // 1.15 * 100 y 4.35 * 100 no dan enteros en coma flotante
    expect(parsePriceCents("1.15")).toBe(115);
    expect(parsePriceCents("4.35")).toBe(435);
    expect(parsePriceCents("0.29")).toBe(29);
  });

  it.each(["12", "12.5", "12,50", "-1.00", "100000.00", "1e2", " 1.00", "abc", ""])("rechaza %j", (price) => {
    expect(() => parsePriceCents(price)).toThrow(RangeError);
  });
});

describe("formatPrice", () => {
  it.each([
    ["12.50", "day", "12,50 € / día"],
    ["30.00", "week", "30 € / semana"],
    ["25.00", "hour", "25 € / hora"],
    ["650.00", "month", "650 € / mes"],
    ["0.01", "hour", "0,01 € / hora"],
    ["0.10", "day", "0,10 € / día"],
    ["99999.99", "month", "99.999,99 € / mes"],
    ["49.90", "day", "49,90 € / día"],
    ["1000.00", "day", "1000 € / día"],
  ] as const)("%s por %s se ve como «%s»", (price, unit, expected) => {
    expect(shown(price, unit)).toBe(expected);
  });

  it("deja los céntimos solo cuando no son cero", () => {
    expect(formatPrice("30.00", "day").amount).not.toContain(",");
    expect(formatPrice("30.01", "day").amount).toContain(",01");
  });

  it("no pierde ningún céntimo en una muestra de todo el rango", () => {
    let seed = 12345;
    for (let sample = 0; sample < 2000; sample += 1) {
      seed = (seed * 1_103_515_245 + 12_345) % 2_147_483_648;
      const cents = seed % 10_000_000;
      const price = `${Math.floor(cents / 100)}.${String(cents % 100).padStart(2, "0")}`;
      const digits = visible(formatPrice(price, "day").amount).replace(/\D/g, "");
      const expected = cents % 100 === 0 ? String(cents / 100) : String(cents);
      expect(digits).toBe(expected);
    }
  });
});

describe("formatPrice con una unidad desconocida", () => {
  it.each(["year", "", "Day", "__proto__", "constructor", "toString"])("rechaza %j", (unit) => {
    expect(() => formatPrice("12.50", unit)).toThrow(RangeError);
  });
});

describe("formatRadius", () => {
  it.each([
    [500, "500 m"],
    [1000, "1 km"],
    [2000, "2 km"],
  ])("%d m se ve como «%s»", (meters, expected) => {
    expect(formatRadius(meters)).toBe(expected);
  });
});

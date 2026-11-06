import { describe, expect, it } from "vitest";
import { hasJsonContentType } from "./http";

function responseWith(contentType: string | null): Response {
  const headers = contentType === null ? undefined : { "Content-Type": contentType };
  return new Response(null, { headers });
}

describe("hasJsonContentType", () => {
  it.each([
    "application/json",
    "application/json; charset=utf-8",
    "Application/JSON",
    " application/json ",
    "application/json ;charset=utf-8",
  ])("acepta %j", (contentType) => {
    expect(hasJsonContentType(responseWith(contentType))).toBe(true);
  });

  it.each([
    "text/html",
    "application/jsonx",
    "application/json-patch+json",
    "application/problem+json",
    "",
  ])("rechaza %j", (contentType) => {
    expect(hasJsonContentType(responseWith(contentType))).toBe(false);
  });

  it("rechaza una respuesta sin cabecera", () => {
    expect(hasJsonContentType(responseWith(null))).toBe(false);
  });
});

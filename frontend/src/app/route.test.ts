import { describe, expect, it } from "vitest";

import { resolveRoute } from "./route";

describe("resolveRoute", () => {
  it("normaliza la raíz y la dirección con barra final", () => {
    expect(resolveRoute("/")).toBe("redirectToMap");
    expect(resolveRoute("/map/")).toBe("redirectToMap");
  });

  it("muestra el mapa en /map", () => {
    expect(resolveRoute("/map")).toBe("map");
  });

  it("normaliza la dirección del registro con barra final", () => {
    expect(resolveRoute("/register/")).toBe("redirectToRegister");
  });

  it("muestra el registro en /register", () => {
    expect(resolveRoute("/register")).toBe("register");
  });

  it.each([
    "/otra",
    "/map//",
    "/map/x",
    "/maps",
    "/MAP",
    "/map.html",
    "/index.html",
    "//map",
    "",
    "/register//",
    "/REGISTER",
    "/register/x",
    "/registers",
    "//register",
    "/register.html",
  ])(
    "muestra la página no encontrada en %j",
    (pathname) => {
      expect(resolveRoute(pathname)).toBe("notFound");
    },
  );
});

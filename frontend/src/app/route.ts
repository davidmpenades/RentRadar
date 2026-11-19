export type Route =
  | "redirectToMap"
  | "map"
  | "redirectToRegister"
  | "register"
  | "redirectToLogin"
  | "login"
  | "notFound";

export function resolveRoute(pathname: string): Route {
  if (pathname === "/" || pathname === "/map/") return "redirectToMap";
  if (pathname === "/map") return "map";
  if (pathname === "/register/") return "redirectToRegister";
  if (pathname === "/register") return "register";
  if (pathname === "/login/") return "redirectToLogin";
  if (pathname === "/login") return "login";
  return "notFound";
}

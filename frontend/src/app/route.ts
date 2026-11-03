export type Route = "redirectToMap" | "map" | "notFound";

export function resolveRoute(pathname: string): Route {
  if (pathname === "/" || pathname === "/map/") return "redirectToMap";
  if (pathname === "/map") return "map";
  return "notFound";
}

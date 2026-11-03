import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { NotFoundPage } from "./app/NotFoundPage";
import { resolveRoute } from "./app/route";
import { MapPage } from "./pages/MapPage";
import "./styles/index.css";

const root = document.getElementById("root");
if (!root) throw new Error("Falta el contenedor raíz");

const route = resolveRoute(window.location.pathname);
// replaceState y no pushState: Atrás no debe devolver a la raíz
if (route === "redirectToMap") window.history.replaceState(null, "", "/map");

createRoot(root).render(<StrictMode>{route === "notFound" ? <NotFoundPage /> : <MapPage />}</StrictMode>);

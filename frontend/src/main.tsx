import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { es } from "./i18n/es";
import "./styles/index.css";

const root = document.getElementById("root");
if (!root) throw new Error("Falta el contenedor raíz");

createRoot(root).render(
  <StrictMode>
    <h1 className="p-4 text-2xl font-bold text-accent">{es.app.name}</h1>
  </StrictMode>,
);

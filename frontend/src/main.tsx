import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { sessionClient } from "./api/session";
import { AppShell } from "./app/AppShell";
import { createNavigator } from "./app/navigation";
import { resolveRoute } from "./app/route";
import { SessionProvider } from "./session/SessionProvider";
import "./styles/index.css";

const root = document.getElementById("root");
if (!root) throw new Error("Falta el contenedor raíz");

// replaceState y no pushState: Atrás no debe devolver a la raíz
if (resolveRoute(window.location.pathname) === "redirectToMap") window.history.replaceState(null, "", "/map");

const appNavigator = createNavigator({
  history: window.history,
  getPathname: () => window.location.pathname,
  addPopStateListener: (listener) => window.addEventListener("popstate", listener),
});
const logError = (error: unknown) => console.error(error);

createRoot(root).render(
  <StrictMode>
    <SessionProvider client={sessionClient} logError={logError}>
      <AppShell navigator={appNavigator} />
    </SessionProvider>
  </StrictMode>,
);

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: "localhost",
    port: 5173,
    strictPort: true,
    // El navegador solo habla con este origen: la API llega por el proxy
    // Como objeto: la forma abreviada activa changeOrigin y Django recibiría otro Host
    proxy: { "/api": { target: "http://localhost:8000", changeOrigin: false } },
  },
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
  },
});

import { defineConfig } from "vite";

// Dev frontend runs on :5173, backend on :8000. main.ts connects directly
// to the backend URL instead of through a Vite proxy (Vite 8's WS proxy is
// fiddly and not worth debugging for a hobby app). In production, the backend
// serves the built bundle at the same origin, so the client uses location.host.
export default defineConfig({
  server: {
    port: 5173,
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
});

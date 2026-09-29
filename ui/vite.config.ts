import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The build goes straight into the Python app's web folder: the server (and the desktop app)
// serve it as static files, so running ENGRAMM needs no Node.js.
export default defineConfig({
  plugins: [react()],
  base: "./",
  build: {
    outDir: "../engramm/app/web",
    emptyOutDir: true,
    assetsDir: "assets",
    sourcemap: false,
  },
  server: {
    port: 5173,
    proxy: { "/api": "http://127.0.0.1:8770" },
  },
});

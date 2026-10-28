import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The API runs separately (uvicorn on port 8000, or set API_URL). In
// development Vite forwards API requests to it, so the browser only ever
// talks to one address and no CORS setup is needed.
const API = process.env.API_URL ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/players": API,
      "/matches": API,
      "/healthz": API,
    },
  },
});

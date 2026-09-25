/// <reference types="vitest/config" />
import { defineConfig } from "vite";

// The Python backend (uvicorn app.main:app) runs on :8000; proxy the stream and the socket.
export default defineConfig({
  build: {
    chunkSizeWarningLimit: 900, // three.js is most of the bundle
  },
  server: {
    proxy: {
      "/video": "http://127.0.0.1:8000",
      "/ws": { target: "ws://127.0.0.1:8000", ws: true },
    },
  },
  test: {
    environment: "node",
  },
});

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        // The activity stream is a long-lived SSE connection. Without this,
        // the proxy's default socket timeout can silently kill an idle
        // connection, and the browser's EventSource then reconnects in a
        // tight loop — showing up as a burst of repeated /activity/stream
        // requests and brief gaps in the live event feed.
        timeout: 0,
        proxyTimeout: 0
      }
    }
  }
});

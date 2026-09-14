import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    strictPort: true,
    proxy: {
      // Proxy all /api/ calls to the FastAPI backend — avoids CORS issues in dev
      // Use 127.0.0.1 explicitly: on Windows, 'localhost' may resolve to IPv6 [::1]
      // but uvicorn listens on IPv4 127.0.0.1, causing connection refused errors.
      "/api/": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        secure: false,
      },
      "/health": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});

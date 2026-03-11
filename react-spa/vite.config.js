import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

/**
 * Vite configuration for DesignApp React SPA.
 *
 * Dev mode  : npm run dev
 *   - Runs on http://localhost:5173
 *   - Proxies /api/* → http://localhost:5000  (Flask)
 *   - Hot-module replacement on all .jsx/.js changes
 *
 * Production: npm run build
 *   - Output → ../ui/static/dist/
 *   - Flask serves this directory at /static/dist/ (configured in app.py)
 */
export default defineConfig({
  plugins: [react()],

  // Resolve "@/" as "src/"
  resolve: {
    alias: { "@": path.resolve(__dirname, "src") },
  },

  server: {
    port: 5173,
    proxy: {
      // Forward all /api/* calls to Flask during dev
      "/api": {
        target:       "http://localhost:5000",
        changeOrigin: true,
        secure:       false,
      },
    },
  },

  build: {
    // Output directly into Flask's static/dist folder
    outDir:    path.resolve(__dirname, "../ui/static/dist"),
    emptyOutDir: true,
    sourcemap: false,
    rollupOptions: {
      output: {
        // Split vendor chunk for better caching
        manualChunks: {
          vendor: ["react", "react-dom", "react-router-dom"],
        },
      },
    },
  },
});

import { resolve } from "path";
import tailwindcss from "tailwindcss";
import autoprefixer from "autoprefixer";
import { defineConfig } from "vite";

// Django serves unicap/static/ at /static/; the build goes to its dist/ folder, which
// DJANGO_VITE["default"] reads ("static_url_prefix": "dist", "manifest_path": .../dist/manifest.json).
// Manifest keys are relative to this root, so templates load `unicap/assets/js/index.js`.
export default defineConfig({
  base: "/static/dist/",
  server: {
    watch: { ignored: ["**/*.py", "**/*.pyc", "**/__pycache__/**", "**/.venv/**"] },
  },
  build: {
    manifest: "manifest.json",
    outDir: resolve("./unicap/static/dist"),
    emptyOutDir: true,
    rollupOptions: {
      input: { index: resolve("./unicap/assets/js/index.js") },
    },
  },
  css: {
    postcss: { plugins: [tailwindcss(), autoprefixer()] },
  },
});

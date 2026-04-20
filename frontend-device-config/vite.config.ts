import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";

export default defineConfig({
  base: "/config/",
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5174,
    strictPort: true,
    hmr: {
      protocol: "wss",
      host: "localhost",
      clientPort: 8443,
      path: "/config/",
    },
  },
});

import { defineConfig, Plugin } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import fs from "fs";
import { componentTagger } from "lovable-tagger";

// 本地 storage 目录的绝对路径（根据你的仓库位置可调整）
const STORAGE_DIR = path.resolve(__dirname, "../storage");

function localStorageStaticPlugin(mode: string): Plugin | null {
  if (mode !== 'development') return null;
  return {
    name: 'local-storage-static',
    configureServer(server) {
      server.middlewares.use("/storage", (req, res) => {
        const reqUrl = req.url || "/";
        const filePath = path.join(STORAGE_DIR, reqUrl.replace(/^\/storage\/?/, ""));
        fs.stat(filePath, (err, stats) => {
          if (err || !stats.isFile()) {
            res.statusCode = 404;
            res.end("Not Found");
            return;
          }
          fs.createReadStream(filePath).pipe(res);
        });
      });
    },
  };
}

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
  server: {
    host: "::",
    port: 8080,
  },
  plugins: [
    react(),
    localStorageStaticPlugin(mode),
    mode === 'development' && componentTagger(),
  ].filter(Boolean) as Plugin[],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
}));

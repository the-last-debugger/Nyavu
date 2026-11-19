/**
 * Serve the exported web build and proxy /api to the local service.
 *
 * The exported app is same-origin, which is right for a real deployment; the preview needs
 * something to forward the API calls, and a 40-line server is less trouble than loosening
 * CORS on the product.
 */
import http from "node:http";
import fs from "node:fs";
import path from "node:path";

const ROOT = path.resolve("dist");
const PORT = Number(process.env.PORT || 8081);
const API = process.env.API || "http://127.0.0.1:8000";

const TYPES = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".css": "text/css",
};

http.createServer((req, res) => {
  if (req.url.startsWith("/api/")) {
    const target = new URL(API + req.url);
    const proxy = http.request(
      { hostname: target.hostname, port: target.port, path: target.pathname + target.search,
        method: req.method, headers: { ...req.headers, host: target.host } },
      (upstream) => {
        res.writeHead(upstream.statusCode || 502, upstream.headers);
        upstream.pipe(res);
      }
    );
    proxy.on("error", () => { res.writeHead(502); res.end("upstream failed"); });
    req.pipe(proxy);
    return;
  }

  // the pathname, not the raw url: a query string like ?url=... is part of the handoff the
  // app reads, and joining it onto the folder returned a directory and a 404
  const pathname = new URL(req.url, "http://127.0.0.1").pathname;
  const file = path.join(ROOT, pathname === "/" ? "index.html" : pathname);
  fs.readFile(file, (error, data) => {
    if (error) {
      res.writeHead(404);
      res.end("not found");
      return;
    }
    res.writeHead(200, { "Content-Type": TYPES[path.extname(file)] || "application/octet-stream" });
    res.end(data);
  });
}).listen(PORT, "127.0.0.1", () => console.log(`preview on http://127.0.0.1:${PORT}`));

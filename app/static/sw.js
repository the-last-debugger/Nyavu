/**
 * Nyavu service worker.
 *
 * Network-first for the shell so a deploy reaches the browser on the next load rather
 * than being pinned by a cache, with the cache as an offline fallback only. API calls
 * are never cached: a stale verdict would be worse than no verdict.
 */
const VERSION = "nyavu-v8";
// guards.css carries the no-spoiler gate; a cached shell without it shows the verdict early, which is
// exactly what a stale service worker would do to a reader who has visited before.
const SHELL = ["/", "/styles.css", "/guards.css", "/app.js", "/autopsy.js", "/institutions.js",
               "/manifest.webmanifest",
               "/icon-192.png", "/icon-512.png", "/logo-mark.svg", "/logo-mark-small.svg", "/favicon-32.png", "/fonts/jetbrains-mono-500.woff2"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(VERSION)
      .then((cache) => cache.addAll(SHELL))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== VERSION).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

/** Give a slow network a bounded chance before serving from cache. */
function withTimeout(request, ms) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), ms);
  return fetch(request, { signal: controller.signal }).finally(() => clearTimeout(timer));
}

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  if (event.request.method !== "GET") return;
  if (url.origin !== self.location.origin) return;
  if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/download/")) return;

  // A versioned shell asset is immutable and its URL changes when its content does, so the
  // worker stays out of the way: a timed-out fetch here would leave the page unstyled.
  if (url.searchParams.has("v")) return;

  const isNavigation = event.request.mode === "navigate";

  event.respondWith(
    withTimeout(event.request, isNavigation ? 12000 : 8000)
      .then((response) => {
        if (response && response.status === 200 && response.type === "basic") {
          const copy = response.clone();
          caches.open(VERSION).then((c) => c.put(event.request, copy)).catch(() => {});
        }
        return response;
      })
      .catch(async () => {
        // Fall back to exactly this resource. Only a navigation may fall back to the
        // shell: returning HTML for a stylesheet or script would break the page's MIME
        // type, which is what a blanket "/" fallback used to do offline.
        const hit = await caches.match(event.request);
        if (hit) return hit;
        if (isNavigation) {
          const shell = await caches.match("/");
          if (shell) return shell;
        }
        return Response.error();
      })
  );
});

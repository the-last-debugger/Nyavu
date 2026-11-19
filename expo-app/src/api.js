/**
 * Every call to the service.
 *
 * On the web, cookies are handled by the browser. On a phone they are not, so the session
 * cookie is read off the response and sent back by hand; that is what keeps history and
 * sign-in state working between screens without a native cookie store.
 */
import { Platform } from "react-native";

// On a phone the API is a different origin, so it is absolute. In a browser build it is
// same-origin, which is what a deployed web build and the local preview proxy both expect.
export const BASE = Platform.OS === "web" ? "" : "https://nyavu.onrender.com";

let session = null;

function rememberCookies(response) {
  if (Platform.OS === "web") return;
  const raw = response.headers?.get?.("set-cookie");
  if (!raw) return;
  const first = raw.split(";")[0];
  if (first && first.includes("=")) session = first;
}

async function call(path, options = {}) {
  const headers = { Accept: "application/json", ...(options.headers || {}) };
  if (session) headers.Cookie = session;
  if (options.body) headers["Content-Type"] = "application/json";

  const response = await fetch(`${BASE}${path}`, { ...options, headers });
  rememberCookies(response);
  const text = await response.text();
  let json = null;
  try {
    json = text ? JSON.parse(text) : null;
  } catch {
    json = null;
  }
  if (!response.ok) {
    throw new Error(json?.detail || `Nyavu could not be reached (${response.status}).`);
  }
  return json;
}

export const predict = (url) =>
  call("/api/predict", { method: "POST", body: JSON.stringify({ url }) });

export const history = () => call("/api/history?limit=25");

export const model = () => call("/api/model");

export const me = () => call("/api/auth/me");

export const logout = async () => {
  const result = await call("/api/auth/logout", { method: "POST", body: "{}" });
  session = null;
  return result;
};

/** Bulk screening takes a CSV upload, which is what the endpoint expects. */
export async function bulk(urls) {
  const boundary = `----nyavu${Date.now()}`;
  const body =
    `--${boundary}\r\n` +
    `Content-Disposition: form-data; name="file"; filename="list.csv"\r\n` +
    `Content-Type: text/csv\r\n\r\n` +
    `${urls.join("\n")}\r\n` +
    `--${boundary}--\r\n`;

  const headers = {
    Accept: "application/json",
    "Content-Type": `multipart/form-data; boundary=${boundary}`,
  };
  if (session) headers.Cookie = session;

  const response = await fetch(`${BASE}/api/scan/bulk`, { method: "POST", headers, body });
  rememberCookies(response);
  const text = await response.text();
  if (!response.ok) throw new Error(text.slice(0, 120) || "Bulk screening failed.");
  return JSON.parse(text);
}

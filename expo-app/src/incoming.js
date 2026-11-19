/**
 * Where a link comes from.
 *
 * A person taps a link in WhatsApp and the system offers to open it with Nyavu. Three routes
 * arrive here and they are not the same thing:
 *
 * 1. **VIEW with http(s)** — Android hands the app the link itself. Configured by the intent
 *    filters in app.json; the URL arrives as the deep link, and this module reads it.
 * 2. **nyavu://check?url=...** — our own scheme, used by the QR code on the site and by
 *    anything that wants to hand Nyavu a specific address.
 * 3. **SEND text/plain** — the share sheet. The system passes the link as an *extra*, not as a
 *    URL, and reading extras needs a native module (`expo-share-intent`). Until the app is
 *    built with it, sharing to Nyavu opens the app without the link. That is stated in
 *    docs/MIGRATION.md rather than hidden.
 */
import { Linking, Platform } from "react-native";

const WEB_OR_NATIVE_LINK = /https?:\/\/[^\s"'<>]+/i;

/** Pull the address out of whatever the system handed us. */
export function addressFromLink(raw) {
  if (!raw) return null;
  const text = String(raw).trim();

  // our own scheme carries the address in a query parameter
  if (text.toLowerCase().startsWith("nyavu://")) {
    const query = text.split("?")[1] || "";
    const params = new URLSearchParams(query);
    const carried = params.get("url") || params.get("u");
    if (carried) return decodeURIComponent(carried);
    return null;
  }

  // the web build reports its own location, so a ?url= there is the same handoff
  if (Platform.OS === "web") {
    const query = text.split("?")[1] || "";
    const params = new URLSearchParams(query);
    const carried = params.get("url") || params.get("u");
    if (carried) return decodeURIComponent(carried);
    return null;
  }

  // an http(s) VIEW intent is the address itself
  const match = text.match(WEB_OR_NATIVE_LINK);
  return match ? match[0] : null;
}

/** The link that launched the app, if any. */
export async function firstLink() {
  try {
    const url = await Linking.getInitialURL();
    return addressFromLink(url);
  } catch {
    return null;
  }
}

/** Links that arrive while the app is already open. */
export function onLink(handler) {
  const subscription = Linking.addEventListener("url", (event) => {
    const address = addressFromLink(event.url);
    if (address) handler(address);
  });
  return () => subscription.remove();
}

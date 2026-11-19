/**
 * The product's tokens, in one place.
 *
 * This is the difference that matters between this app and the Kotlin one: colours, type and
 * spacing are declared data that every screen reads, rather than values copied into each
 * view constructor. The Kotlin screens were rigid because each one assembled itself from
 * literals, so a change meant visiting every file.
 */
import { Platform } from "react-native";

export const colour = {
  bg: "#04060B",
  panel: "#0A0F15",
  raised: "#111823",
  line: "rgba(255,255,255,0.10)",
  ink: "#E9E6DE",
  muted: "#A7ADA1",
  faint: "#6E7468",
  accent: "#8FA98F",
  accentSoft: "#B9CBB9",
  safe: "#7FA98F",
  danger: "#C97B84",
  warn: "#C7A76A",
  bone: "#E9E3D6",
  onBone: "#14170F",
};

export const type = {
  serif: Platform.select({ ios: "Georgia", android: "serif", default: "Georgia, serif" }),
  body: Platform.select({ ios: "System", android: "sans-serif", default: "system-ui" }),
  mono: Platform.select({ ios: "Menlo", android: "monospace", default: "ui-monospace, monospace" }),
};

export const space = (n) => n * 4;

export const band = (risk) =>
  risk === "high" || risk === "phishing" ? colour.danger
  : risk === "medium" || risk === "suspicious" ? colour.warn
  : colour.safe;

export const headline = (risk) =>
  risk === "high" || risk === "phishing" ? "This one is worth avoiding"
  : risk === "medium" || risk === "suspicious" ? "Worth a second look"
  : "This reads as ordinary";

export const reasonTitle = (risk) =>
  risk === "high" || risk === "phishing" ? "What Nyavu noticed"
  : risk === "medium" || risk === "suspicious" ? "What gave Nyavu pause"
  : "What stood out, in a good way";

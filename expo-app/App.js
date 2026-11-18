import { useState } from "react";
import {
  ActivityIndicator, Pressable, SafeAreaView, ScrollView, StyleSheet,
  Text, TextInput, View,
} from "react-native";

const API = "http://100.102.9.78:8000";   // the laptop over Tailscale

const TONE = {
  high: { bg: "#3b0d12", line: "#f2545b", text: "#ffb4b8" },
  medium: { bg: "#2e2408", line: "#fbbf24", text: "#ffd166" },
  low: { bg: "#0e2a1e", line: "#34d399", text: "#6ee7b7" },
};

export default function App() {
  const [url, setUrl] = useState("http://mpesa.co.ke.verify-account.top/");
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function analyse() {
    setBusy(true);
    setError("");
    setResult(null);
    try {
      const res = await fetch(`${API}/api/predict`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      setResult(data);
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setBusy(false);
    }
  }

  const tone = result ? TONE[result.risk] || TONE.low : TONE.low;

  return (
    <SafeAreaView style={s.screen}>
      <ScrollView contentContainerStyle={s.body} keyboardShouldPersistTaps="handled">
        <Text style={s.brand}>Nyavu</Text>
        <Text style={s.tag}>Machine learning · URL text only · no page fetching</Text>
        <Text style={s.h1}>Check a link before you click it.</Text>

        <TextInput
          style={s.input}
          value={url}
          onChangeText={setUrl}
          autoCapitalize="none"
          autoCorrect={false}
          placeholder="https://example.com/login"
          placeholderTextColor="#64789a"
        />

        <Pressable style={s.button} onPress={analyse} disabled={busy}>
          {busy ? <ActivityIndicator color="#04121f" /> : <Text style={s.buttonText}>Shusha Nyavu</Text>}
        </Pressable>

        {error ? <Text style={s.error}>{error}</Text> : null}

        {result ? (
          <View style={[s.card, { backgroundColor: tone.bg, borderColor: tone.line }]}>
            <Text style={[s.band, { color: tone.text }]}>
              {result.band} · {Math.round(result.probability * 100)}%
            </Text>
            <Text style={s.verdict}>
              {result.verdict === "phishing" ? "This link looks like phishing" : "No phishing pattern detected"}
            </Text>
            <Text style={s.host}>{result.host}</Text>

            {result.reputation === "established" ? (
              <Text style={s.rep}>Established domain, name evidence not enough to flag it</Text>
            ) : null}

            {result.suggested ? (
              <Text style={s.suggest}>
                Did you mean {result.suggested.domain}?
              </Text>
            ) : null}

            {(result.reasons || []).map((r, i) => (
              <Text key={i} style={s.reason}>• {r}</Text>
            ))}

            <Text style={s.meta}>Latency {result.inference_ms} ms</Text>
          </View>
        ) : null}

        <Text style={s.foot}>
          A verdict is an assessment, not a guarantee of safety.
        </Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  screen: { flex: 1, backgroundColor: "#0a1020" },
  body: { padding: 22, paddingTop: 48 },
  brand: { color: "#3fb8f5", fontSize: 22, fontWeight: "700", letterSpacing: -0.4 },
  tag: { color: "#64789a", fontSize: 11, letterSpacing: 1, textTransform: "uppercase", marginTop: 6 },
  h1: { color: "#e8eefb", fontSize: 26, fontWeight: "700", marginTop: 14, marginBottom: 18 },
  input: {
    backgroundColor: "#0e1628", borderColor: "#2c3d5e", borderWidth: 1, borderRadius: 12,
    color: "#e8eefb", paddingHorizontal: 14, paddingVertical: 12, fontSize: 14,
  },
  button: {
    backgroundColor: "#3fb8f5", borderRadius: 12, paddingVertical: 14,
    alignItems: "center", marginTop: 12,
  },
  buttonText: { color: "#04121f", fontWeight: "700", fontSize: 15 },
  error: { color: "#f2545b", marginTop: 12 },
  card: { borderWidth: 1, borderRadius: 14, padding: 18, marginTop: 20 },
  band: { fontSize: 12, fontWeight: "700", letterSpacing: 1, textTransform: "uppercase" },
  verdict: { color: "#e8eefb", fontSize: 19, fontWeight: "700", marginTop: 8 },
  host: { color: "#93a6c4", fontSize: 13, marginTop: 6, marginBottom: 10 },
  rep: { color: "#8fd4f8", fontSize: 13, marginBottom: 8 },
  suggest: { color: "#7dd3fc", fontSize: 14, marginBottom: 8 },
  reason: { color: "#c4d2e6", fontSize: 13, lineHeight: 19, marginBottom: 6 },
  meta: { color: "#64789a", fontSize: 11, marginTop: 10 },
  foot: { color: "#64789a", fontSize: 11, marginTop: 26, textAlign: "center" },
});

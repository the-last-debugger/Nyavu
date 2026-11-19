/**
 * Nyavu, in React Native: one screen, and the examination is the point.
 *
 * The Kotlin app could show a dissection, but making it feel like writing took a chain of
 * handlers, one per character, because the View system has no notion of a value that
 * animates. Here the same idea is a single interval and one piece of state, which is why
 * this port exists at all.
 *
 * What it does: you paste an address, the caret types it out left to right, then the notes
 * arrive from the ending backwards, and the verdict lands. Nothing else: no tabs, no bulk
 * list, no model page.
 */
import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  Animated, Easing, Image, Linking, Platform, Pressable, SafeAreaView, ScrollView,
  StyleSheet, Text, TextInput, View,
} from "react-native";
import * as api from "./src/api";
import { dissect, readingNote } from "./src/dissection";
import { band, colour, headline, reasonTitle, space, type } from "./src/theme";

// the site's rhythm: one character every 52ms, a note 320ms after the caret reaches it
const PER_CHARACTER = 52;
const NOTE_GAP = 320;

export default function App() {
  const [url, setUrl] = useState("");
  const [phase, setPhase] = useState("idle");   // idle | reading | writing | explaining | verdict
  const [payload, setPayload] = useState(null);
  const [error, setError] = useState("");
  const [typed, setTyped] = useState(0);
  const [notesShown, setNotesShown] = useState(0);

  const parts = payload ? dissect(payload.url) : [];
  const totalChars = parts.reduce((sum, part) => sum + part.text.length, 0);

  const caret = useRef(new Animated.Value(1)).current;
  const sheet = useRef(new Animated.Value(0)).current;

  // the caret blinks while it is idle or thinking, and stops while it is writing
  useEffect(() => {
    if (phase === "writing") {
      caret.setValue(1);
      return undefined;
    }
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(caret, { toValue: 0.15, duration: 420, useNativeDriver: true }),
        Animated.timing(caret, { toValue: 1, duration: 420, useNativeDriver: true }),
      ])
    );
    loop.start();
    return () => loop.stop();
  }, [phase, caret]);

  // the examination: type every character, then read the notes backwards
  useEffect(() => {
    if (phase !== "writing" || !totalChars) return undefined;
    let index = 0;
    let noteTimer = null;
    const typing = setInterval(() => {
      index += 1;
      setTyped(index);
      if (index >= totalChars) {
        clearInterval(typing);
        setPhase("explaining");
        let shown = 0;
        noteTimer = setInterval(() => {
          shown += 1;
          setNotesShown(shown);
          if (shown >= parts.length) {
            clearInterval(noteTimer);
            setPhase("verdict");
            Animated.timing(sheet, {
              toValue: 1, duration: 240, easing: Easing.out(Easing.cubic), useNativeDriver: true,
            }).start();
          }
        }, NOTE_GAP);
      }
    }, PER_CHARACTER);
    return () => {
      clearInterval(typing);
      if (noteTimer) clearInterval(noteTimer);
    };
  }, [phase, totalChars, parts.length, sheet]);

  const scan = useCallback(async (value) => {
    const target = (value ?? url).trim();
    if (!target) {
      setError("Paste a link first.");
      return;
    }
    setError("");
    setPayload(null);
    setTyped(0);
    setNotesShown(0);
    setPhase("reading");
    try {
      const result = await api.predict(target);
      setPayload(result);
      setPhase("writing");
    } catch (issue) {
      setPhase("idle");
      setError(issue.message || "That did not work.");
    }
  }, [url]);

  const reset = () => {
    setPhase("idle");
    setPayload(null);
    setTyped(0);
    setNotesShown(0);
  };

  const typedFor = (index) => {
    let before = 0;
    for (let i = 0; i < index; i += 1) before += parts[i].text.length;
    return Math.max(0, Math.min(parts[index].text.length, typed - before));
  };

  const risk = payload?.risk || "low";
  const pct = Math.round((payload?.probability ?? 0) * 100);
  const established = payload?.reputation === "established";
  const tone = established ? colour.safe : band(risk);
  const examining = phase === "writing" || phase === "explaining" || phase === "verdict";

  return (
    <SafeAreaView style={styles.app}>
      <ScrollView contentContainerStyle={styles.page} keyboardShouldPersistTaps="handled">
        <View style={styles.header}>
          <Image source={require("./assets/logo-mark.png")} style={styles.mark} resizeMode="contain" />
          <View>
            <Text style={styles.brand}>Nyavu</Text>
            <Text style={styles.tagline}>Your personal link inspector</Text>
          </View>
        </View>

        {phase === "idle" ? (
          <>
            <Text style={styles.headline}>Read the address before you trust it.</Text>
            <View style={styles.field}>
              <TextInput
                value={url}
                onChangeText={setUrl}
                placeholder="Paste a link"
                placeholderTextColor={colour.faint}
                autoCapitalize="none"
                autoCorrect={false}
                keyboardType="url"
                style={styles.input}
                onSubmitEditing={() => scan()}
                returnKeyType="go"
              />
            </View>
            <Pressable style={styles.primary} onPress={() => scan()}>
              <Text style={styles.primaryText}>Examine it</Text>
            </Pressable>
            {error ? <Text style={styles.warning}>{error}</Text> : null}
            <Text style={styles.label}>OR TRY ONE</Text>
            {["safaricom.co.ke", "safaricom-secure-login.tk", "mpesa.co.ke.verify-account.top"].map((sample) => (
              <Pressable key={sample} onPress={() => { setUrl(sample); scan(sample); }}>
                <Text style={styles.sample}>{sample}</Text>
              </Pressable>
            ))}
          </>
        ) : null}

        {phase === "reading" ? (
          <View style={styles.readingRow}>
            <Text style={styles.reading}>Reading the address</Text>
            <Animated.Text style={[styles.caretGlyph, { opacity: caret }]}>|</Animated.Text>
          </View>
        ) : null}

        {examining ? (
          <View style={styles.plate}>
            <Text style={styles.plateLabel}>
              {phase === "writing" ? "REVIEWING THE ADDRESS" : "READING FROM THE RIGHT"}
            </Text>
            {parts.map((part, index) => {
              const shown = part.text.slice(0, typedFor(index));
              const typing = shown.length < part.text.length;
              const noteVisible = parts.length - index <= notesShown;
              return (
                <View key={`${part.role}-${index}`} style={styles.part}>
                  <Text style={[styles.partText, { color: part.wrong && !established ? tone : colour.ink }]}>
                    {shown}
                    {typing ? <Animated.Text style={{ opacity: caret }}>|</Animated.Text> : null}
                  </Text>
                  {noteVisible ? <Text style={styles.partNote}>{part.note}</Text> : null}
                </View>
              );
            })}
            {notesShown > 0 ? <Text style={styles.readingNote}>{readingNote(parts)}</Text> : null}
          </View>
        ) : null}

        {phase === "verdict" ? (
          <Animated.View
            style={[
              styles.verdict,
              {
                opacity: sheet,
                transform: [{ translateY: sheet.interpolate({ inputRange: [0, 1], outputRange: [18, 0] }) }],
              },
            ]}
          >
            <Text style={styles.headline}>{established ? "An established domain" : headline(risk)}</Text>
            <View style={styles.figureRow}>
              <Text style={[styles.figure, { color: tone }]}>{pct}</Text>
              <Text style={styles.figureLabel}>risk out of 100</Text>
            </View>
            <Text style={styles.note}>
              {established
                ? `Held at ${pct} so a known site is never flagged on the shape of its name.`
                : `Scored ${pct} out of 100. That is the estimated chance this address is a phish, read from its name alone.`}
            </Text>

            <Text style={styles.label}>{reasonTitle(risk).toUpperCase()}</Text>
            {(payload?.reasons || []).slice(0, 4).map((reason, index) => (
              <View key={index} style={styles.reason}>
                <Text style={styles.reasonNumber}>{index + 1}</Text>
                <Text style={styles.reasonText}>{reason}</Text>
              </View>
            ))}

            <View style={styles.actions}>
              {risk === "low" || established ? (
                <Pressable
                  style={styles.primary}
                  onPress={() => { reset(); Linking.openURL(payload.url).catch(() => {}); }}
                >
                  <Text style={styles.primaryText}>Open link</Text>
                </Pressable>
              ) : null}
              <Pressable style={styles.ghost} onPress={reset}>
                <Text style={styles.ghostText}>Examine another</Text>
              </Pressable>
            </View>
          </Animated.View>
        ) : null}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  app: { flex: 1, backgroundColor: colour.bg },
  page: { paddingHorizontal: space(5), paddingTop: space(4), paddingBottom: space(10) },
  header: { flexDirection: "row", alignItems: "center", gap: space(3), marginBottom: space(6) },
  mark: { width: 34, height: 34, tintColor: colour.accentSoft },
  brand: { fontFamily: type.serif, fontWeight: "700", fontSize: 24, color: colour.ink },
  tagline: { fontFamily: type.body, fontSize: 11.5, color: colour.faint },
  headline: { fontFamily: type.serif, fontSize: 26, lineHeight: 33, color: colour.ink, marginBottom: space(4) },
  field: { borderWidth: 1, borderColor: colour.line, backgroundColor: colour.raised, borderRadius: 14 },
  input: {
    fontFamily: type.body, fontSize: 15, color: colour.ink,
    paddingHorizontal: space(4), paddingVertical: Platform.OS === "web" ? space(3) : space(2),
    outlineStyle: "none",
  },
  primary: { height: 50, borderRadius: 26, backgroundColor: colour.bone, alignItems: "center", justifyContent: "center", marginTop: space(3) },
  primaryText: { fontFamily: type.body, fontWeight: "700", fontSize: 15, color: colour.onBone },
  warning: { fontFamily: type.body, fontSize: 12, color: colour.warn, marginTop: space(3) },
  label: { fontFamily: type.body, fontSize: 9.5, letterSpacing: 1.6, color: colour.faint, marginTop: space(6), marginBottom: space(1) },
  sample: { fontFamily: type.mono, fontSize: 13, color: colour.muted, paddingVertical: space(2) },
  readingRow: { flexDirection: "row", alignItems: "center", gap: space(1), marginTop: space(4) },
  reading: { fontFamily: type.body, fontSize: 12.5, color: colour.faint },
  caretGlyph: { fontFamily: type.mono, fontSize: 14, color: colour.accentSoft },
  plate: { borderWidth: 1, borderColor: colour.line, backgroundColor: colour.panel, borderRadius: 16, padding: space(4), marginTop: space(4) },
  plateLabel: { fontFamily: type.body, fontSize: 9.5, letterSpacing: 1.6, color: colour.faint, marginBottom: space(3) },
  part: { marginBottom: space(3) },
  partText: { fontFamily: type.mono, fontSize: 16 },
  partNote: { fontFamily: type.body, fontSize: 11, color: colour.faint, marginTop: space(1) },
  readingNote: { fontFamily: type.serif, fontSize: 12, color: colour.muted, marginTop: space(1) },
  verdict: { marginTop: space(4) },
  figureRow: { flexDirection: "row", alignItems: "flex-end" },
  figure: { fontFamily: type.mono, fontSize: 34 },
  figureLabel: { fontFamily: type.body, fontSize: 11.5, color: colour.faint, marginLeft: space(2), paddingBottom: space(2) },
  note: { fontFamily: type.body, fontSize: 12.5, color: colour.muted, marginTop: space(3), lineHeight: 19 },
  reason: { flexDirection: "row", backgroundColor: colour.panel, borderRadius: 14, borderWidth: 1, borderColor: colour.line, padding: space(3), marginTop: space(2) },
  reasonNumber: { fontFamily: type.mono, fontSize: 10, color: colour.faint, width: 18 },
  reasonText: { flex: 1, fontFamily: type.body, fontSize: 12.5, color: colour.muted, lineHeight: 19 },
  actions: { marginTop: space(4), gap: space(2) },
  ghost: { height: 46, borderRadius: 26, borderWidth: 1, borderColor: colour.line, alignItems: "center", justifyContent: "center" },
  ghostText: { fontFamily: type.body, fontWeight: "700", fontSize: 14, color: colour.ink },
});

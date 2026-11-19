/**
 * Nyavu, native.
 *
 * One screen and one sheet. The shell does the things a phone expects: safe areas, the
 * Android back button closing the sheet before leaving the screen, ripple on Android and an
 * opacity dip elsewhere, haptics on the actions that matter, and a sheet that can be dragged
 * down. The examination is the product and lives in ExamSurface.
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Animated, BackHandler, Easing, Image, Linking, PanResponder, Platform, Pressable,
  SafeAreaView, ScrollView, StyleSheet, Text, TextInput, View,
} from "react-native";
import { SafeAreaProvider, useSafeAreaInsets } from "react-native-safe-area-context";
import * as Haptics from "expo-haptics";
import * as SplashScreen from "expo-splash-screen";
import * as api from "./src/api";
import { firstLink, onLink } from "./src/incoming";
import { dissect } from "./src/dissection";
import ExamSurface from "./src/ExamSurface";
import { band, colour, headline, reasonTitle, space, type } from "./src/theme";

SplashScreen.preventAutoHideAsync().catch(() => {});

const SAMPLES = [
  "safaricom.co.ke",
  "safaricom-secure-login.tk",
  "mpesa.co.ke.verify-account.top",
];

const buzz = (style) => {
  try {
    Haptics.impactAsync(style);
  } catch {
    // a device without haptics is still a device
  }
};

function App() {
  const insets = useSafeAreaInsets();
  const [phase, setPhase] = useState("idle");   // idle | reading | exam | verdict
  const [url, setUrl] = useState("");
  const [payload, setPayload] = useState(null);
  const [error, setError] = useState("");
  const [examKey, setExamKey] = useState(0);

  const sheet = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    SplashScreen.hideAsync().catch(() => {});
  }, []);

  // arriving from another app: the link that opened us, and links that arrive later
  useEffect(() => {
    firstLink().then((address) => {
      if (address) {
        setUrl(address);
        scan(address);
      }
    });
    return onLink((address) => {
      setUrl(address);
      scan(address);
    });
  }, []);

  // the back button closes the sheet first, and only then leaves the screen
  useEffect(() => {
    const onBack = () => {
      if (phase === "verdict" || phase === "exam") {
        reset();
        return true;
      }
      return false;
    };
    const subscription = BackHandler.addEventListener("hardwareBackPress", onBack);
    return () => subscription.remove();
  }, [phase]);

  const scan = useCallback(async (value) => {
    const target = (value ?? url).trim();
    if (!target) {
      setError("Paste a link first.");
      buzz(Haptics.ImpactFeedbackStyle.Rigid);
      return;
    }
    if (phase !== "idle") return;          // one examination at a time
    setError("");
    setPayload(null);
    setPhase("reading");
    buzz(Haptics.ImpactFeedbackStyle.Medium);
    try {
      const result = await api.predict(target);
      setPayload(result);
      setExamKey((key) => key + 1);
      setPhase("exam");
    } catch (issue) {
      setPhase("idle");
      setError(issue.message || "That did not work.");
      buzz(Haptics.ImpactFeedbackStyle.Rigid);
    }
  }, [url, phase]);

  const reset = () => {
    setPhase("idle");
    setPayload(null);
    sheet.setValue(0);
  };

  const showVerdict = useCallback(() => {
    setPhase("verdict");
    buzz(Haptics.ImpactFeedbackStyle.Heavy);
    Animated.timing(sheet, {
      toValue: 1, duration: 280, easing: Easing.out(Easing.cubic), useNativeDriver: true,
    }).start();
  }, [sheet]);

  const parts = payload ? dissect(payload.url) : [];
  const risk = payload?.risk || "low";
  const pct = Math.round((payload?.probability ?? 0) * 100);
  const established = payload?.reputation === "established";
  const tone = established ? colour.safe : band(risk);

  return (
    <View style={[styles.app, { paddingTop: insets.top }]}>
      <ScrollView
        contentContainerStyle={[styles.page, { paddingBottom: space(8) + insets.bottom }]}
        keyboardShouldPersistTaps="handled"
      >
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
                accessibilityLabel="Link to examine"
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

            <Action label="Examine it" onPress={() => scan()} primary />
            {error ? <Text style={styles.warning}>{error}</Text> : null}

            <Text style={styles.label}>OR TRY ONE</Text>
            {SAMPLES.map((sample) => (
              <Action
                key={sample}
                label={sample}
                onPress={() => { setUrl(sample); scan(sample); }}
                mono
              />
            ))}
          </>
        ) : null}

        {phase === "reading" ? (
          <View style={styles.readingRow}>
            <Text style={styles.reading}>Reading the address</Text>
          </View>
        ) : null}

        {phase === "exam" || phase === "verdict" ? (
          <ExamSurface
            key={examKey}
            parts={parts}
            onFinished={showVerdict}
          />
        ) : null}
      </ScrollView>

      {phase === "verdict" ? (
        <VerdictSheet
          payload={payload}
          sheet={sheet}
          tone={tone}
          pct={pct}
          risk={risk}
          established={established}
          onClose={reset}
        />
      ) : null}
    </View>
  );
}

function Action({ label, onPress, primary, mono }) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      onPress={() => { buzz(Haptics.ImpactFeedbackStyle.Light); onPress(); }}
      android_ripple={{ color: "rgba(255,255,255,0.08)" }}
      style={({ pressed }) => [
        primary ? styles.primary : styles.sampleRow,
        pressed && Platform.OS !== "android" && { opacity: 0.7 },
      ]}
    >
      <Text style={[
        primary ? styles.primaryText : styles.sample,
        mono && { fontFamily: type.mono },
      ]}>
        {label}
      </Text>
    </Pressable>
  );
}

function VerdictSheet({ payload, sheet, tone, pct, risk, established, onClose }) {
  const insets = useSafeAreaInsets();
  const drag = useRef(new Animated.Value(0)).current;

  const pan = useMemo(
    () => PanResponder.create({
      onMoveShouldSetPanResponder: (_, gesture) => gesture.dy > 6,
      onPanResponderMove: (_, gesture) => {
        if (gesture.dy > 0) drag.setValue(gesture.dy);
      },
      onPanResponderRelease: (_, gesture) => {
        if (gesture.dy > 110) {
          buzz(Haptics.ImpactFeedbackStyle.Light);
          onClose();
        } else {
          Animated.spring(drag, { toValue: 0, useNativeDriver: true, stiffness: 320, damping: 30 }).start();
        }
      },
    }),
    [drag, onClose]
  );

  const reasons = (payload?.reasons || []).slice(0, 4);

  return (
    <View style={StyleSheet.absoluteFill} pointerEvents="box-none">
      <Pressable style={styles.scrim} onPress={onClose} />
      <Animated.View
        {...pan.panHandlers}
        style={[
          styles.sheet,
          { paddingBottom: insets.bottom + space(5) },
          {
            transform: [
              { translateY: Animated.add(sheet.interpolate({ inputRange: [0, 1], outputRange: [420, 0] }), drag) },
            ],
          },
        ]}
      >
        <View style={styles.grabber} />

        <ScrollView
          style={styles.sheetScroll}
          contentContainerStyle={{ paddingBottom: space(2) }}
          showsVerticalScrollIndicator={false}
          bounces
        >
        <Text style={styles.sheetHeadline}>
          {established ? "An established domain" : headline(risk)}
        </Text>

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
        {reasons.map((reason, index) => (
          <View key={index} style={styles.reason}>
            <Text style={styles.reasonNumber}>{index + 1}</Text>
            <Text style={styles.reasonText}>{reason}</Text>
          </View>
        ))}

        <View style={{ marginTop: space(4), gap: space(2) }}>
          {risk === "low" || established ? (
            <Action
              label="Open link"
              primary
              onPress={() => {
                const target = String(payload?.url || "");
                if (!/^https?:\/\//i.test(target)) {
                  buzz(Haptics.ImpactFeedbackStyle.Rigid);
                  return;
                }
                onClose();
                Linking.openURL(target).catch(() => {});
              }}
            />
          ) : null}
          <Action label="Examine another" onPress={onClose} />
        </View>
        </ScrollView>
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  app: { flex: 1, backgroundColor: colour.bg },
  page: { paddingHorizontal: space(5), paddingTop: space(3) },
  header: { flexDirection: "row", alignItems: "center", gap: space(3), marginBottom: space(6) },
  mark: { width: 34, height: 34, tintColor: colour.accentSoft },
  brand: { fontFamily: type.serif, fontWeight: "700", fontSize: 24, color: colour.ink },
  tagline: { fontFamily: type.body, fontSize: 11.5, color: colour.faint },
  headline: { fontFamily: type.serif, fontSize: 26, lineHeight: 33, color: colour.ink, marginBottom: space(4) },
  field: { borderWidth: 1, borderColor: colour.line, backgroundColor: colour.raised, borderRadius: 14 },
  input: {
    fontFamily: type.body, fontSize: 16, color: colour.ink,
    paddingHorizontal: space(4), paddingVertical: Platform.OS === "web" ? space(3) : space(2),
    outlineStyle: "none",
  },
  primary: { minHeight: 52, borderRadius: 26, backgroundColor: colour.bone, alignItems: "center", justifyContent: "center", marginTop: space(3) },
  primaryText: { fontFamily: type.body, fontWeight: "700", fontSize: 16, color: colour.onBone },
  sampleRow: { minHeight: 48, justifyContent: "center", borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colour.line },
  sample: { fontFamily: type.body, fontSize: 14, color: colour.muted },
  warning: { fontFamily: type.body, fontSize: 12, color: colour.warn, marginTop: space(3) },
  label: { fontFamily: type.body, fontSize: 9.5, letterSpacing: 1.6, color: colour.faint, marginTop: space(6), marginBottom: space(1) },
  readingRow: { marginTop: space(6) },
  reading: { fontFamily: type.body, fontSize: 13, color: colour.faint },
  scrim: { ...StyleSheet.absoluteFillObject, backgroundColor: "rgba(3,7,11,0.72)" },
  sheetScroll: { maxHeight: "66%" },
  sheet: {
    position: "absolute", left: 0, right: 0, bottom: 0,
    maxHeight: "86%",
    backgroundColor: colour.panel,
    borderTopLeftRadius: 24, borderTopRightRadius: 24,
    borderTopWidth: 1, borderColor: colour.line,
    paddingHorizontal: space(5), paddingTop: space(2),
  },
  grabber: { alignSelf: "center", width: 44, height: 4, borderRadius: 2, backgroundColor: "rgba(255,255,255,0.18)", marginBottom: space(4) },
  sheetHeadline: { fontFamily: type.serif, fontSize: 24, lineHeight: 30, color: colour.ink },
  figureRow: { flexDirection: "row", alignItems: "flex-end", marginTop: space(2) },
  figure: { fontFamily: type.mono, fontSize: 34 },
  figureLabel: { fontFamily: type.body, fontSize: 11.5, color: colour.faint, marginLeft: space(2), paddingBottom: space(2) },
  note: { fontFamily: type.body, fontSize: 12.5, color: colour.muted, marginTop: space(2), lineHeight: 19 },
  reason: { flexDirection: "row", backgroundColor: colour.bg, borderRadius: 14, borderWidth: 1, borderColor: colour.line, padding: space(3), marginTop: space(2) },
  reasonNumber: { fontFamily: type.mono, fontSize: 10, color: colour.faint, width: 18 },
  reasonText: { flex: 1, fontFamily: type.body, fontSize: 12.5, color: colour.muted, lineHeight: 19 },
});

export default function Root() {
  return (
    <SafeAreaProvider>
      <App />
    </SafeAreaProvider>
  );
}

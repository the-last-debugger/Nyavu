/**
 * The verdict, as a sheet that rises over the screen.
 *
 * This is the piece the Kotlin app could not make feel alive without a hundred lines of
 * handler plumbing. Here the examination is a single effect with a clock: the pieces are
 * typed at a fixed interval, then the notes arrive from the ending backwards, and the sheet
 * itself animates in. The rhythm is the site's, because the constants are the site's.
 */
import React, { useEffect, useRef, useState } from "react";
import {
  Animated, Easing, Modal, Pressable, ScrollView, StyleSheet, Text, View,
} from "react-native";
import { dissect, readingNote } from "./dissection";
import { band, colour, headline, reasonTitle, space, type } from "./theme";

const PER_CHARACTER = 52;
const NOTE_GAP = 320;

export default function Verdict({ payload, onClose, onOpen }) {
  const [revealed, setRevealed] = useState(0);   // characters typed so far, whole address
  const [notes, setNotes] = useState(0);         // notes shown, counted from the end
  const [worked, setWorked] = useState(false);
  const [barWidth, setBarWidth] = useState(new Animated.Value(0));
  const rise = useRef(new Animated.Value(0)).current;

  const parts = dissect(payload?.url || "");
  const risk = payload?.risk || "low";
  const pct = Math.round((payload?.probability ?? 0) * 100);
  const established = payload?.reputation === "established";
  const tone = established ? colour.safe : band(risk);
  const totalChars = parts.reduce((sum, part) => sum + part.text.length, 0);

  useEffect(() => {
    Animated.timing(rise, {
      toValue: 1, duration: 260, easing: Easing.out(Easing.cubic), useNativeDriver: true,
    }).start();
    Animated.timing(barWidth, {
      toValue: pct, duration: 720, easing: Easing.out(Easing.cubic), useNativeDriver: false,
    }).start();
  }, [rise, barWidth, pct]);

  useEffect(() => {
    if (!totalChars) return undefined;
    let typed = 0;
    const typing = setInterval(() => {
      typed += 1;
      setRevealed(typed);
      if (typed >= totalChars) {
        clearInterval(typing);
        // reading the notes from the ending backwards is the lesson
        let shown = 0;
        const reading = setInterval(() => {
          shown += 1;
          setNotes(shown);
          if (shown >= parts.length) clearInterval(reading);
        }, NOTE_GAP);
      }
    }, PER_CHARACTER);
    return () => clearInterval(typing);
  }, [totalChars, parts.length]);

  // one running counter maps onto the pieces so each is typed in turn
  const typedFor = (index) => {
    let before = 0;
    for (let i = 0; i < index; i += 1) before += parts[i].text.length;
    return Math.max(0, Math.min(parts[index].text.length, revealed - before));
  };

  const reasons = Array.isArray(payload?.reasons) ? payload.reasons.slice(0, 4) : [];
  const noteVisible = (index) => parts.length - index <= notes;

  return (
    <Modal transparent animationType="none" visible onRequestClose={onClose}>
      <View style={styles.scrim}>
        <Animated.View
          style={[
            styles.sheet,
            {
              opacity: rise,
              transform: [{ translateY: rise.interpolate({ inputRange: [0, 1], outputRange: [26, 0] }) }],
            },
          ]}
        >
          <ScrollView contentContainerStyle={styles.body}>
            <View style={styles.headRow}>
              <Text style={[styles.headline, { flex: 1 }]}>
                {established ? "An established domain" : headline(risk)}
              </Text>
              <Pressable onPress={onClose} hitSlop={12}>
                <Text style={styles.close}>Close</Text>
              </Pressable>
            </View>

            <Text style={styles.host}>{payload?.host || payload?.url}</Text>

            <View style={styles.parts}>
              {parts.map((part, index) => {
                const shown = part.text.slice(0, typedFor(index));
                const typing = shown.length < part.text.length;
                return (
                  <View key={`${part.role}-${index}`} style={styles.part}>
                    <Text style={[styles.partText, { color: part.wrong && !established ? tone : colour.ink }]}>
                      {shown}
                      {typing ? <Text style={styles.caret}>|</Text> : null}
                    </Text>
                    {noteVisible(index) ? (
                      <Text style={styles.partNote}>{part.note}</Text>
                    ) : null}
                  </View>
                );
              })}
              <Text style={styles.reading}>{readingNote(parts)}</Text>
            </View>

            <View style={styles.figureRow}>
              <Text style={[styles.figure, { color: tone }]}>{pct}</Text>
              <Text style={styles.figureLabel}>risk out of 100</Text>
            </View>
            <View style={styles.track}>
              <Animated.View style={[styles.fill, { backgroundColor: tone, width: barWidth.interpolate({ inputRange: [0, 100], outputRange: ["0%", "100%"] }) }]} />
            </View>

            <Text style={styles.note}>
              {established
                ? `Held at ${pct} so a known site is never flagged on the shape of its name.`
                : `Scored ${pct} out of 100. That is the estimated chance this address is a phish, read from its name alone.`}
            </Text>

            <Pressable onPress={() => setWorked((value) => !value)}>
              <Text style={styles.fold}>{worked ? "−" : "+"}  How that was worked out</Text>
            </Pressable>
            {worked ? (
              <Text style={styles.worked}>
                Anything above 65 is treated as a concern, and below 35 as clear. The number comes
                from a logistic-regression model trained on 17,730 addresses, whose hold-out
                accuracy is 75.4 per cent.
              </Text>
            ) : null}

            <Text style={styles.label}>{reasonTitle(risk).toUpperCase()}</Text>
            {reasons.length ? reasons.map((reason, index) => (
              <View key={index} style={styles.reason}>
                <Text style={styles.reasonNumber}>{index + 1}</Text>
                <Text style={styles.reasonText}>{reason}</Text>
              </View>
            )) : (
              <View style={styles.reason}>
                <Text style={styles.reasonNumber}>1</Text>
                <Text style={styles.reasonText}>Nothing in the name raised a pattern Nyavu knows.</Text>
              </View>
            )}

            <View style={styles.actions}>
              {established || risk === "low" ? (
                <Pressable style={styles.primary} onPress={() => onOpen(payload?.url)}>
                  <Text style={styles.primaryText}>Open link</Text>
                </Pressable>
              ) : null}
              <Pressable style={styles.ghost} onPress={onClose}>
                <Text style={styles.ghostText}>Close</Text>
              </Pressable>
            </View>
          </ScrollView>
        </Animated.View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  scrim: { flex: 1, backgroundColor: "rgba(3,7,11,0.94)", justifyContent: "center" },
  sheet: { maxHeight: "92%", marginHorizontal: space(3) },
  body: { backgroundColor: colour.panel, borderRadius: 20, borderWidth: 1, borderColor: colour.line, padding: space(5) },
  headRow: { flexDirection: "row", alignItems: "flex-start", gap: space(3) },
  headline: { fontFamily: type.serif, fontSize: 25, color: colour.ink, lineHeight: 31 },
  close: { fontFamily: type.body, fontSize: 12, color: colour.faint, paddingTop: space(2) },
  host: { fontFamily: type.mono, fontSize: 12.5, color: colour.muted, marginTop: space(2) },
  parts: { backgroundColor: colour.bg, borderRadius: 16, borderWidth: 1, borderColor: colour.line, padding: space(4), marginTop: space(4) },
  part: { marginBottom: space(3) },
  partText: { fontFamily: type.mono, fontSize: 15 },
  caret: { color: colour.accentSoft },
  partNote: { fontFamily: type.body, fontSize: 11, color: colour.faint, marginTop: space(1) },
  reading: { fontFamily: type.serif, fontSize: 11.5, color: colour.muted, marginTop: space(1) },
  figureRow: { flexDirection: "row", alignItems: "flex-end", marginTop: space(4) },
  figure: { fontFamily: type.mono, fontSize: 34 },
  figureLabel: { fontFamily: type.body, fontSize: 11.5, color: colour.faint, marginLeft: space(2), paddingBottom: space(2) },
  track: { height: 3, backgroundColor: "rgba(255,255,255,0.08)", marginTop: space(2), borderRadius: 2, overflow: "hidden" },
  fill: { height: 3, borderRadius: 2 },
  note: { fontFamily: type.body, fontSize: 12.5, color: colour.muted, marginTop: space(3), lineHeight: 19 },
  fold: { fontFamily: type.body, fontSize: 12, color: colour.faint, marginTop: space(4) },
  worked: { fontFamily: type.body, fontSize: 12, color: colour.faint, marginTop: space(2), lineHeight: 18 },
  label: { fontFamily: type.body, fontSize: 9.5, letterSpacing: 1.4, color: colour.faint, marginTop: space(5) },
  reason: { flexDirection: "row", backgroundColor: colour.bg, borderRadius: 14, borderWidth: 1, borderColor: colour.line, padding: space(3), marginTop: space(2) },
  reasonNumber: { fontFamily: type.mono, fontSize: 10, color: colour.faint, width: 18 },
  reasonText: { flex: 1, fontFamily: type.body, fontSize: 12.5, color: colour.muted, lineHeight: 19 },
  actions: { marginTop: space(4), gap: space(2) },
  primary: { height: 46, borderRadius: 26, backgroundColor: colour.bone, alignItems: "center", justifyContent: "center" },
  primaryText: { fontFamily: type.body, fontWeight: "700", fontSize: 14, color: colour.onBone },
  ghost: { height: 46, borderRadius: 26, borderWidth: 1, borderColor: colour.line, alignItems: "center", justifyContent: "center" },
  ghostText: { fontFamily: type.body, fontWeight: "700", fontSize: 14, color: colour.ink },
});

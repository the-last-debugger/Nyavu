/**
 * The examination.
 *
 * One continuous address, drawn character by character, with the caret in the flow rather
 * than absolutely positioned. That is the correction the first pass needed: an absolutely
 * positioned caret drifted to the edge of the container while the text wrapped, so there were
 * two cursors and neither was where the writing was. A caret that occupies its own two pixels
 * in the text can only ever be at the writing edge, on whatever line the layout put it.
 *
 * Notes arrive from the ending backwards, one per piece, which is the lesson.
 */
import React, { useEffect, useMemo, useRef, useState } from "react";
import { Animated, StyleSheet, Text, View } from "react-native";
import * as Haptics from "expo-haptics";
import { colour, space, type } from "./theme";

const PER_CHARACTER = 52;
const NOTE_GAP = 320;

const tick = (style) => {
  try {
    Haptics.impactAsync(style);
  } catch {
    // no taptic engine, no problem
  }
};

export default function ExamSurface({ parts, onFinished }) {
  // the address as one run of characters, each remembering which piece it belongs to
  const chars = useMemo(() => {
    const run = [];
    parts.forEach((part, pieceIndex) => {
      Array.from(part.text).forEach((char) => run.push({ char, pieceIndex }));
    });
    return run;
  }, [parts]);

  const [typed, setTyped] = useState(0);
  const [notesShown, setNotesShown] = useState(0);
  const caret = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    const blink = Animated.loop(
      Animated.sequence([
        Animated.timing(caret, { toValue: 0.2, duration: 380, useNativeDriver: true }),
        Animated.timing(caret, { toValue: 1, duration: 380, useNativeDriver: true }),
      ])
    );
    blink.start();
    return () => blink.stop();
  }, [caret]);

  useEffect(() => {
    if (!chars.length) return undefined;
    let index = 0;
    let reading = null;

    const typing = setInterval(() => {
      index += 1;
      setTyped(index);

      // a tick as each piece completes, not per glyph
      const landed = chars[index - 1];
      const next = chars[index];
      if (!next || next.pieceIndex !== landed.pieceIndex) {
        tick(Haptics.ImpactFeedbackStyle.Light);
      }

      if (index >= chars.length) {
        clearInterval(typing);
        let shown = 0;
        reading = setInterval(() => {
          shown += 1;
          setNotesShown(shown);
          tick(Haptics.ImpactFeedbackStyle.Soft);
          if (shown >= parts.length) {
            clearInterval(reading);
            if (onFinished) onFinished();
          }
        }, NOTE_GAP);
      }
    }, PER_CHARACTER);

    return () => {
      clearInterval(typing);
      if (reading) clearInterval(reading);
    };
  }, [chars, parts.length, onFinished]);

  const doneTyping = typed >= chars.length;

  return (
    <View style={styles.surface}>
      <Text style={styles.mode}>{doneTyping ? "READING FROM THE RIGHT" : "REVIEWING THE ADDRESS"}</Text>

      <View style={styles.address}>
        {chars.slice(0, typed).map((item, index) => {
          const part = parts[item.pieceIndex];
          const flagged = part.wrong;
          return (
            <Text
              key={index}
              style={[styles.char, { color: flagged ? colour.danger : colour.ink }]}
            >
              {item.char === " " ? "\u00a0" : item.char}
            </Text>
          );
        })}
        {!doneTyping ? (
          <Animated.View style={[styles.caret, { opacity: caret }]} />
        ) : null}
      </View>

      {notesShown > 0 ? (
        <View style={styles.notes}>
          {[...parts].reverse().map((part, reverseIndex) => {
            const pieceIndex = parts.length - 1 - reverseIndex;
            if (reverseIndex >= notesShown) return null;
            return (
              <View key={pieceIndex} style={styles.noteRow}>
                <Text style={[styles.notePiece, { color: part.wrong ? colour.danger : colour.muted }]}>
                  {part.text}
                </Text>
                <Text style={styles.noteText}>{part.note}</Text>
              </View>
            );
          })}
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  surface: { paddingHorizontal: space(5), paddingTop: space(6) },
  mode: {
    fontFamily: type.body,
    fontSize: 9.5,
    letterSpacing: 1.8,
    color: colour.faint,
    marginBottom: space(4),
  },
  address: { flexDirection: "row", flexWrap: "wrap", alignItems: "flex-end" },
  char: { fontFamily: type.mono, fontSize: 22, lineHeight: 32 },
  caret: {
    width: 2,
    height: 26,
    marginBottom: 3,
    marginLeft: -1,
    backgroundColor: colour.accentSoft,
    borderRadius: 1,
  },
  notes: { marginTop: space(6), gap: space(4) },
  noteRow: { borderLeftWidth: 1, borderLeftColor: colour.line, paddingLeft: space(3) },
  notePiece: { fontFamily: type.mono, fontSize: 13 },
  noteText: {
    fontFamily: type.body,
    fontSize: 12,
    color: colour.faint,
    marginTop: space(1),
    lineHeight: 17,
  },
});

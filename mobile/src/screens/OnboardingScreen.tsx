/**
 * オンボーディング画面(#20)。
 * ログイン後の初回に、利用の流れ（撮影→アップロード→AI分析→スコア→育成）を案内する。
 */

import React, { useState } from "react";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";

import { colors } from "../utils/theme";

interface Step {
  icon: string;
  title: string;
  body: string;
}

const STEPS: Step[] = [
  {
    icon: "🎥",
    title: "練習動画をアップロード",
    body: "3分以内の練習・プレー動画をアップロードするだけ。撮影のコツはガイドを参考にしてください。",
  },
  {
    icon: "🤖",
    title: "AIが自動で分析",
    body: "スプリント・ボールコントロール・ポジショニング・身体の使い方を解析し、参考スコアを算出します。",
  },
  {
    icon: "📈",
    title: "弱点を練習メニューで強化",
    body: "スコアの弱点に合わせた練習メニューを提案。活動記録から怪我リスクも把握できます。",
  },
];

interface Props {
  onDone: () => void;
}

export default function OnboardingScreen({ onDone }: Props) {
  const [step, setStep] = useState(0);
  const isLast = step === STEPS.length - 1;
  const current = STEPS[step];

  return (
    <View style={styles.container} testID="onboarding">
      <View style={styles.body}>
        <Text style={styles.icon}>{current.icon}</Text>
        <Text style={styles.title}>{current.title}</Text>
        <Text style={styles.text}>{current.body}</Text>
      </View>

      <View style={styles.dots}>
        {STEPS.map((_, i) => (
          <View key={i} style={[styles.dot, i === step && styles.dotActive]} />
        ))}
      </View>

      <View style={styles.actions}>
        <TouchableOpacity onPress={onDone} testID="onboarding-skip">
          <Text style={styles.skip}>スキップ</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={styles.button}
          onPress={() => (isLast ? onDone() : setStep((s) => s + 1))}
          testID="onboarding-next"
        >
          <Text style={styles.buttonText}>{isLast ? "はじめる" : "次へ"}</Text>
        </TouchableOpacity>
      </View>

      <Text style={styles.note}>
        ※ AI スコアは参考値です。未成年の方は保護者の同意のもとご利用ください。
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background, padding: 24, justifyContent: "center" },
  body: { alignItems: "center", flex: 1, justifyContent: "center" },
  icon: { fontSize: 72, marginBottom: 24 },
  title: { fontSize: 24, fontWeight: "bold", color: colors.primary, textAlign: "center" },
  text: {
    fontSize: 15,
    color: colors.textMuted,
    textAlign: "center",
    marginTop: 16,
    lineHeight: 24,
  },
  dots: { flexDirection: "row", justifyContent: "center", gap: 8, marginBottom: 24 },
  dot: { width: 8, height: 8, borderRadius: 4, backgroundColor: colors.border },
  dotActive: { backgroundColor: colors.accent, width: 20 },
  actions: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  skip: { color: colors.textMuted, fontSize: 15 },
  button: {
    backgroundColor: colors.accent,
    borderRadius: 8,
    paddingVertical: 14,
    paddingHorizontal: 32,
  },
  buttonText: { color: "#fff", fontSize: 16, fontWeight: "600" },
  note: {
    fontSize: 11,
    color: colors.textMuted,
    textAlign: "center",
    marginTop: 24,
    lineHeight: 16,
  },
});

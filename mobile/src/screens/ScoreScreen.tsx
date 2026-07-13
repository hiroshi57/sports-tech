/**
 * スコア閲覧画面 — 1 動画の AI 分析結果をレーダーチャート + 数値で表示する。
 */

import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";

import RadarChart, { RadarAxis } from "../components/RadarChart";
import * as api from "../utils/api";
import { colors } from "../utils/theme";

interface Props {
  videoId: string;
  onBack: () => void;
}

const SCORE_LABELS: { key: keyof api.AnalysisResultResponse; label: string }[] = [
  { key: "sprint_score", label: "スプリント" },
  { key: "ball_control_score", label: "ボール\nコントロール" },
  { key: "positioning_score", label: "ポジ\nショニング" },
  { key: "body_usage_score", label: "身体の\n使い方" },
];

export default function ScoreScreen({ videoId, onBack }: Props) {
  const [analysis, setAnalysis] = useState<api.AnalysisResultResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAnalysis = useCallback(() => {
    return api.fetchAnalysis(videoId).then(
      (res) => {
        setAnalysis(res);
        setError(null);
        setLoading(false);
      },
      (e: unknown) => {
        if (e instanceof api.ApiClientError && e.status === 409) {
          setError("分析中です。しばらくしてから再度お試しください。");
        } else if (e instanceof api.ApiClientError) {
          setError(e.detail);
        } else {
          setError("分析結果の取得に失敗しました");
        }
        setLoading(false);
      }
    );
  }, [videoId]);

  const retry = useCallback(() => {
    setLoading(true);
    setError(null);
    void fetchAnalysis();
  }, [fetchAnalysis]);

  useEffect(() => {
    void fetchAnalysis();
  }, [fetchAnalysis]);

  const axes: RadarAxis[] = analysis
    ? SCORE_LABELS.map(({ key, label }) => ({
        label,
        value: analysis[key] as number,
      }))
    : [];

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.inner}>
      <TouchableOpacity onPress={onBack} testID="score-back">
        <Text style={styles.back}>← 戻る</Text>
      </TouchableOpacity>

      <Text style={styles.heading}>分析結果</Text>

      {loading ? (
        <ActivityIndicator color={colors.accent} style={styles.loader} testID="score-loading" />
      ) : error ? (
        <View>
          <Text style={styles.error} testID="score-error">
            {error}
          </Text>
          <TouchableOpacity style={styles.retryButton} onPress={retry} testID="score-retry">
            <Text style={styles.retryText}>再読み込み</Text>
          </TouchableOpacity>
        </View>
      ) : analysis ? (
        <>
          <View style={styles.totalBox} testID="score-total">
            <Text style={styles.totalLabel}>総合スコア（参考値）</Text>
            <Text style={styles.totalValue}>{analysis.total_score}</Text>
            <Text style={styles.totalMargin} testID="score-margin">
              ± {analysis.error_margin}（信頼度:{" "}
              {analysis.reliability_level === "high"
                ? "高"
                : analysis.reliability_level === "moderate"
                  ? "中"
                  : "低"}
              ）
            </Text>
          </View>

          <Text style={styles.reliabilityNote}>{analysis.reliability_note}</Text>

          <RadarChart axes={axes} />

          <View style={styles.scoreList}>
            {SCORE_LABELS.map(({ key, label }) => (
              <View key={key} style={styles.scoreRow}>
                <Text style={styles.scoreRowLabel}>{label.replace(/\n/g, "")}</Text>
                <Text style={styles.scoreRowValue}>{analysis[key] as number}</Text>
              </View>
            ))}
          </View>

          {analysis.feedback ? (
            <View style={styles.feedbackBox}>
              <Text style={styles.feedbackText}>{analysis.feedback}</Text>
            </View>
          ) : null}

          <Text style={styles.disclaimer} testID="score-disclaimer">
            ※ AI スコアはあくまで参考値です。選手評価の唯一の根拠として使用しないでください。
            {analysis.confidence < 0.5 ? "（現在は開発中のスコアです）" : ""}
          </Text>
        </>
      ) : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  inner: { padding: 16 },
  back: { color: colors.accent, fontSize: 15, marginBottom: 8 },
  heading: {
    fontSize: 24,
    fontWeight: "bold",
    color: colors.primary,
    marginBottom: 16,
  },
  loader: { marginTop: 48 },
  error: { color: colors.danger, textAlign: "center", marginTop: 24 },
  retryButton: {
    marginTop: 16,
    alignSelf: "center",
    borderWidth: 1,
    borderColor: colors.accent,
    borderRadius: 8,
    paddingVertical: 10,
    paddingHorizontal: 24,
  },
  retryText: { color: colors.accent, fontWeight: "600" },
  totalBox: {
    backgroundColor: colors.primary,
    borderRadius: 12,
    padding: 20,
    alignItems: "center",
    marginBottom: 20,
  },
  totalLabel: { color: "#cbd5e1", fontSize: 13 },
  totalValue: { color: "#fff", fontSize: 44, fontWeight: "bold" },
  totalMargin: { color: "#cbd5e1", fontSize: 12, marginTop: 2 },
  reliabilityNote: {
    color: colors.textMuted,
    fontSize: 12,
    lineHeight: 18,
    marginBottom: 16,
  },
  scoreList: { marginTop: 20 },
  scoreRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  scoreRowLabel: { fontSize: 14, color: colors.text },
  scoreRowValue: { fontSize: 16, fontWeight: "600", color: colors.accent },
  feedbackBox: {
    backgroundColor: colors.card,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.border,
    padding: 14,
    marginTop: 20,
  },
  feedbackText: { fontSize: 13, color: colors.text, lineHeight: 20 },
  disclaimer: {
    fontSize: 11,
    color: colors.textMuted,
    marginTop: 20,
    lineHeight: 18,
  },
});

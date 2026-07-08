/**
 * 育成画面 — 怪我リスク(#13)と AI 練習メニュー(#11)を表示する。
 *
 * 選手の改善ループ「分析 → 弱点把握 → 練習メニュー → 活動記録 → リスク管理」を
 * 1 画面で可視化する。
 */

import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";

import * as api from "../utils/api";
import { colors } from "../utils/theme";

const RISK_STYLES: Record<api.InjuryRisk["risk_level"], { label: string; color: string }> = {
  low: { label: "低", color: colors.success },
  moderate: { label: "中", color: colors.warning },
  high: { label: "高", color: colors.danger },
};

const SKILL_LABELS: Record<string, string> = {
  sprint: "スプリント",
  ball_control: "ボールコントロール",
  positioning: "ポジショニング",
  body_usage: "身体の使い方",
};

export default function CareScreen() {
  const [risk, setRisk] = useState<api.InjuryRisk | null>(null);
  const [menus, setMenus] = useState<api.TrainingMenu[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAll = useCallback(() => {
    return Promise.all([api.fetchInjuryRisk(), api.listTrainingMenus()]).then(
      ([r, m]) => {
        setRisk(r);
        setMenus(m);
        setError(null);
      },
      (e: unknown) => {
        setError(e instanceof api.ApiClientError ? e.detail : "データの取得に失敗しました");
      }
    );
  }, []);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    void fetchAll().finally(() => setRefreshing(false));
  }, [fetchAll]);

  useEffect(() => {
    void fetchAll();
  }, [fetchAll]);

  const handleGenerate = () => {
    setGenerating(true);
    setError(null);
    api.generateTrainingMenu(60).then(
      () => void fetchAll().finally(() => setGenerating(false)),
      (e: unknown) => {
        setError(e instanceof api.ApiClientError ? e.detail : "メニューの生成に失敗しました");
        setGenerating(false);
      }
    );
  };

  const handleDelete = (id: string) => {
    void api.deleteTrainingMenu(id).then(
      () => setMenus((prev) => prev.filter((m) => m.id !== id)),
      () => setError("メニューの削除に失敗しました")
    );
  };

  const riskStyle = risk ? RISK_STYLES[risk.risk_level] : null;

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.inner}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
    >
      <Text style={styles.heading}>育成</Text>

      {error ? (
        <Text style={styles.error} testID="care-error">
          {error}
        </Text>
      ) : null}

      {/* ── 怪我リスク ── */}
      <Text style={styles.sectionTitle}>怪我リスク</Text>
      {risk && riskStyle ? (
        <View style={styles.riskCard} testID="risk-card">
          <View style={styles.riskHeader}>
            <View style={[styles.riskBadge, { backgroundColor: riskStyle.color }]}>
              <Text style={styles.riskBadgeText}>{riskStyle.label}</Text>
            </View>
            <Text style={styles.riskScore}>{risk.risk_score}</Text>
            <Text style={styles.riskScoreMax}>/100</Text>
            {risk.acwr != null ? <Text style={styles.acwr}>ACWR {risk.acwr}</Text> : null}
          </View>
          {risk.factors.map((f, i) => (
            <Text key={i} style={styles.factor}>
              ・{f}
            </Text>
          ))}
          <Text style={styles.note}>
            ※ 参考値です。医療的診断ではありません。痛みや不調がある場合は専門家に相談してください。
          </Text>
        </View>
      ) : (
        <ActivityIndicator color={colors.accent} style={styles.loader} />
      )}

      {/* ── 練習メニュー ── */}
      <View style={styles.menuHeader}>
        <Text style={styles.sectionTitle}>AI練習メニュー</Text>
        <TouchableOpacity
          style={[styles.generateButton, generating && styles.buttonDisabled]}
          onPress={handleGenerate}
          disabled={generating}
          testID="generate-menu"
        >
          {generating ? (
            <ActivityIndicator color="#fff" size="small" />
          ) : (
            <Text style={styles.generateText}>メニューを生成</Text>
          )}
        </TouchableOpacity>
      </View>

      {menus.length === 0 ? (
        <Text style={styles.empty}>
          まだメニューがありません。「メニューを生成」で弱点に合わせた練習を提案します。
        </Text>
      ) : (
        menus.map((menu) => (
          <View key={menu.id} style={styles.menuCard} testID={`menu-${menu.id}`}>
            <View style={styles.menuTitleRow}>
              <Text style={styles.menuTitle}>{menu.title}</Text>
              <TouchableOpacity onPress={() => handleDelete(menu.id)} testID={`delete-${menu.id}`}>
                <Text style={styles.delete}>削除</Text>
              </TouchableOpacity>
            </View>
            <Text style={styles.menuMeta}>
              {menu.total_duration_min}分 ・ 難易度 {menu.difficulty}
            </Text>
            {menu.description ? <Text style={styles.menuDesc}>{menu.description}</Text> : null}
            {menu.exercises.map((ex, i) => (
              <View key={i} style={styles.exercise}>
                <Text style={styles.exerciseName}>
                  {ex.name}（{ex.duration_min}分）
                </Text>
                {ex.target_skill ? (
                  <Text style={styles.exerciseSkill}>
                    {SKILL_LABELS[ex.target_skill] ?? ex.target_skill}
                  </Text>
                ) : null}
                {ex.description ? <Text style={styles.exerciseDesc}>{ex.description}</Text> : null}
              </View>
            ))}
          </View>
        ))
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  inner: { padding: 16, paddingBottom: 32 },
  heading: { fontSize: 24, fontWeight: "bold", color: colors.primary, marginBottom: 12 },
  sectionTitle: { fontSize: 16, fontWeight: "600", color: colors.text, marginBottom: 8 },
  error: { color: colors.danger, marginBottom: 12 },
  loader: { marginVertical: 24 },
  riskCard: {
    backgroundColor: colors.card,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.border,
    padding: 16,
    marginBottom: 24,
  },
  riskHeader: { flexDirection: "row", alignItems: "flex-end", marginBottom: 10, gap: 8 },
  riskBadge: { borderRadius: 6, paddingHorizontal: 10, paddingVertical: 4 },
  riskBadgeText: { color: "#fff", fontWeight: "700", fontSize: 14 },
  riskScore: { fontSize: 32, fontWeight: "700", color: colors.text, lineHeight: 34 },
  riskScoreMax: { fontSize: 13, color: colors.textMuted, marginBottom: 4 },
  acwr: { marginLeft: "auto", fontSize: 12, color: colors.textMuted, marginBottom: 6 },
  factor: { fontSize: 13, color: colors.text, lineHeight: 20 },
  note: { fontSize: 11, color: colors.textMuted, marginTop: 10, lineHeight: 16 },
  menuHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 8,
  },
  generateButton: {
    backgroundColor: colors.accent,
    borderRadius: 8,
    paddingVertical: 8,
    paddingHorizontal: 16,
  },
  buttonDisabled: { opacity: 0.5 },
  generateText: { color: "#fff", fontSize: 13, fontWeight: "600" },
  empty: { color: colors.textMuted, fontSize: 13, lineHeight: 20, marginTop: 8 },
  menuCard: {
    backgroundColor: colors.card,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.border,
    padding: 16,
    marginBottom: 12,
  },
  menuTitleRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  menuTitle: { fontSize: 15, fontWeight: "700", color: colors.text },
  delete: { color: colors.danger, fontSize: 13 },
  menuMeta: { fontSize: 12, color: colors.textMuted, marginTop: 2 },
  menuDesc: { fontSize: 12, color: colors.textMuted, marginTop: 6, lineHeight: 18 },
  exercise: {
    borderTopWidth: 1,
    borderTopColor: colors.border,
    marginTop: 10,
    paddingTop: 10,
  },
  exerciseName: { fontSize: 14, fontWeight: "600", color: colors.text },
  exerciseSkill: { fontSize: 11, color: colors.accent, marginTop: 2 },
  exerciseDesc: { fontSize: 12, color: colors.textMuted, marginTop: 2, lineHeight: 18 },
});

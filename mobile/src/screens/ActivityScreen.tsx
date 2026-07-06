/**
 * 活動記録（練習ログ）画面。
 * 練習・試合・休養の記録追加とサマリ・一覧表示。
 */

import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";

import * as api from "../utils/api";
import { colors } from "../utils/theme";

const TYPE_LABELS: Record<api.ActivityType, string> = {
  practice: "練習",
  match: "試合",
  rest: "休養",
};

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

export default function ActivityScreen() {
  const [logs, setLogs] = useState<api.ActivityLog[]>([]);
  const [summary, setSummary] = useState<api.ActivitySummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [activityType, setActivityType] = useState<api.ActivityType>("practice");
  const [durationMin, setDurationMin] = useState("60");
  const [fatigue, setFatigue] = useState(3);

  const load = useCallback(() => {
    return Promise.all([api.listActivities(), api.fetchActivitySummary()]).then(
      ([items, s]) => {
        setLogs(items);
        setSummary(s);
        setError(null);
      },
      (e: unknown) => {
        setError(e instanceof api.ApiClientError ? e.detail : "活動記録の取得に失敗しました");
      }
    );
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const handleAdd = () => {
    setLoading(true);
    setError(null);
    const duration = Number(durationMin) || 0;
    api
      .createActivity({
        activity_date: today(),
        activity_type: activityType,
        duration_min: duration,
        fatigue_level: fatigue,
      })
      .then(
        () => load().finally(() => setLoading(false)),
        (e: unknown) => {
          setError(e instanceof api.ApiClientError ? e.detail : "記録の作成に失敗しました");
          setLoading(false);
        }
      );
  };

  const handleDelete = (id: string) => {
    api.deleteActivity(id).then(
      () => void load(),
      () => setError("削除に失敗しました")
    );
  };

  return (
    <View style={styles.container}>
      <Text style={styles.heading}>活動記録</Text>

      {summary ? (
        <View style={styles.summaryRow}>
          <Summary label="回数" value={`${summary.total_count}`} />
          <Summary label="合計時間" value={`${summary.total_duration_min}分`} />
          <Summary
            label="平均疲労"
            value={summary.avg_fatigue_level != null ? `${summary.avg_fatigue_level}` : "-"}
          />
        </View>
      ) : null}

      <View style={styles.form}>
        <View style={styles.typeRow}>
          {(Object.keys(TYPE_LABELS) as api.ActivityType[]).map((t) => (
            <TouchableOpacity
              key={t}
              style={[styles.typeChip, activityType === t && styles.typeChipActive]}
              onPress={() => setActivityType(t)}
              testID={`type-${t}`}
            >
              <Text style={[styles.typeText, activityType === t && styles.typeTextActive]}>
                {TYPE_LABELS[t]}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        <View style={styles.inlineRow}>
          <Text style={styles.label}>時間(分)</Text>
          <TextInput
            style={styles.input}
            value={durationMin}
            onChangeText={setDurationMin}
            keyboardType="number-pad"
            testID="duration-input"
          />
        </View>

        <View style={styles.inlineRow}>
          <Text style={styles.label}>疲労度</Text>
          <View style={styles.fatigueRow}>
            {[1, 2, 3, 4, 5].map((n) => (
              <TouchableOpacity
                key={n}
                style={[styles.fatigueDot, fatigue >= n && styles.fatigueDotActive]}
                onPress={() => setFatigue(n)}
                testID={`fatigue-${n}`}
              >
                <Text style={fatigue >= n ? styles.fatigueTextActive : styles.fatigueText}>
                  {n}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        {error ? (
          <Text style={styles.error} testID="activity-error">
            {error}
          </Text>
        ) : null}

        <TouchableOpacity
          style={[styles.button, loading && styles.buttonDisabled]}
          onPress={handleAdd}
          disabled={loading}
          testID="add-activity"
        >
          {loading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.buttonText}>記録する</Text>
          )}
        </TouchableOpacity>
      </View>

      <FlatList
        data={logs}
        keyExtractor={(x) => x.id}
        style={styles.list}
        ListEmptyComponent={<Text style={styles.empty}>まだ記録がありません。</Text>}
        renderItem={({ item }) => (
          <View style={styles.logCard} testID={`log-${item.id}`}>
            <View style={{ flex: 1 }}>
              <Text style={styles.logTitle}>
                {TYPE_LABELS[item.activity_type]}・{item.duration_min}分
              </Text>
              <Text style={styles.logMeta}>
                {item.activity_date}・疲労度 {item.fatigue_level}/5
              </Text>
            </View>
            <TouchableOpacity onPress={() => handleDelete(item.id)} testID={`delete-${item.id}`}>
              <Text style={styles.delete}>削除</Text>
            </TouchableOpacity>
          </View>
        )}
      />
    </View>
  );
}

function Summary({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.summaryBox}>
      <Text style={styles.summaryValue}>{value}</Text>
      <Text style={styles.summaryLabel}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background, padding: 16 },
  heading: { fontSize: 24, fontWeight: "bold", color: colors.primary, marginBottom: 12 },
  summaryRow: { flexDirection: "row", gap: 8, marginBottom: 16 },
  summaryBox: {
    flex: 1,
    backgroundColor: colors.card,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.border,
    padding: 12,
    alignItems: "center",
  },
  summaryValue: { fontSize: 18, fontWeight: "700", color: colors.accent },
  summaryLabel: { fontSize: 11, color: colors.textMuted, marginTop: 2 },
  form: {
    backgroundColor: colors.card,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.border,
    padding: 14,
    marginBottom: 16,
  },
  typeRow: { flexDirection: "row", gap: 8, marginBottom: 12 },
  typeChip: {
    flex: 1,
    paddingVertical: 8,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: "center",
  },
  typeChipActive: { backgroundColor: colors.accent, borderColor: colors.accent },
  typeText: { color: colors.text, fontSize: 13 },
  typeTextActive: { color: "#fff", fontWeight: "600" },
  inlineRow: { flexDirection: "row", alignItems: "center", marginBottom: 12 },
  label: { fontSize: 13, color: colors.textMuted, width: 64 },
  input: {
    flex: 1,
    backgroundColor: colors.background,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 8,
    padding: 8,
    fontSize: 15,
    color: colors.text,
  },
  fatigueRow: { flexDirection: "row", gap: 8 },
  fatigueDot: {
    width: 34,
    height: 34,
    borderRadius: 17,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: "center",
    justifyContent: "center",
  },
  fatigueDotActive: { backgroundColor: colors.warning, borderColor: colors.warning },
  fatigueText: { color: colors.textMuted },
  fatigueTextActive: { color: "#fff", fontWeight: "700" },
  error: { color: colors.danger, fontSize: 13, marginBottom: 8 },
  button: {
    backgroundColor: colors.accent,
    borderRadius: 8,
    padding: 14,
    alignItems: "center",
  },
  buttonDisabled: { opacity: 0.5 },
  buttonText: { color: "#fff", fontSize: 15, fontWeight: "600" },
  list: { flex: 1 },
  empty: { color: colors.textMuted, textAlign: "center", marginTop: 32 },
  logCard: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: colors.card,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.border,
    padding: 12,
    marginBottom: 8,
  },
  logTitle: { fontSize: 14, fontWeight: "600", color: colors.text },
  logMeta: { fontSize: 12, color: colors.textMuted, marginTop: 2 },
  delete: { color: colors.danger, fontSize: 13 },
});

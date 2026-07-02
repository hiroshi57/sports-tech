/**
 * プロフィール画面 — ログイン中ユーザー情報とログアウト。
 */

import React from "react";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";

import { useAuth } from "../hooks/useAuth";
import { colors } from "../utils/theme";

const roleLabels: Record<string, string> = {
  athlete: "選手",
  scout: "スカウト",
  coach: "コーチ",
};

export default function ProfileScreen() {
  const { user, logout } = useAuth();

  return (
    <View style={styles.container}>
      <Text style={styles.heading}>プロフィール</Text>

      <View style={styles.card}>
        <Row label="メールアドレス" value={user?.email ?? "-"} />
        <Row label="ロール" value={user ? (roleLabels[user.role] ?? user.role) : "-"} />
        <Row label="ステータス" value={user?.is_active ? "有効" : "無効"} />
      </View>

      <Text style={styles.note}>
        ※ AI スコアはあくまで参考値です。選手評価の唯一の根拠として使用しないでください。
      </Text>

      <TouchableOpacity style={styles.logoutButton} onPress={logout} testID="logout-button">
        <Text style={styles.logoutText}>ログアウト</Text>
      </TouchableOpacity>
    </View>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.row}>
      <Text style={styles.rowLabel}>{label}</Text>
      <Text style={styles.rowValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background, padding: 16 },
  heading: {
    fontSize: 24,
    fontWeight: "bold",
    color: colors.primary,
    marginBottom: 16,
  },
  card: {
    backgroundColor: colors.card,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.border,
    padding: 16,
  },
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: 8,
  },
  rowLabel: { fontSize: 14, color: colors.textMuted },
  rowValue: { fontSize: 14, color: colors.text, fontWeight: "500" },
  note: {
    fontSize: 12,
    color: colors.textMuted,
    marginTop: 16,
    lineHeight: 18,
  },
  logoutButton: {
    marginTop: 32,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.danger,
    padding: 14,
    alignItems: "center",
  },
  logoutText: { color: colors.danger, fontSize: 15, fontWeight: "600" },
});

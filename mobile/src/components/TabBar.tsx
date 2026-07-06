/**
 * 軽量ボトムタブバー（ナビゲーションライブラリ非依存）。
 * expo-router / react-navigation 導入時に置き換える。
 */

import React from "react";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";

import { colors } from "../utils/theme";

export type TabKey = "home" | "upload" | "activity" | "profile";

const tabs: { key: TabKey; label: string; icon: string }[] = [
  { key: "home", label: "ホーム", icon: "🏠" },
  { key: "upload", label: "アップロード", icon: "🎥" },
  { key: "activity", label: "活動記録", icon: "📝" },
  { key: "profile", label: "プロフィール", icon: "👤" },
];

interface Props {
  active: TabKey;
  onChange: (tab: TabKey) => void;
}

export default function TabBar({ active, onChange }: Props) {
  return (
    <View style={styles.bar}>
      {tabs.map((t) => (
        <TouchableOpacity
          key={t.key}
          style={styles.tab}
          onPress={() => onChange(t.key)}
          testID={`tab-${t.key}`}
        >
          <Text style={styles.icon}>{t.icon}</Text>
          <Text style={[styles.label, active === t.key && styles.labelActive]}>{t.label}</Text>
        </TouchableOpacity>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  bar: {
    flexDirection: "row",
    borderTopWidth: 1,
    borderTopColor: colors.border,
    backgroundColor: colors.card,
    paddingBottom: 20,
    paddingTop: 8,
  },
  tab: { flex: 1, alignItems: "center" },
  icon: { fontSize: 20 },
  label: { fontSize: 11, color: colors.textMuted, marginTop: 2 },
  labelActive: { color: colors.accent, fontWeight: "600" },
});

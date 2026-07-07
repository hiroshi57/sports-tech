/**
 * 通知画面。分析完了・スカウト閲覧・怪我リスク等のアプリ内通知一覧。
 */

import React, { useCallback, useEffect, useState } from "react";
import { FlatList, RefreshControl, StyleSheet, Text, TouchableOpacity, View } from "react-native";

import * as api from "../utils/api";
import { colors } from "../utils/theme";

const TYPE_ICONS: Record<api.NotificationType, string> = {
  analysis_completed: "✅",
  analysis_failed: "⚠️",
  scout_viewed: "👀",
  injury_risk_alert: "🩹",
};

export default function NotificationScreen() {
  const [items, setItems] = useState<api.Notification[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchItems = useCallback(() => {
    return api.listNotifications().then(
      (list) => {
        setItems(list);
        setError(null);
      },
      (e: unknown) => {
        setError(e instanceof api.ApiClientError ? e.detail : "通知の取得に失敗しました");
      }
    );
  }, []);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    void fetchItems().finally(() => setRefreshing(false));
  }, [fetchItems]);

  useEffect(() => {
    void fetchItems();
  }, [fetchItems]);

  const handleTap = (n: api.Notification) => {
    if (n.is_read) return;
    void api.markNotificationRead(n.id).then(
      () => setItems((prev) => prev.map((x) => (x.id === n.id ? { ...x, is_read: true } : x))),
      () => undefined
    );
  };

  const handleReadAll = () => {
    void api.markAllNotificationsRead().then(
      () => setItems((prev) => prev.map((x) => ({ ...x, is_read: true }))),
      () => undefined
    );
  };

  const hasUnread = items.some((x) => !x.is_read);

  return (
    <View style={styles.container}>
      <View style={styles.headerRow}>
        <Text style={styles.heading}>通知</Text>
        {hasUnread ? (
          <TouchableOpacity onPress={handleReadAll} testID="read-all">
            <Text style={styles.readAll}>すべて既読</Text>
          </TouchableOpacity>
        ) : null}
      </View>

      {error ? <Text style={styles.error}>{error}</Text> : null}

      <FlatList
        data={items}
        keyExtractor={(x) => x.id}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        ListEmptyComponent={<Text style={styles.empty}>通知はありません。</Text>}
        renderItem={({ item }) => (
          <TouchableOpacity
            style={[styles.card, !item.is_read && styles.cardUnread]}
            onPress={() => handleTap(item)}
            testID={`notification-${item.id}`}
          >
            <Text style={styles.icon}>{TYPE_ICONS[item.type] ?? "🔔"}</Text>
            <View style={{ flex: 1 }}>
              <Text style={styles.title}>{item.title}</Text>
              {item.body ? <Text style={styles.body}>{item.body}</Text> : null}
            </View>
            {!item.is_read ? <View style={styles.dot} testID={`unread-${item.id}`} /> : null}
          </TouchableOpacity>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background, padding: 16 },
  headerRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 12,
  },
  heading: { fontSize: 24, fontWeight: "bold", color: colors.primary },
  readAll: { color: colors.accent, fontSize: 13 },
  error: { color: colors.danger, marginBottom: 12 },
  empty: { color: colors.textMuted, textAlign: "center", marginTop: 48 },
  card: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: colors.card,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.border,
    padding: 14,
    marginBottom: 8,
    gap: 12,
  },
  cardUnread: { borderColor: colors.accent, backgroundColor: "#eef5ff" },
  icon: { fontSize: 20 },
  title: { fontSize: 14, fontWeight: "600", color: colors.text },
  body: { fontSize: 12, color: colors.textMuted, marginTop: 2 },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.accent,
  },
});

/**
 * ホーム画面 — 自分の動画一覧と分析ステータス。
 */

import React, { useCallback, useEffect, useState } from "react";
import { FlatList, RefreshControl, StyleSheet, Text, TouchableOpacity, View } from "react-native";

import { useAuth } from "../hooks/useAuth";
import * as api from "../utils/api";
import { colors, statusLabels } from "../utils/theme";

interface Props {
  onSelectVideo: (videoId: string) => void;
}

export default function HomeScreen({ onSelectVideo }: Props) {
  const { user } = useAuth();
  const [videos, setVideos] = useState<api.VideoResponse[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchVideos = useCallback(() => {
    return api.listVideos().then(
      (items) => {
        setVideos(items);
        setError(null);
      },
      (e: unknown) => {
        setError(e instanceof api.ApiClientError ? e.detail : "動画一覧の取得に失敗しました");
      }
    );
  }, []);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    void fetchVideos().finally(() => setRefreshing(false));
  }, [fetchVideos]);

  useEffect(() => {
    if (user?.role === "athlete") {
      void fetchVideos();
    }
  }, [user, fetchVideos]);

  return (
    <View style={styles.container}>
      <Text style={styles.heading}>ホーム</Text>
      <Text style={styles.welcome}>{user ? `${user.email} でログイン中` : ""}</Text>

      {error ? <Text style={styles.error}>{error}</Text> : null}

      <FlatList
        data={videos}
        keyExtractor={(v) => v.id}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        ListEmptyComponent={
          <Text style={styles.empty}>
            まだ動画がありません。「アップロード」タブから練習動画を追加しましょう。
          </Text>
        }
        renderItem={({ item }) => {
          const st = statusLabels[item.status] ?? {
            label: item.status,
            color: colors.textMuted,
          };
          const isCompleted = item.status === "completed";
          return (
            <TouchableOpacity
              style={styles.card}
              testID={`video-${item.id}`}
              disabled={!isCompleted}
              onPress={() => onSelectVideo(item.id)}
            >
              <Text style={styles.cardTitle} numberOfLines={1}>
                {item.s3_key.split("/").pop()}
              </Text>
              <Text style={[styles.cardStatus, { color: st.color }]}>{st.label}</Text>
              {item.duration_sec ? (
                <Text style={styles.cardMeta}>{item.duration_sec} 秒</Text>
              ) : null}
              {isCompleted ? <Text style={styles.cardCta}>タップして分析結果を見る →</Text> : null}
            </TouchableOpacity>
          );
        }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background, padding: 16 },
  heading: { fontSize: 24, fontWeight: "bold", color: colors.primary },
  welcome: { fontSize: 12, color: colors.textMuted, marginBottom: 16 },
  error: { color: colors.danger, marginBottom: 12 },
  empty: {
    color: colors.textMuted,
    textAlign: "center",
    marginTop: 48,
    lineHeight: 20,
  },
  card: {
    backgroundColor: colors.card,
    borderRadius: 10,
    padding: 14,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: colors.border,
  },
  cardTitle: { fontSize: 14, fontWeight: "600", color: colors.text },
  cardStatus: { fontSize: 12, marginTop: 4 },
  cardMeta: { fontSize: 12, color: colors.textMuted, marginTop: 2 },
  cardCta: { fontSize: 12, color: colors.accent, marginTop: 6, fontWeight: "600" },
});

/**
 * 動画アップロード画面。
 *
 * フロー:
 * 1. POST /api/videos/upload-url で Presigned URL を取得
 * 2. 動画ファイルを Presigned URL に PUT（実ファイル選択は expo-image-picker
 *    導入後に接続する — 現段階では手順 1 と 3 の API 接続を実装）
 * 3. POST /api/videos/{id}/complete で完了通知
 */

import React, { useState } from "react";
import {
  ActivityIndicator,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
} from "react-native";

import * as api from "../utils/api";
import { colors } from "../utils/theme";

type Phase = "idle" | "requesting" | "ready" | "completing" | "done";

export default function UploadScreen() {
  const [filename, setFilename] = useState("practice.mp4");
  const [phase, setPhase] = useState<Phase>("idle");
  const [upload, setUpload] = useState<api.VideoUploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const requestUrl = async () => {
    setPhase("requesting");
    setError(null);
    try {
      const res = await api.initiateUpload(filename.trim(), "video/mp4");
      setUpload(res);
      setPhase("ready");
    } catch (e) {
      setError(
        e instanceof api.ApiClientError ? e.detail : "アップロード URL の取得に失敗しました"
      );
      setPhase("idle");
    }
  };

  const complete = async () => {
    if (!upload) return;
    setPhase("completing");
    setError(null);
    try {
      await api.completeUpload(upload.video_id);
      setPhase("done");
    } catch (e) {
      setError(e instanceof api.ApiClientError ? e.detail : "完了通知に失敗しました");
      setPhase("ready");
    }
  };

  const busy = phase === "requesting" || phase === "completing";

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.inner}>
      <Text style={styles.heading}>動画アップロード</Text>
      <Text style={styles.note}>
        練習動画（3 分以内 / 500MB まで / mp4・mov）をアップロードすると AI
        が分析し、参考スコアを算出します。
      </Text>

      <Text style={styles.label}>ファイル名</Text>
      <TextInput
        style={styles.input}
        value={filename}
        onChangeText={setFilename}
        autoCapitalize="none"
        testID="upload-filename-input"
      />

      {error ? (
        <Text style={styles.error} testID="upload-error">
          {error}
        </Text>
      ) : null}

      {phase === "idle" || phase === "requesting" ? (
        <TouchableOpacity
          style={[styles.button, busy && styles.buttonDisabled]}
          onPress={requestUrl}
          disabled={busy || !filename.trim()}
          testID="upload-request-button"
        >
          {busy ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.buttonText}>アップロード URL を取得</Text>
          )}
        </TouchableOpacity>
      ) : null}

      {(phase === "ready" || phase === "completing") && upload ? (
        <>
          <Text style={styles.success} testID="upload-ready">
            URL を取得しました（video_id: {upload.video_id.slice(0, 8)}…）
          </Text>
          <Text style={styles.note}>動画ファイルの選択・送信は次のアップデートで対応します。</Text>
          <TouchableOpacity
            style={[styles.button, busy && styles.buttonDisabled]}
            onPress={complete}
            disabled={busy}
            testID="upload-complete-button"
          >
            {busy ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.buttonText}>アップロード完了を通知</Text>
            )}
          </TouchableOpacity>
        </>
      ) : null}

      {phase === "done" ? (
        <Text style={styles.success} testID="upload-done">
          アップロードが完了しました。分析結果はホーム画面で確認できます。
        </Text>
      ) : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  inner: { padding: 16 },
  heading: { fontSize: 24, fontWeight: "bold", color: colors.primary },
  note: { fontSize: 13, color: colors.textMuted, marginVertical: 12, lineHeight: 20 },
  label: { fontSize: 13, color: colors.text, marginBottom: 6 },
  input: {
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 8,
    padding: 12,
    fontSize: 15,
    color: colors.text,
  },
  error: { color: colors.danger, marginTop: 12, fontSize: 13 },
  success: { color: colors.success, marginTop: 16, fontSize: 14 },
  button: {
    backgroundColor: colors.accent,
    borderRadius: 8,
    padding: 16,
    alignItems: "center",
    marginTop: 20,
  },
  buttonDisabled: { opacity: 0.4 },
  buttonText: { color: "#fff", fontSize: 16, fontWeight: "600" },
});

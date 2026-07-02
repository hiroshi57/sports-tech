/** アプリ共通のカラー・スタイル定数。 */

export const colors = {
  primary: "#1a1a2e",
  accent: "#0f6fff",
  background: "#f7f8fa",
  card: "#ffffff",
  text: "#1a1a2e",
  textMuted: "#6b7280",
  border: "#e5e7eb",
  danger: "#dc2626",
  success: "#16a34a",
  warning: "#d97706",
} as const;

export const statusLabels: Record<string, { label: string; color: string }> = {
  pending: { label: "アップロード待ち", color: colors.textMuted },
  processing: { label: "分析中", color: colors.warning },
  completed: { label: "分析完了", color: colors.success },
  failed: { label: "失敗", color: colors.danger },
};

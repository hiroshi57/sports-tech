/** アプリ共通のカラー・スタイル定数。 */

// Web ダッシュボード（globals.css の Design Token）と統一したパレット
export const colors = {
  primary: "#0b1b3f", // ブランド濃紺
  accent: "#2563eb", // アクション青
  background: "#f6f8fc",
  card: "#ffffff",
  text: "#111827",
  textMuted: "#6b7280",
  border: "#e6e9f0",
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

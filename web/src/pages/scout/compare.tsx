import Head from "next/head";
import Link from "next/link";
import { useRouter } from "next/router";
import { useCallback, useEffect, useState } from "react";

import MultiRadarChart, { type RadarSeries } from "@/components/MultiRadarChart";
import { type AthleteScores, getAthleteScores, getToken } from "@/lib/api";
import styles from "@/styles/dashboard.module.css";

const AXES = [
  { key: "sprint_score", label: "スプリント" },
  { key: "ball_control_score", label: "ボール" },
  { key: "positioning_score", label: "ポジ" },
  { key: "body_usage_score", label: "身体" },
] as const;

const COLORS = ["#2563eb", "#16a34a", "#d97706", "#dc2626"];

export default function ComparePage() {
  const router = useRouter();
  const [items, setItems] = useState<AthleteScores[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (ids: string[]) => {
    setLoading(true);
    setError(null);
    try {
      const results = await Promise.all(ids.map((id) => getAthleteScores(id)));
      setItems(results);
    } catch {
      setError("比較データの取得に失敗しました");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!getToken()) {
      void router.replace("/auth/login");
      return;
    }
    const raw = router.query.ids;
    if (raw === undefined) return; // ルーター未確定
    const ids = String(raw)
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean)
      .slice(0, 4); // 最大4人
    if (ids.length === 0) {
      void Promise.resolve().then(() => setLoading(false));
      return;
    }
    void Promise.resolve().then(() => load(ids));
  }, [router.query.ids, router, load]);

  const series: RadarSeries[] = items
    .filter((it) => it.latest)
    .map((it, i) => ({
      name: it.name,
      color: COLORS[i % COLORS.length],
      values: AXES.map((a) => it.latest![a.key]),
    }));

  return (
    <>
      <Head>
        <title>選手比較 | sports-tech スカウト</title>
      </Head>
      <div className={styles.page}>
        <header className={styles.header}>
          <span className={styles.brand}>
            <span className={styles.brandMark}>⚽</span>
            sports-tech スカウト
          </span>
          <Link className={styles.link} href="/scout/search">
            ← 検索に戻る
          </Link>
        </header>

        <div className={styles.container}>
          <h1 className={styles.pageTitle}>選手比較</h1>
          <p className={styles.pageLead}>
            最大4人の能力を重ねて比較できます。検索画面で選手を選んでください。
          </p>

          {loading ? <p className={styles.loading}>読み込み中…</p> : null}
          {error ? <p className={styles.error}>{error}</p> : null}

          {!loading && series.length === 0 && !error ? (
            <p className={styles.empty}>
              比較する選手が選択されていません。検索画面のカードで「比較に追加」してください。
            </p>
          ) : null}

          {series.length > 0 ? (
            <>
              {/* 凡例 */}
              <div className={styles.legendRow}>
                {series.map((s) => (
                  <span key={s.name} className={styles.legendItem}>
                    <span className={styles.legendDot} style={{ background: s.color }} />
                    {s.name}
                  </span>
                ))}
              </div>

              <div className={styles.chartWrap} style={{ marginBottom: "var(--space-6)" }}>
                <MultiRadarChart axisLabels={AXES.map((a) => a.label)} series={series} />
              </div>

              {/* 比較テーブル */}
              <div className={styles.chartWrap} style={{ display: "block", overflowX: "auto" }}>
                <table className={styles.histTable}>
                  <thead>
                    <tr>
                      <th>項目</th>
                      {items
                        .filter((i) => i.latest)
                        .map((i) => (
                          <th key={i.id}>{i.name}</th>
                        ))}
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>総合スコア</td>
                      {items
                        .filter((i) => i.latest)
                        .map((i) => (
                          <td key={i.id}>
                            <strong>{i.latest!.total_score}</strong>
                          </td>
                        ))}
                    </tr>
                    {AXES.map((a) => (
                      <tr key={a.key}>
                        <td>{a.label}</td>
                        {items
                          .filter((i) => i.latest)
                          .map((i) => (
                            <td key={i.id}>{i.latest![a.key]}</td>
                          ))}
                      </tr>
                    ))}
                    <tr>
                      <td>ポジション</td>
                      {items
                        .filter((i) => i.latest)
                        .map((i) => (
                          <td key={i.id}>{i.position ?? "—"}</td>
                        ))}
                    </tr>
                  </tbody>
                </table>
              </div>

              <p className={styles.disclaimer}>
                ※ AI スコアはあくまで参考値です。選手評価の唯一の根拠として使用しないでください。
              </p>
            </>
          ) : null}
        </div>
      </div>
    </>
  );
}

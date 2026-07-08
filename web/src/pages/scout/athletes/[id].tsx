import Head from "next/head";
import Link from "next/link";
import { useRouter } from "next/router";
import { useCallback, useEffect, useState } from "react";

import RadarChart, { type RadarAxis } from "@/components/RadarChart";
import ScoreHistoryChart from "@/components/ScoreHistoryChart";
import ScoreRing from "@/components/ScoreRing";
import { ApiError, type AthleteScores, getAthleteScores, getToken } from "@/lib/api";
import styles from "@/styles/dashboard.module.css";

export default function AthleteDetailPage() {
  const router = useRouter();
  const { id } = router.query;
  const [data, setData] = useState<AthleteScores | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async (athleteId: string) => {
    setLoading(true);
    setError(null);
    try {
      setData(await getAthleteScores(athleteId));
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setError("選手が見つかりませんでした（非公開の可能性があります）。");
      } else {
        setError(err instanceof ApiError ? err.detail : "取得に失敗しました");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!getToken()) {
      void router.replace("/auth/login");
      return;
    }
    if (typeof id === "string") {
      const athleteId = id;
      void Promise.resolve().then(() => load(athleteId));
    }
  }, [id, router, load]);

  const axes: RadarAxis[] = data?.latest
    ? [
        { label: "スプリント", value: data.latest.sprint_score },
        { label: "ボール", value: data.latest.ball_control_score },
        { label: "ポジ", value: data.latest.positioning_score },
        { label: "身体", value: data.latest.body_usage_score },
      ]
    : [];

  return (
    <>
      <Head>
        <title>{data ? `${data.name} | ` : ""}選手詳細 | sports-tech スカウト</title>
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
          {loading ? <p className={styles.loading}>読み込み中…</p> : null}
          {error ? <p className={styles.error}>{error}</p> : null}

          {data ? (
            <>
              <div className={styles.detailHead}>
                {data.latest ? (
                  <div className={styles.bigRing}>
                    <ScoreRing value={data.latest.total_score} size={96} stroke={7} />
                    <div className={styles.bigRingValue}>
                      <span className={styles.bigRingNum}>{data.latest.total_score}</span>
                      <span className={styles.bigRingLabel}>参考値</span>
                    </div>
                  </div>
                ) : (
                  <div className={styles.ringEmpty} style={{ width: 96, height: 96 }}>
                    分析なし
                  </div>
                )}
                <div>
                  <h1 className={styles.detailName}>{data.name}</h1>
                  <p className={styles.detailMeta}>
                    {[data.position, data.sport, data.location].filter(Boolean).join(" ・ ")}
                  </p>
                  <p className={styles.detailMeta}>
                    {[
                      data.height_cm ? `身長 ${data.height_cm}cm` : null,
                      data.weight_kg ? `体重 ${data.weight_kg}kg` : null,
                    ]
                      .filter(Boolean)
                      .join(" ・ ") || "身体データ未登録"}
                  </p>
                </div>
              </div>

              {data.latest ? (
                <>
                  <section className={styles.section}>
                    <h2 className={styles.subheading}>能力バランス</h2>
                    <div className={styles.chartWrap}>
                      <RadarChart axes={axes} />
                    </div>
                  </section>

                  <section className={styles.section}>
                    <h2 className={styles.subheading}>総合スコアの推移</h2>
                    <div className={styles.chartWrap}>
                      <ScoreHistoryChart history={data.history} />
                    </div>
                  </section>
                </>
              ) : (
                <p className={styles.empty}>分析データがまだありません。</p>
              )}

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

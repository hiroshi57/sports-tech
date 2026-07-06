import Head from "next/head";
import Link from "next/link";
import { useRouter } from "next/router";
import { useCallback, useEffect, useState } from "react";

import { ApiError, type AthleteSearchItem, getAthlete, getToken } from "@/lib/api";
import styles from "@/styles/dashboard.module.css";

export default function AthleteDetailPage() {
  const router = useRouter();
  const { id } = router.query;
  const [athlete, setAthlete] = useState<AthleteSearchItem | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async (athleteId: string) => {
    setLoading(true);
    setError(null);
    try {
      setAthlete(await getAthlete(athleteId));
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

  return (
    <>
      <Head>
        <title>{athlete ? `${athlete.name} | ` : ""}選手詳細 | sports-tech スカウト</title>
      </Head>
      <div className={styles.page}>
        <header className={styles.header}>
          <span className={styles.brand}>sports-tech スカウト</span>
          <Link className={styles.link} href="/scout/search">
            ← 検索に戻る
          </Link>
        </header>

        <div className={styles.container}>
          {loading ? <p className={styles.loading}>読み込み中…</p> : null}
          {error ? <p className={styles.error}>{error}</p> : null}

          {athlete ? (
            <>
              <h1 className={styles.heading}>{athlete.name}</h1>
              <p className={styles.cardMeta}>
                {[athlete.position, athlete.sport, athlete.location].filter(Boolean).join(" ・ ")}
              </p>
              <p className={styles.cardMeta}>
                {[
                  athlete.height_cm ? `身長 ${athlete.height_cm}cm` : null,
                  athlete.weight_kg ? `体重 ${athlete.weight_kg}kg` : null,
                ]
                  .filter(Boolean)
                  .join(" ・ ") || "身体データ未登録"}
              </p>

              {athlete.latest_total_score != null ? (
                <>
                  <div className={styles.score}>{athlete.latest_total_score}</div>
                  <div className={styles.scoreLabel}>総合スコア（参考値）</div>
                </>
              ) : (
                <p className={styles.cardMeta}>分析データがまだありません。</p>
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

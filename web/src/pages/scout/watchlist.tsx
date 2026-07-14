import Head from "next/head";
import Link from "next/link";
import { useRouter } from "next/router";
import { useCallback, useEffect, useState } from "react";

import ScoreRing from "@/components/ScoreRing";
import { getToken, listWatchlist, removeWatchlist, type WatchlistItem } from "@/lib/api";
import styles from "@/styles/dashboard.module.css";

export default function WatchlistPage() {
  const router = useRouter();
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    return listWatchlist().then(
      (list) => {
        setItems(list);
        setError(null);
        setLoading(false);
      },
      () => {
        setError("ウォッチリストの取得に失敗しました");
        setLoading(false);
      }
    );
  }, []);

  useEffect(() => {
    if (!getToken()) {
      void router.replace("/auth/login");
      return;
    }
    void Promise.resolve().then(() => load());
  }, [router, load]);

  const handleRemove = (id: string) => {
    void removeWatchlist(id).then(
      () => setItems((prev) => prev.filter((i) => i.id !== id)),
      () => undefined
    );
  };

  return (
    <>
      <Head>
        <title>ウォッチリスト | sports-tech スカウト</title>
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
          <h1 className={styles.pageTitle}>ウォッチリスト</h1>
          <p className={styles.pageLead}>気になる選手を保存して比較・追跡できます。</p>

          {loading ? <p className={styles.loading}>読み込み中…</p> : null}
          {error ? <p className={styles.error}>{error}</p> : null}

          {!loading && items.length === 0 && !error ? (
            <p className={styles.empty}>
              まだ登録がありません。検索画面のカードで「★ 保存」してください。
            </p>
          ) : null}

          <div className={styles.grid}>
            {items.map((it) => (
              <div key={it.id} className={styles.card}>
                <Link
                  href={`/scout/athletes/${it.athlete_id}`}
                  style={{ display: "contents", color: "inherit" }}
                >
                  {it.latest_total_score != null ? (
                    <div className={styles.ring}>
                      <ScoreRing value={it.latest_total_score} />
                      <span className={styles.ringValue}>{it.latest_total_score}</span>
                    </div>
                  ) : (
                    <div className={styles.ringEmpty}>分析なし</div>
                  )}
                  <div className={styles.cardBody}>
                    <div className={styles.cardName}>{it.name}</div>
                    <div className={styles.cardMeta}>
                      {[it.position, it.sport, it.location].filter(Boolean).join(" ・ ")}
                    </div>
                    {it.tags ? <div className={styles.cardMeta}>🏷 {it.tags}</div> : null}
                    {it.note ? <div className={styles.cardMeta}>📝 {it.note}</div> : null}
                  </div>
                </Link>
                <button
                  type="button"
                  className={styles.cardSelect}
                  style={{
                    background: "none",
                    border: "none",
                    cursor: "pointer",
                    color: "var(--color-danger)",
                  }}
                  onClick={() => handleRemove(it.id)}
                >
                  ★ 保存済み（削除）
                </button>
              </div>
            ))}
          </div>

          <p className={styles.disclaimer}>
            ※ AI スコアはあくまで参考値です。選手評価の唯一の根拠として使用しないでください。
          </p>
        </div>
      </div>
    </>
  );
}

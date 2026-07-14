import Head from "next/head";
import Link from "next/link";
import { useRouter } from "next/router";
import { useCallback, useEffect, useState } from "react";

import { deleteSavedSearch, getToken, listSavedSearches, type SavedSearch } from "@/lib/api";
import styles from "@/styles/dashboard.module.css";

export default function SavedSearchesPage() {
  const router = useRouter();
  const [items, setItems] = useState<SavedSearch[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    return listSavedSearches().then(
      (list) => {
        setItems(list);
        setError(null);
        setLoading(false);
      },
      () => {
        setError("保存条件の取得に失敗しました");
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
    void deleteSavedSearch(id).then(
      () => setItems((prev) => prev.filter((s) => s.id !== id)),
      () => undefined
    );
  };

  const toQuery = (s: SavedSearch) => {
    const p = new URLSearchParams();
    if (s.position) p.set("position", s.position);
    if (s.location) p.set("location", s.location);
    if (s.min_total_score != null) p.set("min", String(s.min_total_score));
    return p.toString();
  };

  return (
    <>
      <Head>
        <title>保存条件 | sports-tech スカウト</title>
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
          <h1 className={styles.pageTitle}>保存した検索条件</h1>
          <p className={styles.pageLead}>
            条件を保存すると、新しく条件に合致した選手の件数（新着）を確認できます。
          </p>

          {loading ? <p className={styles.loading}>読み込み中…</p> : null}
          {error ? <p className={styles.error}>{error}</p> : null}

          {!loading && items.length === 0 && !error ? (
            <p className={styles.empty}>
              まだ保存条件がありません。検索画面で「🔔 この条件を保存」してください。
            </p>
          ) : null}

          <div className={styles.grid}>
            {items.map((s) => (
              <div key={s.id} className={styles.card} style={{ alignItems: "stretch" }}>
                <div className={styles.cardBody}>
                  <div className={styles.cardName}>
                    {s.name}
                    {s.new_count > 0 ? (
                      <span
                        style={{
                          marginLeft: 8,
                          background: "var(--color-danger)",
                          color: "#fff",
                          borderRadius: "var(--radius-full)",
                          padding: "2px 8px",
                          fontSize: "var(--text-xs)",
                        }}
                      >
                        新着 {s.new_count}
                      </span>
                    ) : null}
                  </div>
                  <div className={styles.cardMeta}>
                    {[
                      s.position ? `ポジ:${s.position}` : null,
                      s.location ? `地域:${s.location}` : null,
                      s.min_total_score != null ? `スコア≥${s.min_total_score}` : null,
                    ]
                      .filter(Boolean)
                      .join(" ・ ") || "条件なし（全選手）"}
                  </div>
                  <div
                    style={{ marginTop: "var(--space-2)", display: "flex", gap: "var(--space-4)" }}
                  >
                    <Link className={styles.cardSelect} href={`/scout/search?${toQuery(s)}`}>
                      この条件で検索 →
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
                      onClick={() => handleRemove(s.id)}
                    >
                      削除
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}

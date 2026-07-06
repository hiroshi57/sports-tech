import Head from "next/head";
import Link from "next/link";
import { useRouter } from "next/router";
import { useCallback, useEffect, useState } from "react";

import {
  ApiError,
  type AthleteSearchItem,
  getToken,
  searchAthletes,
  setToken,
  type SearchFilters,
} from "@/lib/api";
import styles from "@/styles/dashboard.module.css";

export default function ScoutSearchPage() {
  const router = useRouter();
  const [athletes, setAthletes] = useState<AthleteSearchItem[]>([]);
  const [filters, setFilters] = useState<SearchFilters>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runSearch = useCallback(async (f: SearchFilters) => {
    setLoading(true);
    setError(null);
    try {
      const items = await searchAthletes(f);
      setAthletes(items);
    } catch (err) {
      if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
        setError("認証が切れました。再度ログインしてください。");
      } else {
        setError(err instanceof ApiError ? err.detail : "検索に失敗しました");
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
    // 同期 setState を避けるためマイクロタスクで実行
    void Promise.resolve().then(() => runSearch({}));
  }, [router, runSearch]);

  const handleLogout = () => {
    setToken(null);
    void router.push("/auth/login");
  };

  return (
    <>
      <Head>
        <title>選手を探す | sports-tech スカウト</title>
      </Head>
      <div className={styles.page}>
        <header className={styles.header}>
          <span className={styles.brand}>sports-tech スカウト</span>
          <button className={styles.link} onClick={handleLogout}>
            ログアウト
          </button>
        </header>

        <div className={styles.container}>
          <h1 className={styles.heading}>選手を探す</h1>

          <form
            className={styles.filters}
            onSubmit={(e) => {
              e.preventDefault();
              void runSearch(filters);
            }}
          >
            <div className={styles.field}>
              <label className={styles.label}>ポジション</label>
              <input
                className={styles.input}
                placeholder="FW / MF / DF / GK"
                value={filters.position ?? ""}
                onChange={(e) =>
                  setFilters((f) => ({ ...f, position: e.target.value || undefined }))
                }
              />
            </div>
            <div className={styles.field}>
              <label className={styles.label}>地域</label>
              <input
                className={styles.input}
                placeholder="東京"
                value={filters.location ?? ""}
                onChange={(e) =>
                  setFilters((f) => ({ ...f, location: e.target.value || undefined }))
                }
              />
            </div>
            <div className={styles.field}>
              <label className={styles.label}>総合スコア下限</label>
              <input
                className={styles.input}
                type="number"
                min={0}
                max={100}
                placeholder="0"
                value={filters.min_total_score ?? ""}
                onChange={(e) =>
                  setFilters((f) => ({
                    ...f,
                    min_total_score: e.target.value ? Number(e.target.value) : undefined,
                  }))
                }
              />
            </div>
            <button className={styles.button} type="submit" disabled={loading}>
              {loading ? "検索中…" : "検索"}
            </button>
          </form>

          {error ? <p className={styles.error}>{error}</p> : null}
          {loading ? <p className={styles.loading}>読み込み中…</p> : null}

          {!loading && !error && athletes.length === 0 ? (
            <p className={styles.empty}>条件に一致する公開選手が見つかりませんでした。</p>
          ) : null}

          <div className={styles.grid}>
            {athletes.map((a) => (
              <Link key={a.id} href={`/scout/athletes/${a.id}`} className={styles.card}>
                <div className={styles.cardName}>{a.name}</div>
                <div className={styles.cardMeta}>
                  {[a.position, a.sport, a.location].filter(Boolean).join(" ・ ")}
                </div>
                {a.latest_total_score != null ? (
                  <>
                    <div className={styles.score}>{a.latest_total_score}</div>
                    <div className={styles.scoreLabel}>総合スコア（参考値）</div>
                  </>
                ) : (
                  <div className={styles.cardMeta}>分析データなし</div>
                )}
              </Link>
            ))}
          </div>

          <p className={styles.disclaimer}>
            ※ AI スコアはあくまで参考値です。選手評価の唯一の根拠として使用しないでください。
            未成年の選手は保護者同意がある場合のみ表示されます。
          </p>
        </div>
      </div>
    </>
  );
}

import Head from "next/head";
import Link from "next/link";
import { useRouter } from "next/router";
import { useCallback, useEffect, useMemo, useState } from "react";

import ScoreRing from "@/components/ScoreRing";
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
    void Promise.resolve().then(() => runSearch({}));
  }, [router, runSearch]);

  const handleLogout = () => {
    setToken(null);
    void router.push("/auth/login");
  };

  // KPI 集計
  const stats = useMemo(() => {
    const scored = athletes.filter((a) => a.latest_total_score != null);
    const avg = scored.length
      ? Math.round(scored.reduce((s, a) => s + (a.latest_total_score ?? 0), 0) / scored.length)
      : null;
    const top = scored.reduce<number | null>(
      (m, a) =>
        a.latest_total_score != null && (m == null || a.latest_total_score > m)
          ? a.latest_total_score
          : m,
      null
    );
    return { total: athletes.length, scored: scored.length, avg, top };
  }, [athletes]);

  return (
    <>
      <Head>
        <title>選手を探す | sports-tech スカウト</title>
      </Head>
      <div className={styles.page}>
        <header className={styles.header}>
          <span className={styles.brand}>
            <span className={styles.brandMark}>⚽</span>
            sports-tech スカウト
          </span>
          <button className={styles.link} onClick={handleLogout}>
            ログアウト
          </button>
        </header>

        <div className={styles.container}>
          <h1 className={styles.pageTitle}>選手を探す</h1>
          <p className={styles.pageLead}>
            公開設定された選手を条件で絞り込み、AI 参考スコアから有望株を発見できます。
          </p>

          {/* KPI 統計 */}
          <div className={styles.stats}>
            <div className={styles.statCard}>
              <div className={styles.statValue}>{stats.total}</div>
              <div className={styles.statLabel}>該当選手</div>
            </div>
            <div className={styles.statCard}>
              <div className={styles.statValue}>{stats.scored}</div>
              <div className={styles.statLabel}>分析済み</div>
            </div>
            <div className={styles.statCard}>
              <div className={styles.statValue}>{stats.avg ?? "—"}</div>
              <div className={styles.statLabel}>平均総合スコア</div>
            </div>
            <div className={styles.statCard}>
              <div className={styles.statValue}>{stats.top ?? "—"}</div>
              <div className={styles.statLabel}>最高総合スコア</div>
            </div>
          </div>

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
                {a.latest_total_score != null ? (
                  <div className={styles.ring}>
                    <ScoreRing value={a.latest_total_score} />
                    <span className={styles.ringValue}>{a.latest_total_score}</span>
                  </div>
                ) : (
                  <div className={styles.ringEmpty}>分析なし</div>
                )}
                <div className={styles.cardBody}>
                  <div className={styles.cardName}>{a.name}</div>
                  <div className={styles.cardMeta}>
                    {[a.position, a.sport, a.location].filter(Boolean).join(" ・ ")}
                  </div>
                </div>
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

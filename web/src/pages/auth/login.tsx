import Head from "next/head";
import { useRouter } from "next/router";
import { type FormEvent, useState } from "react";

import { ApiError, fetchMe, login, setToken } from "@/lib/api";
import styles from "@/styles/dashboard.module.css";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const token = await login(email.trim());
      setToken(token.access_token);
      const me = await fetchMe();
      if (me.role === "athlete") {
        setToken(null);
        setError("スカウト/コーチ用のダッシュボードです。選手はモバイルアプリをご利用ください。");
        return;
      }
      await router.push("/scout/search");
    } catch (err) {
      setToken(null);
      setError(err instanceof ApiError ? err.detail : "ログインに失敗しました");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Head>
        <title>ログイン | sports-tech スカウト</title>
      </Head>
      <div className={styles.page}>
        <div className={styles.loginBox}>
          <h1 className={styles.loginTitle}>スカウトログイン</h1>
          <form onSubmit={handleSubmit}>
            <div className={styles.field}>
              <label className={styles.label} htmlFor="email">
                メールアドレス
              </label>
              <input
                id="email"
                className={styles.input}
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="scout@example.com"
                required
              />
            </div>
            {error ? <p className={styles.error}>{error}</p> : null}
            <button
              className={`${styles.button} ${styles.fullWidth}`}
              type="submit"
              disabled={loading || !email.includes("@")}
            >
              {loading ? "ログイン中…" : "ログイン"}
            </button>
          </form>
        </div>
      </div>
    </>
  );
}

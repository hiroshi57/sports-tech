import Head from "next/head";
import Link from "next/link";

import styles from "@/styles/dashboard.module.css";

/**
 * 選手登録の案内ページ。
 * 選手のアカウント作成・動画アップロードはモバイルアプリで行うため、
 * ここでは案内とスカウト向けログインへの導線を示す。
 */
export default function AthleteRegisterPage() {
  return (
    <>
      <Head>
        <title>選手登録のご案内 | sports-tech</title>
      </Head>
      <div className={styles.loginWrap}>
        <div className={styles.loginBox}>
          <h1 className={styles.loginTitle}>選手登録について</h1>
          <p className={styles.loginLead}>
            選手のアカウント作成・練習動画のアップロード・AI 分析は
            <strong>モバイルアプリ</strong>からご利用いただけます。
          </p>
          <p
            style={{
              fontSize: "var(--text-sm)",
              color: "var(--color-text-muted)",
              lineHeight: 1.8,
              marginBottom: "var(--space-5)",
            }}
          >
            スカウト・コーチの方は、Web ダッシュボードで公開選手の検索・スコア閲覧ができます。
          </p>
          <Link className={`${styles.button} ${styles.fullWidth}`} href="/auth/login">
            スカウトとしてログイン
          </Link>
          <p style={{ textAlign: "center", marginTop: "var(--space-4)" }}>
            <Link className={styles.link} href="/" style={{ color: "var(--color-accent)" }}>
              ← トップに戻る
            </Link>
          </p>
        </div>
      </div>
    </>
  );
}

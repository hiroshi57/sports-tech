import Head from "next/head";
import Link from "next/link";
import { Geist } from "next/font/google";
import styles from "@/styles/Home.module.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const NAV_LINKS = [
  { label: "選手を探す", href: "/scout/search" },
  { label: "選手を登録する", href: "/athlete/register" },
  { label: "ログイン", href: "/auth/login" },
] as const;

const FEATURES = [
  {
    icon: "🎥",
    title: "AI動画分析",
    description:
      "練習動画をアップロードするだけで、AIが走力・ボールコントロールなど多角的にスコア化",
  },
  {
    icon: "🔍",
    title: "スカウトDB検索",
    description: "ポジション・年齢・スコアで世界中の才能ある選手を絞り込み、直接コンタクト",
  },
  {
    icon: "📊",
    title: "プロ選手比較",
    description: "プロ選手や上位選手の動きと自分の動きを重ね合わせて、具体的な改善点を把握",
  },
  {
    icon: "💪",
    title: "セルフケア",
    description: "活動量・疲労度・栄養データをもとに、怪我リスクと回復状態をAIがモニタリング",
  },
] as const;

export default function Home() {
  return (
    <>
      <Head>
        <title>sports-tech — AIスポーツスカウティング & 選手育成プラットフォーム</title>
        <meta
          name="description"
          content="AI動画分析で選手の才能を可視化。スカウト・育成・セルフケアを一体化したスポーツテクノロジープラットフォーム。"
        />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <div className={`${styles.page} ${geistSans.variable}`}>
        {/* ── ナビゲーション ── */}
        <header className={styles.header}>
          <span className={styles.logo}>⚽ sports-tech</span>
          <nav className={styles.nav}>
            {NAV_LINKS.map((link) => (
              <Link key={link.href} href={link.href} className={styles.navLink}>
                {link.label}
              </Link>
            ))}
          </nav>
        </header>

        <main className={styles.main}>
          {/* ── ヒーロー ── */}
          <section className={styles.hero}>
            <h1 className={styles.heroTitle}>才能は、動画の中にある。</h1>
            <p className={styles.heroSubtitle}>
              練習動画をアップロードするだけで、AIが選手の能力を多角的にスコア化。
              <br />
              スカウトと選手をつなぐ、次世代のスポーツプラットフォーム。
            </p>
            <div className={styles.ctas}>
              <Link href="/athlete/register" className={styles.primary}>
                選手として登録する
              </Link>
              <Link href="/scout/search" className={styles.secondary}>
                スカウトとして探す
              </Link>
            </div>
          </section>

          {/* ── 機能一覧 ── */}
          <section className={styles.features}>
            <h2 className={styles.sectionTitle}>主な機能</h2>
            <div className={styles.featureGrid}>
              {FEATURES.map((feature) => (
                <div key={feature.title} className={styles.featureCard}>
                  <span className={styles.featureIcon}>{feature.icon}</span>
                  <h3 className={styles.featureTitle}>{feature.title}</h3>
                  <p className={styles.featureDescription}>{feature.description}</p>
                </div>
              ))}
            </div>
          </section>

          {/* ── 注意書き ── */}
          <p className={styles.disclaimer}>
            ※ 表示されるスコアはAIによる参考値です。確定的な選手評価を保証するものではありません。
          </p>
        </main>

        <footer className={styles.footer}>
          <p>© 2026 sports-tech. All rights reserved.</p>
        </footer>
      </div>
    </>
  );
}

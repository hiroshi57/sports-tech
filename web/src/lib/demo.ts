/**
 * デモモード用の組み込みデータ。
 *
 * NEXT_PUBLIC_DEMO === "1" のとき、API クライアントはバックエンドに接続せず
 * このデータを返す。公開バックエンドなしで Vercel 上のダッシュボードを
 * 体験してもらうための仕組み（スコアは架空の参考値）。
 */

import type {
  Ability,
  AthleteScores,
  AthleteSearchItem,
  Health,
  Nutrition,
  OverseasReadiness,
  PhysicalPoint,
  Prediction,
  ScoreSnapshot,
} from "./api";

interface DemoAthlete {
  id: string;
  name: string;
  position: string;
  location: string;
  age: number;
  height_cm: number;
  weight_kg: number;
  base: [number, number, number, number]; // sprint, ball, positioning, body
}

/** id から決定論的な擬似乱数（0-1） */
function seed(id: string, salt: string): number {
  let h = 2166136261;
  const s = `${id}:${salt}`;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return ((h >>> 0) % 1000) / 1000;
}

/** 基準値 ± range で id 依存の値を作り 0-100 に収める */
function around(id: string, salt: string, center: number, range: number): number {
  const v = center + (seed(id, salt) - 0.5) * 2 * range;
  return Math.round(Math.max(0, Math.min(100, v)));
}

const ATHLETES: DemoAthlete[] = [
  {
    id: "d1",
    name: "三笘 次郎",
    position: "MF",
    location: "神奈川",
    age: 17,
    height_cm: 170,
    weight_kg: 65,
    base: [90, 85, 80, 77],
  },
  {
    id: "d2",
    name: "南野 五郎",
    position: "FW",
    location: "大阪",
    age: 18,
    height_cm: 174,
    weight_kg: 68,
    base: [88, 80, 76, 74],
  },
  {
    id: "d3",
    name: "久保 太郎",
    position: "FW",
    location: "東京",
    age: 16,
    height_cm: 178,
    weight_kg: 70,
    base: [82, 74, 88, 79],
  },
  {
    id: "d4",
    name: "冨安 三郎",
    position: "DF",
    location: "大阪",
    age: 19,
    height_cm: 188,
    weight_kg: 82,
    base: [70, 60, 85, 90],
  },
  {
    id: "d5",
    name: "遠藤 四郎",
    position: "MF",
    location: "福岡",
    age: 17,
    height_cm: 178,
    weight_kg: 72,
    base: [65, 78, 72, 68],
  },
];

function total(b: [number, number, number, number]): number {
  return Math.round((b[0] * 0.3 + b[1] * 0.3 + b[2] * 0.2 + b[3] * 0.2) * 10) / 10;
}

export function demoSearch(): AthleteSearchItem[] {
  return ATHLETES.map((a) => ({
    id: a.id,
    name: a.name,
    position: a.position,
    sport: "football",
    location: a.location,
    height_cm: a.height_cm,
    weight_kg: a.weight_kg,
    latest_total_score: total(a.base),
    is_reference_score: true,
  })).sort((x, y) => (y.latest_total_score ?? 0) - (x.latest_total_score ?? 0));
}

export function demoScores(id: string): AthleteScores {
  const a = ATHLETES.find((x) => x.id === id) ?? ATHLETES[0];
  // 3 回分の履歴（0.9 → 0.95 → 1.0 で成長）
  const history: ScoreSnapshot[] = [0.9, 0.95, 1.0].map((f, i) => {
    const b = a.base.map((s) => Math.round(s * f * 10) / 10) as [number, number, number, number];
    return {
      sprint_score: b[0],
      ball_control_score: b[1],
      positioning_score: b[2],
      body_usage_score: b[3],
      total_score: total(b),
      analyzed_at: `2026-0${i + 4}-01T00:00:00Z`,
    };
  });
  const latest = history[history.length - 1];

  // 同ポジション平均（ベンチマーク）
  const peers = ATHLETES.filter((x) => x.position === a.position);
  const mean = (idx: number) =>
    Math.round((peers.reduce((s, p) => s + p.base[idx], 0) / peers.length) * 10) / 10;
  const benchmark = {
    sprint_score: mean(0),
    ball_control_score: mean(1),
    positioning_score: mean(2),
    body_usage_score: mean(3),
    total_score:
      Math.round((peers.reduce((s, p) => s + total(p.base), 0) / peers.length) * 10) / 10,
    sample_size: peers.length,
  };

  // パーセンタイル（同ポジション内で自分以下の割合）
  const myTotal = total(a.base);
  const below = peers.filter((p) => total(p.base) <= myTotal).length;
  const percentile = Math.round((below / peers.length) * 100);

  // 安定性（履歴総合スコアの標準偏差 → 0-100）
  const totals = history.map((h) => h.total_score);
  const avg = totals.reduce((s, v) => s + v, 0) / totals.length;
  const sd = Math.sqrt(totals.reduce((s, v) => s + (v - avg) ** 2, 0) / totals.length);
  const consistency = Math.round(Math.max(0, 100 - sd * 5) * 10) / 10;

  const h = a.height_cm / 100;
  const bmi = Math.round((a.weight_kg / (h * h)) * 10) / 10;

  // ── 多面能力（技術/フィジカル/メンタル/健康）──
  const [sp, bc, po, bo] = a.base;
  const abilities: Ability[] = [
    {
      category: "技術",
      name: "ポジショニング正確性",
      value: po,
      avg: benchmark.positioning_score,
      note: "オフザボールの位置取り",
    },
    { category: "技術", name: "ボールコントロール", value: bc, avg: benchmark.ball_control_score },
    { category: "技術", name: "基礎技術", value: around(a.id, "basic-tech", (bc + po) / 2, 8) },
    {
      category: "フィジカル",
      name: "瞬発力（スプリント）",
      value: sp,
      avg: benchmark.sprint_score,
    },
    {
      category: "フィジカル",
      name: "持久力",
      value: around(a.id, "stamina", 72, 15),
      note: "走行データより推定",
    },
    { category: "フィジカル", name: "基礎体力", value: around(a.id, "fitness", 74, 12) },
    { category: "フィジカル", name: "敏捷性", value: around(a.id, "agility", sp - 4, 10) },
    {
      category: "フィジカル",
      name: "柔軟性（足首の柔らかさ）",
      value: around(a.id, "ankle", 68, 16),
    },
    {
      category: "フィジカル",
      name: "軸の固さ（体幹）",
      value: bo,
      avg: benchmark.body_usage_score,
    },
    {
      category: "メンタル",
      name: "安定性（メンタル）",
      value: Math.round(consistency),
      note: "試合間のブレの小ささ",
    },
    { category: "メンタル", name: "協調性", value: around(a.id, "teamwork", 76, 14) },
    { category: "メンタル", name: "コミュニケーション力", value: around(a.id, "comm", 72, 16) },
    { category: "健康", name: "健康面", value: around(a.id, "health", 82, 10) },
    { category: "健康", name: "コンディション安定", value: around(a.id, "cond", 78, 12) },
  ];

  // ── 身体データの時系列（過去12ヶ月・成長中）──
  const physical_history: PhysicalPoint[] = [0, 3, 6, 9, 12].map((mAgo, i) => {
    const grow = (12 - mAgo) / 12; // 過去ほど小さい
    return {
      date: `2025-${String(((i * 3) % 12) + 1).padStart(2, "0")}`,
      height_cm: Math.round((a.height_cm - (1 - grow) * 3) * 10) / 10,
      weight_kg: Math.round((a.weight_kg - (1 - grow) * 4) * 10) / 10,
      body_fat_pct: Math.round((12 + (1 - grow) * 2) * 10) / 10,
    };
  });

  // ── 栄養・食事 ──
  const adequacy = around(a.id, "nutrition", 74, 18);
  const nutrition: Nutrition = {
    avg_calories: 2600 + Math.round(seed(a.id, "cal") * 600),
    protein_g: 90 + Math.round(seed(a.id, "pro") * 60),
    adequacy,
    note:
      adequacy >= 75
        ? "たんぱく質・総カロリーとも成長期の目安を概ね充足。"
        : "総カロリーがやや不足気味。増量期は補食の追加を推奨。",
  };

  // ── 将来予測（成長率 + ポテンシャル）──
  const potential = around(a.id, "potential", a.age <= 17 ? 85 : 72, 12);
  const projected_total = Math.round(Math.min(99, myTotal + potential / 12) * 10) / 10;
  const prediction: Prediction = {
    horizon: "12ヶ月後",
    projected_total,
    projected_height_cm: Math.round((a.height_cm + (a.age <= 17 ? 2.5 : 0.8)) * 10) / 10,
    projected_weight_kg: Math.round((a.weight_kg + 3) * 10) / 10,
    potential,
    comment:
      a.age <= 17
        ? "成長期でフィジカル向上余地が大きい。総合スコアの上振れ期待。"
        : "技術の伸びが中心。フィジカルは現状維持〜微増の見込み。",
  };

  // ── 健康・可用性 ──
  const injuryRisk = around(a.id, "injury", 30, 20);
  const health: Health = {
    injury_risk: injuryRisk,
    availability_pct: 100 - Math.round(injuryRisk / 3),
    note:
      injuryRisk >= 45
        ? "直近の負荷が高め。オーバートレーニングに注意。"
        : "急性:慢性 負荷比は適正範囲。大きな懸念なし。",
  };

  // ── 海外適性 ──
  const overseasScore = around(a.id, "overseas", (myTotal + potential) / 2, 10);
  const overseas: OverseasReadiness = {
    score: overseasScore,
    factors: [
      `総合力 ${myTotal}（同ポジ上位${100 - percentile}%）`,
      potential >= 80
        ? "高いポテンシャルで育成環境に適応余地大"
        : "即戦力寄りで適応に時間を要する可能性",
      overseasScore >= 75
        ? "フィジカル・メンタルとも海外基準に近い"
        : "フィジカル強化が渡航前の課題",
      `年齢 ${a.age}歳（若年は移籍市場で有利）`,
    ],
  };

  return {
    id: a.id,
    name: a.name,
    position: a.position,
    sport: "football",
    location: a.location,
    age: a.age,
    height_cm: a.height_cm,
    weight_kg: a.weight_kg,
    latest,
    history,
    benchmark,
    percentile,
    consistency,
    bmi,
    abilities,
    physical_history,
    nutrition,
    prediction,
    health,
    overseas,
    is_reference_score: true,
  };
}

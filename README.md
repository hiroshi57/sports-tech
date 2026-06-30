# sports-tech

> AI動画解析で選手の才能を可視化し、スカウト・育成を革新するスポーツテクノロジープラットフォーム

[![CI](https://github.com/hiroshi57/sports-tech/actions/workflows/ci.yml/badge.svg)](https://github.com/hiroshi57/sports-tech/actions/workflows/ci.yml)

---

## 概要

選手が練習動画をアップロードするだけで、AIが走力・ボールコントロール等を分析し独自スコアを算出。スカウト向けDBと選手育成機能を一体化したモバイルアプリ + Webダッシュボード。

---

## モノレポ構成

```
sports-tech/
├── mobile/      # React Native + Expo（iOS / Android）
├── backend/     # FastAPI + Celery（AI推論 API）
├── web/         # Next.js（スカウト向けWebダッシュボード）
└── shared/      # 共有型定義・定数（TypeScript）
```

---

## 技術スタック

| レイヤー | 技術 |
|---|---|
| モバイル | React Native + Expo |
| バックエンド | FastAPI + Celery |
| Web | Next.js |
| AI/ML | MediaPipe + カスタムモデル |
| DB | PostgreSQL + pgvector |
| ストレージ | AWS S3 |
| 認証 | Supabase Auth |

---

## セットアップ

### 前提環境
- Node.js 20.x 以上
- Python 3.11 以上
- Expo CLI

### バックエンド

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env  # 環境変数を設定
uvicorn app.main:app --reload
```

### モバイルアプリ

```bash
cd mobile
npm install
npx expo start
```

### Webダッシュボード

```bash
cd web
npm install
npm run dev
```

---

## テスト実行

```bash
# バックエンド
cd backend && python -m pytest tests/ -v

# モバイル
cd mobile && npm test

# Web
cd web && npm test
```

---

## 参考サービス

- [CUJU](https://cuju.pro/)
- [SmartCoach](https://smartcoach.mb.softbank.jp/lp/details/index.html)
- [SportsMate](https://sportsmate.jp/)

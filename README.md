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

| レイヤー     | 技術                       |
| ------------ | -------------------------- |
| モバイル     | React Native + Expo        |
| バックエンド | FastAPI + Celery           |
| Web          | Next.js                    |
| AI/ML        | MediaPipe + カスタムモデル |
| DB           | PostgreSQL + pgvector      |
| ストレージ   | AWS S3                     |
| 認証         | Supabase Auth              |

---

## セットアップ

### 前提環境

- Node.js 20.x 以上
- Python 3.11 以上
- Expo CLI
- Docker / Docker Compose（バックエンド一式をまとめて起動する場合）

### Docker Compose（推奨: DB + Redis + API + Worker を一括起動）

```bash
# 初回はビルドから
docker compose up --build

# API:   http://localhost:8000  (Swagger: /docs)
# DB:    localhost:5432 (postgres)
# Redis: localhost:6379

# DB と Redis だけ起動したい場合
docker compose up -d db redis

# 停止（データは pgdata ボリュームに保持）
docker compose down
```

起動時に `alembic upgrade head` が自動実行され、動画分析は Celery worker が
Redis 経由で非同期処理します。`backend/` はボリュームマウントされ、
コード変更は `--reload` で即反映されます。

> **注意**: `docker-compose.yml` はローカル/検証用です。本番デプロイには使用しません。

### バックエンド（Docker を使わない場合）

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env  # 環境変数を設定
alembic upgrade head  # DB マイグレーション
uvicorn app.main:app --reload

# 別ターミナルで Celery worker を起動（AI分析の非同期処理に必要）
celery -A app.worker.celery_app worker --loglevel=info
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

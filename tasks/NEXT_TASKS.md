# 直近タスク — sports-tech

> **更新日**: 2026-06-30

---

## 🔥 今すぐ着手（今日〜今週）

### T-01: リポジトリ構成を確定・初期化する
**優先度**: 最高  
**担当**: Claude Code  
**完了条件**: `npm run lint` と `python -m pytest` が通る状態

```
sports-tech/
├── mobile/          # React Native + Expo
├── backend/         # FastAPI + Celery
├── web/             # Next.js（スカウト向け）
└── shared/          # 型定義・定数共有
```

- [ ] モノレポ構成の初期化
- [ ] ESLint / Prettier / Husky セットアップ
- [ ] GitHub Actions CI（lint + test）
- [ ] README.md の作成

---

### T-02: データベーススキーマを設計・定義する
**優先度**: 最高  
**担当**: Claude Code  
**完了条件**: Alembic マイグレーション成功

主要テーブル:
- `users` (id, email, role: athlete/scout/coach, age, consent_flag)
- `athlete_profiles` (user_id, name, position, height, weight, location, is_public)
- `videos` (id, athlete_id, s3_key, status, duration, uploaded_at)
- `analysis_results` (video_id, sprint_score, ball_control_score, positioning_score, total_score, analyzed_at)
- `activity_logs` (athlete_id, date, type, duration, fatigue_level, notes)
- `training_menus` (id, athlete_id, created_by_ai, exercises[])

---

## 📅 次にやること（今週〜来週）

### T-03: 認証フローを実装する
- Supabase Auth 設定
- Google / Apple ログイン
- JWT 検証ミドルウェア
- 未成年者同意フラグ処理

### T-04: 動画アップロード API を実装する
- AWS S3 Presigned URL 発行
- アップロード完了通知（Webhook）
- 動画メタデータ保存

### T-05: React Native 基本画面を実装する
- ログイン画面
- ホーム（ダッシュボード）
- 動画アップロード画面
- プロフィール画面

---

## 🗓 今週中に完了したいこと

| タスク | 完了条件 |
|---|---|
| T-01: リポジトリ初期化 | CI が緑になる |
| T-02: DBスキーマ設計 | ER図 + マイグレーション成功 |
| T-03: 認証フロー | ログイン E2E テスト通過 |

---

## 💡 スパイク・調査が必要な項目

- [ ] MediaPipe の React Native 対応状況を調査（v0.10以降）
- [ ] 動画AI分析のコスト見積もり（GPU推論 vs クラウドAI API）
- [ ] 未成年者データの法的要件（COPPA / 日本の個人情報保護法）
- [ ] pgvector の類似選手検索のクエリ設計

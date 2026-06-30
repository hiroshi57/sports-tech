# 手順書 — sports-tech

> **バージョン**: 1.0.0  
> **作成日**: 2026-06-30

---

## 前提環境

| ツール | バージョン | 確認コマンド |
|---|---|---|
| Node.js | 20.x以上 | `node --version` |
| Python | 3.11以上 | `python --version` |
| Expo CLI | 最新 | `npx expo --version` |
| Git | 2.40以上 | `git --version` |
| Docker | 最新（ローカルDB用） | `docker --version` |

---

## フェーズ別実装フロー

### Phase 1: 基盤構築（Month 1-2）

#### Step 1-1: リポジトリ初期化
```bash
# 確認コマンド
git log --oneline -5
ls -la
```
- [ ] モノレポ構成の決定（`/mobile`, `/backend`, `/web`）
- [ ] ESLint / Prettier / Husky 設定
- [ ] GitHub Actions CI パイプライン構築
- [ ] 完了確認: `npm run lint && npm test` が全て通る

#### Step 1-2: 認証システム
```bash
# 確認コマンド
cd backend && python -m pytest tests/auth/ -v
```
- [ ] Supabase Auth 設定（SNSログイン: Google / Apple）
- [ ] JWT トークン検証ミドルウェア
- [ ] 未成年者保護者同意フロー
- [ ] 完了確認: ログイン→トークン発行→API呼び出しの E2E テスト通過

#### Step 1-3: データベース設計・構築
```bash
# 確認コマンド
cd backend && alembic upgrade head && python -m pytest tests/db/ -v
```
- [ ] PostgreSQL スキーマ定義（選手・動画・スコア・活動記録）
- [ ] Alembic マイグレーション
- [ ] pgvector 拡張（類似選手検索用）
- [ ] 完了確認: マイグレーション成功・CRUD テスト通過

#### Step 1-4: 動画アップロード基盤
```bash
# 確認コマンド
cd backend && python -m pytest tests/upload/ -v
```
- [ ] AWS S3 バケット設定・IAM ポリシー
- [ ] Presigned URL 発行 API
- [ ] 動画メタデータ保存
- [ ] 完了確認: 実際にMP4をアップロードしS3に格納確認

---

### Phase 2: AI分析エンジン MVP（Month 3-4）

#### Step 2-1: 骨格検出モデル統合
```bash
# 確認コマンド
cd backend && python scripts/test_mediapipe.py sample_video.mp4
```
- [ ] MediaPipe Pose + Holistic 統合
- [ ] フレーム毎の骨格座標抽出
- [ ] 非同期処理キュー（Celery + Redis）
- [ ] 完了確認: サンプル動画で骨格座標JSON出力確認

#### Step 2-2: スコア算出アルゴリズム
```bash
# 確認コマンド
cd backend && python -m pytest tests/scoring/ -v
```
- [ ] 走力スコア計算モジュール
- [ ] ボールコントロールスコア計算モジュール
- [ ] 総合スコア（加重平均）計算
- [ ] 完了確認: テストケース5本以上でスコア出力確認

#### Step 2-3: 分析結果 API & 通知
```bash
# 確認コマンド
cd backend && python -m pytest tests/api/analysis/ -v
```
- [ ] 分析結果取得 API（GET /api/analyses/{id}）
- [ ] プッシュ通知（Expo Push Notifications）
- [ ] 完了確認: 動画アップロード→10分以内に通知受信の E2E テスト

---

### Phase 3: スカウト機能（Month 5-6）

#### Step 3-1: スカウト向けWebダッシュボード
```bash
# 確認コマンド
cd web && npm run build && npm test
```
- [ ] Next.js プロジェクト初期化
- [ ] 選手検索・フィルタリング UI
- [ ] 選手プロフィールカード
- [ ] 完了確認: 検索→結果表示→プロフィール詳細の動線確認

#### Step 3-2: 比較分析機能
```bash
# 確認コマンド
cd web && npm test -- --grep "comparison"
```
- [ ] レーダーチャートコンポーネント
- [ ] 骨格オーバーレイ動画比較
- [ ] プロ選手ベンチマークデータ
- [ ] 完了確認: 2選手選択→比較チャート表示確認

---

### Phase 4: 育成・セルフケア機能（Month 7-8）

#### Step 4-1: 練習メニュー生成
```bash
# 確認コマンド
cd backend && python -m pytest tests/training_menu/ -v
```
- [ ] 弱点スコア → ドリル推薦ロジック
- [ ] カスタムメニュービルダー UI
- [ ] 完了確認: スコア入力→メニュー5件以上の推薦確認

#### Step 4-2: セルフケアアラート
```bash
# 確認コマンド
cd backend && python -m pytest tests/selfcare/ -v
```
- [ ] 活動量・疲労度からのリスクスコア計算
- [ ] 閾値超過時のプッシュ通知
- [ ] 完了確認: 高負荷データ入力→アラート受信確認

---

## 検証フロー（全フェーズ共通）

```bash
# バックエンド全テスト
cd backend && python -m pytest tests/ -v --cov=app

# フロントエンド全テスト
cd mobile && npm test -- --watchAll=false

# 型チェック
cd mobile && npx tsc --noEmit
cd web && npx tsc --noEmit

# Lint
npm run lint
```

## デプロイフロー

```bash
# Staging デプロイ（Claude Code が担当）
# Backend: Railway / Render
git push origin feature/xxx  # CI → staging 自動デプロイ

# 本番デプロイ（Cursor が担当・Claude Code は禁止）
# vercel --prod（Cursor のみ実行可）
```

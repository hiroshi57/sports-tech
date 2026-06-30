# AI記憶・設計判断ログ — sports-tech

> 重要な設計判断・方針変更・調査結果を記録する。

---

## 設計判断ログ

### [2026-06-30] プロジェクト開始・技術スタック確定
- **決定**: React Native + FastAPI + Next.js のモノレポ構成
- **理由**: iOS/Android 同時対応、AI推論はPython、スカウト向けWebはNext.js
- **代替案**: Flutter（却下：AI推論連携が複雑）、Django（却下：FastAPIの方が非同期処理に向く）

### [2026-06-30] AI分析アーキテクチャ
- **決定**: 動画アップロード後に非同期キュー（Celery + Redis）で分析
- **理由**: 動画分析は5〜10分かかる。同期処理ではUXが悪い
- **注意**: リアルタイム分析は将来フェーズ。初期はオフライン分析のみ

### [2026-06-30] スコア表示方針
- **決定**: 分析スコアは「参考スコア」として表示。確定評価として提示しない
- **理由**: AI評価の限界・誤差を透明化。ユーザーの過信を防ぐ
- **実装**: UIに「このスコアはAIによる参考値です」の注意書きを必ず表示

---

## 未解決の技術課題

- [ ] MediaPipe の React Native 対応（ネイティブモジュール必要の可能性）
- [ ] pgvector の類似選手検索クエリの最適化方法
- [ ] 未成年者（18歳未満）データの法的要件詳細

---

## 参考リソース

- MediaPipe Python: https://developers.google.com/mediapipe/solutions/vision/pose_landmarker/python
- FastAPI + Celery: https://testdriven.io/blog/fastapi-and-celery/
- pgvector: https://github.com/pgvector/pgvector
- Expo Push Notifications: https://docs.expo.dev/push-notifications/overview/

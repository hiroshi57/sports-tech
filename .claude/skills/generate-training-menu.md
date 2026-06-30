---
name: generate-training-menu
description: 選手のスコアデータを基にAI推奨練習メニューを生成・確認する手順
triggers:
  - "練習メニューを生成して"
  - "トレーニングメニューを作って"
  - "練習メニューのテストをして"
---

# 練習メニュー生成スキル

## 手順

### 1. メニュー生成APIのテスト
```bash
cd backend

# スコアデータからメニュー生成
curl -X POST http://localhost:8000/api/training-menus/generate \
  -H "Authorization: Bearer $TEST_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "athlete_id": "test-athlete-001",
    "sprint_score": 62,
    "ball_control_score": 45,
    "positioning_score": 70,
    "difficulty": "intermediate"
  }'
```

### 2. 生成結果の検証項目
- [ ] 弱点スコア（最低点）に対応するドリルが含まれる
- [ ] 各ドリルに `duration_minutes`, `difficulty`, `description` がある
- [ ] メニュー合計時間が 30〜90分の範囲内
- [ ] 少なくとも3種類のドリルが含まれる

### 3. テスト実行
```bash
python -m pytest tests/training_menu/ -v
```

### 4. フロントエンド確認
```bash
cd mobile
# メニュー生成画面の Storybook 確認
npx storybook
# または実機での確認
npx expo start
```

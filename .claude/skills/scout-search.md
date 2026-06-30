---
name: scout-search
description: スカウト向け選手検索機能のテストと動作確認手順
triggers:
  - "スカウト検索をテストして"
  - "選手検索の動作確認"
  - "スカウト機能を確認して"
---

# スカウト検索スキル

## 手順

### 1. 検索APIのテスト
```bash
cd backend

# ポジション・年齢・スコアでフィルタリング
curl "http://localhost:8000/api/athletes/search?position=FW&age_min=18&age_max=22&total_score_min=70" \
  -H "Authorization: Bearer $SCOUT_TOKEN"

# 類似選手検索（pgvector）
curl "http://localhost:8000/api/athletes/similar/{athlete_id}?limit=10" \
  -H "Authorization: Bearer $SCOUT_TOKEN"
```

### 2. 検索結果の検証項目
- [ ] `is_public: true` の選手のみ返される
- [ ] 未成年者（`age < 18`）は `consent_flag: true` の場合のみ表示
- [ ] スコアフィルターが正しく機能する
- [ ] ページネーションが動作する（`limit`, `offset`）

### 3. テスト実行
```bash
python -m pytest tests/api/scout/ -v
cd web && npm test -- --grep "scout"
```

### 4. Web ダッシュボード確認
```bash
cd web
npm run dev
# http://localhost:3000/scout にアクセスして検索UIを確認
```

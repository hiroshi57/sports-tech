---
name: analyze-video
description: 選手の練習動画をAI分析APIに投入し、スコア結果を確認する手順
triggers:
  - "動画を分析して"
  - "スコアを確認して"
  - "AI分析を実行して"
---

# 動画AI分析スキル

## 手順

### 1. ローカルでの分析テスト（開発時）
```bash
cd backend

# サンプル動画で分析テスト
python scripts/analyze_video.py --video tests/fixtures/sample.mp4 --output results/

# 結果確認
cat results/analysis_result.json
```

### 2. 分析APIのエンドポイントテスト
```bash
# バックエンドを起動
uvicorn app.main:app --reload --port 8000

# 動画アップロード → 分析キュー投入
curl -X POST http://localhost:8000/api/videos/upload \
  -H "Authorization: Bearer $TEST_TOKEN" \
  -F "file=@tests/fixtures/sample.mp4"

# 分析結果を確認（video_id で照会）
curl http://localhost:8000/api/analyses/{video_id} \
  -H "Authorization: Bearer $TEST_TOKEN"
```

### 3. 分析結果の検証項目
- [ ] `sprint_score`: 0〜100の範囲内
- [ ] `ball_control_score`: 0〜100の範囲内
- [ ] `positioning_score`: 0〜100の範囲内
- [ ] `total_score`: 各スコアの加重平均と一致
- [ ] `analyzed_at`: 分析完了時刻が記録されている
- [ ] `status`: "completed" になっている

### 4. テスト実行
```bash
python -m pytest tests/scoring/ -v
python -m pytest tests/api/analysis/ -v
```

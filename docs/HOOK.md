# フック設計書 — sports-tech

> **バージョン**: 1.0.0  
> **作成日**: 2026-06-30

---

## hooks の基本方針

- hooks は「絶対に守るべき最小集合」のみ登録する
- CLAUDE.md は助言、hooks は強制
- PostToolUse は `.claude/agents/` と必ず対応させる

---

## SessionStart フック

セッション開始時に自動実行する。

### 実行内容
```bash
echo "=== sports-tech セッション開始 ==="
echo "📋 直近タスク:"
cat tasks/NEXT_TASKS.md | head -30
echo ""
echo "🔄 Git 状態:"
git status -sb
echo ""
echo "📦 依存関係の更新確認:"
# backend
if [ -f backend/requirements.txt ]; then
  echo "Backend: requirements.txt 確認済み"
fi
# mobile
if [ -f mobile/package.json ]; then
  echo "Mobile: package.json 確認済み"
fi
```

### settings.json への設定
```json
{
  "hooks": {
    "SessionStart": [
      {
        "type": "command",
        "command": "cat tasks/NEXT_TASKS.md | head -30 && git status -sb"
      }
    ]
  }
}
```

---

## PostToolUse フック（品質ゲート）

コード生成・編集ツール実行後に自動起動する品質チェックエージェント。

### 登録エージェント一覧

| エージェント | ファイル | トリガー条件 |
|---|---|---|
| AI品質チェッカー | `.claude/agents/ai-quality-checker.md` | Python/AIコード編集後 |
| プライバシー・セキュリティチェッカー | `.claude/agents/privacy-security-checker.md` | 全コード編集後 |

### settings.json への設定
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit",
        "hooks": [
          {
            "type": "prompt",
            "prompt": ".claude/agents/privacy-security-checker.md"
          }
        ]
      },
      {
        "matcher": "Edit|Write",
        "file_pattern": "**/*.py",
        "hooks": [
          {
            "type": "prompt",
            "prompt": ".claude/agents/ai-quality-checker.md"
          }
        ]
      }
    ]
  }
}
```

---

## 権限設計（allow / ask / deny）

### allow（自動でOK）
- `Bash(npm test *)` — テスト実行
- `Bash(python -m pytest *)` — Pythonテスト実行
- `Bash(npx tsc --noEmit)` — 型チェック
- `Bash(npm run lint)` — Lint実行
- `Bash(git status *)` — Git状態確認
- `Bash(git diff *)` — Git差分確認
- `Bash(git add *)` — ステージング
- `Bash(git commit *)` — コミット
- `Bash(git push origin feature/*)` — feature ブランチへのプッシュ

### ask（確認が必要）
- `Bash(git push origin main)` — main ブランチへのプッシュ
- `Bash(alembic upgrade *)` — DBマイグレーション実行
- `Bash(docker *)` — Docker操作

### deny（絶対NG）
- `Read(./.env)` — 環境変数ファイルの読み取り
- `Read(./secrets/**)` — シークレットファイルの読み取り
- `Write(./.env)` — 環境変数ファイルへの書き込み
- `Write(./secrets/**)` — シークレットファイルへの書き込み
- `Bash(vercel --prod *)` — 本番デプロイ（Cursor のみ）

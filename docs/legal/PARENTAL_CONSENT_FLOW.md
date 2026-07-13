# 保護者同意フロー 要件定義（ドラフト / 未レビュー）

> **重要**: 電子的同意の法的有効性は弁護士確認が必要（外販ロードマップ D #32）。
> **作成日**: 2026-07-13

## 目的

18歳未満の選手のデータ取得・スカウト公開にあたり、**親権者の有効な同意**を電子的に取得・記録する。

## 現状の実装

- `User.birth_date` から年齢算出、`User.parental_consent`(bool) を保持。
- 未成年かつ `parental_consent=False` はスカウト検索・詳細から除外（`scout_service._is_publicly_visible`）。
- 登録時に未成年は同意フラグが必要（`auth_service` の 422 バリデーション）。

## 不足（実装すべき要件）

1. **同意主体の確認**: 誰が同意したか（親権者の氏名・続柄・メール）を記録する。
   - 追加案: `ParentalConsent` テーブル（user_id, guardian_name, relation, email, consented_at, method, ip, revoked_at）
2. **同意の証跡**: 同意日時・IP・同意文言のバージョンを保存（後から「何に同意したか」を再現可能に）。
3. **二段階確認**: 選手登録 → 保護者メールへ確認リンク → 保護者が承認して初めて `parental_consent=True`。
4. **撤回**: 保護者はいつでも撤回でき、撤回で即座に非公開化＋削除請求導線。
5. **同意文言のバージョン管理**: 規約改定時は再同意を要求。

## フロー（案）

```
選手(未成年)が登録
  ↓ 保護者メール入力
確認メール送信（トークン付きリンク・有効期限あり）
  ↓ 保護者がリンクを開く
同意画面（取得データ・利用目的・公開範囲・撤回方法を明示）
  ↓ 同意
ParentalConsent 記録 + user.parental_consent=True
  ↓
以降スカウト公開が可能（本人が公開設定した場合）
```

## データモデル案

```
ParentalConsent
- id: uuid
- user_id: uuid (FK, 選手)
- guardian_name: str
- relation: str  # 父/母/その他親権者
- guardian_email: str
- consent_version: str  # 同意文言バージョン
- method: str  # email_link 等
- consented_at: datetime
- ip_address: str | None
- revoked_at: datetime | None
```

## API 案

- `POST /api/consent/request` — 保護者へ確認メール送信
- `POST /api/consent/confirm` — トークンで承認、記録作成
- `POST /api/consent/revoke` — 撤回（本人/保護者）

## 弁護士確認事項

- [ ] メールリンク方式で親権者同意として法的に十分か
- [ ] 親権者本人性の確認をどこまで求めるべきか
- [ ] 撤回時のデータ削除の範囲・期限
- [ ] 同意文言に必須の記載事項

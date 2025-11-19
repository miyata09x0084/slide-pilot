# Supabase RLS (Row Level Security) セットアップガイド

## 概要

このプロジェクトでは、Supabase RLSポリシーを使用してスライドデータへのアクセス制御を行います。

## RLSポリシー構成

### 本番環境（推奨構成）

| ポリシー名 | Role | Command | 説明 |
|----------|------|---------|------|
| `Sample slides are viewable by everyone` | public | SELECT | サンプルスライド（`user_id = 00000000-...`）は全員が閲覧可能 |
| `Users can read own slides` | authenticated | SELECT | 認証ユーザーは自分のスライドのみ読取可能 |
| `Users can insert own slides` | authenticated | INSERT | 認証ユーザーは自分のスライドのみ作成可能 |
| `Users can update own slides` | authenticated | UPDATE | 認証ユーザーは自分のスライドのみ更新可能 |
| `Users can delete own slides` | authenticated | DELETE | 認証ユーザーは自分のスライドのみ削除可能 |

### 開発環境（オプション）

開発中は以下のポリシーを追加することで、全スライドへのアクセスを許可できます:

| ポリシー名 | Role | Command | 説明 |
|----------|------|---------|------|
| `Enable read access for all users` | public | SELECT | 全スライドが全員から読み取り可能（⚠️ 開発用のみ） |
| `Enable insert for all users` | public | INSERT | 全員が挿入可能（⚠️ 開発用のみ） |

**⚠️ 警告:** 開発用ポリシーは本番環境デプロイ前に必ず削除してください。

## セットアップ手順

### 1. サンプルスライド用RLSポリシー追加

```bash
# Supabase SQL Editorで実行
cat backend/scripts/add_sample_rls_policy.sql
```

または、以下のSQLを直接実行:

```sql
CREATE POLICY "Sample slides are viewable by everyone"
ON public.slides
FOR SELECT
USING (user_id::text = '00000000-0000-0000-0000-000000000000');
```

### 2. サンプルデータ投入

```bash
cd backend
python3 scripts/seed_sample_slides.py
```

**投入されるサンプル:**
- 多言語AIで文書解析（UUID: `11111111-1111-1111-1111-111111111111`）
- 2Dと3Dで学ぶ空間理解（UUID: `22222222-2222-2222-2222-222222222222`）

### 3. 本番デプロイ前のクリーンアップ

```bash
# Supabase SQL Editorで実行
cat backend/scripts/cleanup_rls_policies.sql
```

または、以下のSQLを直接実行:

```sql
-- 開発用ポリシーを削除
DROP POLICY IF EXISTS "Enable read access for all users" ON public.slides;
DROP POLICY IF EXISTS "Enable insert for all users" ON public.slides;
```

## 動作確認

### ポリシー一覧確認

```sql
SELECT
  policyname,
  roles,
  cmd,
  qual
FROM pg_policies
WHERE tablename = 'slides'
ORDER BY policyname;
```

### サンプルスライドアクセステスト

```sql
-- サンプルスライドが取得できることを確認
SELECT id, title, user_id
FROM public.slides
WHERE user_id::text = '00000000-0000-0000-0000-000000000000';
```

期待される結果: 2件のサンプルスライドが返される

### 認証ユーザースライドアクセステスト

```sql
-- 認証ユーザーのスライドのみ取得できることを確認
-- （auth.uid()は実際の認証ユーザーIDに置き換え）
SELECT id, title, user_id
FROM public.slides
WHERE user_id = auth.uid()::text;
```

## トラブルシューティング

### エラー: `operator does not exist: text = uuid`

**原因:** UUID型のカラムと文字列を直接比較している

**解決策:** 明示的に型キャスト
```sql
-- ❌ NG
user_id = '00000000-0000-0000-0000-000000000000'::uuid

-- ✅ OK
user_id::text = '00000000-0000-0000-0000-000000000000'
```

### サンプルスライドが表示されない

**確認事項:**
1. RLSポリシーが正しく追加されているか確認
   ```sql
   SELECT * FROM pg_policies WHERE policyname = 'Sample slides are viewable by everyone';
   ```

2. サンプルデータが投入されているか確認
   ```sql
   SELECT * FROM slides WHERE user_id::text = '00000000-0000-0000-0000-000000000000';
   ```

3. RLSが有効化されているか確認
   ```sql
   SELECT relname, relrowsecurity FROM pg_class WHERE relname = 'slides';
   ```

### 他人のスライドが見えてしまう

**原因:** 開発用ポリシー `Enable read access for all users` が残っている

**解決策:**
```sql
DROP POLICY "Enable read access for all users" ON public.slides;
```

## セキュリティベストプラクティス

1. **本番環境では開発用ポリシーを削除**
   - `Enable read access for all users`
   - `Enable insert for all users`

2. **認証必須の原則**
   - 通常のスライドは `authenticated` ロールのみアクセス可能
   - サンプルスライドのみ `public` ロールでアクセス可能

3. **最小権限の原則**
   - ユーザーは自分のスライドのみ操作可能
   - `auth.uid()` で厳密にユーザー識別

4. **定期的なポリシー監査**
   ```sql
   -- 全ポリシーを確認
   SELECT * FROM pg_policies WHERE tablename = 'slides';
   ```

## 参考資料

- [Supabase RLS ドキュメント](https://supabase.com/docs/guides/auth/row-level-security)
- [PostgreSQL RLS ドキュメント](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)

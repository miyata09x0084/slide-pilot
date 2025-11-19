-- Supabase RLSポリシー クリーンアップ
-- 本番環境デプロイ前に実行してください

-- 開発用の緩いポリシーを削除（セキュリティリスク）
DROP POLICY IF EXISTS "Enable read access for all users" ON public.slides;
DROP POLICY IF EXISTS "Enable insert for all users" ON public.slides;

-- 確認: 最終的なポリシー一覧を表示
SELECT
  policyname,
  roles,
  cmd,
  qual
FROM pg_policies
WHERE tablename = 'slides'
ORDER BY policyname;

-- 期待されるポリシー構成:
-- 1. "Sample slides are viewable by everyone" (public, SELECT) - サンプルスライドは全員閲覧可
-- 2. "Users can delete own slides" (authenticated, DELETE) - 自分のスライドのみ削除可
-- 3. "Users can insert own slides" (authenticated, INSERT) - 自分のスライドのみ作成可
-- 4. "Users can read own slides" (authenticated, SELECT) - 自分のスライドのみ読取可
-- 5. "Users can update own slides" (authenticated, UPDATE) - 自分のスライドのみ更新可

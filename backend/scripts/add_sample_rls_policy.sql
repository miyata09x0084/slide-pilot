-- サンプルスライドRLSポリシー追加
-- Supabase SQL Editor で実行してください

-- サンプルスライドを全員が読み取り可能にするポリシー
CREATE POLICY "Sample slides are viewable by everyone"
ON public.slides
FOR SELECT
USING (user_id = '00000000-0000-0000-0000-000000000000'::uuid);

-- 確認: 既存のポリシー一覧を表示
-- SELECT * FROM pg_policies WHERE tablename = 'slides';

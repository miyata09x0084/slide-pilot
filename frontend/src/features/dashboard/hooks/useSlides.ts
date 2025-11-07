/**
 * useSlides Hook
 * React Queryを使用してスライド一覧を取得
 */

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api-client';

// クエリキーの定義（キャッシュ管理とキャッシュ無効化に使用）
export const slidesKeys = {
  all: ['slides'] as const,
  lists: () => [...slidesKeys.all, 'list'] as const,
  list: (userId: string, limit?: number) =>
    [...slidesKeys.lists(), { userId, limit }] as const,
};

/**
 * スライド一覧を取得するカスタムフック
 * @param userId ユーザーのメールアドレス
 * @param limit 取得件数（デフォルト: 20）
 */
export function useSlides(userId: string, limit = 20) {
  return useQuery({
    queryKey: slidesKeys.list(userId, limit),
    queryFn: () => api.getSlides(userId, limit),
    enabled: !!userId, // userIdがある場合のみ実行
  });
}

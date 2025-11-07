/**
 * useSlideDetail Hook
 * React Queryを使用してスライド詳細を取得
 */

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api-client';

// クエリキーの定義
export const slideKeys = {
  all: ['slide'] as const,
  details: () => [...slideKeys.all, 'detail'] as const,
  detail: (id: string) => [...slideKeys.details(), id] as const,
};

/**
 * スライド詳細を取得するカスタムフック
 * @param slideId スライドID
 */
export function useSlideDetail(slideId: string) {
  return useQuery({
    queryKey: slideKeys.detail(slideId),
    queryFn: () => api.getSlideDetail(slideId),
    enabled: !!slideId, // slideIdがある場合のみ実行
  });
}

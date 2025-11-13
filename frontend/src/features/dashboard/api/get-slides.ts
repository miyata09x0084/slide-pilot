/**
 * API: Get Slides
 * Fetches user's slide history
 *
 * Issue: Supabase Auth統合（JWT自動送信対応）
 */

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api-client';
import type { Slide } from '@/types';

// API response type
interface GetSlidesResponse {
  slides: Slide[];
  message: string;
}

// Query parameters
interface GetSlidesParams {
  limit?: number;
}

// クエリキーの定義（キャッシュ管理とキャッシュ無効化に使用）
export const slidesKeys = {
  all: ['slides'] as const,
  lists: () => [...slidesKeys.all, 'list'] as const,
  list: (userEmail: string, limit?: number) =>
    [...slidesKeys.lists(), { userEmail, limit }] as const,
};

/**
 * Fetches slides from the API
 * User ID is automatically extracted from JWT by backend
 * api-client の response interceptor が response.data を返すため、
 * 戻り値はすでに GetSlidesResponse 型
 */
export const getSlides = async (params: GetSlidesParams = {}): Promise<GetSlidesResponse> => {
  const { limit = 20 } = params;
  return api.get('/slides', {
    params: { limit },
  });
};

/**
 * Custom hook to fetch slides
 */
export const useSlides = (params: GetSlidesParams = {}, options?: { enabled?: boolean }) => {
  return useQuery({
    queryKey: ['slides', params.limit],
    queryFn: () => getSlides(params),
    ...options,
  });
};

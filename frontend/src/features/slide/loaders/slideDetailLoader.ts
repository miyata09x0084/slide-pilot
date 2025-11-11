/**
 * slideDetailLoader - React Router Loader with React Query prefetch
 * ページ遷移前にスライド詳細をReact Queryキャッシュにプリフェッチ
 */

import type { LoaderFunctionArgs } from 'react-router-dom';
import { QueryClient } from '@tanstack/react-query';
import { getSlideDetail } from '../api/get-slide-detail';

export const createSlideDetailLoader = (queryClient: QueryClient) => {
  return async ({ params }: LoaderFunctionArgs) => {
    const { slideId } = params;

    if (!slideId) {
      throw new Error('Slide ID is required');
    }

    // React Queryキャッシュにプリフェッチ
    // prefetchQueryはエラーを無視するため、try-catchは不要
    await queryClient.prefetchQuery({
      queryKey: ['slide', slideId],
      queryFn: () => getSlideDetail(slideId),
    });

    return null;
  };
};

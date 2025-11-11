/**
 * API: Get Slide Detail
 * Fetches slide details including markdown content
 */

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api-client';

// Slide detail type definition
export interface SlideDetail {
  id: string;
  title: string;
  topic: string;
  created_at: string;
  pdf_url?: string;
  markdown?: string;
}

// API response type
interface GetSlideDetailResponse {
  slide_id: string;
  title: string;
  created_at: string;
  pdf_url?: string;
  markdown?: string;
}

/**
 * Fetches slide detail from the API
 */
export const getSlideDetail = async (slideId: string): Promise<SlideDetail> => {
  const data: GetSlideDetailResponse = await api.get(`/slides/${slideId}/markdown`);

  // Transform API response to SlideDetail type
  return {
    id: data.slide_id,
    title: data.title,
    topic: data.title, // Use title as topic fallback
    created_at: data.created_at,
    pdf_url: data.pdf_url,
    markdown: data.markdown,
  };
};

/**
 * Custom hook to fetch slide detail
 */
export const useSlideDetail = (slideId: string, options?: { enabled?: boolean }) => {
  return useQuery({
    queryKey: ['slide', slideId],
    queryFn: () => getSlideDetail(slideId),
    ...options,
  });
};

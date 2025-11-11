/**
 * API: Get Slides
 * Fetches user's slide history
 */

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api-client';
import type { Slide } from '@/types';

// API response type
interface GetSlidesResponse {
  slides: Slide[];
}

// Query parameters
interface GetSlidesParams {
  user_id: string;
  limit?: number;
}

/**
 * Fetches slides from the API
 */
export const getSlides = async (params: GetSlidesParams): Promise<GetSlidesResponse> => {
  const { user_id, limit = 20 } = params;
  return api.get('/slides', {
    params: { user_id, limit },
  });
};

/**
 * Custom hook to fetch slides
 */
export const useSlides = (params: GetSlidesParams, options?: { enabled?: boolean }) => {
  return useQuery({
    queryKey: ['slides', params.user_id, params.limit],
    queryFn: () => getSlides(params),
    ...options,
  });
};

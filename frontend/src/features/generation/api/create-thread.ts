/**
 * API: Create Thread
 * Creates a new LangGraph thread for agent conversation
 */

import { useMutation } from '@tanstack/react-query';
import { api } from '@/lib/api-client';

interface CreateThreadParams {
  metadata?: {
    user_email: string;
    created_from: string;
    created_at: string;
  };
}

interface CreateThreadResponse {
  thread_id: string;
}

/**
 * Creates a new thread
 */
export const createThread = async (params: CreateThreadParams): Promise<CreateThreadResponse> => {
  return api.post('/agent/threads', params);
};

/**
 * Custom hook to create a thread
 */
export const useCreateThread = () => {
  return useMutation({
    mutationFn: createThread,
  });
};

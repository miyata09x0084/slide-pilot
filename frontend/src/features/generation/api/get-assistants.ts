/**
 * API: Get Assistants
 * Fetches available LangGraph assistants
 */

import { api } from '@/lib/api-client';

interface Assistant {
  assistant_id: string;
  graph_id: string;
  config: Record<string, unknown>;
  created_at: string;
  metadata: Record<string, unknown>;
}

interface GetAssistantsParams {
  limit?: number;
}

/**
 * Fetches assistants from the API
 */
export const getAssistants = async (params: GetAssistantsParams = {}): Promise<Assistant[]> => {
  return api.post('/agent/assistants/search', params);
};

/**
 * Finds a specific assistant by graph_id
 */
export const findAssistantByGraphId = async (graphId: string): Promise<Assistant | null> => {
  const assistants = await getAssistants({ limit: 10 });
  return assistants.find(a => a.graph_id === graphId) || null;
};

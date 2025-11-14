/**
 * API: Submit Feedback
 * Submits user feedback (rating + comment) for a slide
 */

import { api } from '@/lib/api-client';

interface SubmitFeedbackRequest {
  slide_id: string;
  rating: number;
  comment?: string;
}

interface SubmitFeedbackResponse {
  success: boolean;
  message: string;
  feedback_id: string;
}

/**
 * Submits feedback to the API
 */
export const submitFeedback = async (
  request: SubmitFeedbackRequest
): Promise<SubmitFeedbackResponse> => {
  const data: SubmitFeedbackResponse = await api.post('/feedback', request);
  return data;
};

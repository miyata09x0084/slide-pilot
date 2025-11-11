/**
 * API: Upload PDF
 * Uploads a PDF file for slide generation
 */

import axios from 'axios';
import { env } from '@/config/env';

interface UploadPdfParams {
  file: File;
  user_id?: string;
}

interface UploadPdfResponse {
  path: string;
  filename: string;
}

/**
 * Uploads a PDF file
 * Note: Uses axios directly instead of api-client because FormData requires different handling
 */
export const uploadPdf = async (params: UploadPdfParams): Promise<UploadPdfResponse> => {
  const { file, user_id } = params;

  const formData = new FormData();
  formData.append('file', file);

  const url = user_id
    ? `${env.API_URL}/upload-pdf?user_id=${encodeURIComponent(user_id)}`
    : `${env.API_URL}/upload-pdf`;

  const response = await axios.post(url, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
};

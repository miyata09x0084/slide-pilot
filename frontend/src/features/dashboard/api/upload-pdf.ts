/**
 * API: Upload PDF
 * Uploads a PDF file for slide generation
 *
 * Issue: Supabase Auth統合（JWT自動送信対応）
 */

import { api } from '@/lib/api-client';

interface UploadPdfParams {
  file: File;
}

interface UploadPdfResponse {
  status: string;
  path: string;
  url: string;
  filename: string;
  size: number;
}

/**
 * Uploads a PDF file
 * JWT authentication is automatically added by api-client interceptor
 */
export const uploadPdf = async (params: UploadPdfParams): Promise<UploadPdfResponse> => {
  const { file } = params;

  const formData = new FormData();
  formData.append('file', file);

  // api-client の interceptor が JWT を自動付与
  // api-client の response interceptor が response.data を返すため、
  // 戻り値はすでに UploadPdfResponse 型
  return api.post('/upload-pdf', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
};

/**
 * 動画ジョブステータス取得API
 *
 * Cloud Run Jobで非同期生成中の動画のステータスをポーリングする。
 */

import { env } from '@/config/env';
import type { VideoJobStatus } from '@/types';

export async function getVideoStatus(jobId: string): Promise<VideoJobStatus> {
  const response = await fetch(`${env.API_URL}/video/status/${jobId}`);

  if (!response.ok) {
    throw new Error(`Failed to get video status: ${response.statusText}`);
  }

  return response.json();
}

/**
 * 動画ジョブステータス取得API
 *
 * Cloud Run Jobで非同期生成中の動画のステータスをポーリングする。
 */

import { api } from '@/lib/api-client';
import type { VideoJobStatus } from '@/types';

export async function getVideoStatus(jobId: string): Promise<VideoJobStatus> {
  return api.get(`/video/status/${jobId}`);
}

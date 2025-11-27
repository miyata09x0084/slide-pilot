/**
 * サンプルスライド取得API
 *
 * 新規ユーザー向けにサンプルスライド一覧を取得
 * バックエンドAPIから動的に取得（user_id = 00000000-... のスライド）
 */
import { useQuery } from "@tanstack/react-query";
import { env } from "@/config/env";

export interface Sample {
  id: string;
  title: string;
  topic: string;
  created_at: string;
  pdf_url?: string;
  video_url?: string;
}

interface SamplesResponse {
  samples: Sample[];
}

/**
 * サンプルスライド一覧を取得するReact Query Hook
 *
 * バックエンドの GET /samples から動的に取得
 * user_id = 00000000-0000-0000-0000-000000000000 のスライドが返される
 *
 * @param options - useQueryオプション
 * @returns サンプルスライドデータとクエリステータス
 */
export const useSamples = (options?: { enabled?: boolean }) => {
  return useQuery<SamplesResponse>({
    queryKey: ["samples"],
    queryFn: async () => {
      const response = await fetch(`${env.API_URL}/samples`);
      if (!response.ok) {
        throw new Error("Failed to fetch samples");
      }
      return response.json();
    },
    staleTime: 5 * 60 * 1000, // 5分キャッシュ
    ...options,
  });
};

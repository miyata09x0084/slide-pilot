/**
 * サンプルスライド取得API
 *
 * 新規ユーザー向けにサンプルスライド一覧を取得
 */
import { useQuery } from "@tanstack/react-query";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8001";

export interface Sample {
  id: string;
  title: string;
  pdf_path: string;
  md_path: string;
  created_at: string;
  is_sample: boolean;
}

interface SamplesResponse {
  samples: Sample[];
}

/**
 * サンプルスライド一覧を取得するReact Query Hook
 *
 * @param options - useQueryオプション
 * @returns サンプルスライドデータとクエリステータス
 */
export const useSamples = (options?: { enabled?: boolean }) => {
  return useQuery<SamplesResponse>({
    queryKey: ["samples"],
    queryFn: async () => {
      const response = await fetch(`${API_BASE_URL}/api/samples`);
      if (!response.ok) {
        throw new Error("Failed to fetch samples");
      }
      return response.json();
    },
    staleTime: Infinity, // サンプルは静的なので無期限キャッシュ
    ...options,
  });
};

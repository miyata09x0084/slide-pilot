/**
 * サンプルスライド取得API
 *
 * 新規ユーザー向けにサンプルスライド一覧を取得
 * サンプルスライドはSupabaseに実データとして登録済み（固定UUID）
 */
import { useQuery } from "@tanstack/react-query";

export interface Sample {
  id: string;
  title: string;
  topic: string;
  created_at: string;
  pdf_url?: string;
}

interface SamplesResponse {
  samples: Sample[];
}

// 固定サンプルスライドID（Supabaseに登録済み）
const SAMPLE_SLIDE_IDS = [
  "11111111-1111-1111-1111-111111111111",  // 多言語AIで文書解析
  "22222222-2222-2222-2222-222222222222",  // 2Dと3Dで学ぶ空間理解
];

/**
 * サンプルスライド一覧を取得するReact Query Hook
 *
 * 固定UUIDのリストを返す（実データはSupabaseに存在）
 * 詳細取得は通常のslideAPI (`/slides/{id}/markdown`) を使用
 *
 * @param options - useQueryオプション
 * @returns サンプルスライドデータとクエリステータス
 */
export const useSamples = (options?: { enabled?: boolean }) => {
  return useQuery<SamplesResponse>({
    queryKey: ["samples"],
    queryFn: async () => {
      // 固定UUIDのリストを返す（実データはSupabaseに存在）
      return {
        samples: [
          {
            id: SAMPLE_SLIDE_IDS[0],
            title: "多言語AIで文書解析",
            topic: "多言語AIで文書解析",
            created_at: "2025-01-15T00:00:00Z",
          },
          {
            id: SAMPLE_SLIDE_IDS[1],
            title: "2Dと3Dで学ぶ空間理解",
            topic: "2Dと3Dで学ぶ空間理解",
            created_at: "2025-01-15T00:00:00Z",
          },
        ],
      };
    },
    staleTime: Infinity, // サンプルは静的なので無期限キャッシュ
    ...options,
  });
};

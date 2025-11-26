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
  description?: string; // サンプルの説明文
  readTime?: string;    // 読了時間の目安
}

interface SamplesResponse {
  samples: Sample[];
}

// 固定サンプルスライドID（Supabaseに登録済み・動画付き）
const SAMPLE_SLIDE_IDS = [
  "4f16150c-4576-4495-b7cd-6293caff9b3f",  // 新時代のAI技術
  "91997e40-ff18-45fc-b106-e5d568fd5725",  // 未来予測AI
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
            title: "新時代のAI技術",
            topic: "新時代のAI技術",
            created_at: "2025-11-26T00:00:00Z",
            description: "Kimi Linearの革新的な技術を対話形式で理解",
            readTime: "3分",
          },
          {
            id: SAMPLE_SLIDE_IDS[1],
            title: "未来予測AI",
            topic: "未来予測AI",
            created_at: "2025-11-26T00:00:00Z",
            description: "TimeGPTで未来を予測する仕組みを解説",
            readTime: "3分",
          },
        ],
      };
    },
    staleTime: Infinity, // サンプルは静的なので無期限キャッシュ
    ...options,
  });
};

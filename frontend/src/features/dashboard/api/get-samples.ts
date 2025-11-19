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

// 固定サンプルスライドID（Supabaseに登録済み）
const SAMPLE_SLIDE_IDS = [
  "11111111-1111-1111-1111-111111111111",  // 速いAIの秘密
  "22222222-2222-2222-2222-222222222222",  // AIアートの秘密
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
            title: "速いAIの秘密",
            topic: "速いAIの秘密",
            created_at: "2025-01-15T00:00:00Z",
            description: "Kimi Linearの仕組みを対話形式で理解",
            readTime: "3分",
          },
          {
            id: SAMPLE_SLIDE_IDS[1],
            title: "AIアートの秘密",
            topic: "AIアートの秘密",
            created_at: "2025-01-15T00:00:00Z",
            description: "ComfyUI-Copilotの使い方を初心者向けに解説",
            readTime: "3分",
          },
        ],
      };
    },
    staleTime: Infinity, // サンプルは静的なので無期限キャッシュ
    ...options,
  });
};

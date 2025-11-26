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
  "862ae7f8-793f-4a39-9c7c-a003659b213c",  // 疑似科学を見抜く力（最新）
  "743cb44b-8546-47f9-bd91-2caebb423dab",  // 映画制作の未来
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
            title: "疑似科学を見抜く力",
            topic: "疑似科学を見抜く力",
            created_at: "2025-11-26T06:54:35Z",
            description: "科学的に見せかけた誤情報を見抜くスキルを解説",
            readTime: "3分",
          },
          {
            id: SAMPLE_SLIDE_IDS[1],
            title: "映画制作の未来",
            topic: "映画制作の未来",
            created_at: "2025-11-26T02:18:22Z",
            description: "AIが変える映画制作の世界を対話形式で理解",
            readTime: "3分",
          },
          {
            id: SAMPLE_SLIDE_IDS[2],
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

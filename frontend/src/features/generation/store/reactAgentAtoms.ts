/**
 * Recoil Atoms for React Agent State Management
 * DashboardPage と GenerationProgressPage で状態を共有するためのグローバルステート
 */

import { atom } from 'recoil';
import type { Message } from '../../../components/ChatMessage';
import type { ThinkingStep } from '../components/ThinkingIndicator';
import type { SlideData } from '../hooks/useReactAgent';

// チャットメッセージ履歴
export const messagesAtom = atom<Message[]>({
  key: 'reactAgent/messages',
  default: [],
});

// 思考過程ステップ
export const thinkingStepsAtom = atom<ThinkingStep[]>({
  key: 'reactAgent/thinkingSteps',
  default: [],
});

// 思考中フラグ
export const isThinkingAtom = atom<boolean>({
  key: 'reactAgent/isThinking',
  default: false,
});

// スレッドID
export const threadIdAtom = atom<string | null>({
  key: 'reactAgent/threadId',
  default: null,
});

// エラー状態
export const errorAtom = atom<string | null>({
  key: 'reactAgent/error',
  default: null,
});

// スライドデータ（生成完了後の情報）
export const slideDataAtom = atom<SlideData>({
  key: 'reactAgent/slideData',
  default: {},
});

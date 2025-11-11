// ReActエージェントとの通信を管理するカスタムフック
// SSEストリーミングでメッセージ送受信と思考過程を取得
// Recoilでグローバル状態管理（ページ間で状態共有）

import { useCallback } from 'react';
import { useRecoilState } from 'recoil';
import type { Message } from '@/types';
import {
  messagesAtom,
  thinkingStepsAtom,
  isThinkingAtom,
  threadIdAtom,
  errorAtom,
  slideDataAtom,
} from '../store/reactAgentAtoms';
import { createThread } from '../api/create-thread';
import { findAssistantByGraphId } from '../api/get-assistants';
import { env } from '@/config/env';

// SSE用のAPI URL（fetchで直接呼び出す）
const API_BASE_URL = `${env.API_URL}/agent`;

export function useReactAgent() {
  const [messages, setMessages] = useRecoilState(messagesAtom);
  const [thinkingSteps, setThinkingSteps] = useRecoilState(thinkingStepsAtom);
  const [isThinking, setIsThinking] = useRecoilState(isThinkingAtom);
  const [threadId, setThreadId] = useRecoilState(threadIdAtom);
  const [error, setError] = useRecoilState(errorAtom);
  const [slideData, setSlideData] = useRecoilState(slideDataAtom);

  // スライド生成中フラグ（ローカル変数で管理）
  // @ts-ignore - Used in closure but TypeScript doesn't detect it
  let _isGeneratingSlides = false;

  // スレッド作成
  const createThreadHandler = useCallback(async () => {
    try {
      // ユーザー情報取得（localStorage から）
      const user = JSON.parse(localStorage.getItem('user') || '{}');
      const userEmail = user.email || 'anonymous@example.com';

      const data = await createThread({
        metadata: {
          user_email: userEmail,
          created_from: 'web_ui',
          created_at: new Date().toISOString()
        }
      });

      setThreadId(data.thread_id);
      setError(null);
      return data.thread_id;
    } catch (err: any) {
      setError(err.message);
      throw err;
    }
  }, []);

  // メッセージ送信（オプションでスレッドIDを渡せる）
  const sendMessage = useCallback(async (content: string, customThreadId?: string) => {
    const activeThreadId = customThreadId || threadId;
    if (!activeThreadId) {
      throw new Error('Thread not created. Call createThread() first.');
    }

    // ユーザーメッセージを即座に表示
    const userMessage: Message = { role: 'user', content };
    setMessages(prev => [...prev, userMessage]);
    setIsThinking(true);
    setThinkingSteps([]);
    setError(null);
    _isGeneratingSlides = false; // スライド生成フラグをリセット

    try {
      // assistant_id取得（react-agentを明示的に探す）
      const reactAgent = await findAssistantByGraphId('react-agent');
      if (!reactAgent) {
        throw new Error('ReAct agent not found. Please check LangGraph configuration.');
      }

      const assistantId = reactAgent.assistant_id;

      // メッセージ履歴を構築（現在のメッセージ含む）
      const allMessages = [...messages, userMessage];

      // ──────────────────────────────────────────────────────────────
      // ユーザー情報取得（Issue #24: Supabase統合）
      // ──────────────────────────────────────────────────────────────
      const user = JSON.parse(localStorage.getItem('user') || '{}');
      const userEmail = user.email || 'anonymous@example.com';

      // SSEストリーミング開始
      const response = await fetch(`${API_BASE_URL}/threads/${activeThreadId}/runs/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-Email': userEmail  // ユーザー識別ヘッダー
        },
        body: JSON.stringify({
          assistant_id: assistantId,
          input: {
            messages: allMessages.map(m => ({ role: m.role, content: m.content }))
          },
          stream_mode: ['updates', 'messages']
        })
      });

      if (!response.ok) throw new Error(`Stream failed: ${response.statusText}`);

      // SSEレスポンスを処理
      const reader = response.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let assistantResponse = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const json = JSON.parse(line.slice(6));

              // LangGraphは配列を直接返す (messages mode)
              if (Array.isArray(json)) {
                json.forEach((msg: any) => {
                  if (msg.type === 'ai' && msg.content) {
                    // AIメッセージの最終contentを保存
                    assistantResponse = msg.content;

                    // ツール呼び出しがあれば思考ステップに追加
                    if (msg.tool_calls && msg.tool_calls.length > 0) {
                      msg.tool_calls.forEach((call: any) => {
                        // generate_slidesツールの場合は1回だけ表示
                        if (call.name === 'generate_slides') {
                          _isGeneratingSlides = true;
                          setThinkingSteps(prev => {
                            // 既に表示済みなら追加しない
                            const alreadyExists = prev.some(step =>
                              step.content.includes('スライド生成中')
                            );
                            if (alreadyExists) return prev;

                            return [...prev, {
                              type: 'action',
                              content: 'スライド生成中（AI情報の収集・分析・評価）...'
                            }];
                          });
                        } else {
                          setThinkingSteps(prev => [...prev, {
                            type: 'action',
                            content: `${call.name}を実行中...`
                          }]);
                        }
                      });
                    }
                  } else if (msg.type === 'tool') {
                    // ツール実行結果の処理

                    // スライド生成ツールの結果からファイルパスを抽出
                    if ((msg.name === 'generate_slides' || msg.name === 'generate_slidev_test' || msg.name === 'generate_slidev_mvp1') && msg.content) {
                      _isGeneratingSlides = false; // スライド生成完了

                      try {
                        // ツール結果をパース（JSON文字列の場合）
                        const result = typeof msg.content === 'string'
                          ? JSON.parse(msg.content)
                          : msg.content;

                        if (result.slide_path || result.path) {
                          setSlideData({
                            path: result.slide_path || result.path,
                            title: result.title || 'スライド',
                            slide_id: result.slide_id,     // Supabase ID（Issue #24）
                            pdf_url: result.pdf_url        // Supabase公開URL（Issue #24）
                          });

                          // 完了メッセージを追加
                          setThinkingSteps(prev => [...prev, {
                            type: 'observation',
                            content: 'スライド生成完了'
                          }]);
                        }
                      } catch (e) {
                        console.warn('Failed to parse slide data:', e);
                      }
                    }
                  }
                });
              }
              // オブジェクト形式の場合（updatesモード用の予備処理）
              else if (typeof json === 'object' && json.data) {
                parseReActSteps(json.data);
              }
            } catch (e) {
              console.warn('❌ SSE parse error:', e);
              console.warn('Failed line:', line);
            }
          }
        }
      }

      // アシスタントの応答をメッセージに追加
      if (assistantResponse) {
        const assistantMessage: Message = { role: 'assistant', content: assistantResponse };
        setMessages(prev => [...prev, assistantMessage]);
      }

      setIsThinking(false);
      setThinkingSteps([]);
    } catch (err: any) {
      setError(err.message);
      setIsThinking(false);
      setThinkingSteps([]);

      // エラーメッセージを表示
      const errorMessage: Message = {
        role: 'assistant',
        content: `エラーが発生しました: ${err.message}`
      };
      setMessages(prev => [...prev, errorMessage]);
    }
  }, [threadId, messages]);

  // ReActステップを解析して思考過程に追加
  const parseReActSteps = (data: any) => {
    // agent ノードのメッセージを抽出
    if (data.agent?.messages) {
      const agentMessages = Array.isArray(data.agent.messages)
        ? data.agent.messages
        : [data.agent.messages];

      agentMessages.forEach((msg: any) => {
        if (msg.type === 'ai') {
          // ツール呼び出しの場合
          if (msg.tool_calls && msg.tool_calls.length > 0) {
            msg.tool_calls.forEach((call: any) => {
              setThinkingSteps(prev => [...prev, {
                type: 'action',
                content: `${call.name}を実行中...`
              }]);
            });
          }
          // LLMの推論内容
          if (msg.content) {
            setThinkingSteps(prev => [...prev, {
              type: 'thinking',
              content: msg.content
            }]);
          }
        } else if (msg.type === 'tool') {
          // ツールの実行結果
          setThinkingSteps(prev => [...prev, {
            type: 'observation',
            content: msg.content || '実行完了'
          }]);
        }
      });
    }
  };

  // チャットリセット
  const resetChat = useCallback(() => {
    setMessages([]);
    setThinkingSteps([]);
    setIsThinking(false);
    setThreadId(null);
    setError(null);
    setSlideData({});
  }, []);

  return {
    messages,
    thinkingSteps,
    isThinking,
    threadId,
    error,
    slideData,
    createThread: createThreadHandler,
    sendMessage,
    resetChat
  };
}

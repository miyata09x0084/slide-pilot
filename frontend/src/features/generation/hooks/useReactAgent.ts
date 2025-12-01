// ReActエージェントとの通信を管理するカスタムフック
// SSEストリーミングでメッセージ送受信と思考過程を取得
// Recoilでグローバル状態管理（ページ間で状態共有）
// React Queryでキャッシュ無効化（動画生成完了時）
// Cloud Run Jobでの非同期動画生成ステータスポーリング

import { useCallback, useState, useRef, useEffect } from 'react';
import { useRecoilState } from 'recoil';
import { useQueryClient } from '@tanstack/react-query';
import type { Message } from '@/types';
import { slidesKeys } from '@/features/dashboard/api/get-slides';
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
import { getVideoStatus } from '../api/get-video-status';
import { env } from '@/config/env';
import { supabase } from '@/lib/supabase';

// SSE用のAPI URL（fetchで直接呼び出す）
const API_BASE_URL = `${env.API_URL}/agent`;

export function useReactAgent() {
  const [messages, setMessages] = useRecoilState(messagesAtom);
  const [thinkingSteps, setThinkingSteps] = useRecoilState(thinkingStepsAtom);
  const [isThinking, setIsThinking] = useRecoilState(isThinkingAtom);
  const [threadId, setThreadId] = useRecoilState(threadIdAtom);
  const [error, setError] = useRecoilState(errorAtom);
  const [slideData, setSlideData] = useRecoilState(slideDataAtom);
  const [cachedAssistantId, setCachedAssistantId] = useState<string | null>(null);
  const [isPollingVideo, setIsPollingVideo] = useState(false);

  // React Queryのクライアント（キャッシュ無効化用）
  const queryClient = useQueryClient();

  // 動画生成中フラグ（ローカル変数で管理）
  // @ts-ignore - Used in closure but TypeScript doesn't detect it
  let _isGeneratingVideo = false;

  // ポーリング用のref
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // コンポーネントアンマウント時にポーリングを停止
  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, []);

  // 動画ジョブステータスをポーリング
  const pollVideoStatus = useCallback(async (jobId: string) => {
    setIsPollingVideo(true);
    setThinkingSteps(prev => [...prev, {
      type: 'action',
      content: '動画生成中（バックグラウンド処理）...'
    }]);

    const poll = async () => {
      try {
        const status = await getVideoStatus(jobId);

        if (status.status === 'completed' && status.video_url) {
          // 完了
          if (pollingIntervalRef.current) {
            clearInterval(pollingIntervalRef.current);
            pollingIntervalRef.current = null;
          }
          setIsPollingVideo(false);

          setSlideData(prev => ({
            ...prev,
            video_url: status.video_url
          }));

          setThinkingSteps(prev => [...prev, {
            type: 'observation',
            content: '動画生成完了'
          }]);

          // 動画一覧のキャッシュを無効化
          const user = JSON.parse(localStorage.getItem('user') || '{}');
          if (user.email) {
            queryClient.invalidateQueries({
              queryKey: slidesKeys.list(user.email, 20),
            });
          }
        } else if (status.status === 'failed') {
          // 失敗
          if (pollingIntervalRef.current) {
            clearInterval(pollingIntervalRef.current);
            pollingIntervalRef.current = null;
          }
          setIsPollingVideo(false);

          setThinkingSteps(prev => [...prev, {
            type: 'observation',
            content: `動画生成エラー: ${status.error_message || '不明なエラー'}`
          }]);
        }
        // pending/processing の場合は継続
      } catch (e) {
        console.warn('Video status poll error:', e);
      }
    };

    // 即座に1回実行
    await poll();

    // 5秒間隔でポーリング
    pollingIntervalRef.current = setInterval(poll, 5000);
  }, [setSlideData, setThinkingSteps, queryClient]);

  // スレッド作成
  const createThreadHandler = useCallback(async () => {
    try {
      // 防御的プログラミング: 新しいスレッド作成時に古い状態をクリア
      setMessages([]);
      setThinkingSteps([]);
      setIsThinking(false);
      setError(null);
      setSlideData({});

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
      return data.thread_id;
    } catch (err: any) {
      setError(err.message);
      throw err;
    }
  }, [setThreadId, setError, setMessages, setThinkingSteps, setIsThinking, setSlideData]);

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
    _isGeneratingVideo = false; // 動画生成フラグをリセット

    try {
      // assistant_id取得（キャッシュを優先）
      let assistantId = cachedAssistantId;
      if (!assistantId) {
        const reactAgent = await findAssistantByGraphId('react-agent');
        if (!reactAgent) {
          throw new Error('ReAct agent not found. Please check LangGraph configuration.');
        }
        assistantId = reactAgent.assistant_id;
        setCachedAssistantId(assistantId);  // キャッシュに保存
      }

      // メッセージ履歴を構築（現在のメッセージ含む）
      const allMessages = [...messages, userMessage];

      // ──────────────────────────────────────────────────────────────
      // JWT取得（Issue #24: Supabase統合）
      // ──────────────────────────────────────────────────────────────
      const { data: { session } } = await supabase.auth.getSession();

      // SSEストリーミング開始
      const response = await fetch(`${API_BASE_URL}/threads/${activeThreadId}/runs/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(session?.access_token && { 'Authorization': `Bearer ${session.access_token}` })
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
                          _isGeneratingVideo = true;
                          setThinkingSteps(prev => {
                            // 既に表示済みなら追加しない
                            const alreadyExists = prev.some(step =>
                              step.content.includes('動画生成中')
                            );
                            if (alreadyExists) return prev;

                            return [...prev, {
                              type: 'action',
                              content: '動画生成中（AI情報の収集・分析・評価）...'
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

                    // 動画生成ツールの結果からファイルパスを抽出
                    if ((msg.name === 'generate_slides' || msg.name === 'generate_slidev_test' || msg.name === 'generate_slidev_mvp1') && msg.content) {
                      _isGeneratingVideo = false; // 動画生成完了

                      try {
                        // ツール結果をパース（JSON文字列の場合）
                        const result = typeof msg.content === 'string'
                          ? JSON.parse(msg.content)
                          : msg.content;

                        if (result.slide_path || result.path) {
                          setSlideData({
                            path: result.slide_path || result.path,
                            title: result.title || '動画',
                            slide_id: result.slide_id,     // Supabase ID（Issue #24）
                            pdf_url: result.pdf_url,       // Supabase公開URL（Issue #24）
                            video_url: result.video_url,   // 動画URL（同期版）
                            video_job_id: result.video_job_id  // Cloud Run Job ID（非同期版）
                          });

                          // 非同期動画生成の場合はポーリング開始
                          if (result.video_job_id && !result.video_url) {
                            pollVideoStatus(result.video_job_id);
                          } else {
                            // 同期版: 完了メッセージを追加
                            setThinkingSteps(prev => [...prev, {
                              type: 'observation',
                              content: '動画生成完了'
                            }]);

                            // 動画一覧のキャッシュを無効化（新しい動画を反映）
                            const user = JSON.parse(localStorage.getItem('user') || '{}');
                            if (user.email) {
                              queryClient.invalidateQueries({
                                queryKey: slidesKeys.list(user.email, 20),
                              });
                            }
                          }
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
  }, [cachedAssistantId, threadId, messages, setMessages, setThinkingSteps, setIsThinking, setError, setSlideData]);

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
    setIsPollingVideo(false);
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
  }, [setMessages, setThinkingSteps, setIsThinking, setThreadId, setError, setSlideData]);

  return {
    messages,
    thinkingSteps,
    isThinking,
    isPollingVideo,  // 動画生成ポーリング中フラグ
    threadId,
    error,
    slideData,
    createThread: createThreadHandler,
    sendMessage,
    resetChat
  };
}

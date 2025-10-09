// ReActエージェントとの通信を管理するカスタムフック
// SSEストリーミングでメッセージ送受信と思考過程を取得

import { useState, useCallback } from 'react';
import type { Message } from '../components/ChatMessage';
import type { ThinkingStep } from '../components/ThinkingIndicator';

const API_BASE_URL = 'http://localhost:2024';

export function useReactAgent() {
  const [messages, setMessages] = useState<Message[]>([]);        // チャット履歴
  const [thinkingSteps, setThinkingSteps] = useState<ThinkingStep[]>([]);  // 思考過程
  const [isThinking, setIsThinking] = useState(false);            // 思考中フラグ
  const [threadId, setThreadId] = useState<string | null>(null);  // スレッドID
  const [error, setError] = useState<string | null>(null);        // エラー状態

  // スレッド作成
  const createThread = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/threads`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });

      if (!res.ok) throw new Error(`Thread creation failed: ${res.statusText}`);

      const data = await res.json();
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

    try {
      // assistant_id取得
      const assistantRes = await fetch(`${API_BASE_URL}/assistants/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ limit: 1 })
      });

      if (!assistantRes.ok) throw new Error('Failed to get assistant');

      const assistants = await assistantRes.json();
      const assistantId = assistants[0]?.assistant_id;

      if (!assistantId) throw new Error('No assistant found');

      // メッセージ履歴を構築（現在のメッセージ含む）
      const allMessages = [...messages, userMessage];

      // SSEストリーミング開始
      const response = await fetch(`${API_BASE_URL}/threads/${activeThreadId}/runs/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
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
            console.log('📥 Raw SSE line:', line);
            try {
              const json = JSON.parse(line.slice(6));
              console.log('📦 Parsed JSON:', json);

              // LangGraphは配列を直接返す (messages mode)
              if (Array.isArray(json)) {
                json.forEach((msg: any) => {
                  if (msg.type === 'ai' && msg.content) {
                    // AIメッセージの最終contentを保存
                    assistantResponse = msg.content;

                    // ツール呼び出しがあれば思考ステップに追加
                    if (msg.tool_calls && msg.tool_calls.length > 0) {
                      msg.tool_calls.forEach((call: any) => {
                        setThinkingSteps(prev => [...prev, {
                          type: 'action',
                          content: `${call.name}を実行中...`
                        }]);
                      });
                    }
                  } else if (msg.type === 'tool') {
                    // ツール実行結果を思考ステップに追加
                    setThinkingSteps(prev => [...prev, {
                      type: 'observation',
                      content: msg.content || '実行完了'
                    }]);
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
  }, []);

  return {
    messages,
    thinkingSteps,
    isThinking,
    threadId,
    error,
    createThread,
    sendMessage,
    resetChat
  };
}

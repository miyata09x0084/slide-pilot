// メインアプリケーション
// チャット形式のUIでReActエージェントと対話

import { useState, useEffect, useRef } from 'react';
import type { CredentialResponse } from '@react-oauth/google';
import { jwtDecode } from 'jwt-decode';
import Login from './components/Login';
import ChatMessage from './components/ChatMessage';
import ChatInput from './components/ChatInput';
import ThinkingIndicator from './components/ThinkingIndicator';
import { useReactAgent } from './hooks/useReactAgent';

interface UserInfo {
  name: string;
  email: string;
  picture: string;
}

function App() {
  const [user, setUser] = useState<UserInfo | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // ReActエージェントのカスタムフック
  const {
    messages,
    thinkingSteps,
    isThinking,
    threadId,
    error,
    createThread,
    sendMessage,
    resetChat
  } = useReactAgent();

  // ログイン成功時の処理
  const handleLoginSuccess = (credentialResponse: CredentialResponse) => {
    if (credentialResponse.credential) {
      const decoded: any = jwtDecode(credentialResponse.credential);
      const userInfo: UserInfo = {
        name: decoded.name,
        email: decoded.email,
        picture: decoded.picture
      };
      setUser(userInfo);
      localStorage.setItem('user', JSON.stringify(userInfo));
    }
  };

  // ログアウト処理
  const handleLogout = () => {
    setUser(null);
    localStorage.removeItem('user');
    resetChat();
  };

  // ページロード時にlocalStorageから復元
  useEffect(() => {
    const savedUser = localStorage.getItem('user');
    if (savedUser) {
      setUser(JSON.parse(savedUser));
    }
  }, []);

  // 自動スクロール（新しいメッセージが追加された時）
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, thinkingSteps]);

  // ログインしていない場合はログイン画面を表示
  if (!user) {
    return <Login onSuccess={handleLoginSuccess} />;
  }

  // メッセージ送信処理
  const handleSendMessage = async (content: string) => {
    try {
      // threadIdがnullの場合のみcreateThread()を呼び出し、結果は必ずstring型
      const currentThreadId = threadId || await createThread();
      await sendMessage(content, currentThreadId);
    } catch (err) {
      console.error('Failed to send message:', err);
    }
  };

  // 新しいチャットを開始
  const handleNewChat = async () => {
    resetChat();
    try {
      await createThread();
    } catch (err) {
      console.error('Failed to create thread:', err);
    }
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100vh',
      background: '#f5f5f5',
      fontFamily: 'Arial, sans-serif'
    }}>
      {/* ヘッダー */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '16px 24px',
        background: 'white',
        borderBottom: '1px solid #dee2e6',
        boxShadow: '0 2px 4px rgba(0,0,0,0.05)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <h1 style={{ margin: 0, fontSize: '20px', color: '#333' }}>
            SlidePilot Chat
          </h1>
          {threadId && (
            <button
              onClick={handleNewChat}
              style={{
                padding: '6px 12px',
                fontSize: '13px',
                background: '#28a745',
                color: 'white',
                border: 'none',
                borderRadius: '5px',
                cursor: 'pointer'
              }}
            >
              新しいチャット
            </button>
          )}
        </div>

        {/* ユーザー情報 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <img
            src={user.picture}
            alt={user.name}
            style={{ width: '32px', height: '32px', borderRadius: '50%' }}
          />
          <div style={{ fontSize: '14px' }}>
            <div style={{ fontWeight: 'bold' }}>{user.name}</div>
          </div>
          <button
            onClick={handleLogout}
            style={{
              padding: '6px 12px',
              fontSize: '13px',
              background: '#dc3545',
              color: 'white',
              border: 'none',
              borderRadius: '5px',
              cursor: 'pointer'
            }}
          >
            ログアウト
          </button>
        </div>
      </div>

      {/* メインチャットエリア */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '24px',
        display: 'flex',
        flexDirection: 'column'
      }}>
        {/* スレッド未作成時の案内 */}
        {!threadId && messages.length === 0 && (
          <div style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '16px',
            color: '#6c757d'
          }}>
            <div style={{ fontSize: '48px' }}>💬</div>
            <h2 style={{ margin: 0, fontSize: '24px', color: '#333' }}>
              SlidePilotへようこそ
            </h2>
            <p style={{ margin: 0, textAlign: 'center', maxWidth: '400px' }}>
              AIがスライド生成やメール送信をお手伝いします。<br />
              下のメッセージ欄から会話を始めてください。
            </p>
            <div style={{
              marginTop: '16px',
              padding: '16px',
              background: '#e7f3ff',
              borderRadius: '8px',
              maxWidth: '500px'
            }}>
              <div style={{ fontWeight: 'bold', marginBottom: '8px', color: '#0056b3' }}>
                使用例:
              </div>
              <ul style={{ margin: 0, paddingLeft: '20px', color: '#495057' }}>
                <li>「AI最新情報のスライドを作って」</li>
                <li>「スライド作ってdev@example.comに送って」</li>
                <li>「OpenAIの最新情報を教えて」</li>
              </ul>
            </div>
          </div>
        )}

        {/* メッセージ履歴 */}
        {messages.map((message, index) => (
          <ChatMessage key={index} message={message} />
        ))}

        {/* 思考過程インジケーター */}
        <ThinkingIndicator steps={thinkingSteps} isActive={isThinking} />

        {/* エラー表示 */}
        {error && (
          <div style={{
            padding: '12px 16px',
            background: '#f8d7da',
            color: '#721c24',
            borderRadius: '8px',
            marginTop: '16px',
            border: '1px solid #f5c6cb'
          }}>
            ❌ エラー: {error}
          </div>
        )}

        {/* 自動スクロール用の参照 */}
        <div ref={messagesEndRef} />
      </div>

      {/* 入力欄 */}
      <ChatInput
        onSend={handleSendMessage}
        disabled={isThinking}
        placeholder={
          !threadId
            ? 'メッセージを入力してチャットを開始...'
            : isThinking
            ? 'AIが考え中...'
            : 'メッセージを入力...'
        }
      />
    </div>
  );
}

export default App;

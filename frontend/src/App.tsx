// メインアプリケーション（2モード対応: input/chat）
// PDFアップロード→自動スライド生成→チャット画面

import { useState, useEffect, useRef } from 'react';
import type { CredentialResponse } from '@react-oauth/google';
import { jwtDecode } from 'jwt-decode';
import Login from './components/Login';
import InitialInputForm from './components/InitialInputForm';
import ChatMessage from './components/ChatMessage';
import ChatInput from './components/ChatInput';
import ThinkingIndicator from './components/ThinkingIndicator';
import { SlideViewer } from './components/SlideViewer';
import { useReactAgent } from './hooks/useReactAgent';

interface UserInfo {
  name: string;
  email: string;
  picture: string;
}

type Mode = 'input' | 'chat';

function App() {
  const [user, setUser] = useState<UserInfo | null>(null);
  const [mode, setMode] = useState<Mode>('input');
  const [showSlideViewer, setShowSlideViewer] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // ReActエージェントのカスタムフック
  const {
    messages,
    thinkingSteps,
    isThinking,
    threadId,
    error,
    slideData,
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
    setMode('input');
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

  // PDFアップロード処理（初回入力画面から）
  const handlePdfUpload = async (path: string) => {
    console.log('📄 Starting slide generation from PDF:', path);

    try {
      // チャット画面に遷移
      setMode('chat');

      // スレッド作成
      const tid = await createThread();

      // PDFからスライド生成を自動実行
      await sendMessage(
        `このPDFから中学生向けのわかりやすいスライドを作成してください: ${path}`,
        tid
      );
    } catch (err) {
      console.error('❌ PDF処理エラー:', err);
    }
  };

  // YouTube URL送信処理（将来実装）
  const handleYoutubeSubmit = async (url: string) => {
    console.log('🎥 YouTube URL:', url);

    try {
      setMode('chat');
      const tid = await createThread();
      await sendMessage(
        `このYouTube動画から中学生向けのスライドを作成してください: ${url}`,
        tid
      );
    } catch (err) {
      console.error('❌ YouTube処理エラー:', err);
    }
  };

  // メッセージ送信処理
  const handleSendMessage = async (content: string) => {
    try {
      const currentThreadId = threadId || await createThread();
      await sendMessage(content, currentThreadId);
    } catch (err) {
      console.error('Failed to send message:', err);
    }
  };

  // 新しいスライドを作成（初回画面に戻る）
  const handleNewSlide = () => {
    resetChat();
    setMode('input');
  };

  // 初回入力画面
  if (mode === 'input') {
    return (
      <div style={{
        minHeight: '100vh',
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
          <h1 style={{ margin: 0, fontSize: '20px', color: '#333' }}>
            SlidePilot
          </h1>

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

        {/* 初回入力フォーム */}
        <InitialInputForm
          onPdfUpload={handlePdfUpload}
          onYoutubeSubmit={handleYoutubeSubmit}
        />
      </div>
    );
  }

  // チャット画面
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
          <button
            onClick={handleNewSlide}
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
            新しいスライドを作成
          </button>
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
        {/* メッセージ履歴 */}
        {messages.map((message, index) => (
          <ChatMessage key={index} message={message} />
        ))}

        {/* 思考過程インジケーター */}
        <ThinkingIndicator steps={thinkingSteps} isActive={isThinking} />

        {/* スライドダウンロード（Issue #24: Supabase統合対応） */}
        {slideData.path && (
          <div style={{
            margin: '16px 0',
            padding: '16px',
            background: '#d4edda',
            borderRadius: '12px',
            border: '1px solid #c3e6cb',
            textAlign: 'center'
          }}>
            <div style={{
              fontSize: '16px',
              fontWeight: 'bold',
              color: '#155724',
              marginBottom: '12px'
            }}>
              ✅ スライド生成完了
            </div>
            {slideData.title && (
              <div style={{
                fontSize: '14px',
                color: '#155724',
                marginBottom: '12px'
              }}>
                タイトル: {slideData.title}
              </div>
            )}

            {/* Supabase統合時: プレビュー + PDFダウンロード */}
            {slideData.slide_id ? (
              <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
                <button
                  onClick={() => setShowSlideViewer(true)}
                  style={{
                    padding: '10px 24px',
                    background: '#007bff',
                    color: 'white',
                    border: 'none',
                    borderRadius: '6px',
                    fontSize: '15px',
                    fontWeight: 'bold',
                    cursor: 'pointer',
                    transition: 'background 0.2s'
                  }}
                  onMouseOver={(e) => e.currentTarget.style.background = '#0056b3'}
                  onMouseOut={(e) => e.currentTarget.style.background = '#007bff'}
                >
                  📄 スライドを見る
                </button>
                {slideData.pdf_url && (
                  <a
                    href={slideData.pdf_url}
                    download
                    style={{
                      display: 'inline-block',
                      padding: '10px 24px',
                      background: '#28a745',
                      color: 'white',
                      textDecoration: 'none',
                      borderRadius: '6px',
                      fontSize: '15px',
                      fontWeight: 'bold',
                      transition: 'background 0.2s'
                    }}
                    onMouseOver={(e) => e.currentTarget.style.background = '#218838'}
                    onMouseOut={(e) => e.currentTarget.style.background = '#28a745'}
                  >
                    📥 PDFダウンロード
                  </a>
                )}
              </div>
            ) : (
              // ローカルのみ（Supabase未設定時）
              <a
                href={slideData.path}
                download
                style={{
                  display: 'inline-block',
                  padding: '10px 24px',
                  background: '#28a745',
                  color: 'white',
                  textDecoration: 'none',
                  borderRadius: '6px',
                  fontSize: '15px',
                  fontWeight: 'bold',
                  transition: 'background 0.2s'
                }}
                onMouseOver={(e) => e.currentTarget.style.background = '#218838'}
                onMouseOut={(e) => e.currentTarget.style.background = '#28a745'}
              >
                📥 スライドをダウンロード
              </a>
            )}
          </div>
        )}

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
          isThinking
            ? 'AIが考え中...'
            : 'スライド内容について質問してください...'
        }
      />

      {/* SlideViewerモーダル（Issue #24） */}
      {showSlideViewer && slideData.slide_id && (
        <SlideViewer
          slideId={slideData.slide_id}
          onClose={() => setShowSlideViewer(false)}
        />
      )}

      {/* レスポンシブ対応のCSS */}
      <style>{`
        @media (max-width: 768px) {
          h1 {
            font-size: 18px !important;
          }
          button {
            font-size: 12px !important;
            padding: 5px 10px !important;
          }
        }
      `}</style>
    </div>
  );
}

export default App;

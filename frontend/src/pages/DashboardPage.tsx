/**
 * DashboardPage
 * トップページ: PDFアップロード + スライド履歴表示
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { useReactAgent } from '../hooks/useReactAgent';
import InitialInputForm from '../components/InitialInputForm';
import { SlideHistory } from '../components/SlideHistory';
import { SlideViewer } from '../components/SlideViewer';

export default function DashboardPage() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { createThread, sendMessage } = useReactAgent();
  const [previewSlideId, setPreviewSlideId] = useState<string | null>(null);

  // ログアウト処理
  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  // PDFアップロード処理
  const handlePdfUpload = async (path: string) => {
    console.log('📄 Starting slide generation from PDF:', path);

    try {
      // スレッド作成
      const tid = await createThread();

      // 生成進行状況ページへ遷移
      navigate(`/generate/${tid}`, {
        state: { pdfPath: path }
      });

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
      const tid = await createThread();
      navigate(`/generate/${tid}`, {
        state: { youtubeUrl: url }
      });

      await sendMessage(
        `このYouTube動画から中学生向けのスライドを作成してください: ${url}`,
        tid
      );
    } catch (err) {
      console.error('❌ YouTube処理エラー:', err);
    }
  };

  // スライド履歴カードクリック
  const handleSlidePreview = (slideId: string) => {
    // Phase 1: モーダルプレビュー（既存機能）
    setPreviewSlideId(slideId);

    // Phase 3: スライド詳細ページへ遷移（将来実装）
    // navigate(`/slides/${slideId}`);
  };

  if (!user) {
    return null; // ProtectedRouteでリダイレクトされるので表示されない
  }

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

      {/* スライド履歴セクション */}
      <div style={{
        maxWidth: '1200px',
        margin: '40px auto',
        padding: '0 24px'
      }}>
        <h2 style={{
          fontSize: '20px',
          fontWeight: 600,
          marginBottom: '20px',
          color: '#333',
          display: 'flex',
          alignItems: 'center',
          gap: '8px'
        }}>
          <span>📚</span>
          <span>過去のスライド</span>
        </h2>
        <SlideHistory
          userEmail={user.email}
          onPreview={handleSlidePreview}
        />
      </div>

      {/* プレビューモーダル（履歴から開く） */}
      {previewSlideId && (
        <SlideViewer
          slideId={previewSlideId}
          onClose={() => setPreviewSlideId(null)}
        />
      )}
    </div>
  );
}

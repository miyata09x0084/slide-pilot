/**
 * SlideDetailPage (React Query対応、Phase 3最適化済み)
 * スライド詳細ページ - React Queryでデータ取得とキャッシュ管理
 * Phase 3: useCallback()でイベントハンドラーをメモ化
 */

import { useNavigate, useParams } from 'react-router-dom';
import { useCallback } from 'react';
import { useSlideDetail } from './hooks/useSlideDetail';
import SlideDetailLayout from './components/SlideDetailLayout';
import ChatPanel from './components/ChatPanel';
import { SlideContentViewer } from './components/SlideContentViewer';

const styles: Record<string, React.CSSProperties> = {
  container: {
    minHeight: '100vh',
    background: '#f5f5f5',
    fontFamily: 'Arial, sans-serif',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '16px 24px',
    background: 'white',
    borderBottom: '1px solid #dee2e6',
    boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
  },
  backButton: {
    padding: '8px 16px',
    fontSize: '13px',
    background: '#6c757d',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    fontWeight: '600',
    transition: 'background 0.2s',
  } as React.CSSProperties,
  title: {
    margin: 0,
    fontSize: '20px',
    color: '#333',
    fontWeight: 'bold',
  },
  actions: {
    display: 'flex',
    gap: '8px',
  },
  actionButton: {
    padding: '8px 16px',
    fontSize: '13px',
    background: '#28a745',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    fontWeight: '600',
    textDecoration: 'none',
    transition: 'background 0.2s',
    display: 'inline-block',
  } as React.CSSProperties,
  slideViewerWrapper: {
    height: '100%',
  },
};

// ホバースタイル（Phase 3: パフォーマンス最適化）
const hoverStyles = `
  .back-button:hover {
    background: #5a6268 !important;
  }

  .action-button:hover {
    background: #218838 !important;
  }
`;

export default function SlideDetailPage() {
  const { slideId } = useParams<{ slideId: string }>();
  const navigate = useNavigate();

  // React Queryでスライド詳細を取得（キャッシュあり）
  const { data: slide, isLoading, error } = useSlideDetail(slideId || '');

  // ナビゲーションハンドラー（メモ化）
  const handleBackToDashboard = useCallback(() => {
    navigate('/');
  }, [navigate]);

  // ローディング状態
  if (isLoading) {
    return (
      <div style={styles.container}>
        <div style={styles.header}>
          <button
            onClick={handleBackToDashboard}
            className="back-button"
            style={styles.backButton}
          >
            ← Dashboard
          </button>
        </div>
        <div style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          minHeight: 'calc(100vh - 64px)',
          flexDirection: 'column',
          gap: '16px'
        }}>
          <div style={{
            width: '48px',
            height: '48px',
            border: '4px solid #e5e7eb',
            borderTopColor: '#3b82f6',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite',
          }} />
          <div style={{ color: '#6b7280', fontSize: '14px' }}>読み込み中...</div>
          <style>{`
            @keyframes spin {
              to { transform: rotate(360deg); }
            }
          `}</style>
        </div>
      </div>
    );
  }

  // エラー状態
  if (error || !slide) {
    return (
      <div style={styles.container}>
        <div style={styles.header}>
          <button
            onClick={handleBackToDashboard}
            className="back-button"
            style={styles.backButton}
          >
            ← Dashboard
          </button>
        </div>
        <div style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          minHeight: 'calc(100vh - 64px)',
          flexDirection: 'column',
          gap: '16px'
        }}>
          <div style={{ fontSize: '48px', color: '#ef4444' }}>✕</div>
          <div style={{ color: '#ef4444', fontSize: '16px', fontWeight: '600' }}>エラーが発生しました</div>
          <div style={{ color: '#6b7280', fontSize: '14px' }}>
            {error?.message || 'スライドが見つかりません'}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      {/* ヘッダー */}
      <div style={styles.header}>
        <div style={styles.headerLeft}>
          <button
            onClick={handleBackToDashboard}
            className="back-button"
            style={styles.backButton}
          >
            ← Dashboard
          </button>
          <h1 style={styles.title}>{slide.title}</h1>
        </div>

        <div style={styles.actions}>
          {slide.pdf_url && (
            <a
              href={slide.pdf_url}
              target="_blank"
              rel="noopener noreferrer"
              className="action-button"
              style={styles.actionButton}
            >
              📄 PDF を開く
            </a>
          )}
        </div>
      </div>

      {/* 2ペインレイアウト */}
      <SlideDetailLayout
        slidePane={
          <div style={styles.slideViewerWrapper}>
            <SlideContentViewer slideId={slide.id} />
          </div>
        }
        chatPane={<ChatPanel slideId={slide.id} />}
      />

      <style>{hoverStyles}</style>
    </div>
  );
}

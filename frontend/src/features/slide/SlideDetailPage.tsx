/**
 * SlideDetailPage (Phase 2: React Query対応)
 * スライド詳細ページ
 */

import { useNavigate, useParams } from 'react-router-dom';
import { useState, useCallback } from 'react';
import SlideDetailLayout from './components/SlideDetailLayout';
import ChatPanel from './components/ChatPanel';
import { SlideContentViewer } from './components/SlideContentViewer';
import { useSlideDetail } from './api/get-slide-detail';
import FeedbackModal from './components/FeedbackModal';
import { submitFeedback } from './api/submit-feedback';

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
  },
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
  },
  feedbackButton: {
    padding: '8px 16px',
    fontSize: '13px',
    background: '#3b82f6',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    fontWeight: '600',
    transition: 'background 0.2s',
  },
  slideViewerWrapper: {
    height: '100%',
  },
};

export default function SlideDetailPage() {
  const { slideId } = useParams<{ slideId: string }>();
  const navigate = useNavigate();
  const [showFeedbackModal, setShowFeedbackModal] = useState(false);

  // React Queryでスライド詳細を取得
  const { data: slide, isLoading, error } = useSlideDetail(slideId || '');

  const handleFeedbackSubmit = useCallback(
    async (rating: number, comment: string) => {
      if (!slideId) return;

      await submitFeedback({
        slide_id: slideId,
        rating,
        comment,
      });

      alert('フィードバックをありがとうございます！');
    },
    [slideId]
  );

  if (isLoading) {
    return <div style={{ ...styles.container, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>Loading...</div>;
  }

  if (error || !slide) {
    return <div style={{ ...styles.container, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>Error loading slide</div>;
  }

  return (
    <div style={styles.container}>
      {/* ヘッダー */}
      <div style={styles.header}>
        <div style={styles.headerLeft}>
          <button
            onClick={() => navigate('/')}
            onMouseOver={(e) => (e.currentTarget.style.background = '#5a6268')}
            onMouseOut={(e) => (e.currentTarget.style.background = '#6c757d')}
            style={styles.backButton}
          >
            ← Dashboard
          </button>
          <h1 style={styles.title}>{slide.title}</h1>
        </div>

        {/* アクションボタン */}
        <div style={styles.actions}>
          <button
            onClick={() => setShowFeedbackModal(true)}
            onMouseOver={(e) => (e.currentTarget.style.background = '#2563eb')}
            onMouseOut={(e) => (e.currentTarget.style.background = '#3b82f6')}
            style={styles.feedbackButton}
          >
            💬 フィードバック
          </button>
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

      {/* フィードバックモーダル */}
      {showFeedbackModal && (
        <FeedbackModal
          slideId={slide.id}
          onClose={() => setShowFeedbackModal(false)}
          onSubmit={handleFeedbackSubmit}
        />
      )}
    </div>
  );
}

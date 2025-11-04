/**
 * SlideDetailPage (Phase 3: 2ペインレイアウト + チャットUI)
 * スライド詳細ページ
 */

import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import SlideDetailLayout from '../components/slide/SlideDetailLayout';
import ChatPanel from '../components/slide/ChatPanel';
import { SlideContentViewer } from '../components/slide/SlideContentViewer';

interface Slide {
  id: string;
  title: string;
  topic: string;
  created_at: string;
  pdf_url?: string;
}

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
  },
  loadingContainer: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: '#f5f5f5',
  },
  spinner: {
    display: 'inline-block',
    width: '40px',
    height: '40px',
    border: '4px solid #f3f3f3',
    borderTop: '4px solid #007bff',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
  },
  errorContainer: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: '#f5f5f5',
  },
  errorCard: {
    textAlign: 'center',
    padding: '40px',
    background: 'white',
    borderRadius: '12px',
    boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
  },
  errorIcon: {
    fontSize: '48px',
    marginBottom: '16px',
  },
  errorTitle: {
    color: '#dc3545',
    marginBottom: '8px',
  },
  errorText: {
    color: '#666',
    marginBottom: '24px',
  },
  slideViewerWrapper: {
    height: '100%',
  },
};

const spinnerKeyframes = `
  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
`;

export default function SlideDetailPage() {
  const { slideId } = useParams<{ slideId: string }>();
  const navigate = useNavigate();
  const [slide, setSlide] = useState<Slide | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSlide = async () => {
      try {
        const response = await fetch(
          `${import.meta.env.VITE_API_URL || 'http://localhost:8001/api'}/slides/${slideId}/markdown`
        );

        if (!response.ok) {
          throw new Error(`Failed to fetch slide: ${response.statusText}`);
        }

        const data = await response.json();

        // APIレスポンス形式をSlide型に変換
        setSlide({
          id: data.slide_id,
          title: data.title,
          topic: data.title, // topicフィールドはtitleで代用
          created_at: data.created_at,
          pdf_url: data.pdf_url,
        });
      } catch (err: any) {
        console.error('Failed to fetch slide:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    if (slideId) {
      fetchSlide();
    }
  }, [slideId]);

  if (loading) {
    return (
      <>
        <div style={styles.loadingContainer}>
          <div style={{ textAlign: 'center' }}>
            <div style={styles.spinner} />
            <p style={{ marginTop: '12px', color: '#666' }}>読み込み中...</p>
          </div>
        </div>
        <style>{spinnerKeyframes}</style>
      </>
    );
  }

  if (error || !slide) {
    return (
      <div style={styles.errorContainer}>
        <div style={styles.errorCard}>
          <div style={styles.errorIcon}>⚠️</div>
          <h2 style={styles.errorTitle}>スライドが見つかりません</h2>
          <p style={styles.errorText}>
            {error || 'スライドが存在しないか、削除された可能性があります。'}
          </p>
          <button
            onClick={() => navigate('/')}
            onMouseOver={(e) => e.currentTarget.style.background = '#0056b3'}
            onMouseOut={(e) => e.currentTarget.style.background = '#007bff'}
            style={{
              ...styles.actionButton,
              background: '#007bff',
            }}
          >
            ダッシュボードに戻る
          </button>
        </div>
      </div>
    );
  }

  return (
    <>
      <div style={styles.container}>
        {/* ヘッダー */}
        <div style={styles.header}>
          <div style={styles.headerLeft}>
            <button
              onClick={() => navigate('/')}
              onMouseOver={(e) => e.currentTarget.style.background = '#5a6268'}
              onMouseOut={(e) => e.currentTarget.style.background = '#6c757d'}
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
                download
                onMouseOver={(e) => e.currentTarget.style.background = '#218838'}
                onMouseOut={(e) => e.currentTarget.style.background = '#28a745'}
                style={styles.actionButton}
              >
                📥 PDF
              </a>
            )}
          </div>
        </div>

        {/* 2ペインレイアウト */}
        <SlideDetailLayout
          slidePane={
            <div style={styles.slideViewerWrapper}>
              <SlideContentViewer slideId={slideId!} />
            </div>
          }
          chatPane={<ChatPanel slideId={slideId!} />}
        />
      </div>
      <style>{spinnerKeyframes}</style>
    </>
  );
}

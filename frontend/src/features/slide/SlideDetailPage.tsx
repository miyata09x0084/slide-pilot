/**
 * SlideDetailPage (Phase 4修正: React Router Loader対応)
 * スライド詳細ページ
 */

import { useLoaderData, useNavigate } from 'react-router-dom';
import SlideDetailLayout from './components/SlideDetailLayout';
import ChatPanel from './components/ChatPanel';
import { SlideContentViewer } from './components/SlideContentViewer';
import type { SlideDetail } from './loaders/slideDetailLoader';

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
  slideViewerWrapper: {
    height: '100%',
  },
};

export default function SlideDetailPage() {
  const { slide } = useLoaderData() as { slide: SlideDetail };
  const navigate = useNavigate();

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

        <div style={styles.actions}>
          {slide.pdf_url && (
            <a
              href={slide.pdf_url}
              target="_blank"
              rel="noopener noreferrer"
              onMouseOver={(e) => (e.currentTarget.style.background = '#218838')}
              onMouseOut={(e) => (e.currentTarget.style.background = '#28a745')}
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
    </div>
  );
}

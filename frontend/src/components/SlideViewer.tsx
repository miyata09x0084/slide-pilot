/**
 * SlideViewer - Markdownスライドプレビューコンポーネント
 *
 * Issue #24: ブラウザプレビュー + Supabase履歴管理
 * Supabaseから取得したMarkdownをreact-markdownで表示
 */

import { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface SlideViewerProps {
  slideId: string;
  onClose: () => void;
}

interface SlideContent {
  slide_id: string;
  title: string;
  markdown: string;
  created_at: string;
  pdf_url?: string;
}

export function SlideViewer({ slideId, onClose }: SlideViewerProps) {
  const [slide, setSlide] = useState<SlideContent | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSlide = async () => {
      try {
        const response = await fetch(`http://localhost:8001/api/slides/${slideId}/markdown`);

        if (!response.ok) {
          throw new Error(`Failed to fetch slide: ${response.statusText}`);
        }

        const data = await response.json();
        setSlide(data);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchSlide();
  }, [slideId]);

  if (loading) {
    return (
      <div style={styles.overlay}>
        <div style={styles.modal}>
          <p>読み込み中...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={styles.overlay}>
        <div style={styles.modal}>
          <h2>エラー</h2>
          <p>{error}</p>
          <button onClick={onClose} style={styles.closeButton}>
            閉じる
          </button>
        </div>
      </div>
    );
  }

  if (!slide) {
    return null;
  }

  return (
    <div style={styles.overlay} onClick={onClose}>
      <div style={styles.modal} onClick={(e) => e.stopPropagation()}>
        {/* ヘッダー */}
        <div style={styles.header}>
          <h2 style={styles.title}>{slide.title}</h2>
          <button onClick={onClose} style={styles.closeButton}>
            ✕
          </button>
        </div>

        {/* Markdownコンテンツ */}
        <div style={styles.content}>
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              // Slidev固有のタグを無視
              hr: () => <div style={styles.slideSeparator}>───</div>,
              // コードブロックのスタイリング
              code: ({ inline, children, ...props }) =>
                inline ? (
                  <code style={styles.inlineCode} {...props}>{children}</code>
                ) : (
                  <pre style={styles.codeBlock}>
                    <code {...props}>{children}</code>
                  </pre>
                ),
              // リストのスタイリング
              ul: ({ children }) => <ul style={styles.list}>{children}</ul>,
              ol: ({ children }) => <ol style={styles.list}>{children}</ol>,
            }}
          >
            {slide.markdown}
          </ReactMarkdown>
        </div>

        {/* フッター */}
        <div style={styles.footer}>
          <span style={styles.timestamp}>
            作成日時: {new Date(slide.created_at).toLocaleString('ja-JP')}
          </span>
          {slide.pdf_url && (
            <a href={slide.pdf_url} download style={styles.downloadLink}>
              📥 PDFダウンロード
            </a>
          )}
        </div>
      </div>
    </div>
  );
}

// スタイル定義
const styles: Record<string, React.CSSProperties> = {
  overlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
  },
  modal: {
    backgroundColor: '#1e1e1e',
    color: '#e0e0e0',
    borderRadius: '8px',
    width: '90%',
    maxWidth: '900px',
    maxHeight: '90vh',
    display: 'flex',
    flexDirection: 'column',
    boxShadow: '0 4px 20px rgba(0, 0, 0, 0.5)',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '20px',
    borderBottom: '1px solid #333',
  },
  title: {
    margin: 0,
    fontSize: '1.5rem',
    color: '#fff',
  },
  closeButton: {
    background: 'transparent',
    border: 'none',
    color: '#fff',
    fontSize: '1.5rem',
    cursor: 'pointer',
    padding: '0 10px',
  },
  content: {
    flex: 1,
    overflow: 'auto',
    padding: '20px',
    lineHeight: '1.6',
  },
  slideSeparator: {
    margin: '30px 0',
    textAlign: 'center',
    color: '#666',
    fontSize: '1.2rem',
  },
  inlineCode: {
    backgroundColor: '#2d2d2d',
    padding: '2px 6px',
    borderRadius: '3px',
    fontFamily: 'monospace',
    color: '#f92672',
  },
  codeBlock: {
    backgroundColor: '#2d2d2d',
    padding: '15px',
    borderRadius: '5px',
    overflow: 'auto',
    fontFamily: 'monospace',
    fontSize: '0.9rem',
  },
  list: {
    marginLeft: '20px',
    marginBottom: '15px',
  },
  footer: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '15px 20px',
    borderTop: '1px solid #333',
  },
  timestamp: {
    fontSize: '0.9rem',
    color: '#999',
  },
  downloadLink: {
    color: '#4fc3f7',
    textDecoration: 'none',
    fontSize: '1rem',
  },
};

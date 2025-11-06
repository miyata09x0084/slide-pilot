/**
 * SlideContentViewer - モーダルなしMarkdownスライド表示コンポーネント
 * SlideDetailPageの左ペインで使用（2ペインレイアウト用）
 */

import { useEffect, useState, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import mermaid from 'mermaid';

// Mermaid初期化
mermaid.initialize({
  startOnLoad: false,
  theme: 'default',
  securityLevel: 'loose',
});

// Mermaidダイアグラムコンポーネント
function MermaidDiagram({ chart, index }: { chart: string; index: number }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (ref.current && chart) {
      const id = `mermaid-diagram-${index}`;
      mermaid.render(id, chart)
        .then(({ svg }) => {
          if (ref.current) {
            ref.current.innerHTML = svg;
          }
        })
        .catch((err) => {
          console.error('Mermaid render error:', err);
          if (ref.current) {
            ref.current.innerHTML = '<pre style="color: red;">図解のレンダリングに失敗しました</pre>';
          }
        });
    }
  }, [chart, index]);

  return <div ref={ref} style={{ margin: '24px auto', textAlign: 'center' }} />;
}

interface SlideContentViewerProps {
  slideId: string;
}

interface SlideContent {
  slide_id: string;
  title: string;
  markdown: string;
  created_at: string;
  pdf_url?: string;
}

export function SlideContentViewer({ slideId }: SlideContentViewerProps) {
  const [slide, setSlide] = useState<SlideContent | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSlide = async () => {
      try {
        const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8001/api'}/slides/${slideId}/markdown`);

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
      <div style={styles.container}>
        <div style={styles.loadingText}>読み込み中...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={styles.container}>
        <div style={styles.errorCard}>
          <h2 style={styles.errorTitle}>エラー</h2>
          <p style={styles.errorText}>{error}</p>
        </div>
      </div>
    );
  }

  if (!slide) {
    return null;
  }

  // Markdownを `---` で分割してスライドに変換
  const contentWithoutFrontmatter = slide.markdown.replace(/^---\s*\n[\s\S]*?\n---\s*\n/, '');
  const slides = contentWithoutFrontmatter
    .split(/\n---\n/)
    .map(s => s.trim())
    .filter(s => s.length > 0);

  return (
    <div style={styles.container}>
      {/* スライドコンテンツ */}
      <div style={styles.slidesContainer}>
        {slides.map((slideContent, index) => (
          <div key={index} style={styles.slideCard}>
            <div style={styles.slideContent}>
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  h1: ({ children }) => <h1 style={styles.h1}>{children}</h1>,
                  h2: ({ children }) => <h2 style={styles.h2}>{children}</h2>,
                  h3: ({ children }) => <h3 style={styles.h3}>{children}</h3>,
                  code: (props) => {
                    const { children, className, ...rest } = props;
                    const match = /language-(\w+)/.exec(className || '');
                    const language = match ? match[1] : '';
                    const inline = !String(children).includes('\n');

                    if (language === 'mermaid' && !inline) {
                      return <MermaidDiagram chart={String(children).replace(/\n$/, '')} index={index} />;
                    }

                    return inline ? (
                      <code style={styles.inlineCode} {...rest}>{children}</code>
                    ) : (
                      <pre style={styles.codeBlock}>
                        <code {...rest}>{children}</code>
                      </pre>
                    );
                  },
                  ul: ({ children }) => <ul style={styles.list}>{children}</ul>,
                  ol: ({ children }) => <ol style={styles.orderedList}>{children}</ol>,
                  li: ({ children }) => <li style={styles.listItem}>{children}</li>,
                  p: ({ children }) => <p style={styles.paragraph}>{children}</p>,
                }}
              >
                {slideContent}
              </ReactMarkdown>
            </div>
            <div style={styles.pageNumber}>{index + 1} / {slides.length}</div>
          </div>
        ))}
      </div>

      {/* フッター */}
      <div style={styles.footer}>
        <span style={styles.timestamp}>
          作成日時: {new Date(slide.created_at).toLocaleString('ja-JP')}
        </span>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    width: '100%',
    height: '100%',
    overflowY: 'auto',
  },
  loadingText: {
    textAlign: 'center',
    padding: '40px',
    fontSize: '16px',
    color: '#666',
  },
  errorCard: {
    padding: '40px',
    textAlign: 'center',
  },
  errorTitle: {
    color: '#dc3545',
    marginBottom: '16px',
  },
  errorText: {
    color: '#666',
  },
  slidesContainer: {
    display: 'flex',
    flexDirection: 'column',
    gap: '32px',
  },
  slideCard: {
    position: 'relative',
    background: 'white',
    borderRadius: '12px',
    padding: '48px 60px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
    border: '1px solid #e0e0e0',
    minHeight: '400px',
  },
  slideContent: {
    flex: 1,
  },
  pageNumber: {
    position: 'absolute',
    bottom: '16px',
    right: '24px',
    fontSize: '12px',
    color: '#999',
    fontFamily: 'monospace',
  },
  h1: {
    fontSize: '48px',
    fontWeight: 'bold',
    marginBottom: '24px',
    color: '#1a1a1a',
    lineHeight: '1.2',
  },
  h2: {
    fontSize: '36px',
    fontWeight: '600',
    marginTop: '32px',
    marginBottom: '16px',
    color: '#2c2c2c',
    lineHeight: '1.3',
  },
  h3: {
    fontSize: '28px',
    fontWeight: '600',
    marginTop: '24px',
    marginBottom: '12px',
    color: '#3a3a3a',
    lineHeight: '1.4',
  },
  inlineCode: {
    background: '#f5f5f5',
    padding: '2px 6px',
    borderRadius: '4px',
    fontFamily: 'monospace',
    fontSize: '0.9em',
    color: '#e01e5a',
  },
  codeBlock: {
    background: '#2d2d2d',
    color: '#f8f8f2',
    padding: '20px',
    borderRadius: '8px',
    overflowX: 'auto',
    fontSize: '14px',
    lineHeight: '1.6',
    fontFamily: 'monospace',
  },
  list: {
    marginLeft: '32px',
    marginBottom: '16px',
    lineHeight: '1.8',
    fontSize: '20px',
  },
  orderedList: {
    marginLeft: '32px',
    marginBottom: '16px',
    lineHeight: '1.8',
    fontSize: '20px',
  },
  listItem: {
    marginBottom: '8px',
    color: '#1a1a1a',
  },
  paragraph: {
    marginBottom: '16px',
    lineHeight: '1.7',
    fontSize: '20px',
    color: '#1a1a1a',
  },
  footer: {
    marginTop: '32px',
    padding: '16px 0',
    borderTop: '1px solid #e0e0e0',
    textAlign: 'center',
  },
  timestamp: {
    fontSize: '14px',
    color: '#666',
  },
};

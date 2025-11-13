/**
 * SlideViewer - Markdownスライドプレビューコンポーネント
 *
 * Issue #24: ブラウザプレビュー + Supabase履歴管理
 * Supabaseから取得したMarkdownをreact-markdownで表示
 */

import { useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import mermaid from 'mermaid';
import { useSlideDetail } from '../api/get-slide-detail';

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

interface SlideViewerProps {
  slideId: string;
  onClose: () => void;
}

export function SlideViewer({ slideId, onClose }: SlideViewerProps) {
  // React Queryフックでスライド詳細を取得
  const { data: slide, isLoading: loading, error } = useSlideDetail(slideId);

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
          <p>{error.message || 'スライドの読み込みに失敗しました'}</p>
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

  // Markdownを `---` で分割してスライドに変換
  // 最初の `---` で囲まれたYAML frontmatterを除去
  const contentWithoutFrontmatter = slide.markdown?.replace(/^---\s*\n[\s\S]*?\n---\s*\n/, '') || '';

  // 残りを `\n---\n` で分割
  const slides = contentWithoutFrontmatter
    .split(/\n---\n/)
    .map(s => s.trim())
    .filter(s => s.length > 0);

  return (
    <div style={styles.overlay} onClick={onClose}>
      <div style={styles.modal} onClick={(e) => e.stopPropagation()}>
        {/* ヘッダー */}
        <div style={styles.header}>
          <h2 style={styles.headerTitle}>{slide.title}</h2>
          <button onClick={onClose} style={styles.closeButton}>
            ✕
          </button>
        </div>

        {/* スライドコンテンツ（16:9カード形式） */}
        <div style={styles.slidesContainer}>
          {slides.map((slideContent, index) => (
            <div key={index} style={styles.slideCard}>
              <div style={styles.slideContent}>
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    // 見出しスタイリング（apple-basic準拠）
                    h1: ({ children }) => <h1 style={styles.h1}>{children}</h1>,
                    h2: ({ children }) => <h2 style={styles.h2}>{children}</h2>,
                    h3: ({ children }) => <h3 style={styles.h3}>{children}</h3>,
                    // コードブロック
                    code: (props) => {
                      const { children, className, ...rest } = props;
                      const match = /language-(\w+)/.exec(className || '');
                      const language = match ? match[1] : '';
                      const inline = !String(children).includes('\n');

                      // Mermaid図解の場合
                      if (language === 'mermaid' && !inline) {
                        return <MermaidDiagram chart={String(children).replace(/\n$/, '')} index={index} />;
                      }

                      // 通常のコードブロック
                      return inline ? (
                        <code style={styles.inlineCode} {...rest}>{children}</code>
                      ) : (
                        <pre style={styles.codeBlock}>
                          <code {...rest}>{children}</code>
                        </pre>
                      );
                    },
                    // リスト
                    ul: ({ children }) => <ul style={styles.list}>{children}</ul>,
                    ol: ({ children }) => <ol style={styles.orderedList}>{children}</ol>,
                    li: ({ children }) => <li style={styles.listItem}>{children}</li>,
                    // 段落
                    p: ({ children }) => <p style={styles.paragraph}>{children}</p>,
                  }}
                >
                  {slideContent}
                </ReactMarkdown>
              </div>
              {/* スライド番号 */}
              <div style={styles.pageNumber}>{index + 1} / {slides.length}</div>
            </div>
          ))}
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

// スタイル定義（apple-basic テーマ準拠）
const styles: Record<string, React.CSSProperties> = {
  overlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.75)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
    padding: '20px',
  },
  modal: {
    backgroundColor: '#f8f8f8',
    borderRadius: '12px',
    width: '100%',
    maxWidth: '1200px',
    maxHeight: '90vh',
    display: 'flex',
    flexDirection: 'column',
    boxShadow: '0 10px 40px rgba(0, 0, 0, 0.3)',
    overflow: 'hidden',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '16px 24px',
    borderBottom: '1px solid #e0e0e0',
    backgroundColor: '#ffffff',
  },
  headerTitle: {
    margin: 0,
    fontSize: '1.25rem',
    fontWeight: 600,
    color: '#1a1a1a',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  },
  closeButton: {
    background: 'transparent',
    border: 'none',
    color: '#666',
    fontSize: '1.5rem',
    cursor: 'pointer',
    padding: '4px 8px',
    borderRadius: '4px',
    transition: 'background 0.2s',
  },
  slidesContainer: {
    flex: 1,
    overflow: 'auto',
    padding: '24px',
    backgroundColor: '#f8f8f8',
  },
  slideCard: {
    position: 'relative',
    backgroundColor: '#ffffff',
    borderRadius: '8px',
    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)',
    marginBottom: '24px',
    overflow: 'hidden',
    aspectRatio: '16 / 9',
  },
  slideContent: {
    height: '100%',
    padding: '40px 60px',
    overflow: 'auto',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    color: '#1a1a1a',
    fontSize: '18px',
    lineHeight: 1.6,
  },
  pageNumber: {
    position: 'absolute',
    bottom: '16px',
    right: '24px',
    fontSize: '14px',
    color: '#999',
    fontFamily: 'monospace',
  },
  // 見出しスタイル（apple-basic準拠）
  h1: {
    fontSize: '48px',
    fontWeight: 700,
    marginTop: 0,
    marginBottom: '24px',
    color: '#1a1a1a',
    textAlign: 'center',
    lineHeight: 1.2,
  },
  h2: {
    fontSize: '36px',
    fontWeight: 700,
    marginTop: '32px',
    marginBottom: '16px',
    color: '#1a1a1a',
    lineHeight: 1.3,
  },
  h3: {
    fontSize: '24px',
    fontWeight: 600,
    marginTop: '24px',
    marginBottom: '12px',
    color: '#333',
    lineHeight: 1.4,
  },
  // テキストスタイル
  paragraph: {
    margin: '0 0 16px 0',
    lineHeight: 1.8,
    color: '#333',
  },
  // リストスタイル
  list: {
    marginLeft: '24px',
    marginBottom: '16px',
    lineHeight: 1.8,
  },
  orderedList: {
    marginLeft: '24px',
    marginBottom: '16px',
    lineHeight: 1.8,
  },
  listItem: {
    marginBottom: '8px',
    color: '#333',
  },
  // コードスタイル
  inlineCode: {
    backgroundColor: '#f5f5f5',
    padding: '2px 6px',
    borderRadius: '3px',
    fontFamily: '"SF Mono", Monaco, "Cascadia Code", monospace',
    fontSize: '0.9em',
    color: '#c7254e',
    border: '1px solid #e8e8e8',
  },
  codeBlock: {
    backgroundColor: '#f5f5f5',
    padding: '16px',
    borderRadius: '6px',
    overflow: 'auto',
    fontFamily: '"SF Mono", Monaco, "Cascadia Code", monospace',
    fontSize: '14px',
    lineHeight: 1.5,
    border: '1px solid #e8e8e8',
    margin: '16px 0',
  },
  // フッター
  footer: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px 24px',
    borderTop: '1px solid #e0e0e0',
    backgroundColor: '#ffffff',
  },
  timestamp: {
    fontSize: '0.875rem',
    color: '#666',
  },
  downloadLink: {
    color: '#007aff',
    textDecoration: 'none',
    fontSize: '0.9rem',
    fontWeight: 500,
    transition: 'opacity 0.2s',
  },
};

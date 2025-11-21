/**
 * SlideContentViewer - モーダルなしMarkdownスライド表示コンポーネント
 * SlideDetailPageの左ペインで使用（2ペインレイアウト用）
 */

import { useEffect, useState, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import mermaid from 'mermaid';
import { ProgressBar } from './ProgressBar';
import { useSlideDetail } from '../api/get-slide-detail';

// Mermaid初期化
mermaid.initialize({
  startOnLoad: false,
  theme: 'default',
  securityLevel: 'loose',
});

// テーマカラーパレット（Issue #20: 色弱対応・アクセシビリティ配色）
// 色弱の方でも区別しやすい色の組み合わせ
// 参考: 岡部正隆・伊藤啓「色覚バリアフリー」
const THEME_COLORS = {
  science: {
    primary: '#0075C2',           // 明るい青（色弱でも識別しやすい）
    cardBackground: '#E8F4F8',    // 淡い青背景（コントラスト比4.5:1以上）
  },
  story: {
    primary: '#C95F15',           // 黄みがかったオレンジ（赤緑色弱でも区別可能）
    cardBackground: '#FFF4E6',    // 淡いベージュ背景
  },
  math: {
    primary: '#03A89E',           // 青緑（シアン系、全ての色弱タイプで識別可能）
    cardBackground: '#E6F7F7',    // 淡い青緑背景
  },
  default: {
    primary: '#595959',           // ダークグレー（明度差で識別）
    cardBackground: '#F5F5F5',    // ライトグレー背景（高コントラスト）
  }
} as const;

// 絵文字正規表現（Unicode範囲）
const EMOJI_REGEX = /[\u{1F300}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/gu;

// テキストコンテンツを絵文字強調版に変換
function enhanceEmojis(children: React.ReactNode): React.ReactNode {
  if (typeof children !== 'string') return children;

  const parts: string[] = [];
  const emojis: string[] = [];
  let lastIndex = 0;

  // 絵文字を検出して分割
  const matches = [...children.matchAll(EMOJI_REGEX)];
  matches.forEach(match => {
    if (match.index !== undefined) {
      parts.push(children.slice(lastIndex, match.index));
      emojis.push(match[0]);
      lastIndex = match.index + match[0].length;
    }
  });
  parts.push(children.slice(lastIndex));

  // 絵文字を<span>でラップ
  return (
    <>
      {parts.map((part, i) => (
        <span key={i}>
          {part}
          {emojis[i] && (
            <span style={styles.emojiLarge}>{emojis[i]}</span>
          )}
        </span>
      ))}
    </>
  );
}

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

type ViewMode = 'markdown' | 'pdf' | 'video';

export function SlideContentViewer({ slideId }: SlideContentViewerProps) {
  // React Queryフックでスライド詳細を取得
  const { data: slide, isLoading: loading, error } = useSlideDetail(slideId);
  const [currentSlide, setCurrentSlide] = useState(0); // Issue #20: 進捗バー用の現在位置
  const [viewMode, setViewMode] = useState<ViewMode>('markdown'); // Phase 5: 表示モード切り替え

  // Intersection Observer でスライド位置を追跡
  useEffect(() => {
    if (!slide) return;

    const observerOptions = {
      root: null,
      rootMargin: '-50% 0px -50% 0px',
      threshold: 0
    };

    const observerCallback = (entries: IntersectionObserverEntry[]) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const index = parseInt(entry.target.getAttribute('data-slide-index') || '0', 10);
          setCurrentSlide(index);
        }
      });
    };

    const observer = new IntersectionObserver(observerCallback, observerOptions);
    const slideElements = document.querySelectorAll('[data-slide-index]');
    slideElements.forEach(el => observer.observe(el));

    return () => observer.disconnect();
  }, [slide]);

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
          <p style={styles.errorText}>{error.message || 'スライドの読み込みに失敗しました'}</p>
        </div>
      </div>
    );
  }

  if (!slide) {
    return null;
  }

  // Markdownを `---` で分割してスライドに変換
  const contentWithoutFrontmatter = slide.markdown?.replace(/^---\s*\n[\s\S]*?\n---\s*\n/, '') || '';
  const slides = contentWithoutFrontmatter
    .split(/\n---\n/)
    .map(s => s.trim())
    .filter(s => s.length > 0);

  // テーマカラーを取得（デフォルトは'story'）
  const templateType = 'story'; // TODO: SlideDetailにtemplate_type追加後に有効化
  const themeColors = THEME_COLORS[templateType];

  return (
    <div style={styles.container}>
      {/* 表示モード切り替えボタン（Phase 5: 動画プレビュー機能） */}
      {(slide.pdf_url || slide.video_url) && (
        <div style={styles.viewModeButtons}>
          <button
            onClick={() => setViewMode('markdown')}
            style={{
              ...styles.viewModeButton,
              ...(viewMode === 'markdown' ? styles.viewModeButtonActive : {}),
            }}
          >
            📝 Markdown表示
          </button>
          {slide.pdf_url && (
            <button
              onClick={() => setViewMode('pdf')}
              style={{
                ...styles.viewModeButton,
                ...(viewMode === 'pdf' ? styles.viewModeButtonActive : {}),
              }}
            >
              📄 PDF表示
            </button>
          )}
          {slide.video_url && (
            <button
              onClick={() => setViewMode('video')}
              style={{
                ...styles.viewModeButton,
                ...(viewMode === 'video' ? styles.viewModeButtonActive : {}),
              }}
            >
              🎬 動画表示
            </button>
          )}

          {/* ダウンロードボタン */}
          <div style={styles.downloadButtons}>
            {slide.pdf_url && (
              <a
                href={slide.pdf_url}
                download
                style={styles.downloadButtonPdf}
              >
                📥 PDFダウンロード
              </a>
            )}
            {slide.video_url && (
              <a
                href={slide.video_url}
                download
                style={styles.downloadButtonVideo}
              >
                🎬 動画ダウンロード
              </a>
            )}
          </div>
        </div>
      )}

      {/* PDF表示 */}
      {viewMode === 'pdf' && slide.pdf_url && (
        <div style={styles.pdfContainer}>
          <iframe
            src={slide.pdf_url}
            style={styles.pdfIframe}
            title="PDF Viewer"
          />
        </div>
      )}

      {/* 動画表示（Phase 5: 動画プレビュー機能） */}
      {viewMode === 'video' && slide.video_url && (
        <div style={styles.videoContainer}>
          <video
            src={slide.video_url}
            controls
            style={styles.videoPlayer}
            preload="metadata"
          >
            お使いのブラウザは動画タグをサポートしていません。
            <a href={slide.video_url} download>動画をダウンロード</a>
          </video>
        </div>
      )}

      {/* 動画が存在しない場合のメッセージ */}
      {viewMode === 'video' && !slide.video_url && (
        <div style={styles.noVideoMessage}>
          <p style={styles.noVideoText}>このスライドには動画版がありません</p>
        </div>
      )}

      {/* Markdown表示（既存のスライド表示） */}
      {viewMode === 'markdown' && (
        <>
          {/* 進捗バー */}
          <ProgressBar
            current={currentSlide + 1}
            total={slides.length}
            themeColor={themeColors.primary}
          />

          {/* スライドコンテンツ */}
          <div style={styles.slidesContainer}>
        {slides.map((slideContent, index) => (
          <div
            key={index}
            data-slide-index={index}
            style={{
              ...styles.slideCard,
              background: themeColors.cardBackground
            }}
          >
            <div style={styles.slideContent}>
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  h1: ({ children }) => <h1 style={styles.h1}>{enhanceEmojis(children)}</h1>,
                  h2: ({ children }) => <h2 style={styles.h2}>{enhanceEmojis(children)}</h2>,
                  h3: ({ children }) => <h3 style={styles.h3}>{enhanceEmojis(children)}</h3>,
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
                  li: ({ children }) => <li style={styles.listItem}>{enhanceEmojis(children)}</li>,
                  p: ({ children }) => <p style={styles.paragraph}>{enhanceEmojis(children)}</p>,
                }}
              >
                {slideContent}
              </ReactMarkdown>
            </div>
            <div style={styles.pageNumber}>{index + 1} / {slides.length}</div>
          </div>
        ))}
          </div>
        </>
      )}

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
  // Issue #20: 絵文字強調スタイル
  emojiLarge: {
    fontSize: '1.5em',
    verticalAlign: 'middle',
    display: 'inline-block',
    margin: '0 4px'
  },
  // Phase 5: 動画プレビュー機能
  viewModeButtons: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '8px',
    marginBottom: '16px',
    padding: '12px',
    background: '#f8f9fa',
    borderRadius: '8px',
    alignItems: 'center',
  },
  viewModeButton: {
    padding: '8px 16px',
    fontSize: '14px',
    background: '#e5e7eb',
    color: '#333',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    fontWeight: 'normal',
    transition: 'all 0.2s',
  },
  viewModeButtonActive: {
    background: '#3b82f6',
    color: 'white',
    fontWeight: 'bold',
  },
  downloadButtons: {
    display: 'flex',
    gap: '8px',
    marginLeft: 'auto',
  },
  downloadButtonPdf: {
    padding: '8px 16px',
    fontSize: '14px',
    background: '#10b981',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    textDecoration: 'none',
    cursor: 'pointer',
    transition: 'all 0.2s',
    display: 'inline-block',
  },
  downloadButtonVideo: {
    padding: '8px 16px',
    fontSize: '14px',
    background: '#8b5cf6',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    textDecoration: 'none',
    cursor: 'pointer',
    transition: 'all 0.2s',
    display: 'inline-block',
  },
  pdfContainer: {
    width: '100%',
    height: '80vh',
    marginBottom: '16px',
  },
  pdfIframe: {
    width: '100%',
    height: '100%',
    border: '1px solid #ddd',
    borderRadius: '8px',
  },
  videoContainer: {
    width: '100%',
    maxWidth: '1200px',
    margin: '0 auto 16px auto',
    background: '#000',
    borderRadius: '8px',
    overflow: 'hidden',
  },
  videoPlayer: {
    width: '100%',
    display: 'block',
  },
  noVideoMessage: {
    padding: '40px',
    textAlign: 'center',
    background: '#f9fafb',
    borderRadius: '8px',
    border: '1px solid #e5e7eb',
    marginBottom: '16px',
  },
  noVideoText: {
    fontSize: '16px',
    color: '#6b7280',
  },
};

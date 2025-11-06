/**
 * SlideDetailLayout
 * スライド詳細ページの2ペインレイアウト
 */

import type { ReactNode } from 'react';

interface SlideDetailLayoutProps {
  slidePane: ReactNode;
  chatPane: ReactNode;
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'grid',
    gridTemplateColumns: '60% 40%',
    gap: '24px',
    maxWidth: '1800px',
    margin: '0 auto',
    padding: '24px',
    minHeight: 'calc(100vh - 64px)',
  },
  slidePane: {
    background: 'white',
    borderRadius: '12px',
    padding: '24px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
    overflowY: 'auto',
    maxHeight: 'calc(100vh - 112px)',
  },
  chatPane: {
    background: 'white',
    borderRadius: '12px',
    padding: '24px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
    display: 'flex',
    flexDirection: 'column',
    maxHeight: 'calc(100vh - 112px)',
  },
};

// レスポンシブ対応のCSS
const responsiveStyles = `
  @media (max-width: 1024px) {
    .slide-detail-layout {
      grid-template-columns: 50% 50% !important;
    }
  }

  @media (max-width: 768px) {
    .slide-detail-layout {
      grid-template-columns: 1fr !important;
    }
    .slide-detail-layout .slide-pane {
      max-height: 60vh;
    }
    .slide-detail-layout .chat-pane {
      max-height: 40vh;
    }
  }
`;

export default function SlideDetailLayout({
  slidePane,
  chatPane,
}: SlideDetailLayoutProps) {
  return (
    <>
      <div className="slide-detail-layout" style={styles.container}>
        <div className="slide-pane" style={styles.slidePane}>
          {slidePane}
        </div>
        <div className="chat-pane" style={styles.chatPane}>
          {chatPane}
        </div>
      </div>
      <style>{responsiveStyles}</style>
    </>
  );
}

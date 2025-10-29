/**
 * DashboardLayout
 * トップページの3カラムレイアウト
 */

import { ReactNode } from 'react';

interface DashboardLayoutProps {
  leftSidebar: ReactNode;
  centerPanel: ReactNode;
  rightSidebar: ReactNode;
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'grid',
    gridTemplateColumns: '300px 1fr 300px',
    gap: '24px',
    maxWidth: '1600px',
    margin: '0 auto',
    padding: '24px',
    minHeight: 'calc(100vh - 64px)', // ヘッダー分を引く
  },
  leftSidebar: {
    background: 'white',
    borderRadius: '12px',
    padding: '20px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
    overflowY: 'auto',
    maxHeight: 'calc(100vh - 112px)',
  },
  centerPanel: {
    background: 'white',
    borderRadius: '12px',
    padding: '32px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
  },
  rightSidebar: {
    background: 'white',
    borderRadius: '12px',
    padding: '20px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
  },
};

// レスポンシブ対応のCSS
const responsiveStyles = `
  @media (max-width: 1024px) {
    .dashboard-layout {
      grid-template-columns: 1fr 300px !important;
    }
    .dashboard-layout .left-sidebar {
      display: none;
    }
  }

  @media (max-width: 768px) {
    .dashboard-layout {
      grid-template-columns: 1fr !important;
    }
    .dashboard-layout .right-sidebar {
      display: none;
    }
  }
`;

export default function DashboardLayout({
  leftSidebar,
  centerPanel,
  rightSidebar,
}: DashboardLayoutProps) {
  return (
    <>
      <div className="dashboard-layout" style={styles.container}>
        <div className="left-sidebar" style={styles.leftSidebar}>
          {leftSidebar}
        </div>
        <div className="center-panel" style={styles.centerPanel}>
          {centerPanel}
        </div>
        <div className="right-sidebar" style={styles.rightSidebar}>
          {rightSidebar}
        </div>
      </div>
      <style>{responsiveStyles}</style>
    </>
  );
}

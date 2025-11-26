/**
 * QuickActionMenu - 新規作成時のクイックアクションメニュー (Phase 3最適化済み)
 * PDFアップロードとテンプレート選択を統合
 * Phase 3: React.memoとuseCallbackで不要な再レンダリングを防止
 */

import { useRef, useCallback, memo } from 'react';

interface QuickActionMenuProps {
  onClose: () => void;
  onSelectUpload: () => void;
}

const styles: Record<string, React.CSSProperties> = {
  overlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background: 'rgba(0, 0, 0, 0.3)',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 1000,
    backdropFilter: 'blur(2px)',
  },
  menu: {
    background: 'white',
    borderRadius: '12px',
    boxShadow: '0 8px 32px rgba(0, 0, 0, 0.12)',
    minWidth: '320px',
    maxWidth: '400px',
    overflow: 'hidden',
  },
  header: {
    padding: '20px 24px',
    borderBottom: '1px solid #e5e7eb',
  },
  headerTitle: {
    fontSize: '18px',
    fontWeight: '700',
    color: '#1a1a1a',
    margin: 0,
  },
  headerSubtitle: {
    fontSize: '13px',
    color: '#6b7280',
    marginTop: '4px',
  },
  menuList: {
    padding: '8px',
  },
  menuItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
    padding: '16px',
    borderRadius: '8px',
    cursor: 'pointer',
    transition: 'all 0.2s',
    border: 'none',
    background: 'white',
    width: '100%',
    textAlign: 'left',
  },
  menuItemPrimary: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
    padding: '16px',
    borderRadius: '8px',
    cursor: 'pointer',
    transition: 'all 0.2s',
    border: 'none',
    background: '#eff6ff',
    width: '100%',
    textAlign: 'left',
  },
  menuIcon: {
    fontSize: '28px',
    flexShrink: 0,
  },
  menuContent: {
    flex: 1,
  },
  menuTitle: {
    fontSize: '15px',
    fontWeight: '600',
    color: '#1a1a1a',
    marginBottom: '2px',
  },
  menuDescription: {
    fontSize: '12px',
    color: '#6b7280',
  },
  menuItemDisabled: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
    padding: '16px',
    borderRadius: '8px',
    cursor: 'not-allowed',
    transition: 'all 0.2s',
    border: 'none',
    background: '#f9fafb',
    width: '100%',
    textAlign: 'left',
    opacity: 0.6,
  },
};

const comingSoonItems = [
  {
    id: 'webpage',
    icon: '🌐',
    title: 'WebページURL',
    description: '🔒 準備中',
  },
  {
    id: 'video',
    icon: '🎬',
    title: '動画URL',
    description: '🔒 準備中',
  },
];

const QuickActionMenu = memo(function QuickActionMenu({
  onClose,
  onSelectUpload,
}: QuickActionMenuProps) {
  // @ts-ignore - Reserved for future use
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleOverlayClick = useCallback((e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  }, [onClose]);

  const handleUploadClick = useCallback(() => {
    onClose();
    onSelectUpload();
  }, [onClose, onSelectUpload]);

  return (
    <div style={styles.overlay} onClick={handleOverlayClick}>
      <div style={styles.menu}>
        <div style={styles.header}>
          <h2 style={styles.headerTitle}>新規作成</h2>
        </div>

        <div style={styles.menuList}>
          {/* PDFアップロード */}
          <button
            style={styles.menuItemPrimary}
            onClick={handleUploadClick}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = '#dbeafe';
              e.currentTarget.style.transform = 'translateX(4px)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = '#eff6ff';
              e.currentTarget.style.transform = 'translateX(0)';
            }}
          >
            <div style={styles.menuIcon}>📄</div>
            <div style={styles.menuContent}>
              <div style={styles.menuTitle}>PDFをアップロード</div>
              <div style={styles.menuDescription}>
                PDFを理解しやすい動画に変換
              </div>
            </div>
          </button>

          {/* 準備中の項目 */}
          {comingSoonItems.map((item) => (
            <div
              key={item.id}
              style={styles.menuItemDisabled}
            >
              <div style={styles.menuIcon}>{item.icon}</div>
              <div style={styles.menuContent}>
                <div style={styles.menuTitle}>{item.title}</div>
                <div style={styles.menuDescription}>
                  {item.description}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
});

export default QuickActionMenu;

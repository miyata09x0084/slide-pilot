/**
 * QuickActionMenu - 新規作成時のクイックアクションメニュー (Phase 3最適化済み)
 * PDFアップロードとテンプレート選択を統合
 * Phase 3: React.memoとuseCallbackで不要な再レンダリングを防止
 */

import { useRef, useCallback, memo } from 'react';

interface QuickActionMenuProps {
  onClose: () => void;
  onSelectUpload: () => void;
  onSelectTemplate: (templateId: string) => void;
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
};

const templates = [
  {
    id: 'ai-news',
    icon: '🤖',
    title: 'AI最新ニュース',
    description: '2025年のトレンドをまとめます',
  },
  {
    id: 'ml-basics',
    icon: '📊',
    title: '機械学習入門',
    description: '基礎から学べるスライド',
  },
  {
    id: 'textbook',
    icon: '📚',
    title: '教科書要約',
    description: '章立てから作成します',
  },
];

const QuickActionMenu = memo(function QuickActionMenu({
  onClose,
  onSelectUpload,
  onSelectTemplate,
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

  const handleTemplateClick = useCallback((templateId: string) => {
    onClose();
    onSelectTemplate(templateId);
  }, [onClose, onSelectTemplate]);

  return (
    <div style={styles.overlay} onClick={handleOverlayClick}>
      <div style={styles.menu}>
        <div style={styles.header}>
          <h2 style={styles.headerTitle}>新規作成</h2>
          <div style={styles.headerSubtitle}>
            作成方法を選択してください
          </div>
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
                PDFファイルからスライドを作成
              </div>
            </div>
          </button>

          {/* テンプレート */}
          {templates.map((template) => (
            <button
              key={template.id}
              style={styles.menuItem}
              onClick={() => handleTemplateClick(template.id)}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = '#f9fafb';
                e.currentTarget.style.transform = 'translateX(4px)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'white';
                e.currentTarget.style.transform = 'translateX(0)';
              }}
            >
              <div style={styles.menuIcon}>{template.icon}</div>
              <div style={styles.menuContent}>
                <div style={styles.menuTitle}>{template.title}</div>
                <div style={styles.menuDescription}>
                  {template.description}
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
});

export default QuickActionMenu;

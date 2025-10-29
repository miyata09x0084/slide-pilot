/**
 * SlideHistoryGrid
 * 左サイドバー用のスライド履歴表示（コンパクト版）
 */

import { SlideHistory } from '../SlideHistory';

interface SlideHistoryGridProps {
  userEmail: string;
  onSlideClick: (slideId: string) => void;
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  header: {
    fontSize: '18px',
    fontWeight: '600',
    color: '#333',
    marginBottom: '8px',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  emptyState: {
    textAlign: 'center',
    padding: '40px 20px',
    color: '#999',
  },
  emptyIcon: {
    fontSize: '48px',
    marginBottom: '12px',
  },
  emptyText: {
    fontSize: '14px',
  },
};

export default function SlideHistoryGrid({
  userEmail,
  onSlideClick,
}: SlideHistoryGridProps) {
  return (
    <div style={styles.container}>
      <h3 style={styles.header}>
        <span>📚</span>
        <span>過去のスライド</span>
      </h3>
      <SlideHistory userEmail={userEmail} onPreview={onSlideClick} />
    </div>
  );
}

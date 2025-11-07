/**
 * UnifiedCard - 統一カードコンポーネント (React.memo最適化済み)
 * 全ての要素を同じサイズ・同じ形のカードとして表示
 * Phase 3: React.memoで不要な再レンダリングを防止
 */

import { memo, useCallback } from 'react';

interface UnifiedCardProps {
  icon: string;
  title: string;
  subtitle?: string;
  onClick?: () => void;  // イベント委譲時は不要になるのでoptional
  variant?: 'primary' | 'default' | 'history' | 'more';
  className?: string;
  'data-slide-id'?: string;  // イベント委譲用のdata属性
}

const styles: Record<string, React.CSSProperties> = {
  card: {
    height: '100%',
    minHeight: '200px',
    background: '#ffffff',
    border: '2px solid #e5e7eb',
    borderRadius: '12px',
    padding: '28px 24px',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center',
    alignItems: 'center',
    textAlign: 'center',
    cursor: 'pointer',
    transition: 'all 0.2s',
    boxSizing: 'border-box',
  },
  cardPrimary: {
    height: '100%',
    minHeight: '200px',
    background: '#eff6ff',
    border: '2px solid #3b82f6',
    borderRadius: '12px',
    padding: '28px 24px',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center',
    alignItems: 'center',
    textAlign: 'center',
    cursor: 'pointer',
    transition: 'all 0.2s',
    boxSizing: 'border-box',
  },
  cardHistory: {
    height: '100%',
    minHeight: '200px',
    background: '#f9fafb',
    border: '2px solid #e5e7eb',
    borderRadius: '12px',
    padding: '28px 24px',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center',
    alignItems: 'center',
    textAlign: 'center',
    cursor: 'pointer',
    transition: 'all 0.2s',
    boxSizing: 'border-box',
  },
  cardMore: {
    height: '100%',
    minHeight: '200px',
    background: '#ffffff',
    border: '2px dashed #d1d5db',
    borderRadius: '12px',
    padding: '28px 24px',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center',
    alignItems: 'center',
    textAlign: 'center',
    cursor: 'pointer',
    transition: 'all 0.2s',
    boxSizing: 'border-box',
  },
  icon: {
    fontSize: '36px',
    marginBottom: '8px',
  },
  iconPrimary: {
    fontSize: '64px',
    marginBottom: '12px',
    fontWeight: '300',
    lineHeight: '1',
  },
  content: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  title: {
    fontSize: '15px',
    fontWeight: '700',
    color: '#1a1a1a',
    lineHeight: '1.3',
    wordBreak: 'break-word',
  },
  titlePrimary: {
    fontSize: '16px',
    fontWeight: '700',
    color: '#1a1a1a',
    lineHeight: '1.3',
    wordBreak: 'break-word',
  },
  subtitle: {
    fontSize: '12px',
    color: '#6b7280',
    lineHeight: '1.4',
  },
  subtitlePrimary: {
    fontSize: '12px',
    color: '#6b7280',
    lineHeight: '1.4',
  },
};

const UnifiedCard = memo(function UnifiedCard({
  icon,
  title,
  subtitle,
  onClick,
  variant = 'default',
  className = '',
  'data-slide-id': dataSlideId,
}: UnifiedCardProps) {
  const isPrimary = variant === 'primary';
  const isHistory = variant === 'history';
  const isMore = variant === 'more';

  const cardStyle = isPrimary
    ? styles.cardPrimary
    : isHistory
    ? styles.cardHistory
    : isMore
    ? styles.cardMore
    : styles.card;
  const iconStyle = isPrimary ? styles.iconPrimary : styles.icon;
  const titleStyle = isPrimary ? styles.titlePrimary : styles.title;
  const subtitleStyle = isPrimary ? styles.subtitlePrimary : styles.subtitle;

  // メモ化されたイベントハンドラー
  const handleMouseEnter = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    e.currentTarget.style.borderColor = '#3b82f6';
    e.currentTarget.style.boxShadow = '0 4px 8px rgba(0,0,0,0.12)';
    if (isPrimary) {
      e.currentTarget.style.background = '#dbeafe';
    } else if (isHistory) {
      e.currentTarget.style.background = '#f3f4f6';
    } else if (isMore) {
      e.currentTarget.style.background = '#f9fafb';
    } else {
      e.currentTarget.style.background = '#f9fafb';
    }
  }, [isPrimary, isHistory, isMore]);

  const handleMouseLeave = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (isPrimary) {
      e.currentTarget.style.borderColor = '#3b82f6';
      e.currentTarget.style.background = '#eff6ff';
    } else if (isHistory) {
      e.currentTarget.style.borderColor = '#e5e7eb';
      e.currentTarget.style.background = '#f9fafb';
    } else if (isMore) {
      e.currentTarget.style.borderColor = '#d1d5db';
      e.currentTarget.style.background = '#ffffff';
    } else {
      e.currentTarget.style.borderColor = '#e5e7eb';
      e.currentTarget.style.background = '#ffffff';
    }
    e.currentTarget.style.boxShadow = 'none';
  }, [isPrimary, isHistory, isMore]);

  // クリックハンドラー: onClickがある場合はイベントの伝播を止める
  const handleClick = useCallback((e: React.MouseEvent) => {
    if (onClick) {
      e.stopPropagation(); // 親のイベント委譲をスキップ
      onClick();
    }
    // data-slide-idのみの場合は伝播させる（親で処理）
  }, [onClick]);

  return (
    <div
      className={className}
      style={cardStyle}
      onClick={handleClick}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      data-slide-id={dataSlideId}
    >
      <div style={iconStyle}>{icon}</div>
      <div style={styles.content}>
        <div style={titleStyle}>{title}</div>
        {subtitle && <div style={subtitleStyle}>{subtitle}</div>}
      </div>
    </div>
  );
});

export default UnifiedCard;

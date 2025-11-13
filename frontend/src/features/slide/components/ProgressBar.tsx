/**
 * ProgressBar - スライド進捗表示コンポーネント
 * Issue #20: 教育向けテーマ - 進捗バー
 */

interface ProgressBarProps {
  current: number;
  total: number;
  themeColor: string;
}

export function ProgressBar({ current, total, themeColor }: ProgressBarProps) {
  const percentage = (current / total) * 100;

  return (
    <div style={styles.container}>
      <div style={styles.label}>
        {current} / {total}
      </div>
      <div style={styles.barBackground}>
        <div
          style={{
            ...styles.barFill,
            width: `${percentage}%`,
            background: themeColor
          }}
        />
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    position: 'sticky',
    top: 0,
    zIndex: 10,
    background: 'white',
    padding: '12px 24px',
    borderBottom: '1px solid #e0e0e0',
    display: 'flex',
    alignItems: 'center',
    gap: '16px'
  },
  label: {
    fontSize: '14px',
    fontWeight: 600,
    color: '#333',
    minWidth: '60px'
  },
  barBackground: {
    flex: 1,
    height: '8px',
    background: '#e0e0e0',
    borderRadius: '4px',
    overflow: 'hidden'
  },
  barFill: {
    height: '100%',
    transition: 'width 0.3s ease-in-out',
    borderRadius: '4px'
  }
};

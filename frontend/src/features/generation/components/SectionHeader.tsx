/**
 * SectionHeader - セクションヘッダーコンポーネント
 * カードグループを視覚的に分類
 */

interface SectionHeaderProps {
  title: string;
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    gridColumn: '1 / -1',
    marginTop: '24px',
    marginBottom: '12px',
  },
  title: {
    fontSize: '14px',
    fontWeight: '700',
    color: '#374151',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    paddingBottom: '8px',
    borderBottom: '2px solid #e5e7eb',
  },
};

export default function SectionHeader({ title }: SectionHeaderProps) {
  return (
    <div style={styles.container}>
      <h2 style={styles.title}>{title}</h2>
    </div>
  );
}

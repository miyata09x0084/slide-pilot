/**
 * QuickActionPanel
 * 右サイドバー: クイックテンプレートボタン
 */

interface QuickActionPanelProps {
  onTemplateClick: (template: string) => void;
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
  },
  button: {
    width: '100%',
    padding: '16px',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    fontSize: '15px',
    fontWeight: '600',
    cursor: 'pointer',
    transition: 'transform 0.2s, box-shadow 0.2s',
    boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
    textAlign: 'left',
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  buttonIcon: {
    fontSize: '24px',
  },
  buttonText: {
    flex: 1,
  },
  buttonHover: {
    transform: 'translateY(-2px)',
    boxShadow: '0 6px 12px rgba(0,0,0,0.15)',
  },
  divider: {
    height: '1px',
    background: '#e0e0e0',
    margin: '12px 0',
  },
  info: {
    padding: '12px',
    background: '#f8f9fa',
    borderRadius: '6px',
    fontSize: '13px',
    color: '#666',
    lineHeight: '1.6',
  },
};

const templates = [
  {
    id: 'ai-news',
    icon: '🤖',
    label: 'AI最新ニュース',
    description: '2025年のAI業界トレンド',
    gradient: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
  },
  {
    id: 'ml-basics',
    icon: '📊',
    label: '機械学習入門',
    description: '基礎から学ぶML',
    gradient: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
  },
  {
    id: 'textbook',
    icon: '📚',
    label: '教科書要約',
    description: '章立てから作成',
    gradient: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
  },
];

export default function QuickActionPanel({ onTemplateClick }: QuickActionPanelProps) {
  const handleMouseEnter = (e: React.MouseEvent<HTMLButtonElement>) => {
    Object.assign(e.currentTarget.style, styles.buttonHover);
  };

  const handleMouseLeave = (e: React.MouseEvent<HTMLButtonElement>) => {
    e.currentTarget.style.transform = '';
    e.currentTarget.style.boxShadow = '0 4px 6px rgba(0,0,0,0.1)';
  };

  return (
    <div style={styles.container}>
      <h3 style={styles.header}>クイックテンプレート</h3>

      {templates.map((template) => (
        <button
          key={template.id}
          onClick={() => onTemplateClick(template.id)}
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
          style={{
            ...styles.button,
            background: template.gradient,
          }}
        >
          <span style={styles.buttonIcon}>{template.icon}</span>
          <div style={styles.buttonText}>
            <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>
              {template.label}
            </div>
            <div style={{ fontSize: '12px', opacity: 0.9 }}>
              {template.description}
            </div>
          </div>
        </button>
      ))}

      <div style={styles.divider} />

      <div style={styles.info}>
        <strong>💡 ワンクリック生成</strong>
        <div style={{ marginTop: '8px' }}>
          テンプレートを選ぶと、自動的にスライドを生成します
        </div>
      </div>
    </div>
  );
}

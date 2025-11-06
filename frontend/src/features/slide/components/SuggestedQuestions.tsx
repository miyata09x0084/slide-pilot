/**
 * SuggestedQuestions
 * 質問候補チップ表示
 */

interface SuggestedQuestionsProps {
  suggestions: string[];
  onSelect: (question: string) => void;
  disabled?: boolean;
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    marginBottom: '16px',
  },
  title: {
    fontSize: '13px',
    fontWeight: '600',
    color: '#666',
    marginBottom: '8px',
  },
  chipContainer: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '8px',
  },
  chip: {
    padding: '8px 12px',
    background: '#f0f0f0',
    border: '1px solid #e0e0e0',
    borderRadius: '16px',
    fontSize: '13px',
    color: '#333',
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  chipHover: {
    background: '#007bff',
    color: 'white',
    borderColor: '#007bff',
  },
  chipDisabled: {
    opacity: 0.5,
    cursor: 'not-allowed',
  },
};

export default function SuggestedQuestions({
  suggestions,
  onSelect,
  disabled = false,
}: SuggestedQuestionsProps) {
  const handleMouseEnter = (e: React.MouseEvent<HTMLButtonElement>) => {
    if (!disabled) {
      Object.assign(e.currentTarget.style, styles.chipHover);
    }
  };

  const handleMouseLeave = (e: React.MouseEvent<HTMLButtonElement>) => {
    if (!disabled) {
      e.currentTarget.style.background = '#f0f0f0';
      e.currentTarget.style.color = '#333';
      e.currentTarget.style.borderColor = '#e0e0e0';
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.title}>💡 こんな質問もできます:</div>
      <div style={styles.chipContainer}>
        {suggestions.map((suggestion, index) => (
          <button
            key={index}
            onClick={() => !disabled && onSelect(suggestion)}
            onMouseEnter={handleMouseEnter}
            onMouseLeave={handleMouseLeave}
            disabled={disabled}
            style={{
              ...styles.chip,
              ...(disabled ? styles.chipDisabled : {}),
            }}
          >
            {suggestion}
          </button>
        ))}
      </div>
    </div>
  );
}

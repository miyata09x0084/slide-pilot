/**
 * InlineFeedback - 動画直下のインラインフィードバックコンポーネント
 * Netflix風の👍👎ワンクリック評価 + 詳細コメントリンク
 */

import { useState, useCallback } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faThumbsUp, faThumbsDown } from '@fortawesome/free-solid-svg-icons';

interface InlineFeedbackProps {
  slideId: string;
  onQuickFeedback: (rating: number) => Promise<void>;
  onOpenDetail: () => void;
}

export function InlineFeedback({
  onQuickFeedback,
  onOpenDetail,
}: InlineFeedbackProps) {
  const [selectedRating, setSelectedRating] = useState<'up' | 'down' | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const handleThumbsUp = useCallback(async () => {
    if (isSubmitting || submitted) return;
    setIsSubmitting(true);
    try {
      await onQuickFeedback(5);
      setSelectedRating('up');
      setSubmitted(true);
    } finally {
      setIsSubmitting(false);
    }
  }, [onQuickFeedback, isSubmitting, submitted]);

  const handleThumbsDown = useCallback(async () => {
    if (isSubmitting || submitted) return;
    setIsSubmitting(true);
    try {
      await onQuickFeedback(1);
      setSelectedRating('down');
      setSubmitted(true);
    } finally {
      setIsSubmitting(false);
    }
  }, [onQuickFeedback, isSubmitting, submitted]);

  return (
    <div style={styles.container}>
      <span style={styles.label}>この動画はいかがでしたか？</span>
      <div style={styles.buttons}>
        <button
          onClick={handleThumbsUp}
          disabled={isSubmitting || submitted}
          style={{
            ...styles.thumbButton,
            ...(selectedRating === 'up' ? styles.thumbButtonSelected : {}),
            ...(isSubmitting ? styles.thumbButtonDisabled : {}),
          }}
          title="良かった"
        >
          <FontAwesomeIcon icon={faThumbsUp} style={styles.thumbIcon} />
        </button>
        <button
          onClick={handleThumbsDown}
          disabled={isSubmitting || submitted}
          style={{
            ...styles.thumbButton,
            ...(selectedRating === 'down' ? styles.thumbButtonSelectedDown : {}),
            ...(isSubmitting ? styles.thumbButtonDisabled : {}),
          }}
          title="改善が必要"
        >
          <FontAwesomeIcon icon={faThumbsDown} style={styles.thumbIcon} />
        </button>
        <button
          onClick={onOpenDetail}
          style={styles.detailLink}
        >
          詳細なフィードバック
        </button>
      </div>
      {submitted && (
        <span style={styles.thankYou}>ありがとうございます！</span>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '12px',
    padding: '20px',
    background: 'rgba(255, 255, 255, 0.05)',
    borderRadius: '12px',
    marginTop: '20px',
  },
  label: {
    fontSize: '15px',
    color: '#ccc',
    fontWeight: '500',
  },
  buttons: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  thumbIcon: {
    color: '#888',
    fontSize: '16px',
  },
  thumbButton: {
    width: '40px',
    height: '40px',
    fontSize: '16px',
    background: 'transparent',
    border: '1px solid rgba(255, 255, 255, 0.2)',
    borderRadius: '50%',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  thumbButtonSelected: {
    background: 'rgba(255, 255, 255, 0.1)',
    borderColor: 'rgba(255, 255, 255, 0.4)',
    transform: 'scale(1.1)',
  },
  thumbButtonSelectedDown: {
    background: 'rgba(255, 255, 255, 0.1)',
    borderColor: 'rgba(255, 255, 255, 0.4)',
    transform: 'scale(1.1)',
  },
  thumbButtonDisabled: {
    opacity: 0.5,
    cursor: 'not-allowed',
  },
  detailLink: {
    fontSize: '13px',
    color: '#60a5fa',
    background: 'transparent',
    border: 'none',
    cursor: 'pointer',
    textDecoration: 'underline',
    marginLeft: '8px',
  },
  thankYou: {
    fontSize: '13px',
    color: '#999',
    fontWeight: '500',
  },
};

/**
 * FeedbackModal - フィードバック送信モーダル
 * スライドに対する評価（1-5）とコメントを収集
 */

import { useState, useCallback } from 'react';

interface FeedbackModalProps {
  slideId: string;
  onClose: () => void;
  onSubmit: (rating: number, comment: string) => Promise<void>;
}

const styles: Record<string, React.CSSProperties> = {
  overlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background: 'rgba(0, 0, 0, 0.5)',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 2000,
    backdropFilter: 'blur(3px)',
  },
  modal: {
    background: 'white',
    borderRadius: '12px',
    boxShadow: '0 12px 40px rgba(0, 0, 0, 0.2)',
    minWidth: '400px',
    maxWidth: '500px',
    overflow: 'hidden',
  },
  header: {
    padding: '24px',
    borderBottom: '1px solid #e5e7eb',
  },
  headerTitle: {
    fontSize: '20px',
    fontWeight: '700',
    color: '#1a1a1a',
    margin: 0,
  },
  headerSubtitle: {
    fontSize: '14px',
    color: '#6b7280',
    marginTop: '6px',
  },
  body: {
    padding: '24px',
  },
  section: {
    marginBottom: '24px',
  },
  label: {
    fontSize: '14px',
    fontWeight: '600',
    color: '#374151',
    marginBottom: '12px',
    display: 'block',
  },
  starContainer: {
    display: 'flex',
    gap: '8px',
    alignItems: 'center',
  },
  star: {
    fontSize: '32px',
    cursor: 'pointer',
    transition: 'transform 0.2s, filter 0.2s',
    userSelect: 'none',
    filter: 'grayscale(100%)',
    opacity: 0.4,
  },
  starActive: {
    fontSize: '32px',
    cursor: 'pointer',
    transition: 'transform 0.2s, filter 0.2s',
    userSelect: 'none',
    transform: 'scale(1.2)',
    filter: 'grayscale(0%)',
    opacity: 1,
  },
  textarea: {
    width: '100%',
    minHeight: '120px',
    padding: '12px',
    fontSize: '14px',
    border: '1px solid #d1d5db',
    borderRadius: '8px',
    resize: 'vertical',
    fontFamily: 'inherit',
    outline: 'none',
    boxSizing: 'border-box',
  },
  footer: {
    padding: '16px 24px',
    borderTop: '1px solid #e5e7eb',
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '12px',
    background: '#f9fafb',
  },
  cancelButton: {
    padding: '10px 20px',
    fontSize: '14px',
    background: '#f3f4f6',
    color: '#374151',
    border: '1px solid #d1d5db',
    borderRadius: '8px',
    cursor: 'pointer',
    fontWeight: '600',
    transition: 'all 0.2s',
  },
  submitButton: {
    padding: '10px 20px',
    fontSize: '14px',
    background: '#3b82f6',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    fontWeight: '600',
    transition: 'all 0.2s',
  },
  submitButtonDisabled: {
    padding: '10px 20px',
    fontSize: '14px',
    background: '#d1d5db',
    color: '#9ca3af',
    border: 'none',
    borderRadius: '8px',
    cursor: 'not-allowed',
    fontWeight: '600',
  },
};

export default function FeedbackModal({
  slideId: _slideId,
  onClose,
  onSubmit,
}: FeedbackModalProps) {
  const [rating, setRating] = useState(0);
  const [hoveredRating, setHoveredRating] = useState(0);
  const [comment, setComment] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleOverlayClick = useCallback(
    (e: React.MouseEvent) => {
      if (e.target === e.currentTarget) {
        onClose();
      }
    },
    [onClose]
  );

  const handleSubmit = useCallback(async () => {
    if (rating === 0 || isSubmitting) return;

    setIsSubmitting(true);
    try {
      await onSubmit(rating, comment);
      onClose();
    } catch (err) {
      console.error('フィードバック送信エラー:', err);
      alert('フィードバックの送信に失敗しました');
    } finally {
      setIsSubmitting(false);
    }
  }, [rating, comment, isSubmitting, onSubmit, onClose]);

  const renderStars = () => {
    return [1, 2, 3, 4, 5].map((value) => {
      const displayRating = hoveredRating || rating;
      const isFilled = value <= displayRating;
      return (
        <span
          key={value}
          style={isFilled ? styles.starActive : styles.star}
          onClick={() => setRating(value)}
          onMouseEnter={() => setHoveredRating(value)}
          onMouseLeave={() => setHoveredRating(0)}
        >
          ⭐
        </span>
      );
    });
  };

  return (
    <div style={styles.overlay} onClick={handleOverlayClick}>
      <div style={styles.modal}>
        <div style={styles.header}>
          <h2 style={styles.headerTitle}>フィードバック</h2>
          <div style={styles.headerSubtitle}>
            このスライドの評価をお聞かせください
          </div>
        </div>

        <div style={styles.body}>
          {/* 評価スター */}
          <div style={styles.section}>
            <label style={styles.label}>評価（必須）</label>
            <div style={styles.starContainer}>{renderStars()}</div>
          </div>

          {/* コメント */}
          <div style={styles.section}>
            <label style={styles.label}>コメント（任意）</label>
            <textarea
              style={styles.textarea}
              placeholder="ご意見・ご感想をお聞かせください..."
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              onFocus={(e) => {
                e.currentTarget.style.borderColor = '#3b82f6';
              }}
              onBlur={(e) => {
                e.currentTarget.style.borderColor = '#d1d5db';
              }}
            />
          </div>
        </div>

        <div style={styles.footer}>
          <button
            onClick={onClose}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = '#e5e7eb';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = '#f3f4f6';
            }}
            style={styles.cancelButton}
            disabled={isSubmitting}
          >
            キャンセル
          </button>
          <button
            onClick={handleSubmit}
            onMouseEnter={(e) => {
              if (rating > 0 && !isSubmitting) {
                e.currentTarget.style.background = '#2563eb';
              }
            }}
            onMouseLeave={(e) => {
              if (rating > 0 && !isSubmitting) {
                e.currentTarget.style.background = '#3b82f6';
              }
            }}
            style={
              rating === 0 || isSubmitting
                ? styles.submitButtonDisabled
                : styles.submitButton
            }
            disabled={rating === 0 || isSubmitting}
          >
            {isSubmitting ? '送信中...' : '送信'}
          </button>
        </div>
      </div>
    </div>
  );
}

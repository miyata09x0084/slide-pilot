/**
 * DropzoneCard - ドラッグ&ドロップ対応のファイルアップロードカード
 * アップロード進捗とエラー状態を表示
 */

import { useState, useRef } from 'react';

type UploadState = 'idle' | 'dragging' | 'uploading' | 'success' | 'error';

interface DropzoneCardProps {
  onUploadSuccess: (data: { path: string }) => void;
  onUploadStart?: () => void;
  userId?: string;  // ユーザーID（Google OAuth email等）
}

const styles: Record<string, React.CSSProperties> = {
  card: {
    height: '100%',
    minHeight: '200px',
    background: 'linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%)',
    border: '3px solid #3b82f6',
    borderRadius: '12px',
    padding: '28px 24px',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center',
    alignItems: 'center',
    textAlign: 'center',
    cursor: 'pointer',
    transition: 'all 0.2s',
    position: 'relative',
    overflow: 'hidden',
    boxSizing: 'border-box',
  },
  cardDragging: {
    height: '100%',
    minHeight: '200px',
    background: 'linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%)',
    border: '3px dashed #3b82f6',
    borderRadius: '12px',
    padding: '28px 24px',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center',
    alignItems: 'center',
    textAlign: 'center',
    cursor: 'pointer',
    transition: 'all 0.2s',
    position: 'relative',
    overflow: 'hidden',
    boxSizing: 'border-box',
  },
  cardUploading: {
    height: '100%',
    minHeight: '200px',
    background: '#f0f9ff',
    border: '2px solid #60a5fa',
    borderRadius: '12px',
    padding: '28px 24px',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center',
    alignItems: 'center',
    textAlign: 'center',
    cursor: 'default',
    transition: 'all 0.2s',
    position: 'relative',
    overflow: 'hidden',
    boxSizing: 'border-box',
  },
  cardSuccess: {
    height: '100%',
    minHeight: '200px',
    background: '#f0fdf4',
    border: '2px solid #22c55e',
    borderRadius: '12px',
    padding: '28px 24px',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center',
    alignItems: 'center',
    textAlign: 'center',
    cursor: 'default',
    transition: 'all 0.2s',
    position: 'relative',
    overflow: 'hidden',
    boxSizing: 'border-box',
  },
  cardError: {
    height: '100%',
    minHeight: '200px',
    background: '#fef2f2',
    border: '2px solid #ef4444',
    borderRadius: '12px',
    padding: '28px 24px',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center',
    alignItems: 'center',
    textAlign: 'center',
    cursor: 'pointer',
    transition: 'all 0.2s',
    position: 'relative',
    overflow: 'hidden',
    boxSizing: 'border-box',
  },
  icon: {
    fontSize: '64px',
    marginBottom: '12px',
    fontWeight: '300',
    lineHeight: '1',
  },
  title: {
    fontSize: '17px',
    fontWeight: '700',
    color: '#1a1a1a',
    lineHeight: '1.3',
    wordBreak: 'break-word',
    marginBottom: '6px',
  },
  subtitle: {
    fontSize: '13px',
    color: '#6b7280',
    lineHeight: '1.4',
  },
  progressContainer: {
    width: '100%',
    marginTop: '12px',
  },
  progressBar: {
    width: '100%',
    height: '8px',
    background: '#e5e7eb',
    borderRadius: '4px',
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    background: '#3b82f6',
    transition: 'width 0.3s ease',
  },
  progressText: {
    fontSize: '11px',
    color: '#6b7280',
    marginTop: '4px',
  },
  errorText: {
    fontSize: '12px',
    color: '#ef4444',
    marginTop: '8px',
    maxWidth: '100%',
    wordBreak: 'break-word',
  },
  retryButton: {
    marginTop: '8px',
    padding: '6px 12px',
    fontSize: '12px',
    background: '#3b82f6',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontWeight: '600',
  },
};

export default function DropzoneCard({ onUploadSuccess, onUploadStart, userId }: DropzoneCardProps) {
  const [state, setState] = useState<UploadState>('idle');
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string>('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (state === 'idle' || state === 'error') {
      setState('dragging');
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (state === 'dragging') {
      setState('idle');
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setState('idle');

    const file = e.dataTransfer.files?.[0];
    if (file) {
      uploadFile(file);
    }
  };

  const handleClick = () => {
    if (state === 'idle' || state === 'error') {
      fileInputRef.current?.click();
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      uploadFile(file);
    }
  };

  const uploadFile = async (file: File) => {
    // ファイルサイズチェック
    if (file.size > 100 * 1024 * 1024) {
      setError('ファイルサイズは100MB以下にしてください');
      setState('error');
      return;
    }

    // ファイル形式チェック
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setError('PDFファイルのみアップロード可能です');
      setState('error');
      return;
    }

    setState('uploading');
    setProgress(0);
    setError('');
    onUploadStart?.();

    try {
      const formData = new FormData();
      formData.append('file', file);

      const xhr = new XMLHttpRequest();

      // アップロード進捗
      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) {
          const percentComplete = Math.round((e.loaded / e.total) * 100);
          setProgress(percentComplete);
        }
      });

      // 完了
      xhr.addEventListener('load', () => {
        if (xhr.status === 200) {
          const data = JSON.parse(xhr.responseText);
          setState('success');
          setProgress(100);

          // 1秒後にコールバック実行（成功状態を見せるため）
          setTimeout(() => {
            onUploadSuccess(data);
          }, 1000);
        } else {
          const errorData = JSON.parse(xhr.responseText);
          throw new Error(errorData.detail || 'アップロード失敗');
        }
      });

      // エラー
      xhr.addEventListener('error', () => {
        setError('ネットワークエラーが発生しました');
        setState('error');
        setProgress(0);
      });

      // タイムアウト
      xhr.addEventListener('timeout', () => {
        setError('アップロードがタイムアウトしました');
        setState('error');
        setProgress(0);
      });

      // user_idをクエリパラメータで送信
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8001/api';
      const uploadUrl = `${apiUrl}/upload-pdf${userId ? `?user_id=${encodeURIComponent(userId)}` : ''}`;

      xhr.open('POST', uploadUrl);
      xhr.timeout = 60000; // 60秒
      xhr.send(formData);
    } catch (err: any) {
      console.error('❌ Upload error:', err);
      setError(err.message || 'アップロードに失敗しました');
      setState('error');
      setProgress(0);
    }
  };

  const handleRetry = () => {
    setState('idle');
    setError('');
    setProgress(0);
  };

  // 状態に応じたスタイル
  const getCardStyle = () => {
    switch (state) {
      case 'dragging':
        return styles.cardDragging;
      case 'uploading':
        return styles.cardUploading;
      case 'success':
        return styles.cardSuccess;
      case 'error':
        return styles.cardError;
      default:
        return styles.card;
    }
  };

  // 状態に応じた表示内容
  const getContent = () => {
    switch (state) {
      case 'dragging':
        return {
          icon: '⬇️',
          title: 'ここにドロップ',
          subtitle: 'PDFファイルをドロップしてください',
        };
      case 'uploading':
        return {
          icon: '📤',
          title: 'アップロード中...',
          subtitle: `${progress}%`,
        };
      case 'success':
        return {
          icon: '✅',
          title: 'アップロード完了',
          subtitle: 'スライド生成を開始します',
        };
      case 'error':
        return {
          icon: '❌',
          title: 'エラー',
          subtitle: '',
        };
      default:
        return {
          icon: '+',
          title: '新規作成',
          subtitle: 'PDFをアップロード',
        };
    }
  };

  const content = getContent();

  return (
    <>
      <div
        className="card-primary"
        style={getCardStyle()}
        onClick={handleClick}
        onDragEnter={handleDragEnter}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onMouseEnter={(e) => {
          if (state === 'idle' || state === 'error') {
            e.currentTarget.style.borderColor = '#2563eb';
            e.currentTarget.style.boxShadow = '0 4px 8px rgba(0,0,0,0.12)';
            e.currentTarget.style.background = state === 'idle' ? 'linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%)' : '#fee2e2';
          }
        }}
        onMouseLeave={(e) => {
          if (state === 'idle' || state === 'error') {
            e.currentTarget.style.borderColor = state === 'idle' ? '#3b82f6' : '#ef4444';
            e.currentTarget.style.boxShadow = 'none';
            e.currentTarget.style.background = state === 'idle' ? 'linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%)' : '#fef2f2';
          }
        }}
      >
        <div style={styles.icon}>{content.icon}</div>
        <div>
          <div style={styles.title}>{content.title}</div>
          {content.subtitle && <div style={styles.subtitle}>{content.subtitle}</div>}
        </div>

        {/* 進捗バー */}
        {state === 'uploading' && (
          <div style={styles.progressContainer}>
            <div style={styles.progressBar}>
              <div style={{ ...styles.progressFill, width: `${progress}%` }} />
            </div>
          </div>
        )}

        {/* エラーメッセージ */}
        {state === 'error' && error && (
          <>
            <div style={styles.errorText}>{error}</div>
            <button
              style={styles.retryButton}
              onClick={(e) => {
                e.stopPropagation();
                handleRetry();
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = '#2563eb';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = '#3b82f6';
              }}
            >
              再試行
            </button>
          </>
        )}
      </div>

      {/* 隠しファイル入力 */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf"
        style={{ display: 'none' }}
        onChange={handleFileSelect}
      />
    </>
  );
}

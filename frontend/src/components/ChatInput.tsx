// チャット入力欄コンポーネント
// メッセージ送信とローディング状態を管理

import { useState, KeyboardEvent } from 'react';

interface ChatInputProps {
  onSend: (message: string) => void;  // メッセージ送信時のコールバック
  disabled?: boolean;                 // 送信無効化フラグ
  placeholder?: string;               // プレースホルダー文言
}

export default function ChatInput({ onSend, disabled = false, placeholder = 'メッセージを入力...' }: ChatInputProps) {
  const [input, setInput] = useState('');

  // 送信処理
  const handleSend = () => {
    const trimmed = input.trim();
    if (trimmed && !disabled) {
      onSend(trimmed);
      setInput(''); // 送信後は入力欄をクリア
    }
  };

  // Enter キーで送信（Shift+Enter は改行）
  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div style={{
      display: 'flex',
      gap: '12px',
      padding: '16px',
      borderTop: '1px solid #dee2e6',
      background: 'white',
      position: 'sticky',
      bottom: 0
    }}>
      {/* 入力欄 */}
      <textarea
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        rows={1}
        style={{
          flex: 1,
          padding: '12px',
          fontSize: '15px',
          border: '2px solid #ddd',
          borderRadius: '8px',
          outline: 'none',
          resize: 'none',
          fontFamily: 'inherit',
          maxHeight: '120px',
          minHeight: '48px'
        }}
        onFocus={(e) => !disabled && (e.target.style.borderColor = '#007bff')}
        onBlur={(e) => e.target.style.borderColor = '#ddd'}
      />

      {/* 送信ボタン */}
      <button
        onClick={handleSend}
        disabled={disabled || !input.trim()}
        style={{
          padding: '12px 24px',
          fontSize: '15px',
          background: (disabled || !input.trim()) ? '#ccc' : '#007bff',
          color: 'white',
          border: 'none',
          borderRadius: '8px',
          cursor: (disabled || !input.trim()) ? 'not-allowed' : 'pointer',
          fontWeight: 'bold',
          whiteSpace: 'nowrap'
        }}
        onMouseOver={(e) => {
          if (!disabled && input.trim()) {
            e.currentTarget.style.background = '#0056b3';
          }
        }}
        onMouseOut={(e) => {
          if (!disabled && input.trim()) {
            e.currentTarget.style.background = '#007bff';
          }
        }}
      >
        送信
      </button>
    </div>
  );
}

// メッセージ表示コンポーネント
// ユーザーとアシスタントのメッセージを区別して表示

export interface Message {
  role: 'user' | 'assistant';
  content: string;
}

interface ChatMessageProps {
  message: Message;
}

export default function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';

  return (
    <>
      <div style={{
        display: 'flex',
        gap: '12px',
        marginBottom: '16px',
        justifyContent: isUser ? 'flex-end' : 'flex-start'
      }}>
        {/* アシスタントの場合、左にアバター */}
        {!isUser && (
          <div className="avatar" style={{
            width: '36px',
            height: '36px',
            borderRadius: '50%',
            background: '#007bff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '18px',
            flexShrink: 0
          }}>
            🤖
          </div>
        )}

        {/* メッセージ本体 */}
        <div className="message-content" style={{
          maxWidth: '70%',
          padding: '12px 16px',
          borderRadius: '12px',
          background: isUser ? '#007bff' : '#f1f3f4',
          color: isUser ? 'white' : '#333',
          fontSize: '15px',
          lineHeight: '1.5',
          wordBreak: 'break-word',
          whiteSpace: 'pre-wrap'
        }}>
          {message.content}
        </div>

        {/* ユーザーの場合、右にアバター */}
        {isUser && (
          <div className="avatar" style={{
            width: '36px',
            height: '36px',
            borderRadius: '50%',
            background: '#6c757d',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '18px',
            flexShrink: 0
          }}>
            👤
          </div>
        )}
      </div>

      {/* レスポンシブ対応のCSS */}
      <style>{`
        @media (max-width: 768px) {
          .message-content {
            max-width: 85% !important;
            font-size: 14px !important;
            padding: 10px 14px !important;
          }
          .avatar {
            width: 32px !important;
            height: 32px !important;
            font-size: 16px !important;
          }
        }
      `}</style>
    </>
  );
}

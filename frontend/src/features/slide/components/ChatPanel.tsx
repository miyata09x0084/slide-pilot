/**
 * ChatPanel
 * スライド専用チャットパネル（Phase 3: UI のみ）
 */

import { useState } from 'react';
import { ChatMessage } from '../../../shared';
import type { Message } from '@/types';

interface ChatPanelProps {
  slideId: string;
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
  },
  header: {
    marginBottom: '20px',
    paddingBottom: '16px',
    borderBottom: '2px solid #e0e0e0',
  },
  title: {
    fontSize: '20px',
    fontWeight: 'bold',
    color: '#333',
    marginBottom: '8px',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  subtitle: {
    fontSize: '14px',
    color: '#666',
  },
  messagesContainer: {
    flex: 1,
    overflowY: 'auto',
    marginBottom: '16px',
    padding: '12px',
    background: '#f8f9fa',
    borderRadius: '8px',
  },
  emptyState: {
    textAlign: 'center',
    padding: '40px 20px',
    color: '#999',
  },
  emptyIcon: {
    fontSize: '48px',
    marginBottom: '16px',
  },
  emptyText: {
    fontSize: '14px',
    lineHeight: '1.6',
  },
  notice: {
    padding: '12px 16px',
    background: '#fff3cd',
    border: '1px solid #ffeaa7',
    borderRadius: '6px',
    fontSize: '14px',
    color: '#856404',
    marginTop: '12px',
    textAlign: 'center',
  },
};

export default function ChatPanel({ slideId: _slideId }: ChatPanelProps) {
  const [messages] = useState<Message[]>([]);

  return (
    <div style={styles.container}>
      {/* ヘッダー */}
      <div style={styles.header}>
        <h3 style={styles.title}>
          <span>💬</span>
          <span>スライドについて質問</span>
        </h3>
        <p style={styles.subtitle}>
          RAGでPDF内容を参照して回答します
        </p>
      </div>

      {/* メッセージ表示エリア */}
      <div style={styles.messagesContainer}>
        {messages.length === 0 ? (
          <div style={styles.emptyState}>
            <div style={styles.emptyIcon}>🤖</div>
            <div style={styles.emptyText}>
              スライドの内容について何でも質問してください。
              <br />
              AIがPDF内容を参照して回答します。
            </div>
          </div>
        ) : (
          messages.map((msg, i) => (
            <ChatMessage key={i} message={msg} />
          ))
        )}
      </div>

      {/* Phase 4 実装予定の通知 */}
      <div style={styles.notice}>
        💬 RAGチャット機能は Phase 4 で実装予定です
      </div>
    </div>
  );
}

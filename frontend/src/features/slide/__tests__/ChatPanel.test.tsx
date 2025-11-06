/**
 * ChatPanel コンポーネントのテスト
 * スライド専用チャットパネル
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import ChatPanel from '../components/ChatPanel';

describe('ChatPanel', () => {
  describe('基本レンダリング', () => {
    it('ヘッダーが表示される', () => {
      render(<ChatPanel slideId="test-slide-123" />);

      expect(screen.getByText('💬')).toBeInTheDocument();
      expect(screen.getByText('スライドについて質問')).toBeInTheDocument();
      expect(screen.getByText('RAGでPDF内容を参照して回答します')).toBeInTheDocument();
    });

    it('メッセージが空の場合、空状態が表示される', () => {
      render(<ChatPanel slideId="test-slide-123" />);

      expect(screen.getByText('🤖')).toBeInTheDocument();
      expect(
        screen.getByText((content) => content.includes('スライドの内容について何でも質問してください'))
      ).toBeInTheDocument();
    });

    it('Phase 4 実装予定の通知が表示される', () => {
      render(<ChatPanel slideId="test-slide-123" />);

      expect(
        screen.getByText((content) => content.includes('RAGチャット機能は Phase 4 で実装予定です'))
      ).toBeInTheDocument();
    });
  });

  describe('slideId プロパティ', () => {
    it('異なるslideIdを受け取ることができる', () => {
      const { rerender } = render(<ChatPanel slideId="slide-1" />);
      expect(screen.getByText('スライドについて質問')).toBeInTheDocument();

      rerender(<ChatPanel slideId="slide-2" />);
      expect(screen.getByText('スライドについて質問')).toBeInTheDocument();
    });
  });
});

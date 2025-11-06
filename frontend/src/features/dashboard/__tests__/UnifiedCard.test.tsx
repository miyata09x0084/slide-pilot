/**
 * UnifiedCard コンポーネントのテスト
 * ダッシュボードの統一カードコンポーネント
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import UnifiedCard from '../components/UnifiedCard';

describe('UnifiedCard', () => {
  describe('基本レンダリング', () => {
    it('タイトルとアイコンが表示される', () => {
      const handleClick = vi.fn();
      render(
        <UnifiedCard title="テストカード" icon="📝" onClick={handleClick} />
      );

      expect(screen.getByText('テストカード')).toBeInTheDocument();
      expect(screen.getByText('📝')).toBeInTheDocument();
    });

    it('subtitle が指定された場合に表示される', () => {
      const handleClick = vi.fn();
      render(
        <UnifiedCard
          title="テストカード"
          subtitle="サブタイトル"
          icon="📄"
          onClick={handleClick}
        />
      );

      expect(screen.getByText('テストカード')).toBeInTheDocument();
      expect(screen.getByText('サブタイトル')).toBeInTheDocument();
    });

    it('subtitle が未指定の場合は表示されない', () => {
      const handleClick = vi.fn();
      render(
        <UnifiedCard title="テストカード" icon="📝" onClick={handleClick} />
      );

      expect(screen.queryByText('サブタイトル')).not.toBeInTheDocument();
    });
  });

  describe('バリアント（variant）', () => {
    it('variant="default" で通常スタイルが適用される', () => {
      const handleClick = vi.fn();
      const { container } = render(
        <UnifiedCard
          title="デフォルト"
          icon="📝"
          onClick={handleClick}
          variant="default"
        />
      );

      const card = container.firstChild as HTMLElement;
      expect(card).toHaveStyle({ background: '#ffffff' });
    });

    it('variant="primary" でプライマリスタイルが適用される', () => {
      const handleClick = vi.fn();
      const { container } = render(
        <UnifiedCard
          title="プライマリ"
          icon="⭐"
          onClick={handleClick}
          variant="primary"
        />
      );

      const card = container.firstChild as HTMLElement;
      expect(card).toHaveStyle({ background: '#eff6ff' });
    });

    it('variant="history" で履歴スタイルが適用される', () => {
      const handleClick = vi.fn();
      const { container } = render(
        <UnifiedCard
          title="履歴"
          icon="📜"
          onClick={handleClick}
          variant="history"
        />
      );

      const card = container.firstChild as HTMLElement;
      expect(card).toHaveStyle({ background: '#f9fafb' });
    });

    it('variant="more" でmoreスタイルが適用される', () => {
      const handleClick = vi.fn();
      const { container } = render(
        <UnifiedCard
          title="もっと見る"
          icon="➕"
          onClick={handleClick}
          variant="more"
        />
      );

      const card = container.firstChild as HTMLElement;
      expect(card).toHaveStyle({ border: '2px dashed #d1d5db' });
    });
  });

  describe('インタラクション', () => {
    it('クリック時に onClick ハンドラーが呼ばれる', () => {
      const handleClick = vi.fn();
      const { container } = render(
        <UnifiedCard title="クリック可能" icon="🔗" onClick={handleClick} />
      );

      const card = container.firstChild as HTMLElement;
      fireEvent.click(card);

      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it('マウスホバー時にスタイルが変更される', () => {
      const handleClick = vi.fn();
      const { container } = render(
        <UnifiedCard title="ホバー" icon="👆" onClick={handleClick} />
      );

      const card = container.firstChild as HTMLElement;
      const originalBorderColor = card.style.borderColor;

      // ホバー
      fireEvent.mouseEnter(card);
      expect(card.style.borderColor).toBe('rgb(59, 130, 246)'); // #3b82f6

      // ホバー解除
      fireEvent.mouseLeave(card);
      expect(card.style.borderColor).toBe(originalBorderColor || 'rgb(229, 231, 235)');
    });

    it('複数回クリックできる', () => {
      const handleClick = vi.fn();
      const { container } = render(
        <UnifiedCard title="複数クリック" icon="🖱️" onClick={handleClick} />
      );

      const card = container.firstChild as HTMLElement;
      fireEvent.click(card);
      fireEvent.click(card);
      fireEvent.click(card);

      expect(handleClick).toHaveBeenCalledTimes(3);
    });
  });

  describe('カスタムクラス名', () => {
    it('className が適用される', () => {
      const handleClick = vi.fn();
      const { container } = render(
        <UnifiedCard
          title="カスタムクラス"
          icon="🎨"
          onClick={handleClick}
          className="custom-class"
        />
      );

      const card = container.firstChild as HTMLElement;
      expect(card).toHaveClass('custom-class');
    });
  });
});

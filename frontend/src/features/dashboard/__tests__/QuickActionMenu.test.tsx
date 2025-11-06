/**
 * QuickActionMenu コンポーネントのテスト
 * 新規作成時のクイックアクションメニュー
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import QuickActionMenu from '../components/QuickActionMenu';

describe('QuickActionMenu', () => {
  describe('基本レンダリング', () => {
    it('メニューが表示される', () => {
      const onClose = vi.fn();
      const onSelectUpload = vi.fn();
      const onSelectTemplate = vi.fn();

      render(
        <QuickActionMenu
          onClose={onClose}
          onSelectUpload={onSelectUpload}
          onSelectTemplate={onSelectTemplate}
        />
      );

      expect(screen.getByText('新規作成')).toBeInTheDocument();
      expect(screen.getByText('作成方法を選択してください')).toBeInTheDocument();
    });

    it('PDFアップロードボタンが表示される', () => {
      const onClose = vi.fn();
      const onSelectUpload = vi.fn();
      const onSelectTemplate = vi.fn();

      render(
        <QuickActionMenu
          onClose={onClose}
          onSelectUpload={onSelectUpload}
          onSelectTemplate={onSelectTemplate}
        />
      );

      expect(screen.getByText('PDFをアップロード')).toBeInTheDocument();
      expect(screen.getByText('PDFファイルからスライドを作成')).toBeInTheDocument();
    });

    it('テンプレートボタンが3つ表示される', () => {
      const onClose = vi.fn();
      const onSelectUpload = vi.fn();
      const onSelectTemplate = vi.fn();

      render(
        <QuickActionMenu
          onClose={onClose}
          onSelectUpload={onSelectUpload}
          onSelectTemplate={onSelectTemplate}
        />
      );

      expect(screen.getByText('AI最新ニュース')).toBeInTheDocument();
      expect(screen.getByText('機械学習入門')).toBeInTheDocument();
      expect(screen.getByText('教科書要約')).toBeInTheDocument();
    });
  });

  describe('インタラクション - PDFアップロード', () => {
    it('PDFアップロードボタンクリックで onSelectUpload と onClose が呼ばれる', () => {
      const onClose = vi.fn();
      const onSelectUpload = vi.fn();
      const onSelectTemplate = vi.fn();

      render(
        <QuickActionMenu
          onClose={onClose}
          onSelectUpload={onSelectUpload}
          onSelectTemplate={onSelectTemplate}
        />
      );

      const uploadButton = screen.getByText('PDFをアップロード').closest('button')!;
      fireEvent.click(uploadButton);

      expect(onClose).toHaveBeenCalledTimes(1);
      expect(onSelectUpload).toHaveBeenCalledTimes(1);
      expect(onSelectTemplate).not.toHaveBeenCalled();
    });
  });

  describe('インタラクション - テンプレート選択', () => {
    it('AI最新ニュース選択で onSelectTemplate("ai-news") が呼ばれる', () => {
      const onClose = vi.fn();
      const onSelectUpload = vi.fn();
      const onSelectTemplate = vi.fn();

      render(
        <QuickActionMenu
          onClose={onClose}
          onSelectUpload={onSelectUpload}
          onSelectTemplate={onSelectTemplate}
        />
      );

      const aiNewsButton = screen.getByText('AI最新ニュース').closest('button')!;
      fireEvent.click(aiNewsButton);

      expect(onClose).toHaveBeenCalledTimes(1);
      expect(onSelectTemplate).toHaveBeenCalledWith('ai-news');
      expect(onSelectUpload).not.toHaveBeenCalled();
    });

    it('機械学習入門選択で onSelectTemplate("ml-basics") が呼ばれる', () => {
      const onClose = vi.fn();
      const onSelectUpload = vi.fn();
      const onSelectTemplate = vi.fn();

      render(
        <QuickActionMenu
          onClose={onClose}
          onSelectUpload={onSelectUpload}
          onSelectTemplate={onSelectTemplate}
        />
      );

      const mlButton = screen.getByText('機械学習入門').closest('button')!;
      fireEvent.click(mlButton);

      expect(onClose).toHaveBeenCalledTimes(1);
      expect(onSelectTemplate).toHaveBeenCalledWith('ml-basics');
    });

    it('教科書要約選択で onSelectTemplate("textbook") が呼ばれる', () => {
      const onClose = vi.fn();
      const onSelectUpload = vi.fn();
      const onSelectTemplate = vi.fn();

      render(
        <QuickActionMenu
          onClose={onClose}
          onSelectUpload={onSelectUpload}
          onSelectTemplate={onSelectTemplate}
        />
      );

      const textbookButton = screen.getByText('教科書要約').closest('button')!;
      fireEvent.click(textbookButton);

      expect(onClose).toHaveBeenCalledTimes(1);
      expect(onSelectTemplate).toHaveBeenCalledWith('textbook');
    });
  });

  describe('インタラクション - オーバーレイ', () => {
    it('オーバーレイクリックで onClose が呼ばれる', () => {
      const onClose = vi.fn();
      const onSelectUpload = vi.fn();
      const onSelectTemplate = vi.fn();

      const { container } = render(
        <QuickActionMenu
          onClose={onClose}
          onSelectUpload={onSelectUpload}
          onSelectTemplate={onSelectTemplate}
        />
      );

      // オーバーレイは最初の div
      const overlay = container.firstChild as HTMLElement;
      fireEvent.click(overlay);

      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it('メニュー内をクリックしても onClose は呼ばれない', () => {
      const onClose = vi.fn();
      const onSelectUpload = vi.fn();
      const onSelectTemplate = vi.fn();

      render(
        <QuickActionMenu
          onClose={onClose}
          onSelectUpload={onSelectUpload}
          onSelectTemplate={onSelectTemplate}
        />
      );

      // メニュー内のヘッダーをクリック
      const header = screen.getByText('新規作成');
      fireEvent.click(header);

      expect(onClose).not.toHaveBeenCalled();
    });
  });

  describe('ホバー効果', () => {
    it('PDFボタンにマウスホバーでスタイルが変更される', () => {
      const onClose = vi.fn();
      const onSelectUpload = vi.fn();
      const onSelectTemplate = vi.fn();

      render(
        <QuickActionMenu
          onClose={onClose}
          onSelectUpload={onSelectUpload}
          onSelectTemplate={onSelectTemplate}
        />
      );

      const uploadButton = screen.getByText('PDFをアップロード').closest('button')!;

      fireEvent.mouseEnter(uploadButton);
      expect(uploadButton.style.background).toBe('rgb(219, 234, 254)'); // #dbeafe

      fireEvent.mouseLeave(uploadButton);
      expect(uploadButton.style.background).toBe('rgb(239, 246, 255)'); // #eff6ff
    });

    it('テンプレートボタンにマウスホバーでスタイルが変更される', () => {
      const onClose = vi.fn();
      const onSelectUpload = vi.fn();
      const onSelectTemplate = vi.fn();

      render(
        <QuickActionMenu
          onClose={onClose}
          onSelectUpload={onSelectUpload}
          onSelectTemplate={onSelectTemplate}
        />
      );

      const aiNewsButton = screen.getByText('AI最新ニュース').closest('button')!;

      fireEvent.mouseEnter(aiNewsButton);
      expect(aiNewsButton.style.background).toBe('rgb(249, 250, 251)'); // #f9fafb

      fireEvent.mouseLeave(aiNewsButton);
      expect(aiNewsButton.style.background).toBe('white');
    });
  });
});

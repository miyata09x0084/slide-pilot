/**
 * QuickActionMenu コンポーネントのテスト
 * 新規作成時のクイックアクションメニュー（更新版: 準備中項目対応）
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import QuickActionMenu from '../components/QuickActionMenu';

describe('QuickActionMenu', () => {
  describe('基本レンダリング', () => {
    it('メニューが表示される', () => {
      const onClose = vi.fn();
      const onSelectUpload = vi.fn();

      render(
        <QuickActionMenu
          onClose={onClose}
          onSelectUpload={onSelectUpload}
        />
      );

      expect(screen.getByText('新規作成')).toBeInTheDocument();
      expect(screen.getByText('PDFアップロードで資料を理解しやすく')).toBeInTheDocument();
    });

    it('PDFアップロードボタンが表示される', () => {
      const onClose = vi.fn();
      const onSelectUpload = vi.fn();

      render(
        <QuickActionMenu
          onClose={onClose}
          onSelectUpload={onSelectUpload}
        />
      );

      expect(screen.getByText('PDFをアップロード')).toBeInTheDocument();
      expect(screen.getByText('PDFを理解しやすいスライドに変換')).toBeInTheDocument();
    });

    it('準備中項目が2つ表示される', () => {
      const onClose = vi.fn();
      const onSelectUpload = vi.fn();

      render(
        <QuickActionMenu
          onClose={onClose}
          onSelectUpload={onSelectUpload}
        />
      );

      expect(screen.getByText('WebページURL')).toBeInTheDocument();
      expect(screen.getByText('動画URL')).toBeInTheDocument();
      expect(screen.getAllByText('🔒 準備中')).toHaveLength(2);
    });
  });

  describe('インタラクション - PDFアップロード', () => {
    it('PDFアップロードボタンクリックで onSelectUpload と onClose が呼ばれる', () => {
      const onClose = vi.fn();
      const onSelectUpload = vi.fn();

      render(
        <QuickActionMenu
          onClose={onClose}
          onSelectUpload={onSelectUpload}
        />
      );

      const uploadButton = screen.getByText('PDFをアップロード').closest('button')!;
      fireEvent.click(uploadButton);

      expect(onClose).toHaveBeenCalledTimes(1);
      expect(onSelectUpload).toHaveBeenCalledTimes(1);
    });
  });

  describe('インタラクション - 準備中項目', () => {
    it('準備中項目はdiv要素で、クリックできない', () => {
      const onClose = vi.fn();
      const onSelectUpload = vi.fn();

      render(
        <QuickActionMenu
          onClose={onClose}
          onSelectUpload={onSelectUpload}
        />
      );

      // WebページURLとVideo URLはdiv要素（ボタンではない）
      const webpageItem = screen.getByText('WebページURL').closest('div')!;
      const videoItem = screen.getByText('動画URL').closest('div')!;

      expect(webpageItem.tagName).toBe('DIV');
      expect(videoItem.tagName).toBe('DIV');

      // クリックしても何も起こらない
      fireEvent.click(webpageItem);
      fireEvent.click(videoItem);

      expect(onSelectUpload).not.toHaveBeenCalled();
      expect(onClose).not.toHaveBeenCalled();
    });
  });

  describe('インタラクション - オーバーレイ', () => {
    it('オーバーレイクリックで onClose が呼ばれる', () => {
      const onClose = vi.fn();
      const onSelectUpload = vi.fn();

      const { container } = render(
        <QuickActionMenu
          onClose={onClose}
          onSelectUpload={onSelectUpload}
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

      render(
        <QuickActionMenu
          onClose={onClose}
          onSelectUpload={onSelectUpload}
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

      render(
        <QuickActionMenu
          onClose={onClose}
          onSelectUpload={onSelectUpload}
        />
      );

      const uploadButton = screen.getByText('PDFをアップロード').closest('button')!;

      fireEvent.mouseEnter(uploadButton);
      expect(uploadButton.style.background).toBe('rgb(219, 234, 254)'); // #dbeafe

      fireEvent.mouseLeave(uploadButton);
      expect(uploadButton.style.background).toBe('rgb(239, 246, 255)'); // #eff6ff
    });
  });
});

/**
 * DropzoneCard コンポーネントのテスト
 * ドラッグ&ドロップ対応のファイルアップロードカード
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import DropzoneCard from '../components/DropzoneCard';

// XMLHttpRequest をモック
class MockXMLHttpRequest {
  public upload = {
    addEventListener: vi.fn(),
  };
  public addEventListener = vi.fn();
  public open = vi.fn();
  public send = vi.fn();
  public timeout = 0;
  public status = 200;
  public responseText = '{}';

  // テスト用のヘルパーメソッド
  triggerProgress(loaded: number, total: number) {
    const progressCallback = this.upload.addEventListener.mock.calls.find(
      (call) => call[0] === 'progress'
    )?.[1];
    if (progressCallback) {
      progressCallback({ lengthComputable: true, loaded, total });
    }
  }

  triggerLoad() {
    const loadCallback = this.addEventListener.mock.calls.find(
      (call) => call[0] === 'load'
    )?.[1];
    if (loadCallback) {
      loadCallback();
    }
  }

  triggerError() {
    const errorCallback = this.addEventListener.mock.calls.find(
      (call) => call[0] === 'error'
    )?.[1];
    if (errorCallback) {
      errorCallback();
    }
  }

  triggerTimeout() {
    const timeoutCallback = this.addEventListener.mock.calls.find(
      (call) => call[0] === 'timeout'
    )?.[1];
    if (timeoutCallback) {
      timeoutCallback();
    }
  }
}

describe('DropzoneCard', () => {
  let mockXHR: MockXMLHttpRequest;

  beforeEach(() => {
    vi.clearAllMocks();
    mockXHR = new MockXMLHttpRequest();
    // @ts-ignore
    global.XMLHttpRequest = vi.fn(() => mockXHR);
  });

  describe('基本レンダリング', () => {
    it('初期状態で新規作成カードが表示される', () => {
      const onUploadSuccess = vi.fn();
      render(<DropzoneCard onUploadSuccess={onUploadSuccess} />);

      expect(screen.getByText('新規作成')).toBeInTheDocument();
      expect(screen.getByText('PDFをアップロード')).toBeInTheDocument();
      expect(screen.getByText('+')).toBeInTheDocument();
    });

    it('カードがクリック可能である', () => {
      const onUploadSuccess = vi.fn();
      const { container } = render(<DropzoneCard onUploadSuccess={onUploadSuccess} />);

      const card = container.querySelector('.card-primary');
      expect(card).toBeInTheDocument();
      expect(card).toHaveStyle({ cursor: 'pointer' });
    });
  });

  describe('ドラッグ&ドロップ', () => {
    it('ファイルドラッグ時に dragging 状態になる', () => {
      const onUploadSuccess = vi.fn();
      const { container } = render(<DropzoneCard onUploadSuccess={onUploadSuccess} />);

      const card = container.querySelector('.card-primary')!;

      const dragEvent = new Event('dragenter', { bubbles: true });
      Object.defineProperty(dragEvent, 'dataTransfer', {
        value: { files: [] },
      });

      fireEvent(card, dragEvent);

      // dragging状態の確認（アイコンが変わる）
      expect(screen.getByText('⬇️')).toBeInTheDocument();
      expect(screen.getByText('ここにドロップ')).toBeInTheDocument();
    });

    it('ドラッグリーブで idle 状態に戻る', () => {
      const onUploadSuccess = vi.fn();
      const { container } = render(<DropzoneCard onUploadSuccess={onUploadSuccess} />);

      const card = container.querySelector('.card-primary')!;

      // ドラッグエンター
      fireEvent.dragEnter(card);
      expect(screen.getByText('⬇️')).toBeInTheDocument();

      // ドラッグリーブ
      fireEvent.dragLeave(card);
      expect(screen.getByText('+')).toBeInTheDocument();
    });

    it('ファイルドロップでアップロード開始', async () => {
      const onUploadSuccess = vi.fn();
      const onUploadStart = vi.fn();
      const { container } = render(
        <DropzoneCard
          onUploadSuccess={onUploadSuccess}
          onUploadStart={onUploadStart}
        />
      );

      const card = container.querySelector('.card-primary')!;

      const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' });
      const dropEvent = new Event('drop', { bubbles: true });
      Object.defineProperty(dropEvent, 'dataTransfer', {
        value: { files: [file] },
      });

      fireEvent(card, dropEvent);

      await waitFor(() => {
        expect(onUploadStart).toHaveBeenCalledTimes(1);
        expect(mockXHR.open).toHaveBeenCalledWith(
          'POST',
          expect.stringContaining('/upload-pdf')
        );
      });
    });
  });

  describe('ファイル選択', () => {
    it('カードクリックでファイル選択ダイアログが開く', () => {
      const onUploadSuccess = vi.fn();
      const { container } = render(<DropzoneCard onUploadSuccess={onUploadSuccess} />);

      const card = container.querySelector('.card-primary')!;
      const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;

      // click メソッドをスパイ
      const clickSpy = vi.spyOn(fileInput, 'click');

      fireEvent.click(card);
      expect(clickSpy).toHaveBeenCalledTimes(1);
    });

    it('PDFファイル選択でアップロード開始', async () => {
      const onUploadSuccess = vi.fn();
      const onUploadStart = vi.fn();
      const { container } = render(
        <DropzoneCard
          onUploadSuccess={onUploadSuccess}
          onUploadStart={onUploadStart}
        />
      );

      const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;
      const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' });

      Object.defineProperty(fileInput, 'files', {
        value: [file],
        writable: false,
      });

      fireEvent.change(fileInput);

      await waitFor(() => {
        expect(onUploadStart).toHaveBeenCalledTimes(1);
        expect(mockXHR.send).toHaveBeenCalled();
      });
    });
  });

  describe('バリデーション', () => {
    it('非PDFファイルでエラー表示', async () => {
      const onUploadSuccess = vi.fn();
      const { container } = render(<DropzoneCard onUploadSuccess={onUploadSuccess} />);

      const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;
      const file = new File(['test'], 'test.txt', { type: 'text/plain' });

      Object.defineProperty(fileInput, 'files', {
        value: [file],
        writable: false,
      });

      fireEvent.change(fileInput);

      await waitFor(() => {
        expect(screen.getByText('PDFファイルのみアップロード可能です')).toBeInTheDocument();
        expect(screen.getByText('❌')).toBeInTheDocument();
      });
    });

    it('100MB超過ファイルでエラー表示', async () => {
      const onUploadSuccess = vi.fn();
      const { container } = render(<DropzoneCard onUploadSuccess={onUploadSuccess} />);

      const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;

      // 大きなファイルをモック（実際に大きなデータを作らない）
      const largeFile = new File(['dummy'], 'large.pdf', {
        type: 'application/pdf',
      });

      // size プロパティを 100MB 超に設定
      Object.defineProperty(largeFile, 'size', {
        value: 101 * 1024 * 1024, // 101MB
        writable: false,
      });

      Object.defineProperty(fileInput, 'files', {
        value: [largeFile],
        writable: false,
      });

      fireEvent.change(fileInput);

      await waitFor(() => {
        expect(screen.getByText('ファイルサイズは100MB以下にしてください')).toBeInTheDocument();
      });
    });
  });

  describe('アップロード進捗', () => {
    it('アップロード中に進捗バーが表示される', async () => {
      const onUploadSuccess = vi.fn();
      const { container } = render(<DropzoneCard onUploadSuccess={onUploadSuccess} />);

      const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;
      const file = new File(['test'], 'test.pdf', { type: 'application/pdf' });

      Object.defineProperty(fileInput, 'files', {
        value: [file],
        writable: false,
      });

      fireEvent.change(fileInput);

      await waitFor(() => {
        expect(screen.getByText('アップロード中...')).toBeInTheDocument();
      });

      // 進捗50%
      mockXHR.triggerProgress(50, 100);

      await waitFor(() => {
        expect(screen.getByText('50%')).toBeInTheDocument();
      });
    });

    it('アップロード完了で成功状態を表示', async () => {
      const onUploadSuccess = vi.fn();
      const { container } = render(<DropzoneCard onUploadSuccess={onUploadSuccess} />);

      const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;
      const file = new File(['test'], 'test.pdf', { type: 'application/pdf' });

      Object.defineProperty(fileInput, 'files', {
        value: [file],
        writable: false,
      });

      mockXHR.status = 200;
      mockXHR.responseText = JSON.stringify({ path: '/uploads/test.pdf' });

      fireEvent.change(fileInput);

      await waitFor(() => {
        expect(mockXHR.send).toHaveBeenCalled();
      });

      mockXHR.triggerLoad();

      await waitFor(() => {
        expect(screen.getByText('アップロード完了')).toBeInTheDocument();
        expect(screen.getByText('✅')).toBeInTheDocument();
      });

      // 1秒後に onUploadSuccess が呼ばれる
      await waitFor(
        () => {
          expect(onUploadSuccess).toHaveBeenCalledWith({ path: '/uploads/test.pdf' });
        },
        { timeout: 1500 }
      );
    });

    it('ネットワークエラーでエラー状態を表示', async () => {
      const onUploadSuccess = vi.fn();

      const { container } = render(<DropzoneCard onUploadSuccess={onUploadSuccess} />);

      const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;
      const file = new File(['test'], 'test.pdf', { type: 'application/pdf' });

      Object.defineProperty(fileInput, 'files', {
        value: [file],
        writable: false,
      });

      fireEvent.change(fileInput);

      await waitFor(() => {
        expect(mockXHR.send).toHaveBeenCalled();
      });

      // エラーをトリガー
      mockXHR.triggerError();

      await waitFor(() => {
        expect(screen.getByText('ネットワークエラーが発生しました')).toBeInTheDocument();
        expect(screen.getByText('再試行')).toBeInTheDocument();
      });
    });

    it('タイムアウトでエラー状態を表示', async () => {
      const onUploadSuccess = vi.fn();

      const { container } = render(<DropzoneCard onUploadSuccess={onUploadSuccess} />);

      const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;
      const file = new File(['test'], 'test.pdf', { type: 'application/pdf' });

      Object.defineProperty(fileInput, 'files', {
        value: [file],
        writable: false,
      });

      fireEvent.change(fileInput);

      await waitFor(() => {
        expect(mockXHR.send).toHaveBeenCalled();
      });

      // タイムアウトをトリガー
      mockXHR.triggerTimeout();

      await waitFor(() => {
        expect(screen.getByText('アップロードがタイムアウトしました')).toBeInTheDocument();
      });
    });
  });

  describe('エラー処理', () => {
    it('エラー後に再試行ボタンが表示される', async () => {
      const onUploadSuccess = vi.fn();
      const { container } = render(<DropzoneCard onUploadSuccess={onUploadSuccess} />);

      const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;
      const file = new File(['test'], 'large.txt', { type: 'text/plain' });

      Object.defineProperty(fileInput, 'files', {
        value: [file],
        writable: false,
      });

      fireEvent.change(fileInput);

      await waitFor(() => {
        expect(screen.getByText('再試行')).toBeInTheDocument();
      });
    });

    it('再試行ボタンクリックで idle 状態に戻る', async () => {
      const onUploadSuccess = vi.fn();
      const { container } = render(<DropzoneCard onUploadSuccess={onUploadSuccess} />);

      const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;
      const file = new File(['test'], 'test.txt', { type: 'text/plain' });

      Object.defineProperty(fileInput, 'files', {
        value: [file],
        writable: false,
      });

      fireEvent.change(fileInput);

      await waitFor(() => {
        expect(screen.getByText('再試行')).toBeInTheDocument();
      });

      const retryButton = screen.getByText('再試行');
      fireEvent.click(retryButton);

      await waitFor(() => {
        expect(screen.getByText('新規作成')).toBeInTheDocument();
        expect(screen.getByText('+')).toBeInTheDocument();
      });
    });
  });

  describe('userId パラメータ', () => {
    it('userId が指定された場合、URLに含まれる', async () => {
      const onUploadSuccess = vi.fn();
      const { container } = render(
        <DropzoneCard onUploadSuccess={onUploadSuccess} userId="test@example.com" />
      );

      const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;
      const file = new File(['test'], 'test.pdf', { type: 'application/pdf' });

      Object.defineProperty(fileInput, 'files', {
        value: [file],
        writable: false,
      });

      fireEvent.change(fileInput);

      await waitFor(() => {
        expect(mockXHR.open).toHaveBeenCalledWith(
          'POST',
          expect.stringContaining('user_id=test%40example.com')
        );
      });
    });

    it('userId が未指定の場合、URLに含まれない', async () => {
      const onUploadSuccess = vi.fn();
      const { container } = render(<DropzoneCard onUploadSuccess={onUploadSuccess} />);

      const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;
      const file = new File(['test'], 'test.pdf', { type: 'application/pdf' });

      Object.defineProperty(fileInput, 'files', {
        value: [file],
        writable: false,
      });

      fireEvent.change(fileInput);

      await waitFor(() => {
        expect(mockXHR.open).toHaveBeenCalledWith(
          'POST',
          expect.not.stringContaining('user_id=')
        );
      });
    });
  });
});

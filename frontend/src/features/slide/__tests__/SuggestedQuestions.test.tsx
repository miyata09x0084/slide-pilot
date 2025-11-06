/**
 * SuggestedQuestions コンポーネントのテスト
 * 推奨質問リストの表示とクリック
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import SuggestedQuestions from '../components/SuggestedQuestions';

describe('SuggestedQuestions', () => {
  const mockSuggestions = [
    'この資料の要点は何ですか？',
    '具体例を教えてください',
    '類似の技術との違いは？',
  ];

  describe('基本レンダリング', () => {
    it('タイトルが表示される', () => {
      const onSelect = vi.fn();
      render(<SuggestedQuestions suggestions={mockSuggestions} onSelect={onSelect} />);

      expect(screen.getByText((content) => content.includes('💡'))).toBeInTheDocument();
      expect(screen.getByText((content) => content.includes('おすすめの質問'))).toBeInTheDocument();
    });

    it('全ての質問が表示される', () => {
      const onSelect = vi.fn();
      render(<SuggestedQuestions suggestions={mockSuggestions} onSelect={onSelect} />);

      mockSuggestions.forEach((question) => {
        expect(screen.getByText(question)).toBeInTheDocument();
      });
    });

    it('質問が空の場合、何も表示されない', () => {
      const onSelect = vi.fn();
      const { container } = render(<SuggestedQuestions suggestions={[]} onSelect={onSelect} />);

      // suggestionsが空の場合、コンポーネントはnullを返す
      expect(container.firstChild).toBeNull();
    });
  });

  describe('インタラクション', () => {
    it('質問クリックで onSelect が呼ばれる', () => {
      const onSelect = vi.fn();
      render(<SuggestedQuestions suggestions={mockSuggestions} onSelect={onSelect} />);

      const firstQuestion = screen.getByText(mockSuggestions[0]);
      fireEvent.click(firstQuestion);

      expect(onSelect).toHaveBeenCalledTimes(1);
      expect(onSelect).toHaveBeenCalledWith(mockSuggestions[0]);
    });

    it('複数の質問をクリックできる', () => {
      const onSelect = vi.fn();
      render(<SuggestedQuestions suggestions={mockSuggestions} onSelect={onSelect} />);

      mockSuggestions.forEach((question, index) => {
        const questionElement = screen.getByText(question);
        fireEvent.click(questionElement);

        expect(onSelect).toHaveBeenCalledTimes(index + 1);
        expect(onSelect).toHaveBeenCalledWith(question);
      });
    });
  });

  describe('質問数の制限', () => {
    it('大量の質問を表示できる', () => {
      const manyQuestions = Array.from({ length: 10 }, (_, i) => `質問${i + 1}`);
      const onSelect = vi.fn();

      render(<SuggestedQuestions suggestions={manyQuestions} onSelect={onSelect} />);

      manyQuestions.forEach((question) => {
        expect(screen.getByText(question)).toBeInTheDocument();
      });
    });
  });

  describe('disabled状態', () => {
    it('disabled=true の場合、ボタンがdisabledになる', () => {
      const onSelect = vi.fn();
      render(<SuggestedQuestions suggestions={mockSuggestions} onSelect={onSelect} disabled={true} />);

      const buttons = screen.getAllByRole('button');
      buttons.forEach((button) => {
        expect(button).toBeDisabled();
      });
    });

    it('disabled時にクリックしても onSelect が呼ばれない', () => {
      const onSelect = vi.fn();
      render(<SuggestedQuestions suggestions={mockSuggestions} onSelect={onSelect} disabled={true} />);

      const firstQuestion = screen.getByText(mockSuggestions[0]);
      fireEvent.click(firstQuestion);

      expect(onSelect).not.toHaveBeenCalled();
    });
  });
});

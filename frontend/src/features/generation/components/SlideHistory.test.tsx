import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { SlideHistory } from './SlideHistory'

// グローバルfetchのモック
global.fetch = vi.fn()

describe('SlideHistory', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('ローディング中はスピナーを表示', () => {
    // fetchを無限待機状態にする
    (global.fetch as any).mockImplementation(() => new Promise(() => {}))

    render(
      <SlideHistory
        userEmail="test@example.com"
        onPreview={() => {}}
      />
    )

    expect(screen.getByText('読み込み中...')).toBeInTheDocument()
  })

  it('スライドが0件の場合、メッセージを表示', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ slides: [] })
    })

    render(
      <SlideHistory
        userEmail="test@example.com"
        onPreview={() => {}}
      />
    )

    await waitFor(() => {
      expect(screen.getByText('まだスライドがありません')).toBeInTheDocument()
    })
  })

  it('スライドリストを正常に表示', async () => {
    const mockSlides = [
      {
        id: '1',
        title: 'テストスライド1',
        topic: 'テストトピック1',
        created_at: '2025-10-28T10:00:00Z',
        pdf_url: null
      },
      {
        id: '2',
        title: 'テストスライド2',
        topic: 'テストトピック2',
        created_at: '2025-10-28T11:00:00Z',
        pdf_url: 'https://example.com/slide.pdf'
      }
    ]

    ;(global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ slides: mockSlides })
    })

    render(
      <SlideHistory
        userEmail="test@example.com"
        onPreview={() => {}}
      />
    )

    await waitFor(() => {
      expect(screen.getByText('テストスライド1')).toBeInTheDocument()
      expect(screen.getByText('テストスライド2')).toBeInTheDocument()
    })
  })

  it('APIエラー時、エラーメッセージを表示', async () => {
    ;(global.fetch as any).mockResolvedValueOnce({
      ok: false,
      statusText: 'Internal Server Error'
    })

    render(
      <SlideHistory
        userEmail="test@example.com"
        onPreview={() => {}}
      />
    )

    await waitFor(() => {
      expect(screen.getByText(/エラー:/)).toBeInTheDocument()
    })
  })

  it('正しいAPIエンドポイントにリクエストを送信', async () => {
    ;(global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ slides: [] })
    })

    render(
      <SlideHistory
        userEmail="user@example.com"
        onPreview={() => {}}
      />
    )

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8001/api/slides?user_id=user%40example.com&limit=20'
      )
    })
  })

  it('プレビューボタンをクリックするとコールバックが呼ばれる', async () => {
    const mockOnPreview = vi.fn()
    const mockSlides = [
      {
        id: 'slide-123',
        title: 'テストスライド',
        topic: 'トピック',
        created_at: '2025-10-28T10:00:00Z'
      }
    ]

    ;(global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ slides: mockSlides })
    })

    render(
      <SlideHistory
        userEmail="test@example.com"
        onPreview={mockOnPreview}
      />
    )

    await waitFor(() => {
      expect(screen.getByText('テストスライド')).toBeInTheDocument()
    })

    const previewButton = screen.getByText('プレビュー')
    previewButton.click()

    expect(mockOnPreview).toHaveBeenCalledWith('slide-123')
  })
})

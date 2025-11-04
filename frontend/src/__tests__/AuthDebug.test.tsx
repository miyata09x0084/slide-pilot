import { describe, it, expect, beforeEach } from 'vitest'

/**
 * Google OAuth問題のデバッグ用テスト
 *
 * 目的: localStorage の動作確認とユーザー情報の保存/取得が正常か検証
 */
describe('Auth Debug - localStorage', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('localStorage にユーザー情報を保存できる', () => {
    const userInfo = {
      name: 'Test User',
      email: 'test@example.com',
      picture: 'https://example.com/avatar.jpg'
    }

    localStorage.setItem('user', JSON.stringify(userInfo))

    const stored = localStorage.getItem('user')
    expect(stored).not.toBeNull()

    const parsed = JSON.parse(stored!)
    expect(parsed.email).toBe('test@example.com')
  })

  it('localStorage からユーザー情報を取得できる', () => {
    const userInfo = {
      name: 'Test User',
      email: 'user@example.com',
      picture: 'https://example.com/avatar.jpg'
    }

    localStorage.setItem('user', JSON.stringify(userInfo))

    // App.tsx の実装を模倣
    const savedUser = localStorage.getItem('user')
    expect(savedUser).not.toBeNull()

    const user = JSON.parse(savedUser!)
    expect(user.email).toBe('user@example.com')
    expect(user.name).toBe('Test User')
  })

  it('localStorage が空の場合、null を返す', () => {
    const savedUser = localStorage.getItem('user')
    expect(savedUser).toBeNull()
  })

  it('user.email が正しくパースされる', () => {
    const userInfo = {
      name: 'Test User',
      email: 'test@example.com',
      picture: 'https://example.com/avatar.jpg'
    }

    localStorage.setItem('user', JSON.stringify(userInfo))

    // useReactAgent.ts:84-85 の実装を模倣
    const user = JSON.parse(localStorage.getItem('user') || '{}')
    const userEmail = user.email || 'anonymous@example.com'

    expect(userEmail).toBe('test@example.com')
  })

  it('localStorage が空の場合、デフォルト値を使用', () => {
    // localStorageが空の状態
    const user = JSON.parse(localStorage.getItem('user') || '{}')
    const userEmail = user.email || 'anonymous@example.com'

    expect(userEmail).toBe('anonymous@example.com')
  })
})

/**
 * API リクエストのデバッグ用テスト
 */
describe('Auth Debug - API Request', () => {
  it('user_id パラメータが正しくURLエンコードされる', () => {
    const userEmail = 'test@example.com'
    const expectedUrl = `http://localhost:8001/api/slides?user_id=${encodeURIComponent(userEmail)}&limit=20`

    expect(expectedUrl).toBe('http://localhost:8001/api/slides?user_id=test%40example.com&limit=20')
  })

  it('特殊文字を含むメールアドレスが正しくエンコードされる', () => {
    const userEmail = 'test+tag@example.com'
    const expectedUrl = `http://localhost:8001/api/slides?user_id=${encodeURIComponent(userEmail)}&limit=20`

    expect(expectedUrl).toContain('test%2Btag%40example.com')
  })
})

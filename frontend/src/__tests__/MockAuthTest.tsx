/**
 * Google OAuth待機中のテスト用: モックユーザーでログイン
 *
 * 使い方:
 * 1. ブラウザの Console で以下を実行:
 *    localStorage.setItem('user', JSON.stringify({
 *      name: 'Test User',
 *      email: 'test@example.com',
 *      picture: 'https://via.placeholder.com/96'
 *    }))
 *
 * 2. ページをリロード
 *
 * 3. ログイン済み状態で「過去のスライド」が表示される
 *
 * 4. テスト終了後:
 *    localStorage.clear()
 */

export function loginWithMockUser() {
  const mockUser = {
    name: 'Test User',
    email: 'test@example.com',
    picture: 'https://via.placeholder.com/96'
  }

  localStorage.setItem('user', JSON.stringify(mockUser))
}

export function logout() {
  localStorage.removeItem('user')
}

// ブラウザのグローバルスコープに関数を公開
if (typeof window !== 'undefined') {
  (window as any).mockLogin = loginWithMockUser;
  (window as any).mockLogout = logout;
}

/**
 * AuthGuard
 * 認証が必要なルートを保護するコンポーネント
 */

import { Outlet } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

export default function AuthGuard() {
  const { isAuthenticated, loading } = useAuth();

  console.log('[AuthGuard] Render:', {
    loading,
    isAuthenticated,
    timestamp: new Date().toISOString()
  });

  // 🚨 デバッグ用：認証チェックを一時的に無効化
  console.warn('[AuthGuard] ⚠️ DEBUG MODE: Authentication check DISABLED - allowing all access');
  return <Outlet />;

  // 以下は一時的にコメントアウト（デバッグ後に復元）
  /*
  // 認証状態の読み込み中はローディング表示
  if (loading) {
    console.log('[AuthGuard] Showing loading spinner');
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#f5f5f5'
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{
            display: 'inline-block',
            width: '40px',
            height: '40px',
            border: '4px solid #f3f3f3',
            borderTop: '4px solid #007bff',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite'
          }} />
          <p style={{ marginTop: '12px', color: '#666' }}>読み込み中...</p>
          <style>{`
            @keyframes spin {
              0% { transform: rotate(0deg); }
              100% { transform: rotate(360deg); }
            }
          `}</style>
        </div>
      </div>
    );
  }

  // 未認証の場合はログインページにリダイレクト
  if (!isAuthenticated) {
    console.log('[AuthGuard] Not authenticated, redirecting to /login');
    return <Navigate to="/login" replace />;
  }

  // 認証済みの場合は子ルートを表示
  console.log('[AuthGuard] Authenticated, rendering protected content');
  return <Outlet />;
  */
}

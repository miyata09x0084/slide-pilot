/**
 * LoginPage
 * Google OAuth UI + Supabase Auth ハイブリッド実装
 *
 * Issue: Google OAuth UI復元
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { GoogleLogin } from '@react-oauth/google';
import type { CredentialResponse } from '@react-oauth/google';
import { useAuth } from './hooks/useAuth';
import { env } from '@/config/env';

export default function LoginPage() {
  const navigate = useNavigate();
  const { loginWithGoogle, authError, clearAuthError } = useAuth();
  const [systemStatus, setSystemStatus] = useState<string | null>(null);

  // アプリ起動時にバックエンドのヘルスチェック
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch(`${env.API_URL}/health/detailed`);
        if (!res.ok) {
          setSystemStatus('サーバーに接続できません。しばらくしてから再度お試しください。');
          return;
        }
        const data = await res.json();
        if (data.degraded_mode) {
          if (data.supabase_db?.status === 'down') {
            setSystemStatus('認証サービスがメンテナンス中です。しばらくしてから再度お試しください。');
          } else if (data.supabase_storage?.status === 'down') {
            setSystemStatus('ストレージサービスがメンテナンス中です。一部機能が制限される場合があります。');
          }
        }
      } catch {
        // ヘルスチェック失敗時は何もしない（ログイン試行時にエラーになる）
        console.warn('[LoginPage] Health check failed');
      }
    };
    checkHealth();
  }, []);

  const handleGoogleSuccess = async (credentialResponse: CredentialResponse) => {
    if (!credentialResponse.credential) {
      console.error('[LoginPage] No credential received from Google');
      return;
    }

    try {
      await loginWithGoogle(credentialResponse.credential);
      await new Promise(resolve => setTimeout(resolve, 100));
      navigate('/', { replace: true });
    } catch (error) {
      console.error('[LoginPage] Login failed:', error);
    }
  };

  const handleGoogleError = () => {
    console.error('[Google OAuth] Login Failed');
    console.error('  Client ID:', import.meta.env.VITE_GOOGLE_CLIENT_ID);
    console.error('  Current Origin:', window.location.origin);
    console.error('  Expected Origin: http://localhost:5173');
    console.error('  Check Google Cloud Console:');
    console.error('    - Authorized JavaScript origins should include: http://localhost:5173');
    console.error('    - Settings may take 5 minutes to several hours to propagate');
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        background: '#f5f5f5',
      }}
    >
      <div
        style={{
          background: 'white',
          padding: '40px',
          borderRadius: '10px',
          boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
          textAlign: 'center',
        }}
      >
        <h1 style={{ marginBottom: '10px', color: '#333' }}>
          Multimodal Lab{' '}
          <span
            style={{
              display: 'inline-block',
              marginLeft: '8px',
              padding: '2px 8px',
              fontSize: '11px',
              fontWeight: '600',
              color: '#6b7280',
              background: '#f3f4f6',
              border: '1px solid #d1d5db',
              borderRadius: '4px',
              letterSpacing: '0.5px',
              verticalAlign: 'middle',
            }}
          >
            α版
          </span>
        </h1>
        <p style={{ marginBottom: '8px', color: '#666', fontWeight: '600' }}>
          Multimodal Content Experiment
        </p>
        <p style={{ marginBottom: '30px', color: '#888', fontSize: '14px' }}>
          難しいPDFを、わかりやすい動画に
        </p>

        {/* システム状態の警告表示 */}
        {systemStatus && (
          <div
            style={{
              marginBottom: '20px',
              padding: '12px 16px',
              background: '#fffbeb',
              border: '1px solid #fcd34d',
              borderRadius: '8px',
              color: '#b45309',
              fontSize: '14px',
            }}
          >
            <p style={{ margin: 0 }}>{systemStatus}</p>
          </div>
        )}

        {/* 認証エラーメッセージ表示 */}
        {authError && (
          <div
            style={{
              marginBottom: '20px',
              padding: '12px 16px',
              background: '#fef2f2',
              border: '1px solid #fecaca',
              borderRadius: '8px',
              color: '#dc2626',
              fontSize: '14px',
            }}
          >
            <p style={{ margin: '0 0 8px 0' }}>{authError}</p>
            <button
              onClick={clearAuthError}
              style={{
                padding: '4px 12px',
                fontSize: '12px',
                color: '#dc2626',
                background: 'white',
                border: '1px solid #dc2626',
                borderRadius: '4px',
                cursor: 'pointer',
              }}
            >
              閉じる
            </button>
          </div>
        )}

        {/* Google 公式 OAuth UI */}
        <div style={{ display: 'flex', justifyContent: 'center' }}>
          <GoogleLogin onSuccess={handleGoogleSuccess} onError={handleGoogleError} />
        </div>
      </div>
    </div>
  );
}

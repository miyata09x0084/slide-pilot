/**
 * LoginPage
 * Google OAuth UI + Supabase Auth ハイブリッド実装
 *
 * Issue: Google OAuth UI復元
 */

import { useNavigate } from 'react-router-dom';
import { useEffect } from 'react';
import { GoogleLogin } from '@react-oauth/google';
import type { CredentialResponse } from '@react-oauth/google';
import { useAuth } from './hooks/useAuth';

export default function LoginPage() {
  const navigate = useNavigate();
  const { loginWithGoogle, isAuthenticated } = useAuth();

  // すでにログイン済みの場合はダッシュボードへリダイレクト
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  const handleGoogleSuccess = async (credentialResponse: CredentialResponse) => {
    if (!credentialResponse.credential) {
      console.error('No credential received from Google');
      return;
    }

    try {
      // Google JWT を Supabase に渡してセッション作成
      await loginWithGoogle(credentialResponse.credential);
      // onAuthStateChange → useEffect が自動的に / へ遷移するため、ここでのnavigate不要
    } catch (error) {
      console.error('Login failed:', error);
    }
  };

  const handleGoogleError = () => {
    console.error('❌ [Google OAuth] Login Failed');
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
          ラクヨミ アシスタントAI{' '}
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
          あなた専用の学習パートナー
        </p>
        <p style={{ marginBottom: '6px', color: '#888', fontSize: '14px' }}>
          PDFをアップロードして、難しい資料を楽に読む
        </p>
        <p style={{ marginBottom: '30px', color: '#999', fontSize: '12px' }}>
          📄 対応形式: PDF
        </p>

        {/* Google 公式 OAuth UI */}
        <GoogleLogin onSuccess={handleGoogleSuccess} onError={handleGoogleError} />
      </div>
    </div>
  );
}

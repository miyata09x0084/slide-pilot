import { GoogleLogin } from '@react-oauth/google';
import type { CredentialResponse } from '@react-oauth/google';

interface LoginProps {
  onSuccess: (credentialResponse: CredentialResponse) => void;
}

function Login({ onSuccess }: LoginProps) {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '100vh',
      background: '#f5f5f5'
    }}>
      <div style={{
        background: 'white',
        padding: '40px',
        borderRadius: '10px',
        boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
        textAlign: 'center'
      }}>
        <h1 style={{ marginBottom: '10px', color: '#333' }}>
          ラクヨミ アシスタントAI
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
        {/* Note: Gmail scope は Google Cloud Console の OAuth consent screen で設定が必要 */}
        <GoogleLogin
          onSuccess={onSuccess}
          onError={() => {
            console.error('❌ [Google OAuth] Login Failed');
            console.error('  Client ID:', import.meta.env.VITE_GOOGLE_CLIENT_ID);
            console.error('  Current Origin:', window.location.origin);
            console.error('  Expected Origin: http://localhost:5173');
            console.error('  Check Google Cloud Console:');
            console.error('    - Authorized JavaScript origins should include: http://localhost:5173');
            console.error('    - Settings may take 5 minutes to several hours to propagate');
          }}
        />
      </div>
    </div>
  );
}

export default Login;

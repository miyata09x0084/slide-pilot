/**
 * LoginPage
 * Google OAuth ログイン画面
 */

import { useNavigate } from 'react-router-dom';
import { useEffect } from 'react';
import type { CredentialResponse } from '@react-oauth/google';
import { jwtDecode } from 'jwt-decode';
import Login from './components/Login';
import { useAuth } from './hooks/useAuth';

export default function LoginPage() {
  const navigate = useNavigate();
  const { login, isAuthenticated } = useAuth();

  // すでにログイン済みの場合はダッシュボードへリダイレクト
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  const handleLoginSuccess = (credentialResponse: CredentialResponse) => {
    if (credentialResponse.credential) {
      const decoded: any = jwtDecode(credentialResponse.credential);
      const userInfo = {
        name: decoded.name,
        email: decoded.email,
        picture: decoded.picture
      };
      login(userInfo);
      navigate('/', { replace: true });
    }
  };

  return <Login onSuccess={handleLoginSuccess} />;
}

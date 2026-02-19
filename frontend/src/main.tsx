import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { RouterProvider } from 'react-router-dom';
import './index.css';
import { initAuthSessionCache } from './lib/auth-session';
import { AppProvider } from './app/provider';
import { router } from './app/router';

// React描画前にセッションキャッシュを初期化
// Supabase v2.39+ではINITIAL_SESSIONが同期的に発火するため、
// この時点でcachedAccessTokenが利用可能になる
initAuthSessionCache();

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AppProvider>
      <RouterProvider router={router} />
    </AppProvider>
  </StrictMode>
);

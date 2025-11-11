/**
 * AppProvider - Global application providers
 * Wraps app with GoogleOAuth, Recoil, Suspense, and ErrorBoundary
 */

import { Suspense } from 'react';
import type { ReactNode } from 'react';
import { GoogleOAuthProvider } from '@react-oauth/google';
import { RecoilRoot } from 'recoil';
import { ErrorBoundary } from '../components/error/ErrorBoundary';
import { Spinner } from '../components/error/Spinner';

interface AppProviderProps {
  children: ReactNode;
}

export function AppProvider({ children }: AppProviderProps) {
  const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;

  if (!clientId) {
    console.error('❌ VITE_GOOGLE_CLIENT_ID is not set in .env.local');
  }

  return (
    <ErrorBoundary>
      <GoogleOAuthProvider clientId={clientId}>
        <RecoilRoot>
          <Suspense fallback={<Spinner />}>{children}</Suspense>
        </RecoilRoot>
      </GoogleOAuthProvider>
    </ErrorBoundary>
  );
}

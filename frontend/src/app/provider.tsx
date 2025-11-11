/**
 * AppProvider - Global application providers
 * Wraps app with GoogleOAuth, React Query, Recoil, Suspense, and ErrorBoundary
 */

import { Suspense } from 'react';
import type { ReactNode } from 'react';
import { GoogleOAuthProvider } from '@react-oauth/google';
import { QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { RecoilRoot } from 'recoil';
import { ErrorBoundary } from '../components/error/ErrorBoundary';
import { Spinner } from '../components/error/Spinner';
import { queryClient } from '../lib/react-query';

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
        <QueryClientProvider client={queryClient}>
          <RecoilRoot>
            <Suspense fallback={<Spinner />}>{children}</Suspense>
          </RecoilRoot>
          {import.meta.env.DEV && <ReactQueryDevtools initialIsOpen={false} />}
        </QueryClientProvider>
      </GoogleOAuthProvider>
    </ErrorBoundary>
  );
}

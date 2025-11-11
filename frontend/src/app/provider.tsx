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
import { env } from '../config/env';

interface AppProviderProps {
  children: ReactNode;
}

export function AppProvider({ children }: AppProviderProps) {
  return (
    <ErrorBoundary>
      <GoogleOAuthProvider clientId={env.GOOGLE_CLIENT_ID}>
        <QueryClientProvider client={queryClient}>
          <RecoilRoot>
            <Suspense fallback={<Spinner />}>{children}</Suspense>
          </RecoilRoot>
          {env.DEV && <ReactQueryDevtools initialIsOpen={false} />}
        </QueryClientProvider>
      </GoogleOAuthProvider>
    </ErrorBoundary>
  );
}

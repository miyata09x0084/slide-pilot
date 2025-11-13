/**
 * Protected Routes Layout
 * Root layout for all authenticated routes
 */

import { AuthGuard } from '@/features/auth';

export function ProtectedLayout() {
  return <AuthGuard />;
}

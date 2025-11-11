/**
 * Protected Routes Layout
 * Root layout for all authenticated routes
 */

import { ProtectedRoute } from '@/features/auth';

export function ProtectedLayout() {
  return <ProtectedRoute />;
}

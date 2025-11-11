/**
 * Router Configuration
 * Defines all application routes using React Router v7
 * Phase 5: File-based routing structure with app/routes/
 * Phase 5.1: React Query prefetch loaders integration
 */

import { createBrowserRouter, Navigate } from 'react-router-dom';
import { queryClient } from '@/lib/react-query';
import { LoginRoute } from './routes/login';
import { DashboardRoute } from './routes';
import { ProtectedLayout } from './routes/app/root';
import { GenerateRoute } from './routes/app/generate';
import { SlidesRoute } from './routes/app/slides';

// Loaderファクトリー関数をimport
import { createDashboardLoader } from '@/features/dashboard/loaders/dashboardLoader';
import { createSlideDetailLoader } from '@/features/slide/loaders/slideDetailLoader';

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginRoute />,
  },
  {
    element: <ProtectedLayout />,
    children: [
      {
        path: '/',
        element: <DashboardRoute />,
        loader: createDashboardLoader(queryClient), // プリフェッチ追加
      },
      {
        path: '/generate/:threadId',
        element: <GenerateRoute />,
        // このページはSSEストリーミングのためプリフェッチ不要
      },
      {
        path: '/slides/:slideId',
        element: <SlidesRoute />,
        loader: createSlideDetailLoader(queryClient), // プリフェッチ追加
      },
    ],
  },
  {
    path: '*',
    element: <Navigate to="/" replace />,
  },
]);

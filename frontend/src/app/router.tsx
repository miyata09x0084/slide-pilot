/**
 * Router Configuration
 * Defines all application routes using React Router v7
 *
 * コード分割戦略:
 * - ダッシュボード（/）: 静的import（初期表示に必須）
 * - ログイン・生成・スライド詳細: lazy import（別チャンクに分割）
 */

import { createBrowserRouter, Navigate } from 'react-router-dom';
import { queryClient } from '@/lib/react-query';
import { ProtectedLayout } from './routes/app/root';
import { DashboardRoute } from './routes';

// Loaderファクトリー関数をimport
import { createDashboardLoader } from '@/features/dashboard/loaders/dashboardLoader';
import { createSlideDetailLoader } from '@/features/slide/loaders/slideDetailLoader';

export const router = createBrowserRouter([
  {
    path: '/login',
    lazy: async () => {
      const { LoginRoute } = await import('./routes/login');
      return { Component: LoginRoute };
    },
  },
  {
    element: <ProtectedLayout />,
    children: [
      {
        path: '/',
        element: <DashboardRoute />,
        loader: createDashboardLoader(queryClient),
      },
      {
        path: '/generate/:threadId?',
        lazy: async () => {
          const { GenerateRoute } = await import('./routes/app/generate');
          return { Component: GenerateRoute };
        },
      },
      {
        path: '/slides/:slideId',
        lazy: async () => {
          const { SlidesRoute } = await import('./routes/app/slides');
          return { Component: SlidesRoute };
        },
        loader: createSlideDetailLoader(queryClient),
      },
    ],
  },
  {
    path: '*',
    element: <Navigate to="/" replace />,
  },
]);

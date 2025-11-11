/**
 * Router Configuration
 * Defines all application routes using React Router v7
 * Phase 2: Removed loaders, using React Query instead
 */

import { createBrowserRouter, Navigate } from 'react-router-dom';
import { LoginPage, ProtectedRoute } from '../features/auth';
import { DashboardPage } from '../features/dashboard';
import { SlideDetailPage } from '../features/slide';
import { GenerationProgressPage } from '../features/generation';

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    element: <ProtectedRoute />,
    children: [
      {
        path: '/',
        element: <DashboardPage />,
      },
      {
        path: '/generate/:threadId',
        element: <GenerationProgressPage />,
      },
      {
        path: '/slides/:slideId',
        element: <SlideDetailPage />,
      },
    ],
  },
  {
    path: '*',
    element: <Navigate to="/" replace />,
  },
]);

/**
 * Router Configuration
 * Defines all application routes using React Router v7
 */

import { createBrowserRouter, Navigate } from 'react-router-dom';
import { LoginPage, ProtectedRoute } from '../features/auth';
import { DashboardPage, dashboardLoader } from '../features/dashboard';
import { SlideDetailPage, slideDetailLoader } from '../features/slide';
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
        loader: dashboardLoader,
      },
      {
        path: '/generate/:threadId',
        element: <GenerationProgressPage />,
      },
      {
        path: '/slides/:slideId',
        element: <SlideDetailPage />,
        loader: slideDetailLoader,
      },
    ],
  },
  {
    path: '*',
    element: <Navigate to="/" replace />,
  },
]);

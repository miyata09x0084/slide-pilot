/**
 * App.tsx (Phase 1: React Router対応 + Recoil状態管理)
 * ルーティング設定とRecoilRootラッパー
 * React Router v6.4+ createBrowserRouter + loader使用
 */

import { createBrowserRouter, RouterProvider, Navigate } from 'react-router-dom';
import { RecoilRoot } from 'recoil';
import { LoginPage, ProtectedRoute } from './features/auth';
import { DashboardPage, dashboardLoader } from './features/dashboard';
import { SlideDetailPage, slideDetailLoader } from './features/slide';
import { GenerationProgressPage } from './features/generation';

const router = createBrowserRouter([
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
        loader: dashboardLoader, // ページ表示前にデータ取得
      },
      {
        path: '/generate/:threadId',
        element: <GenerationProgressPage />,
      },
      {
        path: '/slides/:slideId',
        element: <SlideDetailPage />,
        loader: slideDetailLoader, // ページ表示前にデータ取得
      },
    ],
  },
  {
    path: '*',
    element: <Navigate to="/" replace />,
  },
]);

function App() {
  return (
    <RecoilRoot>
      <RouterProvider router={router} />
    </RecoilRoot>
  );
}

export default App;

/**
 * App.tsx (Phase 1: React Router対応)
 * ルーティング設定のみ
 */

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import GenerationProgressPage from './pages/GenerationProgressPage';
import SlideDetailPage from './pages/SlideDetailPage';
import ProtectedRoute from './components/ProtectedRoute';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* 公開ルート */}
        <Route path="/login" element={<LoginPage />} />

        {/* 認証必須ルート */}
        <Route element={<ProtectedRoute />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/generate/:threadId" element={<GenerationProgressPage />} />
          <Route path="/slides/:slideId" element={<SlideDetailPage />} />
        </Route>

        {/* 存在しないルート */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;

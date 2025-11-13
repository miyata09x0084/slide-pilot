/**
 * App.tsx (Phase 2: Code Splitting導入)
 * ルーティング設定とRecoilRootラッパー
 * React Router v6.4+ createBrowserRouter + loader使用
 * React Query統合でデータフェッチ最適化
 * Code Splittingで初回ロード時間を50-60%削減
 */

import { Suspense } from "react";
import {
  createBrowserRouter,
  RouterProvider,
  Navigate,
} from "react-router-dom";
import { RecoilRoot } from "recoil";
import { QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { queryClient } from "./lib/react-query";
import { lazyImport } from "./lib/lazyImport";
import { PageLoader } from "./shared/components/PageLoader";

// 遅延ロード（loaderなしのページ）
const { LoginPage } = lazyImport(() => import("./features/auth"), "LoginPage");
const { AuthGuard } = lazyImport(
  () => import("./features/auth"),
  "AuthGuard"
);
const { GenerationProgressPage } = lazyImport(
  () => import("./features/generation"),
  "GenerationProgressPage"
);


const router = createBrowserRouter([
  {
    path: "/login",
    element: (
      <Suspense fallback={<PageLoader />}>
        <LoginPage />
      </Suspense>
    ),
  },
  {
    element: (
      <Suspense fallback={<PageLoader />}>
        <AuthGuard />
      </Suspense>
    ),
    // 認証したユーザーのみアクセス可能なルート
    children: [
      // Dashboard: loader+Componentを遅延ロード（文字列リテラルで直接記述）
      {
        path: "/",
        lazy: async () => {
          const module = await import("./features/dashboard");
          return {
            loader: module.lazyDashboardLoader,
            Component: module.lazyDashboardComponent,
          };
        },
      },
      // スライド生成
      {
        path: "/generate/:threadId",
        element: (
          <Suspense fallback={<PageLoader />}>
            <GenerationProgressPage />
          </Suspense>
        ),
      },
      // スライド詳細: loader+Componentを遅延ロード（文字列リテラルで直接記述）
      {
        path: "/slides/:slideId",
        lazy: async () => {
          const module = await import("./features/slide");
          return {
            loader: module.lazySlideDetailLoader,
            Component: module.lazySlideDetailComponent,
          };
        },
      },
    ],
  },
  // 404リダイレクト
  {
    path: "*",
    element: <Navigate to="/" replace />,
  },
]);

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <RecoilRoot>
        <RouterProvider router={router} />
      </RecoilRoot>
      {import.meta.env.DEV && <ReactQueryDevtools initialIsOpen={false} />}
    </QueryClientProvider>
  );
}

export default App;

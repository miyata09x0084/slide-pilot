import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    rollupOptions: {
      output: {
        // Force new hash on each build to bust Firebase Hosting cache
        entryFileNames: `assets/[name]-[hash]-${Date.now()}.js`,
        chunkFileNames: `assets/[name]-[hash]-${Date.now()}.js`,
        assetFileNames: `assets/[name]-[hash].[ext]`,
        manualChunks: {
          // React core（ほぼ全ページで使用、キャッシュ効率最大化）
          'vendor-react': ['react', 'react-dom', 'react-router-dom'],
          // Supabase SDK（認証・DB、サイズ大）
          'vendor-supabase': ['@supabase/supabase-js'],
          // 状態管理・データ取得
          'vendor-state': ['recoil', '@tanstack/react-query', 'axios'],
        },
      },
    },
  },
  // Note: COOP/COEP ヘッダーは Google OAuth と競合するため削除
  // Google Cloud Console の設定反映を待つ必要がある
})

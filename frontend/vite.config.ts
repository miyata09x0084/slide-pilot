import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // Note: COOP/COEP ヘッダーは Google OAuth と競合するため削除
  // Google Cloud Console の設定反映を待つ必要がある
})

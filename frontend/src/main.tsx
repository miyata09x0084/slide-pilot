import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App.tsx";
import { GoogleOAuthProvider } from "@react-oauth/google";

const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;

// デバッグログ: Google OAuth設定の確認
console.log('[DEBUG] Google OAuth Configuration:');
console.log('  Client ID:', clientId);
console.log('  Client ID length:', clientId?.length);
console.log('  Current Origin:', window.location.origin);
console.log('  Expected Origin: http://localhost:5173');

if (!clientId) {
  console.error('❌ VITE_GOOGLE_CLIENT_ID is not set in .env.local');
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <GoogleOAuthProvider clientId={clientId}>
      <App />
    </GoogleOAuthProvider>
  </StrictMode>
);

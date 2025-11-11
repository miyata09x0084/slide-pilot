/**
 * Environment Configuration
 * Centralized type-safe access to environment variables
 */

interface Env {
  API_URL: string;
  GOOGLE_CLIENT_ID: string;
  MODE: string;
  DEV: boolean;
  PROD: boolean;
}

function getEnv(): Env {
  const apiUrl = import.meta.env.VITE_API_URL;
  const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;

  // Validate required environment variables
  if (!googleClientId) {
    console.error('❌ VITE_GOOGLE_CLIENT_ID is not set in .env.local');
  }

  return {
    API_URL: apiUrl || 'http://localhost:8001/api',
    GOOGLE_CLIENT_ID: googleClientId || '',
    MODE: import.meta.env.MODE,
    DEV: import.meta.env.DEV,
    PROD: import.meta.env.PROD,
  };
}

export const env = getEnv();

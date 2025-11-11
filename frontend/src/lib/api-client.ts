/**
 * API Client Configuration
 * Centralized Axios instance with interceptors for authentication and error handling
 */

import axios from 'axios';

// Base URL from environment variable
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001/api';

// Create Axios instance
export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: false,
});

// Request interceptor - Add authentication headers
api.interceptors.request.use(
  (config) => {
    // Get user from localStorage
    const userStr = localStorage.getItem('user');
    if (userStr) {
      try {
        const user = JSON.parse(userStr);
        if (user.email) {
          config.headers['X-User-Email'] = user.email;
        }
      } catch (err) {
        console.warn('Failed to parse user data from localStorage:', err);
      }
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor - Handle errors globally
api.interceptors.response.use(
  (response) => {
    return response.data;
  },
  (error) => {
    // Handle specific error codes
    if (error.response) {
      const { status } = error.response;

      // 401 Unauthorized - Redirect to login
      if (status === 401) {
        localStorage.removeItem('user');
        window.location.href = '/login';
      }

      // Log other errors
      console.error('API Error:', {
        status,
        message: error.response.data?.message || error.message,
        url: error.config?.url,
      });
    } else if (error.request) {
      console.error('Network Error: No response received', error.request);
    } else {
      console.error('Request Error:', error.message);
    }

    return Promise.reject(error);
  }
);

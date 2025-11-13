/**
 * Shared Type Definitions
 * Common types used across multiple features
 */

// ============================================================================
// User & Authentication
// ============================================================================

export interface UserInfo {
  name: string;
  email: string;
  picture: string;
}

// ============================================================================
// Messages & Chat
// ============================================================================

export interface Message {
  role: 'user' | 'assistant';
  content: string;
}

export interface ThinkingStep {
  type: 'thinking' | 'action' | 'observation';
  content: string;
}

// ============================================================================
// Slides
// ============================================================================

export interface Slide {
  id: string;
  title: string;
  created_at: string;
  pdf_url?: string;
  thumbnail_url?: string;
  topic?: string;
}

export interface SlideDetail {
  id: string;
  title: string;
  topic: string;
  created_at: string;
  pdf_url?: string;
  markdown?: string;
}

export interface SlideData {
  path?: string;
  title?: string;
  slide_id?: string;
  pdf_url?: string;
}

// ============================================================================
// API Responses
// ============================================================================

export interface ApiError {
  message: string;
  status?: number;
  code?: string;
}

/**
 * Slide機能のPublic API
 * Phase 2: React Query対応
 */

// 通常import用
export { default as SlideDetailPage } from './SlideDetailPage';
export { SlideViewer } from './components/SlideViewer';
export { default as ChatPanel } from './components/ChatPanel';
export { SlideContentViewer } from './components/SlideContentViewer';
export { default as SlideDetailLayout } from './components/SlideDetailLayout';
export { default as SuggestedQuestions } from './components/SuggestedQuestions';

// React Router lazy loading用
export { slideDetailLoader as lazySlideDetailLoader } from './loaders/slideDetailLoader';
export { default as lazySlideDetailComponent } from './SlideDetailPage';

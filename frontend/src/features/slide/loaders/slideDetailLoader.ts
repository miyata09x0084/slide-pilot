/**
 * slideDetailLoader - SlideDetailPageのReact Router Loader
 * ページ表示前にスライド詳細を取得
 */

import type { LoaderFunctionArgs } from 'react-router-dom';

export interface SlideDetail {
  id: string;
  title: string;
  topic: string;
  created_at: string;
  pdf_url?: string;
}

export async function slideDetailLoader({ params }: LoaderFunctionArgs) {
  const { slideId } = params;

  if (!slideId) {
    throw new Error('Slide ID is required');
  }

  try {
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8001/api';
    const response = await fetch(`${apiUrl}/slides/${slideId}/markdown`);

    if (!response.ok) {
      throw new Error(`Failed to fetch slide: ${response.statusText}`);
    }

    const data = await response.json();

    // APIレスポンス形式をSlideDetail型に変換
    const slide: SlideDetail = {
      id: data.slide_id,
      title: data.title,
      topic: data.title, // topicフィールドはtitleで代用
      created_at: data.created_at,
      pdf_url: data.pdf_url,
    };

    return { slide };
  } catch (err) {
    console.error('Failed to fetch slide:', err);
    throw err; // React Routerのエラーバウンダリで処理
  }
}

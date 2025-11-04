/**
 * SlideDetailPage
 * スライド詳細ページ（Phase 1: 基本構造のみ）
 * Phase 3でRAGチャット機能を追加予定
 */

import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { SlideViewer } from '../components/SlideViewer';

interface Slide {
  id: string;
  title: string;
  topic: string;
  created_at: string;
  pdf_url?: string;
}

export default function SlideDetailPage() {
  const { slideId } = useParams<{ slideId: string }>();
  const navigate = useNavigate();
  const [slide, setSlide] = useState<Slide | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSlide = async () => {
      try {
        const response = await fetch(
          `http://localhost:8001/api/slides/${slideId}`
        );

        if (!response.ok) {
          throw new Error(`Failed to fetch slide: ${response.statusText}`);
        }

        const data = await response.json();
        setSlide(data);
      } catch (err: any) {
        console.error('Failed to fetch slide:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    if (slideId) {
      fetchSlide();
    }
  }, [slideId]);

  if (loading) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#f5f5f5'
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{
            display: 'inline-block',
            width: '40px',
            height: '40px',
            border: '4px solid #f3f3f3',
            borderTop: '4px solid #007bff',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite'
          }} />
          <p style={{ marginTop: '12px', color: '#666' }}>読み込み中...</p>
          <style>{`
            @keyframes spin {
              0% { transform: rotate(0deg); }
              100% { transform: rotate(360deg); }
            }
          `}</style>
        </div>
      </div>
    );
  }

  if (error || !slide) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#f5f5f5'
      }}>
        <div style={{
          textAlign: 'center',
          padding: '40px',
          background: 'white',
          borderRadius: '12px',
          boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
        }}>
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>⚠️</div>
          <h2 style={{ color: '#dc3545', marginBottom: '8px' }}>
            スライドが見つかりません
          </h2>
          <p style={{ color: '#666', marginBottom: '24px' }}>
            {error || 'スライドが存在しないか、削除された可能性があります。'}
          </p>
          <button
            onClick={() => navigate('/')}
            style={{
              padding: '10px 24px',
              background: '#007bff',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              fontSize: '15px',
              fontWeight: 'bold',
              cursor: 'pointer'
            }}
          >
            ダッシュボードに戻る
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: '#f5f5f5',
      fontFamily: 'Arial, sans-serif'
    }}>
      {/* ヘッダー */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '16px 24px',
        background: 'white',
        borderBottom: '1px solid #dee2e6',
        boxShadow: '0 2px 4px rgba(0,0,0,0.05)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <button
            onClick={() => navigate('/')}
            style={{
              padding: '6px 12px',
              fontSize: '13px',
              background: '#6c757d',
              color: 'white',
              border: 'none',
              borderRadius: '5px',
              cursor: 'pointer'
            }}
          >
            ← Dashboard
          </button>
          <h1 style={{ margin: 0, fontSize: '20px', color: '#333' }}>
            {slide.title}
          </h1>
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          {slide.pdf_url && (
            <a
              href={slide.pdf_url}
              download
              style={{
                padding: '6px 12px',
                fontSize: '13px',
                background: '#28a745',
                color: 'white',
                border: 'none',
                borderRadius: '5px',
                textDecoration: 'none',
                cursor: 'pointer'
              }}
            >
              📥 PDF
            </a>
          )}
        </div>
      </div>

      {/* スライドビューア（Phase 1: フルスクリーン表示） */}
      <div style={{
        padding: '24px',
        maxWidth: '1200px',
        margin: '0 auto'
      }}>
        <div style={{
          background: 'white',
          borderRadius: '12px',
          padding: '24px',
          boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
        }}>
          <SlideViewer
            slideId={slideId!}
            onClose={() => navigate('/')}
          />
        </div>
      </div>

      {/* Phase 3: ここにRAGチャットパネルを追加予定 */}
      <div style={{
        padding: '24px',
        maxWidth: '1200px',
        margin: '0 auto'
      }}>
        <div style={{
          background: '#fff3cd',
          border: '1px solid #ffeaa7',
          borderRadius: '8px',
          padding: '16px',
          textAlign: 'center',
          color: '#856404'
        }}>
          💬 RAGチャット機能は Phase 3 で実装予定です
        </div>
      </div>
    </div>
  );
}

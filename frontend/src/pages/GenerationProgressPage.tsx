/**
 * GenerationProgressPage
 * スライド生成進行状況をリアルタイム表示
 */

import { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useReactAgent } from '../hooks/useReactAgent';
import ThinkingIndicator from '../components/ThinkingIndicator';

export default function GenerationProgressPage() {
  const navigate = useNavigate();
  const { thinkingSteps, isThinking, slideData, error } = useReactAgent();
  const hasRedirected = useRef(false);

  // スライド生成完了時に詳細ページへ自動遷移
  useEffect(() => {
    if (slideData.slide_id && !hasRedirected.current && !isThinking) {
      hasRedirected.current = true;

      // Phase 3: SlideDetailPageへ遷移
      setTimeout(() => {
        navigate(`/slides/${slideData.slide_id}`, { replace: true });
      }, 2000);
    }
  }, [slideData, isThinking, navigate]);

  return (
    <div style={{
      minHeight: '100vh',
      background: '#f5f5f5',
      fontFamily: 'Arial, sans-serif',
      display: 'flex',
      flexDirection: 'column'
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
          スライド生成中...
        </h1>
        <div style={{ width: '100px' }} /> {/* Spacer for centering */}
      </div>

      {/* 進行状況表示 */}
      <div style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '40px 20px'
      }}>
        <div style={{
          maxWidth: '800px',
          width: '100%',
          background: 'white',
          borderRadius: '12px',
          padding: '40px',
          boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
        }}>
          <div style={{
            textAlign: 'center',
            marginBottom: '32px'
          }}>
            <div style={{ fontSize: '48px', marginBottom: '16px' }}>
              🤖
            </div>
            <h2 style={{
              fontSize: '24px',
              fontWeight: 'bold',
              color: '#333',
              marginBottom: '8px'
            }}>
              AIアシスタントが作業中
            </h2>
            <p style={{
              fontSize: '14px',
              color: '#666'
            }}>
              スライドを生成しています。しばらくお待ちください...
            </p>
          </div>

          {/* 思考過程インジケーター */}
          <ThinkingIndicator steps={thinkingSteps} isActive={isThinking} />

          {/* 完了メッセージ */}
          {slideData.slide_id && !isThinking && (
            <div style={{
              marginTop: '24px',
              padding: '16px',
              background: '#d4edda',
              borderRadius: '8px',
              border: '1px solid #c3e6cb',
              textAlign: 'center'
            }}>
              <div style={{
                fontSize: '18px',
                fontWeight: 'bold',
                color: '#155724',
                marginBottom: '8px'
              }}>
                ✅ スライド生成完了
              </div>
              {slideData.title && (
                <div style={{
                  fontSize: '14px',
                  color: '#155724'
                }}>
                  {slideData.title}
                </div>
              )}
              <div style={{
                fontSize: '13px',
                color: '#155724',
                marginTop: '8px'
              }}>
                まもなくスライド詳細ページに移動します...
              </div>
            </div>
          )}

          {/* エラー表示 */}
          {error && (
            <div style={{
              marginTop: '24px',
              padding: '16px',
              background: '#f8d7da',
              color: '#721c24',
              borderRadius: '8px',
              border: '1px solid #f5c6cb'
            }}>
              ❌ エラー: {error}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

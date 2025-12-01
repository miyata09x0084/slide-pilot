/**
 * GenerationProgressPage
 * 動画生成進行状況をリアルタイム表示
 */

import { useEffect, useRef, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useReactAgent } from './hooks/useReactAgent';
import { uploadPdf } from '../dashboard/api/upload-pdf';

// 処理ステータス
type ProcessingStatus = 'uploading' | 'creating_thread' | 'generating' | 'completed' | 'error';

export default function GenerationProgressPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { pdfPath, pdfFile, autoStart } = (location.state as { pdfPath?: string; pdfFile?: File; autoStart?: boolean }) || {};
  const { isThinking, isPollingVideo, slideData, error, createThread, sendMessage } = useReactAgent();
  const hasRedirected = useRef(false);
  const hasStarted = useRef(false);
  const [status, setStatus] = useState<ProcessingStatus>('uploading');

  // PDF自動開始処理（アップロード完了時）
  useEffect(() => {
    if (!autoStart || hasStarted.current) return;
    hasStarted.current = true;

    (async () => {
      try {
        // Phase 1: PDFアップロード（ファイルオブジェクトが渡された場合）
        let finalPath = pdfPath;
        if (pdfFile && !pdfPath) {
          setStatus('uploading');
          const uploadResult = await uploadPdf({
            file: pdfFile,
          });
          finalPath = uploadResult.path;
        }

        if (!finalPath) {
          throw new Error('PDFパスが取得できませんでした');
        }

        // Phase 2: スレッド作成
        setStatus('creating_thread');
        const tid = await createThread();

        // Phase 3: スライド生成開始（LangGraphは動画ではなくスライドツールのみ対応）
        setStatus('generating');
        await sendMessage(
          `このPDFから中学生向けのわかりやすいスライドを作成してください: ${finalPath}`,
          tid
        );
      } catch (err) {
        console.error('❌ 処理エラー:', err);
        setStatus('error');
      }
    })();
    // 依存配列からthreadIdを削除（古い値での再実行を防ぐ）
  }, [autoStart, pdfPath, pdfFile, createThread, sendMessage]);

  // 動画生成完了時に詳細ページへ自動遷移
  useEffect(() => {
    // slide_idまたはpathがあり、思考中でなく、ポーリング中でもない場合にリダイレクト
    // isPollingVideo=trueの間は動画レンダリング中なので待機する
    if ((slideData.slide_id || slideData.path) && !hasRedirected.current && !isThinking && !isPollingVideo) {
      hasRedirected.current = true;

      // slide_idがあればSlideDetailPageへ、なければダッシュボードへ
      setTimeout(() => {
        if (slideData.slide_id) {
          navigate(`/slides/${slideData.slide_id}`, { replace: true });
        } else {
          // 古いワークフローの場合はダッシュボードに戻る
          navigate('/', { replace: true });
        }
      }, 2000);
    }
  }, [slideData, isThinking, isPollingVideo, navigate]);

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
            {/* 回転スピナー */}
            <div style={{
              width: '60px',
              height: '60px',
              margin: '0 auto 20px',
              border: '4px solid #e5e7eb',
              borderTop: '4px solid #3b82f6',
              borderRadius: '50%',
              animation: 'spin 1s linear infinite'
            }} />

            {/* 動的ステータス表示 */}
            <h2 style={{
              fontSize: '24px',
              fontWeight: 'bold',
              color: '#333',
              marginBottom: '8px'
            }}>
              {status === 'uploading' && 'PDFアップロード中...'}
              {status === 'creating_thread' && '準備中...'}
              {status === 'generating' && '動画を生成しています'}
              {status === 'completed' && '完了しました'}
              {status === 'error' && 'エラーが発生しました'}
            </h2>

            {/* ステータス別の説明文 */}
            <p style={{
              fontSize: '14px',
              color: '#666'
            }}>
              {status === 'creating_thread' && '動画生成の準備をしています'}
              {status === 'generating' && 'PDFを分析して動画を生成中...（4〜6分）'}
              {status === 'completed' && 'まもなく動画ページに移動します'}
              {status === 'error' && (error || '不明なエラーが発生しました')}
            </p>
          </div>

          {/* 動画レンダリング中の表示 */}
          {isPollingVideo && (
            <div style={{
              marginTop: '24px',
              padding: '16px',
              background: '#fff3cd',
              borderRadius: '8px',
              border: '1px solid #ffc107',
              textAlign: 'center'
            }}>
              <div style={{
                fontSize: '18px',
                fontWeight: 'bold',
                color: '#856404',
                marginBottom: '8px'
              }}>
                🎬 動画をレンダリング中...
              </div>
              <div style={{
                fontSize: '13px',
                color: '#856404'
              }}>
                しばらくお待ちください（1〜2分）
              </div>
            </div>
          )}

          {/* 完了メッセージ */}
          {slideData.slide_id && !isThinking && !isPollingVideo && (
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
                ✅ 動画生成完了
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
                まもなく動画ページに移動します...
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

      {/* CSSアニメーション */}
      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}

/**
 * DashboardPage (Phase 3: ページ遷移対応)
 * トップページ: PDFアップロード + スライド履歴表示
 */

import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { useReactAgent } from '../hooks/useReactAgent';
import DashboardLayout from '../components/dashboard/DashboardLayout';
import AssistantPanel from '../components/dashboard/AssistantPanel';
import SlideHistoryGrid from '../components/dashboard/SlideHistoryGrid';
import QuickActionPanel from '../components/dashboard/QuickActionPanel';

const styles: Record<string, React.CSSProperties> = {
  container: {
    minHeight: '100vh',
    background: '#f5f5f5',
    fontFamily: 'Arial, sans-serif',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '16px 24px',
    background: 'white',
    borderBottom: '1px solid #dee2e6',
    boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
  },
  logo: {
    margin: 0,
    fontSize: '24px',
    fontWeight: 'bold',
    color: '#333',
  },
  userSection: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  avatar: {
    width: '36px',
    height: '36px',
    borderRadius: '50%',
  },
  userName: {
    fontSize: '14px',
    fontWeight: 'bold',
  },
  logoutButton: {
    padding: '8px 16px',
    fontSize: '13px',
    background: '#dc3545',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    fontWeight: '600',
    transition: 'background 0.2s',
  },
};

export default function DashboardPage() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { createThread, sendMessage } = useReactAgent();

  // ログアウト処理
  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  // PDFアップロード処理
  const handlePdfUpload = async (path: string) => {
    console.log('📄 Starting slide generation from PDF:', path);

    try {
      const tid = await createThread();
      navigate(`/generate/${tid}`, { state: { pdfPath: path } });
      await sendMessage(
        `このPDFから中学生向けのわかりやすいスライドを作成してください: ${path}`,
        tid
      );
    } catch (err) {
      console.error('❌ PDF処理エラー:', err);
    }
  };

  // YouTube URL送信処理（将来実装）
  const handleYoutubeSubmit = async (url: string) => {
    console.log('🎥 YouTube URL:', url);

    try {
      const tid = await createThread();
      navigate(`/generate/${tid}`, { state: { youtubeUrl: url } });
      await sendMessage(
        `このYouTube動画から中学生向けのスライドを作成してください: ${url}`,
        tid
      );
    } catch (err) {
      console.error('❌ YouTube処理エラー:', err);
    }
  };

  // クイックテンプレートクリック
  const handleTemplateClick = async (templateId: string) => {
    const templates: Record<string, string> = {
      'ai-news': 'AI最新ニュースについて、2025年のトレンドをまとめたスライドを作成してください',
      'ml-basics': '機械学習の基礎について、初心者向けのスライドを作成してください',
      'textbook': '教科書の章立てから復習用スライドを作成してください',
    };

    const prompt = templates[templateId];
    if (!prompt) return;

    try {
      const tid = await createThread();
      navigate(`/generate/${tid}`, { state: { template: templateId } });
      await sendMessage(prompt, tid);
    } catch (err) {
      console.error('❌ テンプレート処理エラー:', err);
    }
  };

  // スライド履歴カードクリック（Phase 3: 専用ページに遷移）
  const handleSlideClick = (slideId: string) => {
    navigate(`/slides/${slideId}`);
  };

  if (!user) {
    return null;
  }

  return (
    <div style={styles.container}>
      {/* ヘッダー */}
      <div style={styles.header}>
        <h1 style={styles.logo}>SlidePilot</h1>

        <div style={styles.userSection}>
          <img
            src={user.picture}
            alt={user.name}
            style={styles.avatar}
          />
          <div style={styles.userName}>{user.name}</div>
          <button
            onClick={handleLogout}
            onMouseOver={(e) => e.currentTarget.style.background = '#c82333'}
            onMouseOut={(e) => e.currentTarget.style.background = '#dc3545'}
            style={styles.logoutButton}
          >
            ログアウト
          </button>
        </div>
      </div>

      {/* 3カラムレイアウト */}
      <DashboardLayout
        leftSidebar={
          <SlideHistoryGrid
            userEmail={user.email}
            onSlideClick={handleSlideClick}
          />
        }
        centerPanel={
          <AssistantPanel
            onPdfUpload={handlePdfUpload}
            onYoutubeSubmit={handleYoutubeSubmit}
          />
        }
        rightSidebar={
          <QuickActionPanel onTemplateClick={handleTemplateClick} />
        }
      />
    </div>
  );
}

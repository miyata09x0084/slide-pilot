/**
 * DashboardPage - 統一カード形式のダッシュボード
 * 全ての要素を同じサイズのカードとして表示
 */

import { useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { useReactAgent } from '../hooks/useReactAgent';
import UnifiedCard from '../components/UnifiedCard';
import QuickActionMenu from '../components/QuickActionMenu';

const styles: Record<string, React.CSSProperties> = {
  container: {
    minHeight: '100vh',
    background: '#f9fafb',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '16px 32px',
    background: 'white',
    borderBottom: '1px solid #e5e7eb',
    boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
  },
  logoSection: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  logoIcon: {
    fontSize: '28px',
  },
  logo: {
    margin: 0,
    fontSize: '22px',
    fontWeight: '700',
    color: '#1a1a1a',
    letterSpacing: '-0.5px',
  },
  userSection: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
  },
  avatar: {
    width: '36px',
    height: '36px',
    borderRadius: '50%',
    border: '2px solid #e5e7eb',
  },
  userName: {
    fontSize: '14px',
    fontWeight: '600',
    color: '#374151',
  },
  logoutButton: {
    padding: '8px 16px',
    fontSize: '13px',
    background: '#f3f4f6',
    color: '#374151',
    border: '1px solid #d1d5db',
    borderRadius: '6px',
    cursor: 'pointer',
    fontWeight: '600',
    transition: 'all 0.2s',
  },
  gridContainer: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
    gridAutoRows: 'minmax(200px, auto)',
    gap: '20px',
    padding: '32px',
    maxWidth: '1440px',
    margin: '0 auto',
  },
  emptyState: {
    gridColumn: '1 / -1',
    textAlign: 'center',
    padding: '60px 20px',
    color: '#9ca3af',
  },
  emptyIcon: {
    fontSize: '64px',
    marginBottom: '16px',
  },
  emptyText: {
    fontSize: '16px',
    fontWeight: '600',
    color: '#6b7280',
    marginBottom: '8px',
  },
  emptySubtext: {
    fontSize: '14px',
    color: '#9ca3af',
  },
};

// レスポンシブ対応のCSS
const responsiveStyles = `
  @media (max-width: 639px) {
    .dashboard-grid {
      grid-template-columns: 1fr !important;
      padding: 20px !important;
      gap: 16px !important;
    }
  }

  @media (min-width: 640px) and (max-width: 1023px) {
    .dashboard-grid {
      grid-template-columns: repeat(2, 1fr) !important;
      gap: 18px !important;
    }
  }

  @media (min-width: 1024px) and (max-width: 1279px) {
    .dashboard-grid {
      grid-template-columns: repeat(3, 1fr) !important;
      gap: 20px !important;
    }
  }

  @media (min-width: 1280px) {
    .dashboard-grid {
      grid-template-columns: repeat(4, 1fr) !important;
      gap: 24px !important;
    }
  }
`;

interface Slide {
  id: string;
  title: string;
  created_at: string;
}

export default function DashboardPage() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { createThread, sendMessage } = useReactAgent();
  const [slides, setSlides] = useState<Slide[]>([]);
  const [showAll, setShowAll] = useState(false);
  const [showQuickMenu, setShowQuickMenu] = useState(false);

  // スライド履歴を取得
  useEffect(() => {
    const fetchSlides = async () => {
      if (!user?.email) return;

      try {
        const response = await fetch(
          `http://localhost:8001/api/slides?user_id=${encodeURIComponent(user.email)}&limit=20`
        );

        if (!response.ok) {
          throw new Error(`Failed to fetch slides: ${response.statusText}`);
        }

        const data = await response.json();
        setSlides(data.slides || []);
      } catch (err) {
        console.error('Failed to fetch slides:', err);
      }
    };

    fetchSlides();
  }, [user?.email]);

  // ログアウト処理
  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  // クイックメニューを開く
  const handleNewSlide = () => {
    setShowQuickMenu(true);
  };

  // PDFアップロード選択時
  const handleSelectUpload = () => {
    // ファイル選択ダイアログを開く
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.pdf';
    input.onchange = async (e: Event) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (file) {
        await uploadAndGenerate(file);
      }
    };
    input.click();
  };

  // PDFアップロードとスライド生成
  const uploadAndGenerate = async (file: File) => {
    // ファイルサイズチェック
    if (file.size > 100 * 1024 * 1024) {
      alert('ファイルサイズは100MB以下にしてください');
      return;
    }

    try {
      // アップロード
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('http://localhost:8001/api/upload-pdf', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('アップロードに失敗しました');
      }

      const data = await response.json();

      // スライド生成開始
      const tid = await createThread();
      navigate(`/generate/${tid}`, { state: { pdfPath: data.path } });
      await sendMessage(
        `このPDFから中学生向けのわかりやすいスライドを作成してください: ${data.path}`,
        tid
      );
    } catch (err) {
      console.error('❌ スライド生成エラー:', err);
      alert('エラーが発生しました');
    }
  };

  // テンプレートクリック
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

  // スライドクリック
  const handleSlideClick = (slideId: string) => {
    navigate(`/slides/${slideId}`);
  };

  if (!user) {
    return null;
  }

  // 表示するスライド数
  const displayedSlides = showAll ? slides : slides.slice(0, 5);
  const remainingCount = slides.length - displayedSlides.length;

  return (
    <div style={styles.container}>
      {/* ヘッダー */}
      <div style={styles.header}>
        <div style={styles.logoSection}>
          <span style={styles.logoIcon}>📊</span>
          <h1 style={styles.logo}>SlidePilot</h1>
        </div>

        <div style={styles.userSection}>
          <img
            src={user.picture}
            alt={user.name}
            style={styles.avatar}
          />
          <div style={styles.userName}>{user.name}</div>
          <button
            onClick={handleLogout}
            onMouseOver={(e) => {
              e.currentTarget.style.background = '#e5e7eb';
              e.currentTarget.style.borderColor = '#9ca3af';
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.background = '#f3f4f6';
              e.currentTarget.style.borderColor = '#d1d5db';
            }}
            style={styles.logoutButton}
          >
            ログアウト
          </button>
        </div>
      </div>

      {/* カードグリッド */}
      <div className="dashboard-grid" style={styles.gridContainer}>
        {/* 新規作成 */}
        <UnifiedCard
          icon="+"
          title="新規作成"
          subtitle="スライドを作成"
          onClick={handleNewSlide}
          variant="primary"
          className="card-default"
        />

        {/* 空状態 */}
        {displayedSlides.length === 0 ? (
          <div style={styles.emptyState}>
            <div style={styles.emptyIcon}>📄</div>
            <div style={styles.emptyText}>まだスライドがありません</div>
            <div style={styles.emptySubtext}>
              新規作成からスライドを作成してみましょう
            </div>
          </div>
        ) : (
          <>
            {displayedSlides.map((slide) => (
              <UnifiedCard
                key={slide.id}
                icon="📊"
                title={slide.title}
                subtitle={new Date(slide.created_at).toLocaleDateString('ja-JP', {
                  year: 'numeric',
                  month: 'short',
                  day: 'numeric',
                })}
                onClick={() => handleSlideClick(slide.id)}
                variant="history"
                className="card-default"
              />
            ))}

            {/* もっと読み込むカード */}
            {remainingCount > 0 && !showAll && (
              <UnifiedCard
                icon="⬇️"
                title="もっと読み込む"
                subtitle={`残り${remainingCount}件`}
                onClick={() => setShowAll(true)}
                variant="more"
                className="card-default"
              />
            )}
          </>
        )}
      </div>

      {/* クイックアクションメニュー */}
      {showQuickMenu && (
        <QuickActionMenu
          onClose={() => setShowQuickMenu(false)}
          onSelectUpload={handleSelectUpload}
          onSelectTemplate={handleTemplateClick}
        />
      )}

      <style>{responsiveStyles}</style>
    </div>
  );
}

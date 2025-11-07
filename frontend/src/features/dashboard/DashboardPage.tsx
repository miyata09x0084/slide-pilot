/**
 * DashboardPage - 統一カード形式のダッシュボード (Phase 3最適化済み)
 * 全ての要素を同じサイズのカードとして表示
 * React Query使用でデータ取得とキャッシュ管理
 * Phase 3: useCallback()でイベントハンドラーをメモ化、不要な再レンダリング防止
 */

import { useNavigate } from "react-router-dom";
import { useState, useCallback } from "react";
import { useAuth } from "../auth";
import { useReactAgent } from "../generation";
import { useSlides } from "./hooks/useSlides";
import UnifiedCard from "./components/UnifiedCard";
import QuickActionMenu from "./components/QuickActionMenu";

const styles: Record<string, React.CSSProperties> = {
  container: {
    minHeight: "100vh",
    background: "#f9fafb",
    fontFamily:
      '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "16px 32px",
    background: "white",
    borderBottom: "1px solid #e5e7eb",
    boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
  },
  logoSection: {
    display: "flex",
    alignItems: "center",
    gap: "12px",
  },
  logoIcon: {
    fontSize: "28px",
  },
  logo: {
    margin: 0,
    fontSize: "22px",
    fontWeight: "700",
    color: "#1a1a1a",
    letterSpacing: "-0.5px",
  },
  userSection: {
    display: "flex",
    alignItems: "center",
    gap: "16px",
  },
  avatar: {
    width: "36px",
    height: "36px",
    borderRadius: "50%",
    border: "2px solid #e5e7eb",
  },
  userName: {
    fontSize: "14px",
    fontWeight: "600",
    color: "#374151",
  },
  logoutButton: {
    padding: "8px 16px",
    fontSize: "13px",
    background: "#f3f4f6",
    color: "#374151",
    border: "1px solid #d1d5db",
    borderRadius: "6px",
    cursor: "pointer",
    fontWeight: "600",
    transition: "all 0.2s",
  } as React.CSSProperties,
  gridContainer: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
    gridAutoRows: "minmax(200px, auto)",
    gap: "20px",
    padding: "32px",
    maxWidth: "1440px",
    margin: "0 auto",
  },
  emptyState: {
    gridColumn: "1 / -1",
    textAlign: "center",
    padding: "60px 20px",
    color: "#9ca3af",
  },
  emptyIcon: {
    fontSize: "64px",
    marginBottom: "16px",
  },
  emptyText: {
    fontSize: "16px",
    fontWeight: "600",
    color: "#6b7280",
    marginBottom: "8px",
  },
  emptySubtext: {
    fontSize: "14px",
    color: "#9ca3af",
  },
};

// レスポンシブ対応とホバースタイルのCSS（Phase 3: パフォーマンス最適化）
const responsiveStyles = `
  /* ログアウトボタンのホバースタイル */
  .logout-button:hover {
    background: #e5e7eb !important;
    border-color: #9ca3af !important;
  }

  /* レスポンシブグリッド */
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

export default function DashboardPage() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { createThread, sendMessage } = useReactAgent();

  // React Queryでスライド一覧を取得（キャッシュあり）
  const { data: slides = [], isLoading, error } = useSlides(user?.email || '', 20);

  const [showAll, setShowAll] = useState(false);
  const [showQuickMenu, setShowQuickMenu] = useState(false);

  // ログアウト処理（メモ化）
  const handleLogout = useCallback(() => {
    logout();
    navigate("/login", { replace: true });
  }, [logout, navigate]);

  // クイックメニューを開く（メモ化）
  const handleNewSlide = useCallback(() => {
    setShowQuickMenu(true);
  }, []);

  // PDFアップロードとスライド生成（メモ化）
  const uploadAndGenerate = useCallback(async (file: File) => {
    // ファイルサイズチェック
    if (file.size > 100 * 1024 * 1024) {
      alert("ファイルサイズは100MB以下にしてください");
      return;
    }

    try {
      // アップロード
      const formData = new FormData();
      formData.append("file", file);

      // user_idをクエリパラメータで送信
      const apiUrl =
        import.meta.env.VITE_API_URL || "http://localhost:8001/api";
      const uploadUrl = `${apiUrl}/upload-pdf${
        user?.email ? `?user_id=${encodeURIComponent(user.email)}` : ""
      }`;

      const response = await fetch(uploadUrl, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error("アップロードに失敗しました");
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
      console.error("❌ スライド生成エラー:", err);
      alert("エラーが発生しました");
    }
  }, [user?.email, createThread, navigate, sendMessage]);

  // PDFアップロード選択時（メモ化）
  const handleSelectUpload = useCallback(() => {
    // ファイル選択ダイアログを開く
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".pdf";
    input.onchange = async (e: Event) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (file) {
        await uploadAndGenerate(file);
      }
    };
    input.click();
  }, [uploadAndGenerate]);

  // テンプレートクリック（メモ化）
  const handleTemplateClick = useCallback(async (templateId: string) => {
    const templates: Record<string, string> = {
      "ai-news":
        "AI最新ニュースについて、2025年のトレンドをまとめたスライドを作成してください",
      "ml-basics":
        "機械学習の基礎について、初心者向けのスライドを作成してください",
      textbook: "教科書の章立てから復習用スライドを作成してください",
    };

    const prompt = templates[templateId];
    if (!prompt) return;

    try {
      const tid = await createThread();
      navigate(`/generate/${tid}`, { state: { template: templateId } });
      await sendMessage(prompt, tid);
    } catch (err) {
      console.error("❌ テンプレート処理エラー:", err);
    }
  }, [createThread, navigate, sendMessage]);

  // イベント委譲: グリッド全体でクリックを処理（メモ化）
  const handleGridClick = useCallback((e: React.MouseEvent) => {
    const target = e.target as HTMLElement;
    // クリックされた要素から最も近い data-slide-id を持つ要素を探す
    const card = target.closest('[data-slide-id]') as HTMLElement;

    if (card && card.dataset.slideId) {
      navigate(`/slides/${card.dataset.slideId}`);
    }
  }, [navigate]);

  if (!user) {
    return null;
  }

  // ローディング状態
  if (isLoading) {
    return (
      <div style={styles.container}>
        <div style={styles.header}>
          <div style={styles.logoSection}>
            <span style={styles.logoIcon}>📊</span>
            <h1 style={styles.logo}>SlidePilot</h1>
          </div>
        </div>
        <div style={{ ...styles.emptyState, padding: '120px 20px' }}>
          <div style={{
            width: '48px',
            height: '48px',
            border: '4px solid #e5e7eb',
            borderTopColor: '#3b82f6',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite',
            margin: '0 auto 24px',
          }} />
          <div style={styles.emptyText}>読み込み中...</div>
          <style>{`
            @keyframes spin {
              to { transform: rotate(360deg); }
            }
          `}</style>
        </div>
      </div>
    );
  }

  // エラー状態
  if (error) {
    return (
      <div style={styles.container}>
        <div style={styles.header}>
          <div style={styles.logoSection}>
            <span style={styles.logoIcon}>📊</span>
            <h1 style={styles.logo}>SlidePilot</h1>
          </div>
        </div>
        <div style={{ ...styles.emptyState, padding: '120px 20px' }}>
          <div style={{ fontSize: '48px', marginBottom: '16px', color: '#ef4444' }}>✕</div>
          <div style={{ ...styles.emptyText, color: '#ef4444' }}>エラーが発生しました</div>
          <div style={styles.emptySubtext}>{error.message}</div>
        </div>
      </div>
    );
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
          <img src={user.picture} alt={user.name} style={styles.avatar} />
          <div style={styles.userName}>{user.name}</div>
          <button
            onClick={handleLogout}
            className="logout-button"
            style={styles.logoutButton}
          >
            ログアウト
          </button>
        </div>
      </div>

      {/* カードグリッド（イベント委譲でスライドクリックを処理） */}
      <div
        className="dashboard-grid"
        style={styles.gridContainer}
        onClick={handleGridClick}
      >
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
                subtitle={new Date(slide.created_at).toLocaleDateString(
                  "ja-JP",
                  {
                    year: "numeric",
                    month: "short",
                    day: "numeric",
                  }
                )}
                data-slide-id={slide.id}
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

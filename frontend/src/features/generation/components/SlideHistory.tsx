/**
 * SlideHistory - スライド履歴表示コンポーネント
 *
 * React Query フックでSupabaseから取得したユーザーのスライド一覧をカード形式で表示
 */

import { useSlides } from "../../dashboard/api/get-slides";

interface SlideHistoryProps {
  onPreview: (slideId: string) => void;
}

export function SlideHistory({ onPreview }: SlideHistoryProps) {
  // React Queryフックでスライド履歴を取得（JWTから自動的にuser_idを取得）
  const { data, isLoading: loading, error } = useSlides({ limit: 20 });
  const slides = data?.slides || [];

  if (loading) {
    return (
      <div
        style={{
          textAlign: "center",
          padding: "40px",
          color: "#666",
        }}
      >
        <div
          style={{
            display: "inline-block",
            width: "40px",
            height: "40px",
            border: "4px solid #f3f3f3",
            borderTop: "4px solid #007bff",
            borderRadius: "50%",
            animation: "spin 1s linear infinite",
          }}
        />
        <p style={{ marginTop: "12px" }}>読み込み中...</p>
        <style>{`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    );
  }

  if (error) {
    return (
      <div
        style={{
          textAlign: "center",
          padding: "40px",
          color: "#dc3545",
          background: "#f8d7da",
          borderRadius: "8px",
          border: "1px solid #f5c6cb",
        }}
      >
        ⚠️ エラー: {error.message || "スライドの読み込みに失敗しました"}
      </div>
    );
  }

  if (slides.length === 0) {
    return (
      <div
        style={{
          textAlign: "center",
          padding: "60px 20px",
          color: "#999",
          background: "white",
          borderRadius: "12px",
          border: "2px dashed #e0e0e0",
        }}
      >
        <div style={{ fontSize: "48px", marginBottom: "16px" }}>📄</div>
        <p style={{ fontSize: "16px", margin: 0 }}>まだスライドがありません</p>
        <p style={{ fontSize: "14px", marginTop: "8px", color: "#bbb" }}>
          PDFをアップロードしてスライドを作成してみましょう
        </p>
      </div>
    );
  }

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))",
        gap: "20px",
        padding: "4px", // シャドウが切れないように
      }}
    >
      {slides.map((slide) => (
        <div
          key={slide.id}
          style={{
            background: "white",
            borderRadius: "12px",
            padding: "20px",
            boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
            transition: "transform 0.2s, box-shadow 0.2s",
            cursor: "pointer",
            border: "1px solid #e0e0e0",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = "translateY(-4px)";
            e.currentTarget.style.boxShadow = "0 4px 16px rgba(0,0,0,0.15)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = "translateY(0)";
            e.currentTarget.style.boxShadow = "0 2px 8px rgba(0,0,0,0.1)";
          }}
        >
          {/* タイトル */}
          <h3
            style={{
              margin: "0 0 12px 0",
              fontSize: "18px",
              fontWeight: 600,
              color: "#1a1a1a",
              lineHeight: 1.4,
              display: "-webkit-box",
              WebkitLineClamp: 2,
              WebkitBoxOrient: "vertical",
              overflow: "hidden",
            }}
          >
            {slide.title}
          </h3>

          {/* 作成日時 */}
          <p
            style={{
              fontSize: "13px",
              color: "#666",
              margin: "0 0 8px 0",
              display: "flex",
              alignItems: "center",
              gap: "6px",
            }}
          >
            <span>🕒</span>
            {new Date(slide.created_at).toLocaleString("ja-JP", {
              year: "numeric",
              month: "short",
              day: "numeric",
              hour: "2-digit",
              minute: "2-digit",
            })}
          </p>

          {/* トピック */}
          <p
            style={{
              fontSize: "13px",
              color: "#999",
              margin: "0 0 16px 0",
              display: "-webkit-box",
              WebkitLineClamp: 2,
              WebkitBoxOrient: "vertical",
              overflow: "hidden",
              lineHeight: 1.5,
            }}
          >
            {slide.topic}
          </p>

          {/* プレビューボタン */}
          <button
            onClick={() => onPreview(slide.id)}
            style={{
              width: "100%",
              padding: "10px",
              background: "#007bff",
              color: "white",
              border: "none",
              borderRadius: "6px",
              fontSize: "14px",
              fontWeight: 600,
              cursor: "pointer",
              transition: "background 0.2s",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "8px",
            }}
            onMouseOver={(e) => (e.currentTarget.style.background = "#0056b3")}
            onMouseOut={(e) => (e.currentTarget.style.background = "#007bff")}
          >
            <span>📄</span>
            <span>プレビュー</span>
          </button>
        </div>
      ))}
    </div>
  );
}

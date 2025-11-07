/**
 * PageLoader - Code Splitting時のローディングコンポーネント
 *
 * React.Suspenseのfallbackとして使用
 * シンプルな回転スピナーとローディングテキストを表示
 */

export function PageLoader() {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        gap: '24px',
        backgroundColor: '#f9fafb',
      }}
    >
      {/* 回転スピナー */}
      <div
        style={{
          width: '48px',
          height: '48px',
          border: '4px solid #e5e7eb',
          borderTopColor: '#3b82f6',
          borderRadius: '50%',
          animation: 'spin 1s linear infinite',
        }}
      />

      {/* ローディングテキスト */}
      <p
        style={{
          fontSize: '16px',
          color: '#6b7280',
          margin: 0,
        }}
      >
        Loading...
      </p>

      {/* CSS Animation */}
      <style>{`
        @keyframes spin {
          from {
            transform: rotate(0deg);
          }
          to {
            transform: rotate(360deg);
          }
        }
      `}</style>
    </div>
  );
}

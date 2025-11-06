// ReActエージェントの思考過程を可視化するコンポーネント
// ツール呼び出しやLLMの推論ステップをリアルタイム表示

export interface ThinkingStep {
  type: 'thinking' | 'action' | 'observation';  // ステップの種類
  content: string;                              // 表示内容
}

interface ThinkingIndicatorProps {
  steps: ThinkingStep[];   // 思考ステップの配列
  isActive: boolean;       // 現在思考中かどうか
}

export default function ThinkingIndicator({ steps, isActive }: ThinkingIndicatorProps) {
  // 思考中でない、かつステップが空の場合は非表示
  if (!isActive && steps.length === 0) {
    return null;
  }

  return (
    <div style={{
      margin: '16px 0',
      padding: '16px',
      background: '#f8f9fa',
      borderRadius: '12px',
      border: '1px solid #dee2e6'
    }}>
      {/* ヘッダー */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        marginBottom: steps.length > 0 ? '12px' : '0',
        fontSize: '14px',
        fontWeight: 'bold',
        color: '#495057'
      }}>
        <span style={{ fontSize: '18px' }}>🧠</span>
        <span>AIが考えています...</span>
        {isActive && (
          <span style={{
            marginLeft: 'auto',
            fontSize: '12px',
            color: '#6c757d',
            animation: 'pulse 1.5s ease-in-out infinite'
          }}>
            ●
          </span>
        )}
      </div>

      {/* 思考ステップ一覧 */}
      {steps.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {steps.map((step, index) => {
            // ステップ種別ごとのアイコンと色
            const config = {
              thinking: { icon: '💭', color: '#6f42c1', label: '思考' },
              action: { icon: '⚙️', color: '#007bff', label: 'ツール実行' },
              observation: { icon: '👁️', color: '#28a745', label: '観察' }
            }[step.type];

            return (
              <div
                key={index}
                style={{
                  display: 'flex',
                  gap: '8px',
                  padding: '8px 12px',
                  background: 'white',
                  borderRadius: '6px',
                  fontSize: '13px',
                  borderLeft: `3px solid ${config.color}`
                }}
              >
                <span style={{ fontSize: '16px', flexShrink: 0 }}>{config.icon}</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 'bold', color: config.color, marginBottom: '2px' }}>
                    {config.label}
                  </div>
                  <div style={{ color: '#495057', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                    {step.content}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* CSSアニメーション */}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }
      `}</style>
    </div>
  );
}

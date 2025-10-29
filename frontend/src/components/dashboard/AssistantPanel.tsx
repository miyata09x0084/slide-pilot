/**
 * AssistantPanel
 * 中央パネル: PDFドロップ + URL入力（将来）
 */

import FileDropzone from '../FileDropzone';

interface AssistantPanelProps {
  onPdfUpload: (path: string) => void;
  onYoutubeSubmit?: (url: string) => void;
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: '32px',
  },
  greeting: {
    textAlign: 'center',
    marginBottom: '8px',
  },
  greetingIcon: {
    fontSize: '48px',
    marginBottom: '16px',
  },
  greetingTitle: {
    fontSize: '28px',
    fontWeight: 'bold',
    color: '#333',
    marginBottom: '8px',
  },
  greetingSubtitle: {
    fontSize: '16px',
    color: '#666',
  },
  section: {
    marginBottom: '24px',
  },
  sectionTitle: {
    fontSize: '18px',
    fontWeight: '600',
    color: '#333',
    marginBottom: '16px',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  urlInputContainer: {
    textAlign: 'center',
    padding: '24px',
    background: '#f8f9fa',
    borderRadius: '8px',
    border: '2px dashed #dee2e6',
  },
  urlInputLabel: {
    fontSize: '16px',
    color: '#999',
    marginBottom: '12px',
  },
  urlComingSoon: {
    fontSize: '14px',
    color: '#6c757d',
    fontStyle: 'italic',
  },
  usageHints: {
    padding: '20px',
    background: '#f8f9fa',
    borderRadius: '8px',
    fontSize: '14px',
    color: '#666',
  },
  usageTitle: {
    marginBottom: '12px',
    fontWeight: 'bold',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  usageList: {
    margin: 0,
    paddingLeft: '24px',
    lineHeight: '1.8',
  },
};

export default function AssistantPanel({
  onPdfUpload,
  onYoutubeSubmit,
}: AssistantPanelProps) {
  return (
    <div style={styles.container}>
      {/* 挨拶セクション */}
      <div style={styles.greeting}>
        <div style={styles.greetingIcon}>🤖</div>
        <h2 style={styles.greetingTitle}>どの資料からスライドを作る？</h2>
        <p style={styles.greetingSubtitle}>
          難しい資料を、中学生でもわかるスライドに変換します
        </p>
      </div>

      {/* PDFアップロードセクション */}
      <div style={styles.section}>
        <h3 style={styles.sectionTitle}>
          <span>📄</span>
          <span>PDFをアップロード</span>
        </h3>
        <FileDropzone onUpload={onPdfUpload} />
      </div>

      {/* URL入力セクション（将来実装） */}
      {onYoutubeSubmit && (
        <div style={styles.section}>
          <h3 style={styles.sectionTitle}>
            <span>🔗</span>
            <span>URLから作成</span>
          </h3>
          <div style={styles.urlInputContainer}>
            <div style={styles.urlInputLabel}>YouTube、論文サイトなど</div>
            <div style={styles.urlComingSoon}>(準備中)</div>
          </div>
        </div>
      )}

      {/* 使い方ヒント */}
      <div style={styles.usageHints}>
        <div style={styles.usageTitle}>
          <span>💡</span>
          <span>こんな使い方ができます</span>
        </div>
        <ul style={styles.usageList}>
          <li>難しい論文をわかりやすいスライドに</li>
          <li>教科書の内容を復習用スライドに</li>
          <li>スライド作成後、内容について質問もできます</li>
        </ul>
      </div>
    </div>
  );
}

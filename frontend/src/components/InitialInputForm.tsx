/**
 * InitialInputForm Component (Issue #17)
 * PDF/YouTube入力の初回画面
 */

import FileDropzone from './FileDropzone';

interface InitialInputFormProps {
  onPdfUpload: (path: string) => void;
  onYoutubeSubmit?: (url: string) => void;
}

export default function InitialInputForm({
  onPdfUpload,
  onYoutubeSubmit,
}: InitialInputFormProps) {
  return (
    <div
      style={{
        maxWidth: '600px',
        margin: '0 auto',
        padding: '40px 20px',
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
      }}
    >
      <h1
        style={{
          textAlign: 'center',
          marginBottom: '16px',
          fontSize: '32px',
          fontWeight: 'bold',
          color: '#333',
        }}
      >
        📚 中学生でもわかるスライド作成
      </h1>

      <p
        style={{
          textAlign: 'center',
          marginBottom: '40px',
          color: '#666',
          fontSize: '16px',
        }}
      >
        難しいPDFを、わかりやすいスライドに変換します
      </p>

      <FileDropzone onUpload={onPdfUpload} />

      {onYoutubeSubmit && (
        <>
          <div
            style={{
              textAlign: 'center',
              margin: '30px 0',
              color: '#999',
              fontSize: '14px',
            }}
          >
            YouTube対応は準備中...
          </div>
        </>
      )}

      <div
        style={{
          marginTop: '40px',
          padding: '20px',
          backgroundColor: '#f8f9fa',
          borderRadius: '8px',
          fontSize: '14px',
          color: '#666',
        }}
      >
        <div style={{ marginBottom: '8px', fontWeight: 'bold' }}>
          💡 こんな使い方ができます
        </div>
        <ul style={{ margin: '0', paddingLeft: '20px' }}>
          <li>難しい論文をわかりやすいスライドに</li>
          <li>教科書の内容を復習用スライドに</li>
          <li>スライド作成後、内容について質問もできます</li>
        </ul>
      </div>
    </div>
  );
}

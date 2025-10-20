/**
 * FileDropzone Component (Issue #17)
 * PDFファイルのドラッグ&ドロップアップロード機能
 */

import { useState, useRef } from 'react';

interface FileDropzoneProps {
  onUpload: (path: string) => void;
}

export default function FileDropzone({ onUpload }: FileDropzoneProps) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = async (file: File) => {
    // ファイルサイズチェック（100MB）
    if (file.size > 100 * 1024 * 1024) {
      setError('ファイルサイズは100MB以下にしてください');
      return;
    }

    // ファイル形式チェック
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setError('PDFファイルのみアップロード可能です');
      return;
    }

    setUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('http://localhost:8001/api/upload-pdf', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'アップロード失敗');
      }

      const data = await response.json();
      console.log('✅ PDF uploaded:', data);
      onUpload(data.path);
    } catch (err: any) {
      console.error('❌ Upload error:', err);
      setError(err.message || 'アップロードに失敗しました');
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);

    const file = e.dataTransfer.files[0];
    if (file) {
      handleFileSelect(file);
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFileSelect(file);
    }
  };

  return (
    <div>
      <div
        style={{
          border: isDragging ? '2px solid #007bff' : '2px dashed #ccc',
          borderRadius: '8px',
          padding: '40px',
          textAlign: 'center',
          cursor: uploading ? 'not-allowed' : 'pointer',
          backgroundColor: isDragging ? '#f0f8ff' : '#ffffff',
          transition: 'all 0.3s ease',
        }}
        onClick={uploading ? undefined : handleClick}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
      >
        {uploading ? (
          <>
            <div style={{ fontSize: '48px', marginBottom: '16px' }}>📤</div>
            <div style={{ fontSize: '16px', color: '#666' }}>アップロード中...</div>
          </>
        ) : (
          <>
            <div style={{ fontSize: '48px', marginBottom: '16px' }}>📄</div>
            <div style={{ fontSize: '16px', marginBottom: '8px' }}>
              PDFをドラッグ&ドロップ
            </div>
            <div style={{ color: '#999', fontSize: '14px' }}>
              または クリックして選択
            </div>
            <div style={{ color: '#999', fontSize: '12px', marginTop: '8px' }}>
              （最大 100MB）
            </div>
          </>
        )}
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf"
        style={{ display: 'none' }}
        onChange={handleFileInputChange}
        disabled={uploading}
      />

      {error && (
        <div
          style={{
            color: 'red',
            marginTop: '12px',
            padding: '12px',
            backgroundColor: '#ffe6e6',
            borderRadius: '4px',
            fontSize: '14px',
          }}
        >
          ❌ {error}
        </div>
      )}
    </div>
  );
}

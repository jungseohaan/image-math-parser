'use client';

import { ChangeEvent, DragEvent } from 'react';

interface ImageUploaderProps {
  isDragging: boolean;
  sessionNameInput: string;
  onSessionNameChange: (name: string) => void;
  onDrop: (e: DragEvent<HTMLDivElement>) => void;
  onDragOver: (e: DragEvent<HTMLDivElement>) => void;
  onDragLeave: (e: DragEvent<HTMLDivElement>) => void;
  onFileSelect: (e: ChangeEvent<HTMLInputElement>) => void;
}

export default function ImageUploader({
  isDragging,
  sessionNameInput,
  onSessionNameChange,
  onDrop,
  onDragOver,
  onDragLeave,
  onFileSelect
}: ImageUploaderProps) {
  return (
    <div>
      {/* 세션 이름 입력 */}
      <div style={{ marginBottom: '16px' }}>
        <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9em', color: '#666' }}>
          세션 이름 (선택사항 - 비워두면 자동 생성)
        </label>
        <input
          type="text"
          value={sessionNameInput}
          onChange={(e) => onSessionNameChange(e.target.value)}
          placeholder="예: 2024 수능 수학 13번"
          style={{
            width: '100%',
            maxWidth: '400px',
            padding: '10px 14px',
            border: '1px solid #dee2e6',
            borderRadius: '8px',
            fontSize: '14px'
          }}
        />
      </div>

      <div
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onClick={() => document.getElementById('file-input')?.click()}
        style={{
          border: `3px dashed ${isDragging ? '#007bff' : '#ccc'}`,
          padding: '60px 30px',
          textAlign: 'center',
          cursor: 'pointer',
          backgroundColor: isDragging ? '#f0f0ff' : '#fafafa',
          borderRadius: '16px',
          marginBottom: '30px',
          transition: 'all 0.2s'
        }}
      >
        <div style={{ fontSize: '3em', marginBottom: '16px' }}>📄</div>
        <p style={{ margin: 0, fontSize: '1.2em', color: '#666' }}>
          시험지 이미지를 드래그하거나 클릭하여 업로드하세요
        </p>
        <p style={{ margin: '8px 0 0 0', fontSize: '0.9em', color: '#999' }}>
          PNG, JPG, JPEG, GIF, WEBP 지원
        </p>
        <p style={{ margin: '12px 0 0 0', fontSize: '0.95em', color: '#007bff' }}>
          <strong>Ctrl+V</strong> (또는 Cmd+V)로 클립보드 이미지 붙여넣기 가능
        </p>
        <input
          type="file"
          id="file-input"
          accept="image/*"
          onChange={onFileSelect}
          style={{ display: 'none' }}
        />
      </div>
    </div>
  );
}

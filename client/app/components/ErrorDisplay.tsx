'use client';

interface ErrorDisplayProps {
  error: string;
  onRetry: () => void;
}

export default function ErrorDisplay({ error, onRetry }: ErrorDisplayProps) {
  return (
    <div style={{
      padding: '20px',
      backgroundColor: '#ffebee',
      borderRadius: '8px',
      marginBottom: '20px',
      borderLeft: '4px solid #f44336'
    }}>
      <strong style={{ color: '#c62828' }}>오류:</strong> {error}
      <button
        onClick={onRetry}
        style={{
          marginLeft: '16px',
          padding: '6px 12px',
          backgroundColor: '#f44336',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: 'pointer'
        }}
      >
        다시 시도
      </button>
    </div>
  );
}

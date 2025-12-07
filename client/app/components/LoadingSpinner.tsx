'use client';

export default function LoadingSpinner() {
  return (
    <div style={{
      textAlign: 'center',
      padding: '60px',
      backgroundColor: '#f8f9fa',
      borderRadius: '16px'
    }}>
      <div style={{ fontSize: '3em', marginBottom: '16px' }}>🔍</div>
      <p style={{ fontSize: '1.2em', color: '#333' }}>문항 분석 중...</p>
      <p style={{ fontSize: '0.9em', color: '#666' }}>Gemini AI가 이미지를 분석하고 있습니다</p>
    </div>
  );
}

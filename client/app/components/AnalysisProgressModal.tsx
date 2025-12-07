'use client';

interface AnalysisProgressModalProps {
  isOpen: boolean;
  onClose: () => void;
  progress: number;
  step: string;
  error: string | null;
  resultUrl: string | null;
}

export default function AnalysisProgressModal({
  isOpen,
  onClose,
  progress,
  step,
  error,
  resultUrl
}: AnalysisProgressModalProps) {
  if (!isOpen) return null;

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0,0,0,0.5)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000
    }}>
      <div style={{
        background: 'linear-gradient(135deg, #87CEEB 0%, #5DADE2 100%)',
        borderRadius: '16px',
        padding: '24px',
        maxWidth: '500px',
        width: '90%',
        boxShadow: '0 20px 60px rgba(0,0,0,0.3)'
      }}>
        <h3 style={{ color: 'white', marginBottom: '20px', fontSize: '1.3em' }}>
          문항 심층 분석
        </h3>

        {/* 진행 상황 */}
        <div style={{
          backgroundColor: 'rgba(255,255,255,0.2)',
          borderRadius: '8px',
          padding: '16px',
          marginBottom: '16px'
        }}>
          <div style={{ color: 'white', marginBottom: '8px', fontSize: '0.9em' }}>
            {step}
          </div>
          <div style={{
            backgroundColor: 'rgba(255,255,255,0.3)',
            borderRadius: '4px',
            height: '8px',
            overflow: 'hidden'
          }}>
            <div style={{
              backgroundColor: 'white',
              height: '100%',
              width: `${progress}%`,
              transition: 'width 0.3s ease'
            }} />
          </div>
          <div style={{ color: 'rgba(255,255,255,0.8)', marginTop: '8px', fontSize: '0.85em' }}>
            {progress}% 완료
          </div>
        </div>

        {/* 오류 표시 */}
        {error && (
          <div style={{
            backgroundColor: '#ffebee',
            color: '#c62828',
            padding: '12px',
            borderRadius: '8px',
            marginBottom: '16px',
            fontSize: '0.9em'
          }}>
            {error}
          </div>
        )}

        {/* 완료 시 결과 */}
        {resultUrl && (
          <div style={{
            backgroundColor: 'rgba(255,255,255,0.95)',
            borderRadius: '8px',
            padding: '16px',
            marginBottom: '16px'
          }}>
            <div style={{ color: '#333', marginBottom: '12px', fontWeight: 'bold' }}>
              분석 완료!
            </div>
            <a
              href={resultUrl}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: 'inline-block',
                padding: '10px 20px',
                background: 'linear-gradient(135deg, #5DADE2 0%, #3498DB 100%)',
                color: 'white',
                borderRadius: '6px',
                textDecoration: 'none',
                fontWeight: 'bold'
              }}
            >
              분석 결과 보기
            </a>
          </div>
        )}

        {/* 버튼 */}
        <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
          {resultUrl && (
            <a
              href={resultUrl}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                padding: '8px 16px',
                backgroundColor: 'white',
                color: '#3498DB',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '0.9em',
                fontWeight: 'bold',
                textDecoration: 'none'
              }}
            >
              새 탭에서 열기
            </a>
          )}
          <button
            onClick={onClose}
            style={{
              padding: '8px 16px',
              backgroundColor: 'rgba(255,255,255,0.2)',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '0.9em',
              fontWeight: 'bold'
            }}
          >
            닫기
          </button>
        </div>
      </div>
    </div>
  );
}

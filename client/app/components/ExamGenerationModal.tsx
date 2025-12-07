'use client';

export interface ExamSettings {
  questionCount: number;
  difficulty: 'easy' | 'medium' | 'hard' | 'mixed';
  title: string;
  includeAnswerSheet: boolean;
}

interface ExamGenerationModalProps {
  isOpen: boolean;
  onClose: () => void;
  examSettings: ExamSettings;
  onSettingsChange: (settings: ExamSettings) => void;
  isGenerating: boolean;
  progress: number;
  progressStep: string;
  error: string | null;
  onGenerate: () => void;
}

export default function ExamGenerationModal({
  isOpen,
  onClose,
  examSettings,
  onSettingsChange,
  isGenerating,
  progress,
  progressStep,
  error,
  onGenerate
}: ExamGenerationModalProps) {
  if (!isOpen) return null;

  const handleClose = () => {
    if (!isGenerating) {
      onClose();
    }
  };

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
        backgroundColor: 'white',
        borderRadius: '16px',
        width: '90%',
        maxWidth: '500px',
        padding: '24px',
        boxShadow: '0 20px 60px rgba(0,0,0,0.3)'
      }}>
        <h2 style={{ margin: '0 0 24px 0', fontSize: '1.3em' }}>
          문제지 생성 설정
        </h2>

        {/* 제목 입력 */}
        <div style={{ marginBottom: '20px' }}>
          <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold', color: '#333' }}>
            문제지 제목
          </label>
          <input
            type="text"
            value={examSettings.title}
            onChange={(e) => onSettingsChange({ ...examSettings, title: e.target.value })}
            style={{
              width: '100%',
              padding: '10px 14px',
              border: '1px solid #dee2e6',
              borderRadius: '6px',
              fontSize: '14px',
              boxSizing: 'border-box'
            }}
            placeholder="수학 모의고사"
          />
        </div>

        {/* 문항 수 */}
        <div style={{ marginBottom: '20px' }}>
          <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold', color: '#333' }}>
            문항 수: {examSettings.questionCount}문항
          </label>
          <input
            type="range"
            min="1"
            max={20}
            value={examSettings.questionCount}
            onChange={(e) => onSettingsChange({ ...examSettings, questionCount: parseInt(e.target.value) })}
            style={{ width: '100%' }}
          />
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#666' }}>
            <span>1문항</span>
            <span>최대 20문항</span>
          </div>
        </div>

        {/* 난이도 선택 */}
        <div style={{ marginBottom: '20px' }}>
          <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold', color: '#333' }}>
            난이도
          </label>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {[
              { value: 'easy' as const, label: '하' },
              { value: 'medium' as const, label: '중' },
              { value: 'hard' as const, label: '상' },
              { value: 'mixed' as const, label: '혼합' }
            ].map(opt => (
              <button
                key={opt.value}
                onClick={() => onSettingsChange({ ...examSettings, difficulty: opt.value })}
                style={{
                  flex: 1,
                  padding: '10px 16px',
                  border: examSettings.difficulty === opt.value ? '2px solid #007bff' : '1px solid #dee2e6',
                  borderRadius: '6px',
                  backgroundColor: examSettings.difficulty === opt.value ? '#e7f1ff' : 'white',
                  cursor: 'pointer',
                  fontWeight: examSettings.difficulty === opt.value ? 'bold' : 'normal'
                }}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* 정답지 포함 옵션 */}
        <div style={{ marginBottom: '24px' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={examSettings.includeAnswerSheet}
              onChange={(e) => onSettingsChange({ ...examSettings, includeAnswerSheet: e.target.checked })}
              style={{ width: '18px', height: '18px' }}
            />
            <span style={{ fontWeight: 'bold', color: '#333' }}>정답지 포함</span>
          </label>
        </div>

        {/* 진행 상황 */}
        {isGenerating && (
          <div style={{
            padding: '16px',
            backgroundColor: '#e3f2fd',
            borderRadius: '8px',
            marginBottom: '16px'
          }}>
            <div style={{ marginBottom: '8px', color: '#1976d2', fontWeight: 'bold' }}>
              {progressStep}
            </div>
            <div style={{
              height: '8px',
              backgroundColor: '#bbdefb',
              borderRadius: '4px',
              overflow: 'hidden'
            }}>
              <div style={{
                height: '100%',
                width: `${progress}%`,
                backgroundColor: '#1976d2',
                transition: 'width 0.3s ease'
              }} />
            </div>
            <div style={{ marginTop: '4px', fontSize: '12px', color: '#666', textAlign: 'right' }}>
              {progress}%
            </div>
          </div>
        )}

        {/* 오류 메시지 */}
        {error && (
          <div style={{
            padding: '12px',
            backgroundColor: '#ffebee',
            borderRadius: '6px',
            marginBottom: '16px',
            color: '#c62828',
            fontSize: '14px'
          }}>
            {error}
          </div>
        )}

        {/* 버튼 */}
        <div style={{ display: 'flex', gap: '12px' }}>
          <button
            onClick={handleClose}
            disabled={isGenerating}
            style={{
              flex: 1,
              padding: '12px 20px',
              backgroundColor: '#f8f9fa',
              border: '1px solid #dee2e6',
              borderRadius: '6px',
              cursor: isGenerating ? 'not-allowed' : 'pointer',
              fontWeight: 'bold',
              opacity: isGenerating ? 0.5 : 1
            }}
          >
            취소
          </button>
          <button
            onClick={onGenerate}
            disabled={isGenerating}
            style={{
              flex: 1,
              padding: '12px 20px',
              backgroundColor: isGenerating ? '#ccc' : '#007bff',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: isGenerating ? 'not-allowed' : 'pointer',
              fontWeight: 'bold'
            }}
          >
            {isGenerating ? '생성 중...' : '문제지 생성'}
          </button>
        </div>
      </div>
    </div>
  );
}

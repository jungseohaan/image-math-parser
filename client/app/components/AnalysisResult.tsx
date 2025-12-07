'use client';

import { QuestionData, AnalysisResult as AnalysisResultType, VariantRecord } from '../lib/types';
import QuestionCard from './QuestionCard';
import ImagePanel from './ImagePanel';

interface AnalysisResultProps {
  result: AnalysisResultType;
  imageUrl: string | null;
  currentSessionId: string | null;
  variantRecordsByQuestion: Record<string, VariantRecord[]>;
  onReset: () => void;
  onOpenExamModal: () => void;
  onAnalyzeQuestion: (question: QuestionData) => void;
  onRefreshVariants: () => void;
}

export default function AnalysisResult({
  result,
  imageUrl,
  currentSessionId,
  variantRecordsByQuestion,
  onReset,
  onOpenExamModal,
  onAnalyzeQuestion,
  onRefreshVariants
}: AnalysisResultProps) {
  return (
    <div>
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '24px',
        padding: '16px 20px',
        backgroundColor: '#e8f5e9',
        borderRadius: '8px'
      }}>
        <div>
          <span style={{ fontSize: '1.2em', fontWeight: 'bold', color: '#2e7d32' }}>
            ✅ 분석 완료
          </span>
          <span style={{ marginLeft: '16px', color: '#666' }}>
            총 {result.questions?.length || 0}개 문항 인식
          </span>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={onOpenExamModal}
            disabled={!result?.questions?.length}
            style={{
              padding: '8px 16px',
              backgroundColor: '#6c757d',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: result?.questions?.length ? 'pointer' : 'not-allowed',
              fontWeight: 'bold',
              opacity: result?.questions?.length ? 1 : 0.6
            }}
          >
            문제지 생성
          </button>
          <button
            onClick={onReset}
            style={{
              padding: '8px 16px',
              backgroundColor: '#007bff',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: 'bold'
            }}
          >
            새 이미지 분석
          </button>
        </div>
      </div>

      {/* Layout: Image + Questions */}
      <div style={{ display: 'flex', gap: '24px', flexWrap: 'wrap' }}>
        {/* Original Image */}
        {imageUrl && result.questions && (
          <ImagePanel imageUrl={imageUrl} questions={result.questions} />
        )}

        {/* Questions */}
        <div style={{ flex: '1', minWidth: '400px' }}>
          {result.questions && result.questions.length > 0 ? (
            result.questions.map((question, idx) => (
              <QuestionCard
                key={idx}
                question={question}
                index={idx}
                onAnalyzeQuestion={onAnalyzeQuestion}
                sessionId={currentSessionId}
                variantRecords={variantRecordsByQuestion[question.question_number]}
                onRefreshVariants={onRefreshVariants}
              />
            ))
          ) : (
            <div style={{
              padding: '40px',
              textAlign: 'center',
              backgroundColor: '#fff3e0',
              borderRadius: '8px'
            }}>
              <p style={{ margin: 0, color: '#f57c00' }}>
                문항을 인식하지 못했습니다. 다른 이미지를 시도해주세요.
              </p>
            </div>
          )}

          {/* JSON 원본 */}
          <details style={{ marginTop: '24px' }}>
            <summary style={{ cursor: 'pointer', color: '#666', fontSize: '0.9em', padding: '8px' }}>
              📋 JSON 원본 보기 (개발용)
            </summary>
            <pre style={{
              marginTop: '12px',
              padding: '16px',
              backgroundColor: '#263238',
              color: '#aed581',
              borderRadius: '8px',
              overflow: 'auto',
              fontSize: '0.8em',
              maxHeight: '400px'
            }}>
              {JSON.stringify(result, null, 2)}
            </pre>
          </details>
        </div>
      </div>
    </div>
  );
}

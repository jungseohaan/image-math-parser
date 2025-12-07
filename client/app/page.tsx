
// app/page.tsx
'use client';

import React, { useState, useCallback, useEffect, ChangeEvent, DragEvent, ClipboardEvent } from 'react';
import 'katex/dist/katex.min.css';
import { InlineMath, BlockMath } from 'react-katex';

// API URL 설정 (배포 시 환경 변수로 변경)
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4001';

// --- Interfaces ---
interface Choice {
  number: string;
  text: string;
}

interface AnalysisProcess {
  is_word_problem: boolean;
  objects_used: string[];
  step1_to_math: string;
  step2_solve: string;
  step3_to_context: string;
  mathematical_concept: string;
}

interface QuestionData {
  question_number: string;
  question_text: string;
  topic_category?: string;
  has_passage: boolean;
  passage: string;
  choices: Choice[];
  has_figure: boolean;
  figure_description: string;
  graph_url?: string;
  graph_error?: string;
  has_table: boolean;
  table_data: string;
  math_expressions: string[];
  question_type: string;
  cropped_image_url?: string;
  analysis_process?: AnalysisProcess | null;
}

interface AnalysisResult {
  questions: QuestionData[];
  error?: string;
}

interface Session {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
  question_count: number;
  image_filename: string;
  thumbnail_url: string;
}

interface VariantRecord {
  json_filename: string;
  html_filename: string;
  timestamp: string;
  created: number;
  variant_count: number;
  json_url: string;
  html_url: string;
}

// LaTeX 수식을 렌더링하는 컴포넌트
function RenderMathText({ text }: { text: string }) {
  if (!text) return null;

  const parts = text.split(/(\$\$[\s\S]*?\$\$|\$[^$]+?\$)/g);

  return (
    <>
      {parts.map((part, idx) => {
        if (part.startsWith('$$') && part.endsWith('$$')) {
          const math = part.slice(2, -2);
          try {
            return <BlockMath key={idx} math={math} />;
          } catch {
            return <code key={idx}>{part}</code>;
          }
        } else if (part.startsWith('$') && part.endsWith('$')) {
          const math = part.slice(1, -1);
          try {
            return <InlineMath key={idx} math={math} />;
          } catch {
            return <code key={idx}>{part}</code>;
          }
        }
        return <span key={idx}>{part}</span>;
      })}
    </>
  );
}

// 문항 카드 컴포넌트
function QuestionCard({ question, index, onGenerateVariants, onAnalyzeQuestion, sessionId, variantRecords, onRefreshVariants }: {
  question: QuestionData;
  index: number;
  onGenerateVariants?: (question: QuestionData) => void;
  onAnalyzeQuestion?: (question: QuestionData) => void;
  sessionId?: string | null;
  variantRecords?: VariantRecord[];
  onRefreshVariants?: () => void;
}) {
  const [isExpanded, setIsExpanded] = useState(true);
  const [showVariantHistory, setShowVariantHistory] = useState(false);

  return (
    <div style={{
      marginBottom: '24px',
      border: '1px solid #e0e0e0',
      borderRadius: '12px',
      overflow: 'hidden',
      boxShadow: '0 2px 8px rgba(0,0,0,0.08)'
    }}>
      {/* Header */}
      <div
        style={{
          padding: '16px 20px',
          backgroundColor: '#f8f9fa',
          borderBottom: isExpanded ? '1px solid #e0e0e0' : 'none',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}
      >
        <div
          onClick={() => setIsExpanded(!isExpanded)}
          style={{ display: 'flex', alignItems: 'center', gap: '12px', cursor: 'pointer', flex: 1 }}
        >
          {question.question_number && question.question_number !== 'None' && (
            <span style={{
              backgroundColor: '#007bff',
              color: 'white',
              padding: '4px 12px',
              borderRadius: '20px',
              fontWeight: 'bold',
              fontSize: '0.9em'
            }}>
              {question.question_number}번
            </span>
          )}
          <span style={{
            fontSize: '0.85em',
            padding: '4px 8px',
            backgroundColor: question.question_type === '객관식' ? '#e3f2fd' : '#fff3e0',
            color: question.question_type === '객관식' ? '#1976d2' : '#f57c00',
            borderRadius: '4px'
          }}>
            {question.question_type || '유형 미확인'}
          </span>
          {question.topic_category && (
            <span style={{
              fontSize: '0.85em',
              padding: '4px 10px',
              backgroundColor: '#f3e5f5',
              color: '#7b1fa2',
              borderRadius: '12px',
              fontWeight: '500'
            }}>
              {question.topic_category}
            </span>
          )}
          {question.has_figure && <span title="그림 포함">🖼️</span>}
          {question.has_table && <span title="표 포함">📊</span>}
          {question.has_passage && <span title="지문 포함">📖</span>}
          <span style={{ fontSize: '1.2em', marginLeft: 'auto' }}>{isExpanded ? '▼' : '▶'}</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {/* 저장된 변형 문제가 있으면 표시 */}
          {variantRecords && variantRecords.length > 0 && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                setShowVariantHistory(!showVariantHistory);
              }}
              style={{
                padding: '6px 12px',
                backgroundColor: '#e8f5e9',
                color: '#2e7d32',
                border: '1px solid #a5d6a7',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '0.85em',
                fontWeight: 'bold',
                whiteSpace: 'nowrap'
              }}
            >
              📁 변형문제 ({variantRecords.length})
            </button>
          )}
          {onAnalyzeQuestion && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onAnalyzeQuestion(question);
              }}
              style={{
                padding: '6px 14px',
                background: 'linear-gradient(135deg, #87CEEB 0%, #5DADE2 100%)',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '0.85em',
                fontWeight: 'bold',
                whiteSpace: 'nowrap',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              📚 문항 분석
            </button>
          )}
          {onGenerateVariants && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onGenerateVariants(question);
              }}
              style={{
                padding: '6px 14px',
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '0.85em',
                fontWeight: 'bold',
                whiteSpace: 'nowrap',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              🎯 변형문제 생성
            </button>
          )}
        </div>
      </div>

      {/* 변형 문제 기록 패널 */}
      {showVariantHistory && variantRecords && variantRecords.length > 0 && (
        <div style={{
          padding: '16px 20px',
          backgroundColor: '#f0f7f0',
          borderBottom: '1px solid #a5d6a7'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <h4 style={{ margin: 0, fontSize: '0.95em', color: '#2e7d32' }}>
              📁 저장된 변형 문제 ({variantRecords.length}개)
            </h4>
            <button
              onClick={() => setShowVariantHistory(false)}
              style={{
                padding: '4px 8px',
                backgroundColor: 'transparent',
                border: 'none',
                cursor: 'pointer',
                fontSize: '1em',
                color: '#666'
              }}
            >
              ✕
            </button>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {variantRecords.map((record, idx) => (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '10px 14px',
                  backgroundColor: 'white',
                  borderRadius: '6px',
                  border: '1px solid #c8e6c9'
                }}
              >
                <div>
                  <span style={{ fontWeight: '500', fontSize: '0.9em' }}>
                    {new Date(record.created * 1000).toLocaleString()}
                  </span>
                  <span style={{
                    marginLeft: '8px',
                    padding: '2px 6px',
                    backgroundColor: '#e3f2fd',
                    borderRadius: '4px',
                    fontSize: '0.75em',
                    color: '#1976d2'
                  }}>
                    {record.variant_count}개 변형
                  </span>
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <a
                    href={record.html_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      padding: '4px 10px',
                      backgroundColor: '#667eea',
                      color: 'white',
                      borderRadius: '4px',
                      fontSize: '0.8em',
                      textDecoration: 'none'
                    }}
                  >
                    보기
                  </a>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Content */}
      {isExpanded && (
        <div style={{ padding: '20px' }}>
          {/* 문제 본문 */}
          <div style={{
            marginBottom: '20px',
            padding: '16px',
            backgroundColor: '#f8f9fa',
            borderRadius: '8px',
            borderLeft: '4px solid #007bff',
            lineHeight: '1.8',
            fontSize: '1.05em'
          }}>
            <RenderMathText text={question.question_text || '(문제 텍스트 없음)'} />
          </div>

          {/* 분석 프로세스 (저학년/서술형 문제) */}
          {question.analysis_process && question.analysis_process.is_word_problem && (
            <div style={{
              marginBottom: '20px',
              padding: '16px',
              backgroundColor: '#e8f5e9',
              borderRadius: '8px',
              border: '1px solid #a5d6a7'
            }}>
              <h4 style={{ margin: '0 0 16px 0', fontSize: '0.95em', color: '#2e7d32' }}>
                🧮 문제 분석 프로세스
              </h4>

              {/* 사용된 사물 */}
              {question.analysis_process.objects_used && question.analysis_process.objects_used.length > 0 && (
                <div style={{ marginBottom: '12px' }}>
                  <span style={{ fontWeight: '600', color: '#388e3c', fontSize: '0.85em' }}>📦 사용된 사물: </span>
                  <span style={{ color: '#555' }}>{question.analysis_process.objects_used.join(', ')}</span>
                </div>
              )}

              {/* Step 1: 수식 변환 */}
              <div style={{
                marginBottom: '10px',
                padding: '10px 12px',
                backgroundColor: '#fff3e0',
                borderRadius: '6px',
                borderLeft: '3px solid #ff9800'
              }}>
                <div style={{ fontWeight: '600', color: '#e65100', fontSize: '0.85em', marginBottom: '4px' }}>
                  Step 1. 수식으로 변환
                </div>
                <div style={{ color: '#333' }}><RenderMathText text={question.analysis_process.step1_to_math} /></div>
              </div>

              {/* Step 2: 풀이 */}
              <div style={{
                marginBottom: '10px',
                padding: '10px 12px',
                backgroundColor: '#e3f2fd',
                borderRadius: '6px',
                borderLeft: '3px solid #2196f3'
              }}>
                <div style={{ fontWeight: '600', color: '#1565c0', fontSize: '0.85em', marginBottom: '4px' }}>
                  Step 2. 수식 풀이
                </div>
                <div style={{ color: '#333', fontSize: '1.1em' }}>
                  <RenderMathText text={question.analysis_process.step2_solve} />
                </div>
              </div>

              {/* Step 3: 문맥 복원 */}
              <div style={{
                marginBottom: '10px',
                padding: '10px 12px',
                backgroundColor: '#f3e5f5',
                borderRadius: '6px',
                borderLeft: '3px solid #9c27b0'
              }}>
                <div style={{ fontWeight: '600', color: '#7b1fa2', fontSize: '0.85em', marginBottom: '4px' }}>
                  Step 3. 답을 문맥으로 변환
                </div>
                <div style={{ color: '#333' }}><RenderMathText text={question.analysis_process.step3_to_context} /></div>
              </div>

              {/* 수학 개념 */}
              <div style={{
                marginTop: '12px',
                padding: '8px 12px',
                backgroundColor: 'white',
                borderRadius: '6px',
                border: '1px dashed #81c784'
              }}>
                <span style={{ fontWeight: '600', color: '#388e3c', fontSize: '0.85em' }}>💡 수학 개념: </span>
                <span style={{ color: '#333', fontWeight: '500' }}>{question.analysis_process.mathematical_concept}</span>
              </div>
            </div>
          )}

          {/* 지문 */}
          {question.has_passage && question.passage && (
            <div style={{
              marginBottom: '20px',
              padding: '16px',
              backgroundColor: '#fff8e1',
              borderRadius: '8px',
              border: '1px solid #ffe082'
            }}>
              <h4 style={{ margin: '0 0 12px 0', fontSize: '0.9em', color: '#f57c00' }}>📖 지문</h4>
              <div style={{
                fontStyle: 'italic',
                lineHeight: '1.8',
                padding: '12px',
                backgroundColor: 'white',
                borderRadius: '4px',
                border: '1px dashed #ffe082'
              }}>
                <RenderMathText text={question.passage} />
              </div>
            </div>
          )}

          {/* 선택지 */}
          {question.choices && question.choices.length > 0 && (
            <div style={{ marginBottom: '20px' }}>
              <h4 style={{ margin: '0 0 12px 0', fontSize: '0.9em', color: '#666' }}>선택지</h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {question.choices.map((choice, idx) => (
                  <div
                    key={idx}
                    style={{
                      padding: '12px 16px',
                      backgroundColor: '#f5f5f5',
                      borderRadius: '6px',
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: '12px'
                    }}
                  >
                    <span style={{ fontWeight: 'bold', color: '#1976d2', minWidth: '24px' }}>
                      {choice.number}
                    </span>
                    <span style={{ lineHeight: '1.6' }}>
                      <RenderMathText text={choice.text} />
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 원본 이미지 (크롭된 이미지) */}
          {question.cropped_image_url && (
            <div style={{
              marginBottom: '20px',
              padding: '16px',
              backgroundColor: '#f3e5f5',
              borderRadius: '8px',
              border: '1px solid #ce93d8'
            }}>
              <h4 style={{ margin: '0 0 12px 0', fontSize: '0.9em', color: '#7b1fa2' }}>📷 원본 이미지</h4>
              <div style={{
                textAlign: 'center',
                padding: '12px',
                backgroundColor: 'white',
                borderRadius: '8px',
                border: '1px solid #e1bee7'
              }}>
                <img
                  src={question.cropped_image_url}
                  alt="문제 원본 이미지"
                  style={{
                    maxWidth: '100%',
                    maxHeight: '500px',
                    borderRadius: '4px'
                  }}
                />
              </div>
            </div>
          )}

          {/* 그림/도표 설명 */}
          {question.has_figure && (question.figure_description || question.graph_url) && (
            <div style={{
              marginBottom: '20px',
              padding: '16px',
              backgroundColor: '#e8f5e9',
              borderRadius: '8px',
              border: '1px solid #a5d6a7'
            }}>
              <h4 style={{ margin: '0 0 12px 0', fontSize: '0.9em', color: '#388e3c' }}>🖼️ 그림/도표</h4>
              {question.figure_description && (
                <p style={{ margin: '0 0 12px 0', lineHeight: '1.6' }}>{question.figure_description}</p>
              )}
              {question.graph_url && (
                <div style={{
                  marginTop: '12px',
                  textAlign: 'center',
                  padding: '12px',
                  backgroundColor: 'white',
                  borderRadius: '8px',
                  border: '1px solid #c8e6c9'
                }}>
                  <img
                    src={question.graph_url}
                    alt="생성된 그래프"
                    style={{
                      maxWidth: '100%',
                      maxHeight: '400px',
                      borderRadius: '4px'
                    }}
                  />
                  <p style={{ margin: '8px 0 0 0', fontSize: '0.8em', color: '#666' }}>
                    📊 AI가 생성한 그래프
                  </p>
                </div>
              )}
              {question.graph_error && (
                <div style={{
                  marginTop: '12px',
                  padding: '8px 12px',
                  backgroundColor: '#ffebee',
                  borderRadius: '4px',
                  fontSize: '0.85em',
                  color: '#c62828'
                }}>
                  ⚠️ 그래프 생성 실패: {question.graph_error}
                </div>
              )}
            </div>
          )}

          {/* 표 데이터 */}
          {question.has_table && question.table_data && (
            <div style={{
              marginBottom: '20px',
              padding: '16px',
              backgroundColor: '#e3f2fd',
              borderRadius: '8px',
              border: '1px solid #90caf9'
            }}>
              <h4 style={{ margin: '0 0 12px 0', fontSize: '0.9em', color: '#1976d2' }}>📊 표</h4>
              <pre style={{
                margin: 0,
                padding: '12px',
                backgroundColor: 'white',
                borderRadius: '4px',
                overflow: 'auto',
                fontSize: '0.9em'
              }}>
                {question.table_data}
              </pre>
            </div>
          )}

        </div>
      )}
    </div>
  );
}

export default function ExamAnalyzerPage() {
  const [isDragging, setIsDragging] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showPromptEditor, setShowPromptEditor] = useState(false);
  const [systemPrompt, setSystemPrompt] = useState<string>('');
  const [userPrompt, setUserPrompt] = useState<string>('');
  const [defaultSystemPrompt, setDefaultSystemPrompt] = useState<string>('');
  const [defaultUserPrompt, setDefaultUserPrompt] = useState<string>('');
  const [isLoadingPrompt, setIsLoadingPrompt] = useState(false);
  const [isSavingPrompt, setIsSavingPrompt] = useState(false);
  const [promptSaveMessage, setPromptSaveMessage] = useState<string | null>(null);
  const [activePromptTab, setActivePromptTab] = useState<'system' | 'user'>('system');

  // 변형 문제 생성 상태
  const [isGeneratingVariants, setIsGeneratingVariants] = useState(false);
  const [variantsUrl, setVariantsUrl] = useState<string | null>(null);
  const [showVariantsModal, setShowVariantsModal] = useState(false);
  const [variantsError, setVariantsError] = useState<string | null>(null);
  const [variantsProgress, setVariantsProgress] = useState<number>(0);
  const [variantsStep, setVariantsStep] = useState<string>('');
  const [isAutoRetrying, setIsAutoRetrying] = useState(false);
  const [retryCount, setRetryCount] = useState(0);
  const [autoFixAnalysis, setAutoFixAnalysis] = useState<string | null>(null);

  // 세션 관리 상태
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [isLoadingSessions, setIsLoadingSessions] = useState(false);
  const [showSidebar, setShowSidebar] = useState(true);
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [editingSessionName, setEditingSessionName] = useState<string>('');
  const [sessionNameInput, setSessionNameInput] = useState<string>('');
  const [isReanalyzing, setIsReanalyzing] = useState(false);

  // 문항별 변형 문제 기록
  const [variantRecordsByQuestion, setVariantRecordsByQuestion] = useState<Record<string, VariantRecord[]>>({});

  // 문제지 생성 상태
  const [showExamModal, setShowExamModal] = useState(false);
  const [examSettings, setExamSettings] = useState({
    questionCount: 5,
    difficulty: 'mixed' as 'easy' | 'medium' | 'hard' | 'mixed',
    title: '수학 모의고사',
    includeAnswerSheet: true
  });

  // 문항 분석 상태
  const [isAnalyzingQuestion, setIsAnalyzingQuestion] = useState(false);
  const [showAnalysisModal, setShowAnalysisModal] = useState(false);
  const [analysisUrl, setAnalysisUrl] = useState<string | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [analysisProgress, setAnalysisProgress] = useState<number>(0);
  const [analysisStep, setAnalysisStep] = useState<string>('');
  const [isGeneratingExam, setIsGeneratingExam] = useState(false);
  const [examError, setExamError] = useState<string | null>(null);

  // LLM 사용량 통계 상태
  const [showStatsModal, setShowStatsModal] = useState(false);
  const [llmStats, setLlmStats] = useState<{
    session_start: string;
    total_calls: number;
    successful_calls: number;
    failed_calls: number;
    total_input_tokens: number;
    total_output_tokens: number;
    total_tokens: number;
    total_cost_usd: number;
    total_cost_krw: number;
    by_model: Record<string, { calls: number; input_tokens: number; output_tokens: number; cost: number }>;
    by_operation: Record<string, { calls: number; input_tokens: number; output_tokens: number; cost: number }>;
    recent_calls: Array<{
      timestamp: string;
      model: string;
      operation: string;
      input_tokens: number;
      output_tokens: number;
      total_cost: number;
      latency_ms: number;
      success: boolean;
    }>;
  } | null>(null);
  const [isLoadingStats, setIsLoadingStats] = useState(false);

  // 프롬프트 로드
  const loadPrompts = useCallback(async () => {
    setIsLoadingPrompt(true);
    try {
      const response = await fetch(`${API_URL}/prompts`);
      const data = await response.json();
      if (data.success) {
        setSystemPrompt(data.system_prompt);
        setUserPrompt(data.user_prompt);
        setDefaultSystemPrompt(data.default_system_prompt);
        setDefaultUserPrompt(data.default_user_prompt);
      }
    } catch (err) {
      console.error('프롬프트 로드 실패:', err);
    } finally {
      setIsLoadingPrompt(false);
    }
  }, []);

  // 프롬프트 저장
  const savePrompts = useCallback(async () => {
    setIsSavingPrompt(true);
    setPromptSaveMessage(null);
    try {
      const response = await fetch(`${API_URL}/prompts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          system_prompt: systemPrompt,
          user_prompt: userPrompt
        })
      });
      const data = await response.json();
      if (data.success) {
        setPromptSaveMessage('✅ 저장되었습니다');
        setTimeout(() => setPromptSaveMessage(null), 3000);
      }
    } catch (err) {
      console.error('프롬프트 저장 실패:', err);
      setPromptSaveMessage('❌ 저장 실패');
    } finally {
      setIsSavingPrompt(false);
    }
  }, [systemPrompt, userPrompt]);

  // 프롬프트 초기화
  const resetPrompt = useCallback(async (type: 'system' | 'user' | 'all') => {
    try {
      const response = await fetch(`${API_URL}/prompts/reset`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type })
      });
      const data = await response.json();
      if (data.success) {
        setSystemPrompt(data.system_prompt);
        setUserPrompt(data.user_prompt);
        setPromptSaveMessage('✅ 초기화되었습니다');
        setTimeout(() => setPromptSaveMessage(null), 3000);
      }
    } catch (err) {
      console.error('프롬프트 초기화 실패:', err);
    }
  }, []);

  useEffect(() => {
    loadPrompts();
  }, [loadPrompts]);

  // 세션 목록 로드
  const loadSessions = useCallback(async () => {
    setIsLoadingSessions(true);
    try {
      const response = await fetch(`${API_URL}/sessions`);
      const data = await response.json();
      if (data.success) {
        setSessions(data.sessions);
      }
    } catch (err) {
      console.error('세션 목록 로드 실패:', err);
    } finally {
      setIsLoadingSessions(false);
    }
  }, []);

  // 세션 선택 (상세 조회)
  const selectSession = useCallback(async (sessionId: string) => {
    setIsAnalyzing(true);
    setError(null);
    try {
      const response = await fetch(`${API_URL}/sessions/${sessionId}`);
      const data = await response.json();
      if (data.success) {
        setCurrentSessionId(sessionId);
        setImageUrl(data.image_url);
        setResult(data.data);
      } else {
        setError(data.message);
      }
    } catch (err) {
      console.error('세션 로드 실패:', err);
      setError('세션을 불러오는 중 오류가 발생했습니다.');
    } finally {
      setIsAnalyzing(false);
    }
  }, []);

  // 세션 삭제
  const deleteSession = useCallback(async (sessionId: string) => {
    if (!confirm('이 세션을 삭제하시겠습니까?')) return;

    try {
      const response = await fetch(`${API_URL}/sessions/${sessionId}`, {
        method: 'DELETE'
      });
      const data = await response.json();
      if (data.success) {
        setSessions(prev => prev.filter(s => s.id !== sessionId));
        if (currentSessionId === sessionId) {
          setCurrentSessionId(null);
          setResult(null);
          setImageUrl(null);
        }
      }
    } catch (err) {
      console.error('세션 삭제 실패:', err);
    }
  }, [currentSessionId]);

  // 세션 이름 수정
  const updateSessionName = useCallback(async (sessionId: string, newName: string) => {
    try {
      const response = await fetch(`${API_URL}/sessions/${sessionId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newName })
      });
      const data = await response.json();
      if (data.success) {
        setSessions(prev => prev.map(s =>
          s.id === sessionId ? { ...s, name: newName } : s
        ));
        setEditingSessionId(null);
        setEditingSessionName('');
      }
    } catch (err) {
      console.error('세션 이름 수정 실패:', err);
    }
  }, []);

  // 세션 재분석
  const reanalyzeSession = useCallback(async (sessionId: string) => {
    if (!confirm('이 세션을 재분석하시겠습니까? 기존 분석 결과가 덮어씌워집니다.')) return;

    setIsReanalyzing(true);
    setError(null);
    try {
      const response = await fetch(`${API_URL}/sessions/${sessionId}/reanalyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          system_prompt: systemPrompt,
          user_prompt: userPrompt
        })
      });
      const data = await response.json();
      if (data.success) {
        setResult(data.data);
        setSessions(prev => prev.map(s =>
          s.id === sessionId ? { ...s, question_count: data.question_count, updated_at: new Date().toISOString() } : s
        ));
      } else {
        setError(data.message);
      }
    } catch (err) {
      console.error('재분석 실패:', err);
      setError('재분석 중 오류가 발생했습니다.');
    } finally {
      setIsReanalyzing(false);
    }
  }, [systemPrompt, userPrompt]);

  // 세션의 변형 문제 기록 로드
  const loadVariantRecords = useCallback(async (sessionId: string, questions: QuestionData[]) => {
    const records: Record<string, VariantRecord[]> = {};

    for (const question of questions) {
      const qNum = question.question_number;
      try {
        const response = await fetch(`${API_URL}/sessions/${sessionId}/variants/question/${qNum}`);
        const data = await response.json();
        if (data.success && data.variants) {
          records[qNum] = data.variants;
        }
      } catch (err) {
        console.error(`문항 ${qNum}의 변형 문제 기록 로드 실패:`, err);
      }
    }

    setVariantRecordsByQuestion(records);
  }, []);

  // 초기 세션 목록 로드
  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  // 세션 선택 시 변형 문제 기록도 로드
  useEffect(() => {
    if (currentSessionId && result?.questions) {
      loadVariantRecords(currentSessionId, result.questions);
    } else {
      setVariantRecordsByQuestion({});
    }
  }, [currentSessionId, result, loadVariantRecords]);

  // LLM 사용량 통계 로드
  const loadLlmStats = useCallback(async () => {
    setIsLoadingStats(true);
    try {
      const response = await fetch(`${API_URL}/llm-stats`);
      const data = await response.json();
      if (data.success) {
        setLlmStats(data.stats);
      }
    } catch (err) {
      console.error('LLM 통계 로드 실패:', err);
    } finally {
      setIsLoadingStats(false);
    }
  }, []);

  // 통계 초기화
  const resetLlmStats = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/llm-stats/reset`, {
        method: 'POST'
      });
      const data = await response.json();
      if (data.success) {
        setLlmStats(data.stats);
      }
    } catch (err) {
      console.error('LLM 통계 초기화 실패:', err);
    }
  }, []);

  // 통계 모달이 열릴 때 자동 로드
  useEffect(() => {
    if (showStatsModal) {
      loadLlmStats();
    }
  }, [showStatsModal, loadLlmStats]);

  const analyzeImage = useCallback(async (file: File) => {
    setIsAnalyzing(true);
    setResult(null);
    setError(null);
    setImageUrl(null);
    setCurrentSessionId(null);

    try {
      // 항상 새로 분석 (동일한 파일명이어도 분석 가능)
      const formData = new FormData();
      formData.append('image_file', file);
      if (sessionNameInput.trim()) {
        formData.append('session_name', sessionNameInput.trim());
      }
      if (systemPrompt) {
        formData.append('system_prompt', systemPrompt);
      }
      if (userPrompt) {
        formData.append('user_prompt', userPrompt);
      }

      // 세션 기반 분석 API 사용
      const response = await fetch(`${API_URL}/sessions`, {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (data.success) {
        setCurrentSessionId(data.session_id);
        setImageUrl(data.image_url);
        setResult(data.data);
        setSessionNameInput('');
        // 세션 목록 새로고침
        loadSessions();
        // 여러 문제가 발견되면 알림 표시
        if (data.total_questions && data.total_questions > 1) {
          alert(`이미지에서 ${data.total_questions}개의 문제를 발견하여 각각 별도 세션으로 저장했습니다.`);
        }
      } else {
        setError(data.message);
      }
    } catch (err) {
      console.error('분석 오류:', err);
      setError('서버 연결 또는 분석 중 오류가 발생했습니다.');
    } finally {
      setIsAnalyzing(false);
    }
  }, [systemPrompt, userPrompt, sessionNameInput, loadSessions]);

  const handleFile = useCallback((file: File | null) => {
    if (!file || !file.type.startsWith('image/')) {
      alert('이미지 파일만 업로드할 수 있습니다.');
      return;
    }
    analyzeImage(file);
  }, [analyzeImage]);

  const handleDrop = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files.length > 0) handleFile(e.dataTransfer.files[0]);
  }, [handleFile]);

  const handleDragOver = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback(() => setIsDragging(false), []);

  const handleFileInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) handleFile(e.target.files[0]);
  };

  const handleReset = () => {
    setResult(null);
    setImageUrl(null);
    setError(null);
    setCurrentSessionId(null);
  };

  // 클립보드 붙여넣기 처리
  const handlePaste = useCallback((e: ClipboardEvent | globalThis.ClipboardEvent) => {
    const items = e.clipboardData?.items;
    if (!items) return;

    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      if (item.type.startsWith('image/')) {
        e.preventDefault();
        const file = item.getAsFile();
        if (file) {
          analyzeImage(file);
        }
        break;
      }
    }
  }, [analyzeImage]);

  // 전역 붙여넣기 이벤트 리스너
  useEffect(() => {
    const handleGlobalPaste = (e: globalThis.ClipboardEvent) => {
      // 결과 화면이 아닐 때만 붙여넣기 처리
      if (!result && !isAnalyzing) {
        handlePaste(e);
      }
    };

    document.addEventListener('paste', handleGlobalPaste);
    return () => document.removeEventListener('paste', handleGlobalPaste);
  }, [handlePaste, result, isAnalyzing]);

  // 변형 문제 생성 (SSE 사용) - 세션 기반
  const generateVariants = useCallback(async (question: QuestionData) => {
    setIsGeneratingVariants(true);
    setVariantsError(null);
    setVariantsUrl(null);
    setVariantsProgress(0);
    setVariantsStep('시작 중...');
    setShowVariantsModal(true);
    setIsAutoRetrying(false);
    setRetryCount(0);
    setAutoFixAnalysis(null);

    // 세션이 있으면 세션 기반 API 사용, 없으면 기존 API 사용
    const apiUrl = currentSessionId
      ? `${API_URL}/sessions/${currentSessionId}/generate-variants`
      : `${API_URL}/generate-variants`;

    try {
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('스트림을 읽을 수 없습니다.');
      }

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));

              setVariantsProgress(data.progress || 0);
              setVariantsStep(data.message || '');

              // 자동 복구 상태 처리
              if (data.step === 'auto_fix' || data.step === 'auto_retry') {
                setIsAutoRetrying(true);
                if (data.retry_count) setRetryCount(data.retry_count);
              } else if (data.step === 'auto_fixed') {
                setIsAutoRetrying(false);
                if (data.analysis) setAutoFixAnalysis(data.analysis);
              } else if (data.step === 'auto_fix_failed') {
                setIsAutoRetrying(false);
              }

              if (data.step === 'complete') {
                setVariantsUrl(data.html_url);
                setIsGeneratingVariants(false);
                setIsAutoRetrying(false);
                if (data.retry_count) setRetryCount(data.retry_count);
                // 세션에 저장된 경우 변형 문제 기록 새로고침
                if (data.saved_to_session && currentSessionId && result?.questions) {
                  loadVariantRecords(currentSessionId, result.questions);
                }
              } else if (data.step === 'error') {
                setVariantsError(data.message);
                setIsGeneratingVariants(false);
                setIsAutoRetrying(false);
              }
            } catch {
              // JSON 파싱 실패 무시
            }
          }
        }
      }
    } catch (err) {
      console.error('변형 문제 생성 오류:', err);
      setVariantsError('변형 문제 생성 중 오류가 발생했습니다.');
      setIsGeneratingVariants(false);
      setIsAutoRetrying(false);
    }
  }, [currentSessionId, result, loadVariantRecords]);

  // 문항 분석 (SSE 사용)
  const analyzeQuestion = useCallback(async (question: QuestionData) => {
    if (!currentSessionId) {
      alert('세션을 먼저 생성해주세요.');
      return;
    }

    setIsAnalyzingQuestion(true);
    setAnalysisError(null);
    setAnalysisUrl(null);
    setAnalysisProgress(0);
    setAnalysisStep('시작 중...');
    setShowAnalysisModal(true);

    try {
      const response = await fetch(`${API_URL}/sessions/${currentSessionId}/analyze-question`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('스트림을 읽을 수 없습니다.');
      }

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));

              setAnalysisProgress(data.progress || 0);
              setAnalysisStep(data.message || '');

              if (data.step === 'complete') {
                setAnalysisUrl(data.html_url);
                setIsAnalyzingQuestion(false);
              } else if (data.step === 'error') {
                setAnalysisError(data.message);
                setIsAnalyzingQuestion(false);
              }
            } catch {
              // JSON 파싱 실패 무시
            }
          }
        }
      }
    } catch (err) {
      console.error('문항 분석 오류:', err);
      setAnalysisError('문항 분석 중 오류가 발생했습니다.');
      setIsAnalyzingQuestion(false);
    }
  }, [currentSessionId]);

  // 문제지 생성
  const generateExam = useCallback(async () => {
    if (!currentSessionId || !result?.questions) return;

    setIsGeneratingExam(true);
    setExamError(null);

    try {
      const response = await fetch(`${API_URL}/sessions/${currentSessionId}/generate-exam`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question_count: examSettings.questionCount,
          difficulty: examSettings.difficulty,
          title: examSettings.title,
          include_answer_sheet: examSettings.includeAnswerSheet
        })
      });

      const data = await response.json();
      if (data.success) {
        // 새 탭에서 문제지 열기
        window.open(data.exam_url, '_blank');
        setShowExamModal(false);
      } else {
        setExamError(data.message || '문제지 생성에 실패했습니다.');
      }
    } catch (err) {
      console.error('문제지 생성 오류:', err);
      setExamError('문제지 생성 중 오류가 발생했습니다.');
    } finally {
      setIsGeneratingExam(false);
    }
  }, [currentSessionId, result, examSettings]);

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      {/* 사이드바 */}
      {showSidebar && (
        <div style={{
          width: '280px',
          borderRight: '1px solid #e0e0e0',
          backgroundColor: '#f8f9fa',
          display: 'flex',
          flexDirection: 'column',
          flexShrink: 0
        }}>
          {/* 사이드바 헤더 */}
          <div style={{
            padding: '16px',
            borderBottom: '1px solid #e0e0e0',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}>
            <h3 style={{ margin: 0, fontSize: '1em', color: '#333' }}>📁 분석 기록</h3>
            <button
              onClick={loadSessions}
              disabled={isLoadingSessions}
              style={{
                padding: '4px 8px',
                backgroundColor: 'transparent',
                border: '1px solid #dee2e6',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '12px'
              }}
            >
              {isLoadingSessions ? '...' : '🔄'}
            </button>
          </div>

          {/* 세션 목록 */}
          <div style={{ flex: 1, overflow: 'auto', padding: '8px' }}>
            {sessions.length === 0 ? (
              <div style={{
                padding: '20px',
                textAlign: 'center',
                color: '#999',
                fontSize: '0.9em'
              }}>
                분석 기록이 없습니다.
                <br />새 이미지를 업로드해주세요.
              </div>
            ) : (
              sessions.map(session => (
                <div
                  key={session.id}
                  style={{
                    padding: '12px',
                    marginBottom: '8px',
                    backgroundColor: currentSessionId === session.id ? '#e3f2fd' : 'white',
                    borderRadius: '8px',
                    border: currentSessionId === session.id ? '2px solid #1976d2' : '1px solid #e0e0e0',
                    cursor: 'pointer',
                    transition: 'all 0.2s'
                  }}
                  onClick={() => selectSession(session.id)}
                >
                  {/* 세션 썸네일 */}
                  <div style={{
                    width: '100%',
                    height: '80px',
                    backgroundColor: '#f5f5f5',
                    borderRadius: '4px',
                    marginBottom: '8px',
                    overflow: 'hidden',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}>
                    <img
                      src={session.thumbnail_url}
                      alt={session.name}
                      style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }}
                      onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                    />
                  </div>

                  {/* 세션 이름 (편집 모드) */}
                  {editingSessionId === session.id ? (
                    <div style={{ display: 'flex', gap: '4px', marginBottom: '4px' }}>
                      <input
                        type="text"
                        value={editingSessionName}
                        onChange={(e) => setEditingSessionName(e.target.value)}
                        onClick={(e) => e.stopPropagation()}
                        style={{
                          flex: 1,
                          padding: '4px 8px',
                          border: '1px solid #1976d2',
                          borderRadius: '4px',
                          fontSize: '0.85em'
                        }}
                        autoFocus
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            updateSessionName(session.id, editingSessionName);
                          } else if (e.key === 'Escape') {
                            setEditingSessionId(null);
                          }
                        }}
                      />
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          updateSessionName(session.id, editingSessionName);
                        }}
                        style={{
                          padding: '4px 8px',
                          backgroundColor: '#28a745',
                          color: 'white',
                          border: 'none',
                          borderRadius: '4px',
                          fontSize: '12px',
                          cursor: 'pointer'
                        }}
                      >
                        ✓
                      </button>
                    </div>
                  ) : (
                    <div style={{
                      fontWeight: '500',
                      fontSize: '0.9em',
                      marginBottom: '4px',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap'
                    }}>
                      {session.name}
                    </div>
                  )}

                  {/* 세션 정보 */}
                  <div style={{ fontSize: '0.75em', color: '#666' }}>
                    {session.question_count}개 문항 • {new Date(session.created_at).toLocaleDateString()}
                  </div>

                  {/* 세션 액션 버튼 */}
                  <div style={{
                    display: 'flex',
                    gap: '4px',
                    marginTop: '8px'
                  }}>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setEditingSessionId(session.id);
                        setEditingSessionName(session.name);
                      }}
                      style={{
                        flex: 1,
                        padding: '4px',
                        backgroundColor: '#f8f9fa',
                        border: '1px solid #dee2e6',
                        borderRadius: '4px',
                        fontSize: '11px',
                        cursor: 'pointer'
                      }}
                      title="이름 수정"
                    >
                      ✏️
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        reanalyzeSession(session.id);
                      }}
                      disabled={isReanalyzing}
                      style={{
                        flex: 1,
                        padding: '4px',
                        backgroundColor: '#f8f9fa',
                        border: '1px solid #dee2e6',
                        borderRadius: '4px',
                        fontSize: '11px',
                        cursor: 'pointer'
                      }}
                      title="재분석"
                    >
                      🔄
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteSession(session.id);
                      }}
                      style={{
                        flex: 1,
                        padding: '4px',
                        backgroundColor: '#fff5f5',
                        border: '1px solid #ffcdd2',
                        borderRadius: '4px',
                        fontSize: '11px',
                        cursor: 'pointer'
                      }}
                      title="삭제"
                    >
                      🗑️
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* 사이드바 토글 버튼 */}
      <button
        onClick={() => setShowSidebar(!showSidebar)}
        style={{
          position: 'absolute',
          left: showSidebar ? '280px' : '0',
          top: '50%',
          transform: 'translateY(-50%)',
          padding: '8px 4px',
          backgroundColor: '#f8f9fa',
          border: '1px solid #e0e0e0',
          borderLeft: 'none',
          borderRadius: '0 4px 4px 0',
          cursor: 'pointer',
          zIndex: 10
        }}
      >
        {showSidebar ? '◀' : '▶'}
      </button>

      {/* 메인 콘텐츠 */}
      <div style={{ flex: 1, overflow: 'auto', padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '30px' }}>
          <h1 style={{ margin: 0 }}>시험 문항 분석기</h1>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              onClick={() => setShowStatsModal(true)}
              style={{
                padding: '8px 16px',
                backgroundColor: '#28a745',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '14px'
              }}
            >
              📊 LLM 사용량
            </button>
            <button
              onClick={() => setShowPromptEditor(!showPromptEditor)}
              style={{
                padding: '8px 16px',
                backgroundColor: showPromptEditor ? '#6c757d' : '#17a2b8',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '14px'
              }}
            >
              {showPromptEditor ? '프롬프트 편집기 닫기' : '⚙️ 프롬프트 편집'}
            </button>
          </div>
        </div>

      {/* Prompt Editor */}
      {showPromptEditor && (
        <div style={{
          marginBottom: '24px',
          padding: '20px',
          backgroundColor: '#f8f9fa',
          borderRadius: '12px',
          border: '1px solid #dee2e6'
        }}>
          {/* Header with Save Button */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3 style={{ margin: 0, fontSize: '1.1em' }}>🔧 LLM 프롬프트 관리</h3>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              {promptSaveMessage && (
                <span style={{ fontSize: '0.9em', color: promptSaveMessage.includes('✅') ? '#28a745' : '#dc3545' }}>
                  {promptSaveMessage}
                </span>
              )}
              <button
                onClick={savePrompts}
                disabled={isSavingPrompt}
                style={{
                  padding: '8px 16px',
                  backgroundColor: '#28a745',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '14px',
                  fontWeight: 'bold'
                }}
              >
                {isSavingPrompt ? '저장 중...' : '💾 저장'}
              </button>
            </div>
          </div>

          {/* Tabs */}
          <div style={{ display: 'flex', gap: '4px', marginBottom: '16px' }}>
            <button
              onClick={() => setActivePromptTab('system')}
              style={{
                padding: '10px 20px',
                backgroundColor: activePromptTab === 'system' ? '#007bff' : '#e9ecef',
                color: activePromptTab === 'system' ? 'white' : '#495057',
                border: 'none',
                borderRadius: '8px 8px 0 0',
                cursor: 'pointer',
                fontSize: '14px',
                fontWeight: activePromptTab === 'system' ? 'bold' : 'normal'
              }}
            >
              🤖 시스템 프롬프트
            </button>
            <button
              onClick={() => setActivePromptTab('user')}
              style={{
                padding: '10px 20px',
                backgroundColor: activePromptTab === 'user' ? '#17a2b8' : '#e9ecef',
                color: activePromptTab === 'user' ? 'white' : '#495057',
                border: 'none',
                borderRadius: '8px 8px 0 0',
                cursor: 'pointer',
                fontSize: '14px',
                fontWeight: activePromptTab === 'user' ? 'bold' : 'normal'
              }}
            >
              👤 사용자 프롬프트
            </button>
          </div>

          {/* System Prompt Tab */}
          {activePromptTab === 'system' && (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <p style={{ margin: 0, fontSize: '0.9em', color: '#666' }}>
                  기본 분석 형식과 규칙을 정의하는 프롬프트입니다. JSON 출력 형식을 유지하세요.
                </p>
                <button
                  onClick={() => resetPrompt('system')}
                  style={{
                    padding: '6px 12px',
                    backgroundColor: '#6c757d',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontSize: '12px'
                  }}
                >
                  기본값으로 초기화
                </button>
              </div>
              <textarea
                value={systemPrompt}
                onChange={(e) => setSystemPrompt(e.target.value)}
                style={{
                  width: '100%',
                  height: '350px',
                  padding: '12px',
                  border: '2px solid #007bff',
                  borderRadius: '8px',
                  fontFamily: 'monospace',
                  fontSize: '13px',
                  lineHeight: '1.5',
                  resize: 'vertical',
                  backgroundColor: 'white'
                }}
                placeholder="시스템 프롬프트를 입력하세요..."
              />
            </div>
          )}

          {/* User Prompt Tab */}
          {activePromptTab === 'user' && (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <p style={{ margin: 0, fontSize: '0.9em', color: '#666' }}>
                  추가 지시사항을 입력하세요. 시스템 프롬프트 뒤에 추가됩니다. (선택사항)
                </p>
                <button
                  onClick={() => resetPrompt('user')}
                  style={{
                    padding: '6px 12px',
                    backgroundColor: '#6c757d',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontSize: '12px'
                  }}
                >
                  비우기
                </button>
              </div>
              <textarea
                value={userPrompt}
                onChange={(e) => setUserPrompt(e.target.value)}
                style={{
                  width: '100%',
                  height: '200px',
                  padding: '12px',
                  border: '2px solid #17a2b8',
                  borderRadius: '8px',
                  fontFamily: 'monospace',
                  fontSize: '13px',
                  lineHeight: '1.5',
                  resize: 'vertical',
                  backgroundColor: 'white'
                }}
                placeholder="예: 수학 문제만 집중적으로 분석해주세요. 또는 영어 지문은 번역도 포함해주세요."
              />
              <div style={{
                marginTop: '12px',
                padding: '12px',
                backgroundColor: '#e3f2fd',
                borderRadius: '6px',
                fontSize: '0.85em',
                color: '#1565c0'
              }}>
                💡 <strong>사용 예시:</strong>
                <ul style={{ margin: '8px 0 0 0', paddingLeft: '20px' }}>
                  <li>특정 과목 문제에 집중: "수학 문제의 풀이 과정도 간단히 설명해주세요"</li>
                  <li>추가 정보 요청: "각 문항의 예상 난이도(상/중/하)도 표시해주세요"</li>
                  <li>형식 조정: "선택지 번호를 A, B, C, D, E로 표시해주세요"</li>
                </ul>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Upload Zone */}
      {!result && !isAnalyzing && (
        <div>
          {/* 세션 이름 입력 */}
          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9em', color: '#666' }}>
              세션 이름 (선택사항 - 비워두면 자동 생성)
            </label>
            <input
              type="text"
              value={sessionNameInput}
              onChange={(e) => setSessionNameInput(e.target.value)}
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
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
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
              💡 <strong>Ctrl+V</strong> (또는 Cmd+V)로 클립보드 이미지 붙여넣기 가능
            </p>
            <input
              type="file"
              id="file-input"
              accept="image/*"
              onChange={handleFileInputChange}
              style={{ display: 'none' }}
            />
          </div>
        </div>
      )}

      {/* Loading */}
      {isAnalyzing && (
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
      )}

      {/* Error */}
      {error && (
        <div style={{
          padding: '20px',
          backgroundColor: '#ffebee',
          borderRadius: '8px',
          marginBottom: '20px',
          borderLeft: '4px solid #f44336'
        }}>
          <strong style={{ color: '#c62828' }}>오류:</strong> {error}
          <button
            onClick={handleReset}
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
      )}

      {/* Results */}
      {result && (
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
                onClick={() => setShowExamModal(true)}
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
                onClick={handleReset}
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
            {imageUrl && (
              <div style={{ flex: '0 0 350px', maxWidth: '350px' }}>
                <div style={{
                  position: 'sticky',
                  top: '20px'
                }}>
                  {/* 원본 이미지 */}
                  <div style={{
                    border: '1px solid #e0e0e0',
                    borderRadius: '8px',
                    overflow: 'hidden',
                    marginBottom: '16px'
                  }}>
                    <div style={{
                      padding: '12px',
                      backgroundColor: '#f5f5f5',
                      borderBottom: '1px solid #e0e0e0',
                      fontWeight: 'bold',
                      fontSize: '0.9em'
                    }}>
                      📷 원본 이미지
                    </div>
                    <img
                      src={imageUrl}
                      alt="Uploaded exam"
                      style={{ width: '100%', display: 'block' }}
                    />
                  </div>

                  {/* 크롭된 이미지들 */}
                  {result.questions && result.questions.filter(q => q.cropped_image_url).length > 0 && (
                    <div style={{
                      border: '1px solid #ce93d8',
                      borderRadius: '8px',
                      overflow: 'hidden',
                      backgroundColor: '#faf4fc'
                    }}>
                      <div style={{
                        padding: '12px',
                        backgroundColor: '#f3e5f5',
                        borderBottom: '1px solid #ce93d8',
                        fontWeight: 'bold',
                        fontSize: '0.9em',
                        color: '#7b1fa2'
                      }}>
                        ✂️ 문제별 크롭 이미지
                      </div>
                      <div style={{ padding: '12px' }}>
                        {result.questions.filter(q => q.cropped_image_url).map((question, idx) => (
                          <div key={idx} style={{ marginBottom: idx < result.questions.filter(q => q.cropped_image_url).length - 1 ? '12px' : 0 }}>
                            <div style={{
                              fontSize: '0.85em',
                              color: '#7b1fa2',
                              marginBottom: '6px',
                              fontWeight: '500'
                            }}>
                              {question.question_number}번 문제
                            </div>
                            <img
                              src={question.cropped_image_url}
                              alt={`문제 ${question.question_number} 크롭 이미지`}
                              style={{
                                width: '100%',
                                display: 'block',
                                borderRadius: '4px',
                                border: '1px solid #e1bee7'
                              }}
                            />
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Questions */}
            <div style={{ flex: '1', minWidth: '400px' }}>
              {result.questions && result.questions.length > 0 ? (
                result.questions.map((question, idx) => (
                  <QuestionCard
                    key={idx}
                    question={question}
                    index={idx}
                    onGenerateVariants={generateVariants}
                    onAnalyzeQuestion={analyzeQuestion}
                    sessionId={currentSessionId}
                    variantRecords={variantRecordsByQuestion[question.question_number]}
                    onRefreshVariants={() => {
                      if (currentSessionId && result.questions) {
                        loadVariantRecords(currentSessionId, result.questions);
                      }
                    }}
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
      )}

      {/* 문제지 생성 설정 모달 */}
      {showExamModal && (
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
                onChange={(e) => setExamSettings(prev => ({ ...prev, title: e.target.value }))}
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
                onChange={(e) => setExamSettings(prev => ({ ...prev, questionCount: parseInt(e.target.value) }))}
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
                  { value: 'easy', label: '하' },
                  { value: 'medium', label: '중' },
                  { value: 'hard', label: '상' },
                  { value: 'mixed', label: '혼합' }
                ].map(opt => (
                  <button
                    key={opt.value}
                    onClick={() => setExamSettings(prev => ({ ...prev, difficulty: opt.value as 'easy' | 'medium' | 'hard' | 'mixed' }))}
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
                  onChange={(e) => setExamSettings(prev => ({ ...prev, includeAnswerSheet: e.target.checked }))}
                  style={{ width: '18px', height: '18px' }}
                />
                <span style={{ fontWeight: 'bold', color: '#333' }}>정답지 포함</span>
              </label>
            </div>

            {/* 오류 메시지 */}
            {examError && (
              <div style={{
                padding: '12px',
                backgroundColor: '#ffebee',
                borderRadius: '6px',
                marginBottom: '16px',
                color: '#c62828',
                fontSize: '14px'
              }}>
                {examError}
              </div>
            )}

            {/* 버튼 */}
            <div style={{ display: 'flex', gap: '12px' }}>
              <button
                onClick={() => {
                  setShowExamModal(false);
                  setExamError(null);
                }}
                style={{
                  flex: 1,
                  padding: '12px 20px',
                  backgroundColor: '#f8f9fa',
                  border: '1px solid #dee2e6',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontWeight: 'bold'
                }}
              >
                취소
              </button>
              <button
                onClick={generateExam}
                disabled={isGeneratingExam}
                style={{
                  flex: 1,
                  padding: '12px 20px',
                  backgroundColor: isGeneratingExam ? '#ccc' : '#007bff',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: isGeneratingExam ? 'not-allowed' : 'pointer',
                  fontWeight: 'bold'
                }}
              >
                {isGeneratingExam ? '생성 중...' : '문제지 생성'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 문항 분석 모달 */}
      {showAnalysisModal && (
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
              📚 문항 심층 분석
            </h3>

            {/* 진행 상황 */}
            <div style={{
              backgroundColor: 'rgba(255,255,255,0.2)',
              borderRadius: '8px',
              padding: '16px',
              marginBottom: '16px'
            }}>
              <div style={{ color: 'white', marginBottom: '8px', fontSize: '0.9em' }}>
                {analysisStep}
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
                  width: `${analysisProgress}%`,
                  transition: 'width 0.3s ease'
                }} />
              </div>
              <div style={{ color: 'rgba(255,255,255,0.8)', marginTop: '8px', fontSize: '0.85em' }}>
                {analysisProgress}% 완료
              </div>
            </div>

            {/* 오류 표시 */}
            {analysisError && (
              <div style={{
                backgroundColor: '#ffebee',
                color: '#c62828',
                padding: '12px',
                borderRadius: '8px',
                marginBottom: '16px',
                fontSize: '0.9em'
              }}>
                {analysisError}
              </div>
            )}

            {/* 완료 시 결과 */}
            {analysisUrl && (
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
                  href={analysisUrl}
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
                  📊 분석 결과 보기
                </a>
              </div>
            )}

            {/* 버튼 */}
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
              {analysisUrl && (
                <a
                  href={analysisUrl}
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
                  🔗 새 탭에서 열기
                </a>
              )}
              <button
                onClick={() => setShowAnalysisModal(false)}
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
      )}

      {/* 변형 문제 생성 모달 */}
      {showVariantsModal && (
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
            height: '90%',
            maxWidth: '1200px',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            boxShadow: '0 20px 60px rgba(0,0,0,0.3)'
          }}>
            {/* 모달 헤더 */}
            <div style={{
              padding: '16px 24px',
              borderBottom: '1px solid #e0e0e0',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
            }}>
              <h2 style={{ margin: 0, color: 'white', fontSize: '1.3em' }}>
                🎯 변형 문제 생성 결과
              </h2>
              <div style={{ display: 'flex', gap: '12px' }}>
                {variantsUrl && (
                  <a
                    href={variantsUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      padding: '8px 16px',
                      backgroundColor: 'white',
                      color: '#667eea',
                      border: 'none',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      fontSize: '0.9em',
                      fontWeight: 'bold',
                      textDecoration: 'none'
                    }}
                  >
                    🔗 새 탭에서 열기
                  </a>
                )}
                <button
                  onClick={() => setShowVariantsModal(false)}
                  style={{
                    padding: '8px 16px',
                    backgroundColor: 'rgba(255,255,255,0.2)',
                    color: 'white',
                    border: '1px solid rgba(255,255,255,0.3)',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    fontSize: '0.9em',
                    fontWeight: 'bold'
                  }}
                >
                  ✕ 닫기
                </button>
              </div>
            </div>

            {/* 모달 본문 */}
            <div style={{ flex: 1, overflow: 'hidden' }}>
              {isGeneratingVariants ? (
                <div style={{
                  height: '100%',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '24px',
                  padding: '40px'
                }}>
                  {/* 진행률 원형 표시 */}
                  <div style={{
                    position: 'relative',
                    width: '160px',
                    height: '160px'
                  }}>
                    <svg width="160" height="160" style={{ transform: 'rotate(-90deg)' }}>
                      {/* 배경 원 */}
                      <circle
                        cx="80"
                        cy="80"
                        r="70"
                        fill="none"
                        stroke="#e0e0e0"
                        strokeWidth="12"
                      />
                      {/* 진행 원 */}
                      <circle
                        cx="80"
                        cy="80"
                        r="70"
                        fill="none"
                        stroke="url(#progressGradient)"
                        strokeWidth="12"
                        strokeLinecap="round"
                        strokeDasharray={`${2 * Math.PI * 70}`}
                        strokeDashoffset={`${2 * Math.PI * 70 * (1 - variantsProgress / 100)}`}
                        style={{ transition: 'stroke-dashoffset 0.3s ease' }}
                      />
                      <defs>
                        <linearGradient id="progressGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                          <stop offset="0%" stopColor="#667eea" />
                          <stop offset="100%" stopColor="#764ba2" />
                        </linearGradient>
                      </defs>
                    </svg>
                    {/* 퍼센트 텍스트 */}
                    <div style={{
                      position: 'absolute',
                      top: '50%',
                      left: '50%',
                      transform: 'translate(-50%, -50%)',
                      textAlign: 'center'
                    }}>
                      <div style={{ fontSize: '2.5em', fontWeight: 'bold', color: '#667eea' }}>
                        {variantsProgress}%
                      </div>
                    </div>
                  </div>

                  {/* 현재 단계 메시지 */}
                  <div style={{ textAlign: 'center' }}>
                    <p style={{ fontSize: '1.2em', color: '#333', margin: '0 0 8px 0', fontWeight: '500' }}>
                      {variantsStep}
                    </p>
                    <p style={{ fontSize: '0.9em', color: '#666', margin: 0 }}>
                      쉬움 3개 / 보통 4개 / 어려움 3개 생성
                    </p>
                  </div>

                  {/* 진행 바 */}
                  <div style={{
                    width: '80%',
                    maxWidth: '400px',
                    height: '8px',
                    backgroundColor: '#e0e0e0',
                    borderRadius: '4px',
                    overflow: 'hidden'
                  }}>
                    <div style={{
                      width: `${variantsProgress}%`,
                      height: '100%',
                      background: 'linear-gradient(90deg, #667eea 0%, #764ba2 100%)',
                      borderRadius: '4px',
                      transition: 'width 0.3s ease'
                    }} />
                  </div>

                  {/* 단계 안내 */}
                  <div style={{
                    display: 'flex',
                    gap: '16px',
                    flexWrap: 'wrap',
                    justifyContent: 'center',
                    marginTop: '8px'
                  }}>
                    {[
                      { label: '문제 생성', min: 0, max: 50 },
                      { label: '정답 검증', min: 50, max: 85 },
                      { label: '리포트 생성', min: 85, max: 100 }
                    ].map((stage, idx) => (
                      <div
                        key={idx}
                        style={{
                          padding: '6px 14px',
                          borderRadius: '20px',
                          fontSize: '0.85em',
                          fontWeight: variantsProgress >= stage.min && variantsProgress < stage.max ? 'bold' : 'normal',
                          backgroundColor: variantsProgress >= stage.max ? '#c8e6c9' :
                                          variantsProgress >= stage.min ? '#e3f2fd' : '#f5f5f5',
                          color: variantsProgress >= stage.max ? '#2e7d32' :
                                variantsProgress >= stage.min ? '#1976d2' : '#999'
                        }}
                      >
                        {variantsProgress >= stage.max ? '✓ ' : ''}{stage.label}
                      </div>
                    ))}
                  </div>

                  {/* 자동 복구 상태 표시 */}
                  {isAutoRetrying && (
                    <div style={{
                      marginTop: '16px',
                      padding: '16px 24px',
                      backgroundColor: '#fff3e0',
                      borderRadius: '12px',
                      border: '2px solid #ff9800',
                      textAlign: 'center',
                      animation: 'pulse 2s infinite'
                    }}>
                      <div style={{ fontSize: '1.5em', marginBottom: '8px' }}>🔧</div>
                      <p style={{ margin: '0 0 4px 0', fontWeight: 'bold', color: '#e65100' }}>
                        AI 자동 복구 중...
                      </p>
                      <p style={{ margin: 0, fontSize: '0.85em', color: '#f57c00' }}>
                        오류를 분석하고 자동으로 수정하고 있습니다
                      </p>
                    </div>
                  )}

                  {/* 자동 복구 분석 결과 */}
                  {autoFixAnalysis && !isAutoRetrying && (
                    <div style={{
                      marginTop: '12px',
                      padding: '12px 16px',
                      backgroundColor: '#e8f5e9',
                      borderRadius: '8px',
                      fontSize: '0.85em',
                      color: '#2e7d32',
                      maxWidth: '400px',
                      textAlign: 'center'
                    }}>
                      <strong>✅ 자동 수정됨:</strong> {autoFixAnalysis}
                    </div>
                  )}
                </div>
              ) : variantsError ? (
                <div style={{
                  height: '100%',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '20px',
                  padding: '40px'
                }}>
                  <div style={{ fontSize: '4em' }}>
                    {variantsError.includes('API') ? '🔌' :
                     variantsError.includes('모듈') ? '📦' :
                     variantsError.includes('문법') ? '⚠️' : '❌'}
                  </div>
                  <div style={{ textAlign: 'center', maxWidth: '500px' }}>
                    <p style={{ fontSize: '1.2em', color: '#c62828', margin: '0 0 12px 0', fontWeight: 'bold' }}>
                      오류가 발생했습니다
                    </p>
                    <p style={{
                      fontSize: '0.95em',
                      color: '#666',
                      margin: 0,
                      padding: '12px 16px',
                      backgroundColor: '#ffebee',
                      borderRadius: '8px',
                      wordBreak: 'break-word'
                    }}>
                      {variantsError}
                    </p>
                  </div>
                  <div style={{ display: 'flex', gap: '12px', marginTop: '8px' }}>
                    <button
                      onClick={() => {
                        setVariantsError(null);
                        setShowVariantsModal(false);
                      }}
                      style={{
                        padding: '10px 24px',
                        backgroundColor: '#6c757d',
                        color: 'white',
                        border: 'none',
                        borderRadius: '6px',
                        cursor: 'pointer',
                        fontSize: '0.95em'
                      }}
                    >
                      닫기
                    </button>
                  </div>
                  {/* 오류 해결 팁 */}
                  <div style={{
                    marginTop: '16px',
                    padding: '16px',
                    backgroundColor: '#fff3e0',
                    borderRadius: '8px',
                    maxWidth: '450px',
                    fontSize: '0.85em',
                    color: '#e65100'
                  }}>
                    <strong>💡 해결 방법:</strong>
                    <ul style={{ margin: '8px 0 0 0', paddingLeft: '20px' }}>
                      {variantsError.includes('API') && (
                        <>
                          <li>API 키가 올바른지 확인하세요</li>
                          <li>API 사용량 한도를 확인하세요</li>
                        </>
                      )}
                      {variantsError.includes('모듈') && (
                        <>
                          <li>필요한 Python 패키지가 설치되었는지 확인하세요</li>
                          <li><code>pip install -r requirements.txt</code> 실행</li>
                        </>
                      )}
                      {!variantsError.includes('API') && !variantsError.includes('모듈') && (
                        <>
                          <li>서버가 정상적으로 실행 중인지 확인하세요</li>
                          <li>잠시 후 다시 시도해주세요</li>
                        </>
                      )}
                    </ul>
                  </div>
                </div>
              ) : variantsUrl ? (
                <iframe
                  src={variantsUrl}
                  style={{
                    width: '100%',
                    height: '100%',
                    border: 'none'
                  }}
                  title="변형 문제"
                />
              ) : null}
            </div>
          </div>
        </div>
      )}

      {/* LLM 사용량 통계 모달 */}
      {showStatsModal && (
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
            maxWidth: '800px',
            maxHeight: '90%',
            overflow: 'auto',
            boxShadow: '0 20px 60px rgba(0,0,0,0.3)'
          }}>
            {/* 모달 헤더 */}
            <div style={{
              padding: '16px 24px',
              borderBottom: '1px solid #e0e0e0',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              background: 'linear-gradient(135deg, #28a745 0%, #20c997 100%)',
              position: 'sticky',
              top: 0,
              zIndex: 1
            }}>
              <h2 style={{ margin: 0, color: 'white', fontSize: '1.3em' }}>
                📊 LLM API 사용량 통계
              </h2>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  onClick={loadLlmStats}
                  disabled={isLoadingStats}
                  style={{
                    padding: '8px 16px',
                    backgroundColor: 'rgba(255,255,255,0.2)',
                    color: 'white',
                    border: '1px solid rgba(255,255,255,0.3)',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    fontSize: '0.9em'
                  }}
                >
                  🔄 새로고침
                </button>
                <button
                  onClick={() => setShowStatsModal(false)}
                  style={{
                    padding: '8px 16px',
                    backgroundColor: 'rgba(255,255,255,0.2)',
                    color: 'white',
                    border: '1px solid rgba(255,255,255,0.3)',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    fontSize: '0.9em',
                    fontWeight: 'bold'
                  }}
                >
                  ✕ 닫기
                </button>
              </div>
            </div>

            {/* 모달 본문 */}
            <div style={{ padding: '24px' }}>
              {isLoadingStats ? (
                <div style={{ textAlign: 'center', padding: '40px' }}>
                  <div style={{ fontSize: '2em', marginBottom: '16px' }}>⏳</div>
                  <p>통계 로딩 중...</p>
                </div>
              ) : llmStats ? (
                <>
                  {/* 요약 카드 */}
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                    gap: '16px',
                    marginBottom: '24px'
                  }}>
                    <div style={{
                      padding: '20px',
                      backgroundColor: '#e3f2fd',
                      borderRadius: '12px',
                      textAlign: 'center'
                    }}>
                      <div style={{ fontSize: '2em', fontWeight: 'bold', color: '#1976d2' }}>
                        {llmStats.total_calls}
                      </div>
                      <div style={{ fontSize: '0.9em', color: '#666', marginTop: '4px' }}>총 API 호출</div>
                      <div style={{ fontSize: '0.8em', color: '#999', marginTop: '4px' }}>
                        성공: {llmStats.successful_calls} / 실패: {llmStats.failed_calls}
                      </div>
                    </div>
                    <div style={{
                      padding: '20px',
                      backgroundColor: '#e8f5e9',
                      borderRadius: '12px',
                      textAlign: 'center'
                    }}>
                      <div style={{ fontSize: '2em', fontWeight: 'bold', color: '#2e7d32' }}>
                        {llmStats.total_tokens.toLocaleString()}
                      </div>
                      <div style={{ fontSize: '0.9em', color: '#666', marginTop: '4px' }}>총 토큰</div>
                      <div style={{ fontSize: '0.8em', color: '#999', marginTop: '4px' }}>
                        입력: {llmStats.total_input_tokens.toLocaleString()} / 출력: {llmStats.total_output_tokens.toLocaleString()}
                      </div>
                    </div>
                    <div style={{
                      padding: '20px',
                      backgroundColor: '#fff3e0',
                      borderRadius: '12px',
                      textAlign: 'center'
                    }}>
                      <div style={{ fontSize: '2em', fontWeight: 'bold', color: '#f57c00' }}>
                        ${llmStats.total_cost_usd.toFixed(6)}
                      </div>
                      <div style={{ fontSize: '0.9em', color: '#666', marginTop: '4px' }}>예상 비용</div>
                      <div style={{ fontSize: '0.8em', color: '#999', marginTop: '4px' }}>
                        약 ₩{llmStats.total_cost_krw.toFixed(2)}
                      </div>
                    </div>
                  </div>

                  {/* 모델별 통계 */}
                  {Object.keys(llmStats.by_model).length > 0 && (
                    <div style={{ marginBottom: '24px' }}>
                      <h3 style={{ margin: '0 0 12px 0', fontSize: '1em', color: '#333' }}>📈 모델별 사용량</h3>
                      <div style={{
                        backgroundColor: '#f8f9fa',
                        borderRadius: '8px',
                        overflow: 'hidden'
                      }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                          <thead>
                            <tr style={{ backgroundColor: '#e9ecef' }}>
                              <th style={{ padding: '12px', textAlign: 'left', fontSize: '0.9em' }}>모델</th>
                              <th style={{ padding: '12px', textAlign: 'right', fontSize: '0.9em' }}>호출 수</th>
                              <th style={{ padding: '12px', textAlign: 'right', fontSize: '0.9em' }}>입력 토큰</th>
                              <th style={{ padding: '12px', textAlign: 'right', fontSize: '0.9em' }}>출력 토큰</th>
                              <th style={{ padding: '12px', textAlign: 'right', fontSize: '0.9em' }}>비용</th>
                            </tr>
                          </thead>
                          <tbody>
                            {Object.entries(llmStats.by_model).map(([model, data]) => (
                              <tr key={model} style={{ borderTop: '1px solid #dee2e6' }}>
                                <td style={{ padding: '12px', fontFamily: 'monospace', fontSize: '0.85em' }}>{model}</td>
                                <td style={{ padding: '12px', textAlign: 'right' }}>{data.calls}</td>
                                <td style={{ padding: '12px', textAlign: 'right' }}>{data.input_tokens.toLocaleString()}</td>
                                <td style={{ padding: '12px', textAlign: 'right' }}>{data.output_tokens.toLocaleString()}</td>
                                <td style={{ padding: '12px', textAlign: 'right' }}>${data.cost.toFixed(6)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {/* 작업별 통계 */}
                  {Object.keys(llmStats.by_operation).length > 0 && (
                    <div style={{ marginBottom: '24px' }}>
                      <h3 style={{ margin: '0 0 12px 0', fontSize: '1em', color: '#333' }}>🔧 작업별 사용량</h3>
                      <div style={{
                        backgroundColor: '#f8f9fa',
                        borderRadius: '8px',
                        overflow: 'hidden'
                      }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                          <thead>
                            <tr style={{ backgroundColor: '#e9ecef' }}>
                              <th style={{ padding: '12px', textAlign: 'left', fontSize: '0.9em' }}>작업</th>
                              <th style={{ padding: '12px', textAlign: 'right', fontSize: '0.9em' }}>호출 수</th>
                              <th style={{ padding: '12px', textAlign: 'right', fontSize: '0.9em' }}>총 토큰</th>
                              <th style={{ padding: '12px', textAlign: 'right', fontSize: '0.9em' }}>비용</th>
                            </tr>
                          </thead>
                          <tbody>
                            {Object.entries(llmStats.by_operation).map(([op, data]) => (
                              <tr key={op} style={{ borderTop: '1px solid #dee2e6' }}>
                                <td style={{ padding: '12px' }}>
                                  <span style={{
                                    padding: '4px 8px',
                                    backgroundColor: op === 'analyze_image' ? '#e3f2fd' :
                                                    op === 'generate_variants' ? '#e8f5e9' :
                                                    op === 'verify_answer' ? '#fff3e0' : '#f3e5f5',
                                    color: op === 'analyze_image' ? '#1976d2' :
                                          op === 'generate_variants' ? '#2e7d32' :
                                          op === 'verify_answer' ? '#f57c00' : '#7b1fa2',
                                    borderRadius: '4px',
                                    fontSize: '0.85em'
                                  }}>
                                    {op === 'analyze_image' ? '🔍 이미지 분석' :
                                     op === 'generate_variants' ? '🎯 변형 문제 생성' :
                                     op === 'verify_answer' ? '✅ 정답 검증' :
                                     op === 'fix_error' ? '🔧 오류 수정' :
                                     op === 'fix_json' ? '📝 JSON 수정' : op}
                                  </span>
                                </td>
                                <td style={{ padding: '12px', textAlign: 'right' }}>{data.calls}</td>
                                <td style={{ padding: '12px', textAlign: 'right' }}>{(data.input_tokens + data.output_tokens).toLocaleString()}</td>
                                <td style={{ padding: '12px', textAlign: 'right' }}>${data.cost.toFixed(6)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {/* 최근 호출 기록 */}
                  {llmStats.recent_calls.length > 0 && (
                    <div style={{ marginBottom: '24px' }}>
                      <h3 style={{ margin: '0 0 12px 0', fontSize: '1em', color: '#333' }}>📋 최근 호출 기록</h3>
                      <div style={{
                        backgroundColor: '#f8f9fa',
                        borderRadius: '8px',
                        overflow: 'auto',
                        maxHeight: '300px'
                      }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: '600px' }}>
                          <thead>
                            <tr style={{ backgroundColor: '#e9ecef', position: 'sticky', top: 0 }}>
                              <th style={{ padding: '10px', textAlign: 'left', fontSize: '0.85em' }}>시간</th>
                              <th style={{ padding: '10px', textAlign: 'left', fontSize: '0.85em' }}>작업</th>
                              <th style={{ padding: '10px', textAlign: 'right', fontSize: '0.85em' }}>토큰</th>
                              <th style={{ padding: '10px', textAlign: 'right', fontSize: '0.85em' }}>응답시간</th>
                              <th style={{ padding: '10px', textAlign: 'center', fontSize: '0.85em' }}>상태</th>
                            </tr>
                          </thead>
                          <tbody>
                            {[...llmStats.recent_calls].reverse().map((call, idx) => (
                              <tr key={idx} style={{ borderTop: '1px solid #dee2e6' }}>
                                <td style={{ padding: '10px', fontSize: '0.8em', color: '#666' }}>
                                  {new Date(call.timestamp).toLocaleTimeString()}
                                </td>
                                <td style={{ padding: '10px', fontSize: '0.85em' }}>{call.operation}</td>
                                <td style={{ padding: '10px', textAlign: 'right', fontSize: '0.85em' }}>
                                  {(call.input_tokens + call.output_tokens).toLocaleString()}
                                </td>
                                <td style={{ padding: '10px', textAlign: 'right', fontSize: '0.85em' }}>
                                  {(call.latency_ms / 1000).toFixed(2)}s
                                </td>
                                <td style={{ padding: '10px', textAlign: 'center' }}>
                                  {call.success ? '✅' : '❌'}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {/* 세션 정보 및 초기화 */}
                  <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '16px',
                    backgroundColor: '#f8f9fa',
                    borderRadius: '8px',
                    fontSize: '0.85em',
                    color: '#666'
                  }}>
                    <span>
                      세션 시작: {new Date(llmStats.session_start).toLocaleString()}
                    </span>
                    <button
                      onClick={resetLlmStats}
                      style={{
                        padding: '8px 16px',
                        backgroundColor: '#dc3545',
                        color: 'white',
                        border: 'none',
                        borderRadius: '6px',
                        cursor: 'pointer',
                        fontSize: '0.85em'
                      }}
                    >
                      🗑️ 통계 초기화
                    </button>
                  </div>
                </>
              ) : (
                <div style={{ textAlign: 'center', padding: '40px', color: '#666' }}>
                  <p>통계 데이터를 불러올 수 없습니다.</p>
                  <button
                    onClick={loadLlmStats}
                    style={{
                      marginTop: '16px',
                      padding: '8px 16px',
                      backgroundColor: '#007bff',
                      color: 'white',
                      border: 'none',
                      borderRadius: '6px',
                      cursor: 'pointer'
                    }}
                  >
                    다시 시도
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
      </div>
    </div>
  );
}

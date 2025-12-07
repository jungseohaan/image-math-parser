'use client';

import { useState } from 'react';
import RenderMathText from './RenderMathText';
import { QuestionData, VariantRecord } from '../lib/types';

interface QuestionCardProps {
  question: QuestionData;
  index: number;
  onAnalyzeQuestion?: (question: QuestionData) => void;
  sessionId?: string | null;
  variantRecords?: VariantRecord[];
  onRefreshVariants?: () => void;
}

export default function QuestionCard({
  question,
  index,
  onAnalyzeQuestion,
  sessionId,
  variantRecords,
  onRefreshVariants
}: QuestionCardProps) {
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

              {question.analysis_process.objects_used && question.analysis_process.objects_used.length > 0 && (
                <div style={{ marginBottom: '12px' }}>
                  <span style={{ fontWeight: '600', color: '#388e3c', fontSize: '0.85em' }}>📦 사용된 사물: </span>
                  <span style={{ color: '#555' }}>{question.analysis_process.objects_used.join(', ')}</span>
                </div>
              )}

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

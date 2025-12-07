
// app/page.tsx
'use client';

import React, { useState, useCallback, useEffect, ChangeEvent, DragEvent } from 'react';
import 'katex/dist/katex.min.css';

// Import components
import SettingsModal from './components/SettingsModal';
import ExamGenerationModal, { ExamSettings } from './components/ExamGenerationModal';
import AnalysisProgressModal from './components/AnalysisProgressModal';
import ImageUploader from './components/ImageUploader';
import Sidebar from './components/Sidebar';
import AnalysisResultView from './components/AnalysisResult';
import Header from './components/Header';
import LoadingSpinner from './components/LoadingSpinner';
import ErrorDisplay from './components/ErrorDisplay';

// Import types
import { QuestionData, VariantsResult } from './lib/types';

// Import hooks
import { usePrompts, useApiKey, useLlmStats, useSessions } from './hooks';

// Import utilities
import { getApiUrl } from './lib/api';
import { generateExamHtml } from './lib/examHtml';

const API_URL = getApiUrl();

export default function ExamAnalyzerPage() {
  // Custom hooks
  const {
    systemPrompt, setSystemPrompt,
    userPrompt, setUserPrompt,
    isSavingPrompt, promptSaveMessage,
    loadPrompts, savePrompts
  } = usePrompts();

  const {
    geminiApiKey, apiKeyInput, setApiKeyInput,
    saveApiKey, clearApiKey, getApiHeaders
  } = useApiKey();

  const { llmStats, isLoadingStats, loadLlmStats, resetLlmStats } = useLlmStats();

  const {
    sessions, currentSessionId, setCurrentSessionId,
    isLoadingSessions, isReanalyzing,
    result, setResult,
    imageUrl, setImageUrl,
    error, setError,
    variantRecordsByQuestion,
    loadSessions, selectSession, deleteSession,
    updateSessionName, reanalyzeSession, loadVariantRecords,
    resetState
  } = useSessions({ getApiHeaders, systemPrompt, userPrompt });

  // Local states
  const [isDragging, setIsDragging] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [sessionNameInput, setSessionNameInput] = useState<string>('');
  const [showSidebar, setShowSidebar] = useState(true);

  // Exam generation states
  const [showExamModal, setShowExamModal] = useState(false);
  const [examSettings, setExamSettings] = useState<ExamSettings>({
    questionCount: 5,
    difficulty: 'mixed',
    title: '수학 모의고사',
    includeAnswerSheet: true
  });
  const [isGeneratingExam, setIsGeneratingExam] = useState(false);
  const [examError, setExamError] = useState<string | null>(null);
  const [variantsProgress, setVariantsProgress] = useState<number>(0);
  const [variantsStep, setVariantsStep] = useState<string>('');

  // Question analysis states
  const [showAnalysisModal, setShowAnalysisModal] = useState(false);
  const [analysisUrl, setAnalysisUrl] = useState<string | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [analysisProgress, setAnalysisProgress] = useState<number>(0);
  const [analysisStep, setAnalysisStep] = useState<string>('');

  // Settings modal state
  const [showSettingsModal, setShowSettingsModal] = useState(false);

  // Load settings when modal opens
  useEffect(() => {
    if (showSettingsModal) {
      loadLlmStats();
      loadPrompts();
    }
  }, [showSettingsModal, loadLlmStats, loadPrompts]);

  const analyzeImage = useCallback(async (file: File) => {
    setIsAnalyzing(true);
    setResult(null);
    setError(null);
    setImageUrl(null);
    setCurrentSessionId(null);

    try {
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

      const response = await fetch(`${API_URL}/sessions`, {
        method: 'POST',
        headers: getApiHeaders(),
        body: formData,
      });

      const data = await response.json();

      if (data.success) {
        setCurrentSessionId(data.session_id);
        setImageUrl(data.image_url);
        setResult(data.data);
        setSessionNameInput('');
        loadSessions();
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
  }, [systemPrompt, userPrompt, sessionNameInput, loadSessions, getApiHeaders, setResult, setError, setImageUrl, setCurrentSessionId]);

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
    resetState();
  };

  // Clipboard paste handler
  useEffect(() => {
    const handleGlobalPaste = (e: globalThis.ClipboardEvent) => {
      if (!result && !isAnalyzing) {
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
      }
    };

    document.addEventListener('paste', handleGlobalPaste);
    return () => document.removeEventListener('paste', handleGlobalPaste);
  }, [analyzeImage, result, isAnalyzing]);

  // Question analysis (SSE)
  const analyzeQuestion = useCallback(async (question: QuestionData) => {
    if (!currentSessionId) {
      alert('세션을 먼저 생성해주세요.');
      return;
    }

    setAnalysisError(null);
    setAnalysisUrl(null);
    setAnalysisProgress(0);
    setAnalysisStep('시작 중...');
    setShowAnalysisModal(true);

    try {
      const response = await fetch(`${API_URL}/sessions/${currentSessionId}/analyze-question`, {
        method: 'POST',
        headers: getApiHeaders({ 'Content-Type': 'application/json' }),
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
              } else if (data.step === 'error') {
                setAnalysisError(data.message);
              }
            } catch {
              // JSON parsing failed, ignore
            }
          }
        }
      }
    } catch (err) {
      console.error('문항 분석 오류:', err);
      setAnalysisError('문항 분석 중 오류가 발생했습니다.');
    }
  }, [currentSessionId, getApiHeaders]);

  // Exam generation
  const generateExam = useCallback(async () => {
    if (!result?.questions || result.questions.length === 0) {
      setExamError('분석된 문항이 없습니다.');
      return;
    }

    const question = result.questions[0];
    setIsGeneratingExam(true);
    setExamError(null);
    setVariantsProgress(0);
    setVariantsStep('변형 문제 생성 시작...');

    const headers = getApiHeaders({ 'Content-Type': 'application/json' });

    try {
      // Step 1: Generate meta code
      setVariantsStep('메타코드 생성 중...');
      setVariantsProgress(10);

      const codeResponse = await fetch(`${API_URL}/variants/generate-code`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ question })
      });

      if (!codeResponse.ok) {
        const errorData = await codeResponse.json();
        throw new Error(errorData.message || '메타코드 생성 실패');
      }

      const codeResult = await codeResponse.json();
      if (!codeResult.success) {
        throw new Error(codeResult.message || '메타코드 생성 실패');
      }

      setVariantsProgress(25);

      // Step 2: Execute code
      setVariantsStep('변형 문제 생성 중...');
      setVariantsProgress(30);

      const executeResponse = await fetch(`${API_URL}/variants/execute-code`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          code: codeResult.code,
          difficulties: [["쉬움", 3], ["보통", 4], ["어려움", 3]]
        })
      });

      if (!executeResponse.ok) {
        const errorData = await executeResponse.json();
        throw new Error(errorData.message || '코드 실행 실패');
      }

      const executeResult = await executeResponse.json();
      if (!executeResult.success) {
        throw new Error(executeResult.message || '코드 실행 실패');
      }

      setVariantsProgress(50);
      setVariantsStep(`변형 문제 ${executeResult.total}개 생성됨`);

      // Step 3: Generate original solution
      setVariantsStep('원본 문제 풀이 생성 중...');
      setVariantsProgress(55);

      const solveResponse = await fetch(`${API_URL}/variants/solve-original`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ question })
      });

      if (!solveResponse.ok) {
        const errorData = await solveResponse.json();
        throw new Error(errorData.message || '풀이 생성 실패');
      }

      const solveResult = await solveResponse.json();
      setVariantsProgress(65);

      // Step 4: Quick verify variants
      setVariantsStep('변형 문제 검증 중...');
      const verifiedVariants: typeof executeResult.variants = [];

      for (const variant of executeResult.variants) {
        if (variant.error) continue;

        const quickVerifyResponse = await fetch(`${API_URL}/variants/quick-verify`, {
          method: 'POST',
          headers,
          body: JSON.stringify({ variant })
        });

        const quickVerifyResult = await quickVerifyResponse.json();

        if (quickVerifyResult.verified === true) {
          variant.verification = { is_correct: true, method: 'local' };
          verifiedVariants.push(variant);
        }

        setVariantsProgress(65 + Math.floor((verifiedVariants.length / executeResult.total) * 25));
      }

      setVariantsProgress(90);
      setVariantsStep('문제지 생성 중...');

      // Build final result
      const generatedVariants: VariantsResult = {
        original: {
          question_number: question.question_number,
          question_text: question.question_text,
          choices: question.choices,
          answer: solveResult.solution?.answer || '',
          explanation: solveResult.solution?.explanation || '',
          key_concepts: solveResult.solution?.key_concepts || []
        },
        variants: verifiedVariants.slice(0, 10),
        generation_method: 'stepwise_api',
        generated_code: codeResult.code
      };

      // Filter by difficulty
      const difficultyMap: Record<string, string> = {
        easy: '쉬움',
        medium: '보통',
        hard: '어려움'
      };

      let filteredVariants = [...generatedVariants.variants];

      if (examSettings.difficulty !== 'mixed') {
        const targetDifficulty = difficultyMap[examSettings.difficulty];
        filteredVariants = generatedVariants.variants.filter(v => v.difficulty === targetDifficulty);

        if (filteredVariants.length < examSettings.questionCount) {
          const remaining = generatedVariants.variants.filter(v => v.difficulty !== targetDifficulty);
          filteredVariants = [...filteredVariants, ...remaining];
        }
      }

      // Shuffle and select
      const shuffled = filteredVariants.sort(() => Math.random() - 0.5);
      const selected = shuffled.slice(0, examSettings.questionCount);

      // Generate HTML
      const examHtml = generateExamHtml(selected, examSettings.title, examSettings.includeAnswerSheet);

      // Open in new window
      const newWindow = window.open('', '_blank');
      if (newWindow) {
        newWindow.document.write(examHtml);
        newWindow.document.close();
      }

      setVariantsProgress(100);
      setVariantsStep('완료!');
      setShowExamModal(false);
    } catch (err) {
      console.error('문제지 생성 오류:', err);
      setExamError(err instanceof Error ? err.message : '문제지 생성 중 오류가 발생했습니다.');
    } finally {
      setIsGeneratingExam(false);
    }
  }, [result, examSettings, getApiHeaders]);

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      <Sidebar
        isOpen={showSidebar}
        sessions={sessions}
        currentSessionId={currentSessionId}
        isLoadingSessions={isLoadingSessions}
        isReanalyzing={isReanalyzing}
        onLoadSessions={loadSessions}
        onSelectSession={selectSession}
        onUpdateSessionName={updateSessionName}
        onReanalyzeSession={reanalyzeSession}
        onDeleteSession={deleteSession}
        onToggle={() => setShowSidebar(!showSidebar)}
      />

      {/* Main content */}
      <div style={{ flex: 1, overflow: 'auto', padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
        <Header
          geminiApiKey={geminiApiKey}
          onOpenSettings={() => {
            setShowSettingsModal(true);
            loadLlmStats();
          }}
        />

        {/* Upload Zone */}
        {!result && !isAnalyzing && (
          <ImageUploader
            isDragging={isDragging}
            sessionNameInput={sessionNameInput}
            onSessionNameChange={setSessionNameInput}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onFileSelect={handleFileInputChange}
          />
        )}

        {/* Loading */}
        {isAnalyzing && <LoadingSpinner />}

        {/* Error */}
        {error && <ErrorDisplay error={error} onRetry={handleReset} />}

        {/* Results */}
        {result && (
          <AnalysisResultView
            result={result}
            imageUrl={imageUrl}
            currentSessionId={currentSessionId}
            variantRecordsByQuestion={variantRecordsByQuestion}
            onReset={handleReset}
            onOpenExamModal={() => setShowExamModal(true)}
            onAnalyzeQuestion={analyzeQuestion}
            onRefreshVariants={() => {
              if (currentSessionId && result.questions) {
                loadVariantRecords(currentSessionId, result.questions);
              }
            }}
          />
        )}

        {/* Exam generation modal */}
        <ExamGenerationModal
          isOpen={showExamModal}
          onClose={() => {
            setShowExamModal(false);
            setExamError(null);
            setVariantsProgress(0);
            setVariantsStep('');
          }}
          examSettings={examSettings}
          onSettingsChange={setExamSettings}
          isGenerating={isGeneratingExam}
          progress={variantsProgress}
          progressStep={variantsStep}
          error={examError}
          onGenerate={generateExam}
        />

        {/* Question analysis modal */}
        <AnalysisProgressModal
          isOpen={showAnalysisModal}
          onClose={() => setShowAnalysisModal(false)}
          progress={analysisProgress}
          step={analysisStep}
          error={analysisError}
          resultUrl={analysisUrl}
        />

        {/* Settings modal */}
        <SettingsModal
          isOpen={showSettingsModal}
          onClose={() => setShowSettingsModal(false)}
          geminiApiKey={geminiApiKey}
          apiKeyInput={apiKeyInput}
          onApiKeyInputChange={setApiKeyInput}
          onSaveApiKey={saveApiKey}
          onClearApiKey={clearApiKey}
          llmStats={llmStats}
          isLoadingStats={isLoadingStats}
          onLoadStats={loadLlmStats}
          onResetStats={resetLlmStats}
          systemPrompt={systemPrompt}
          userPrompt={userPrompt}
          onSystemPromptChange={setSystemPrompt}
          onUserPromptChange={setUserPrompt}
          onSavePrompts={savePrompts}
          isSavingPrompt={isSavingPrompt}
          promptSaveMessage={promptSaveMessage || ''}
        />
      </div>
    </div>
  );
}

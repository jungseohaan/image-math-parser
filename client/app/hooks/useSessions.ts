import { useState, useCallback, useEffect } from 'react';
import { getApiUrl } from '../lib/api';
import { Session, AnalysisResult, QuestionData, VariantRecord } from '../lib/types';

const API_URL = getApiUrl();

interface UseSessionsOptions {
  getApiHeaders: (additionalHeaders?: Record<string, string>) => Record<string, string>;
  systemPrompt: string;
  userPrompt: string;
}

export function useSessions({ getApiHeaders, systemPrompt, userPrompt }: UseSessionsOptions) {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [isLoadingSessions, setIsLoadingSessions] = useState(false);
  const [isReanalyzing, setIsReanalyzing] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [variantRecordsByQuestion, setVariantRecordsByQuestion] = useState<Record<string, VariantRecord[]>>({});

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

  const selectSession = useCallback(async (sessionId: string) => {
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
    }
  }, []);

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
      }
    } catch (err) {
      console.error('세션 이름 수정 실패:', err);
    }
  }, []);

  const reanalyzeSession = useCallback(async (sessionId: string) => {
    if (!confirm('이 세션을 재분석하시겠습니까? 기존 분석 결과가 덮어씌워집니다.')) return;

    setIsReanalyzing(true);
    setError(null);
    try {
      const response = await fetch(`${API_URL}/sessions/${sessionId}/reanalyze`, {
        method: 'POST',
        headers: getApiHeaders({ 'Content-Type': 'application/json' }),
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
  }, [systemPrompt, userPrompt, getApiHeaders]);

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

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  useEffect(() => {
    if (currentSessionId && result?.questions) {
      loadVariantRecords(currentSessionId, result.questions);
    } else {
      setVariantRecordsByQuestion({});
    }
  }, [currentSessionId, result, loadVariantRecords]);

  const resetState = useCallback(() => {
    setResult(null);
    setImageUrl(null);
    setError(null);
    setCurrentSessionId(null);
  }, []);

  return {
    sessions,
    setSessions,
    currentSessionId,
    setCurrentSessionId,
    isLoadingSessions,
    isReanalyzing,
    result,
    setResult,
    imageUrl,
    setImageUrl,
    error,
    setError,
    variantRecordsByQuestion,
    loadSessions,
    selectSession,
    deleteSession,
    updateSessionName,
    reanalyzeSession,
    loadVariantRecords,
    resetState
  };
}

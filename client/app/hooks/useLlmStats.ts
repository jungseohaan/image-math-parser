import { useState, useCallback } from 'react';
import { getApiUrl } from '../lib/api';
import { LlmStatsData } from '../lib/types';

const API_URL = getApiUrl();

export function useLlmStats() {
  const [llmStats, setLlmStats] = useState<LlmStatsData | null>(null);
  const [isLoadingStats, setIsLoadingStats] = useState(false);

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

  return {
    llmStats,
    isLoadingStats,
    loadLlmStats,
    resetLlmStats
  };
}

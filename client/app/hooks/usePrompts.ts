import { useState, useCallback, useEffect } from 'react';
import { getApiUrl } from '../lib/api';

const API_URL = getApiUrl();

export function usePrompts() {
  const [systemPrompt, setSystemPrompt] = useState<string>('');
  const [userPrompt, setUserPrompt] = useState<string>('');
  const [isSavingPrompt, setIsSavingPrompt] = useState(false);
  const [promptSaveMessage, setPromptSaveMessage] = useState<string | null>(null);

  const loadPrompts = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/prompts`);
      const data = await response.json();
      if (data.success) {
        setSystemPrompt(data.system_prompt);
        setUserPrompt(data.user_prompt);
      }
    } catch (err) {
      console.error('프롬프트 로드 실패:', err);
    }
  }, []);

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
        setPromptSaveMessage('저장되었습니다');
        setTimeout(() => setPromptSaveMessage(null), 3000);
      }
    } catch (err) {
      console.error('프롬프트 저장 실패:', err);
      setPromptSaveMessage('저장 실패');
    } finally {
      setIsSavingPrompt(false);
    }
  }, [systemPrompt, userPrompt]);

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
        setPromptSaveMessage('초기화되었습니다');
        setTimeout(() => setPromptSaveMessage(null), 3000);
      }
    } catch (err) {
      console.error('프롬프트 초기화 실패:', err);
    }
  }, []);

  useEffect(() => {
    loadPrompts();
  }, [loadPrompts]);

  return {
    systemPrompt,
    setSystemPrompt,
    userPrompt,
    setUserPrompt,
    isSavingPrompt,
    promptSaveMessage,
    loadPrompts,
    savePrompts,
    resetPrompt
  };
}

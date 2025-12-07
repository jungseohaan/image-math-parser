import { useState, useEffect, useCallback } from 'react';

export function useApiKey() {
  const [geminiApiKey, setGeminiApiKey] = useState<string>('');
  const [apiKeyInput, setApiKeyInput] = useState<string>('');

  useEffect(() => {
    const savedApiKey = localStorage.getItem('gemini_api_key');
    if (savedApiKey) {
      setGeminiApiKey(savedApiKey);
    } else {
      const envApiKey = process.env.NEXT_PUBLIC_GEMINI_API_KEY || '';
      if (envApiKey) {
        setGeminiApiKey(envApiKey);
      }
    }
  }, []);

  const saveApiKey = useCallback(() => {
    if (apiKeyInput.trim()) {
      localStorage.setItem('gemini_api_key', apiKeyInput.trim());
      setGeminiApiKey(apiKeyInput.trim());
      setApiKeyInput('');
    }
  }, [apiKeyInput]);

  const clearApiKey = useCallback(() => {
    localStorage.removeItem('gemini_api_key');
    setGeminiApiKey('');
  }, []);

  const getApiHeaders = useCallback((additionalHeaders: Record<string, string> = {}): Record<string, string> => {
    const headers: Record<string, string> = { ...additionalHeaders };
    if (geminiApiKey) {
      headers['X-Gemini-API-Key'] = geminiApiKey;
    }
    return headers;
  }, [geminiApiKey]);

  return {
    geminiApiKey,
    apiKeyInput,
    setApiKeyInput,
    saveApiKey,
    clearApiKey,
    getApiHeaders
  };
}

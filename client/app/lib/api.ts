// lib/api.ts - API 유틸리티

// API URL 설정 - 런타임 도메인 기반으로 결정
const FLASK_PRODUCTION_URL = 'https://flask-five-amber.vercel.app';
const FLASK_LOCAL_URL = 'http://localhost:4001';

export const getApiUrl = (): string => {
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname;
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
      return FLASK_LOCAL_URL;
    }
  }
  return FLASK_PRODUCTION_URL;
};

export const API_URL = getApiUrl();

// API 헤더 생성 함수
export const getApiHeaders = (
  additionalHeaders: Record<string, string> = {},
  apiKey?: string | null
): Record<string, string> => {
  const headers: Record<string, string> = { ...additionalHeaders };
  if (apiKey) {
    headers['X-Gemini-API-Key'] = apiKey;
  }
  return headers;
};

// 로컬스토리지에서 API 키 가져오기
export const getStoredApiKey = (): string | null => {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('gemini_api_key');
};

// 로컬스토리지에 API 키 저장
export const setStoredApiKey = (key: string): void => {
  if (typeof window === 'undefined') return;
  localStorage.setItem('gemini_api_key', key);
};

// 로컬스토리지에서 API 키 삭제
export const removeStoredApiKey = (): void => {
  if (typeof window === 'undefined') return;
  localStorage.removeItem('gemini_api_key');
};

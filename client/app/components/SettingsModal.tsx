'use client';

import { useState } from 'react';
import { LlmStatsData } from '../lib/types';

type SettingsTab = 'api-key' | 'llm-stats' | 'prompts';
type PromptTab = 'system' | 'user';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  // API Key
  geminiApiKey: string | null;
  apiKeyInput: string;
  onApiKeyInputChange: (value: string) => void;
  onSaveApiKey: () => void;
  onClearApiKey: () => void;
  // LLM Stats
  llmStats: LlmStatsData | null;
  isLoadingStats: boolean;
  onLoadStats: () => void;
  onResetStats: () => void;
  // Prompts
  systemPrompt: string;
  userPrompt: string;
  onSystemPromptChange: (value: string) => void;
  onUserPromptChange: (value: string) => void;
  onSavePrompts: () => void;
  isSavingPrompt: boolean;
  promptSaveMessage: string;
}

export default function SettingsModal({
  isOpen,
  onClose,
  geminiApiKey,
  apiKeyInput,
  onApiKeyInputChange,
  onSaveApiKey,
  onClearApiKey,
  llmStats,
  isLoadingStats,
  onLoadStats,
  onResetStats,
  systemPrompt,
  userPrompt,
  onSystemPromptChange,
  onUserPromptChange,
  onSavePrompts,
  isSavingPrompt,
  promptSaveMessage
}: SettingsModalProps) {
  const [activeSettingsTab, setActiveSettingsTab] = useState<SettingsTab>('api-key');
  const [activePromptTab, setActivePromptTab] = useState<PromptTab>('system');

  if (!isOpen) return null;

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
        width: '95%',
        maxWidth: '900px',
        maxHeight: '90vh',
        overflow: 'hidden',
        boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
        display: 'flex',
        flexDirection: 'column'
      }}>
        {/* Modal Header */}
        <div style={{
          padding: '16px 24px',
          borderBottom: '1px solid #e0e0e0',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          background: 'linear-gradient(135deg, #495057 0%, #343a40 100%)'
        }}>
          <h2 style={{ margin: 0, color: 'white', fontSize: '1.3em' }}>
            Settings
          </h2>
          <button
            onClick={onClose}
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
            Close
          </button>
        </div>

        {/* Tab Navigation */}
        <div style={{
          display: 'flex',
          borderBottom: '1px solid #e0e0e0',
          backgroundColor: '#f8f9fa'
        }}>
          <button
            onClick={() => setActiveSettingsTab('api-key')}
            style={{
              flex: 1,
              padding: '14px 20px',
              backgroundColor: activeSettingsTab === 'api-key' ? 'white' : 'transparent',
              color: activeSettingsTab === 'api-key' ? '#1976d2' : '#666',
              border: 'none',
              borderBottom: activeSettingsTab === 'api-key' ? '2px solid #1976d2' : '2px solid transparent',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: activeSettingsTab === 'api-key' ? 'bold' : 'normal',
              transition: 'all 0.2s'
            }}
          >
            API Key
          </button>
          <button
            onClick={() => setActiveSettingsTab('llm-stats')}
            style={{
              flex: 1,
              padding: '14px 20px',
              backgroundColor: activeSettingsTab === 'llm-stats' ? 'white' : 'transparent',
              color: activeSettingsTab === 'llm-stats' ? '#28a745' : '#666',
              border: 'none',
              borderBottom: activeSettingsTab === 'llm-stats' ? '2px solid #28a745' : '2px solid transparent',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: activeSettingsTab === 'llm-stats' ? 'bold' : 'normal',
              transition: 'all 0.2s'
            }}
          >
            LLM Usage
          </button>
          <button
            onClick={() => setActiveSettingsTab('prompts')}
            style={{
              flex: 1,
              padding: '14px 20px',
              backgroundColor: activeSettingsTab === 'prompts' ? 'white' : 'transparent',
              color: activeSettingsTab === 'prompts' ? '#17a2b8' : '#666',
              border: 'none',
              borderBottom: activeSettingsTab === 'prompts' ? '2px solid #17a2b8' : '2px solid transparent',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: activeSettingsTab === 'prompts' ? 'bold' : 'normal',
              transition: 'all 0.2s'
            }}
          >
            Prompts
          </button>
        </div>

        {/* Tab Content */}
        <div style={{ flex: 1, overflow: 'auto', padding: '24px' }}>
          {/* API Key Tab */}
          {activeSettingsTab === 'api-key' && (
            <div>
              <h3 style={{ margin: '0 0 16px 0', fontSize: '1.1em', color: '#333' }}>
                Gemini API Key Settings
              </h3>

              <p style={{ margin: '0 0 16px 0', fontSize: '14px', color: '#666' }}>
                Enter your Gemini API key from Google AI Studio.
                <br />
                <a
                  href="https://aistudio.google.com/apikey"
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ color: '#1976d2' }}
                >
                  Get API Key
                </a>
              </p>

              <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold', color: '#333' }}>
                  API Key
                </label>
                <input
                  type="password"
                  value={apiKeyInput}
                  onChange={(e) => onApiKeyInputChange(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '12px 14px',
                    border: '1px solid #dee2e6',
                    borderRadius: '6px',
                    fontSize: '14px',
                    boxSizing: 'border-box',
                    fontFamily: 'monospace'
                  }}
                  placeholder="AIza..."
                />
              </div>

              <div style={{
                padding: '12px',
                backgroundColor: geminiApiKey ? '#d4edda' : '#fff3cd',
                borderRadius: '6px',
                marginBottom: '20px',
                fontSize: '13px',
                color: geminiApiKey ? '#155724' : '#856404'
              }}>
                {geminiApiKey ? 'API key is configured.' : 'API key is not configured.'}
                <br />
                <span style={{ color: '#666', fontSize: '12px' }}>
                  API key is stored in browser local storage and is not sent to the server.
                </span>
              </div>

              <div style={{ display: 'flex', gap: '8px' }}>
                {geminiApiKey && (
                  <button
                    onClick={() => {
                      onClearApiKey();
                      onApiKeyInputChange('');
                    }}
                    style={{
                      padding: '10px 20px',
                      backgroundColor: '#dc3545',
                      color: 'white',
                      border: 'none',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      fontSize: '14px'
                    }}
                  >
                    Delete Key
                  </button>
                )}
                <button
                  onClick={onSaveApiKey}
                  disabled={!apiKeyInput.trim()}
                  style={{
                    padding: '10px 20px',
                    backgroundColor: apiKeyInput.trim() ? '#1976d2' : '#ccc',
                    color: 'white',
                    border: 'none',
                    borderRadius: '6px',
                    cursor: apiKeyInput.trim() ? 'pointer' : 'not-allowed',
                    fontSize: '14px'
                  }}
                >
                  Save
                </button>
              </div>
            </div>
          )}

          {/* LLM Stats Tab */}
          {activeSettingsTab === 'llm-stats' && (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <h3 style={{ margin: 0, fontSize: '1.1em', color: '#333' }}>
                  LLM API Usage Statistics
                </h3>
                <button
                  onClick={onLoadStats}
                  disabled={isLoadingStats}
                  style={{
                    padding: '8px 16px',
                    backgroundColor: '#28a745',
                    color: 'white',
                    border: 'none',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    fontSize: '0.9em'
                  }}
                >
                  Refresh
                </button>
              </div>

              {isLoadingStats ? (
                <div style={{ textAlign: 'center', padding: '40px' }}>
                  <div style={{ fontSize: '2em', marginBottom: '16px' }}>...</div>
                  <p>Loading stats...</p>
                </div>
              ) : llmStats ? (
                <>
                  {/* Summary Cards */}
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
                      <div style={{ fontSize: '0.9em', color: '#666', marginTop: '4px' }}>Total API Calls</div>
                      <div style={{ fontSize: '0.8em', color: '#999', marginTop: '4px' }}>
                        Success: {llmStats.successful_calls} / Failed: {llmStats.failed_calls}
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
                      <div style={{ fontSize: '0.9em', color: '#666', marginTop: '4px' }}>Total Tokens</div>
                      <div style={{ fontSize: '0.8em', color: '#999', marginTop: '4px' }}>
                        In: {llmStats.total_input_tokens.toLocaleString()} / Out: {llmStats.total_output_tokens.toLocaleString()}
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
                      <div style={{ fontSize: '0.9em', color: '#666', marginTop: '4px' }}>Estimated Cost</div>
                      <div style={{ fontSize: '0.8em', color: '#999', marginTop: '4px' }}>
                        ~{llmStats.total_cost_krw.toFixed(2)} KRW
                      </div>
                    </div>
                  </div>

                  {/* Model Stats */}
                  {Object.keys(llmStats.by_model).length > 0 && (
                    <div style={{ marginBottom: '24px' }}>
                      <h4 style={{ margin: '0 0 12px 0', fontSize: '1em', color: '#333' }}>Usage by Model</h4>
                      <div style={{
                        backgroundColor: '#f8f9fa',
                        borderRadius: '8px',
                        overflow: 'hidden'
                      }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                          <thead>
                            <tr style={{ backgroundColor: '#e9ecef' }}>
                              <th style={{ padding: '12px', textAlign: 'left', fontSize: '0.9em' }}>Model</th>
                              <th style={{ padding: '12px', textAlign: 'right', fontSize: '0.9em' }}>Calls</th>
                              <th style={{ padding: '12px', textAlign: 'right', fontSize: '0.9em' }}>Input Tokens</th>
                              <th style={{ padding: '12px', textAlign: 'right', fontSize: '0.9em' }}>Output Tokens</th>
                              <th style={{ padding: '12px', textAlign: 'right', fontSize: '0.9em' }}>Cost</th>
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

                  {/* Session Info & Reset */}
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
                      Session Start: {new Date(llmStats.session_start).toLocaleString()}
                    </span>
                    <button
                      onClick={onResetStats}
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
                      Reset Stats
                    </button>
                  </div>
                </>
              ) : (
                <div style={{ textAlign: 'center', padding: '40px', color: '#666' }}>
                  <p>Unable to load statistics data.</p>
                  <button
                    onClick={onLoadStats}
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
                    Retry
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Prompts Tab */}
          {activeSettingsTab === 'prompts' && (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <h3 style={{ margin: 0, fontSize: '1.1em', color: '#333' }}>
                  LLM Prompt Management
                </h3>
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  {promptSaveMessage && (
                    <span style={{ fontSize: '0.9em', color: promptSaveMessage.includes('success') ? '#28a745' : '#dc3545' }}>
                      {promptSaveMessage}
                    </span>
                  )}
                  <button
                    onClick={onSavePrompts}
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
                    {isSavingPrompt ? 'Saving...' : 'Save'}
                  </button>
                </div>
              </div>

              {/* Prompt Tabs */}
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
                  System Prompt
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
                  User Prompt
                </button>
              </div>

              {/* System Prompt */}
              {activePromptTab === 'system' && (
                <div>
                  <p style={{ margin: '0 0 8px 0', fontSize: '0.9em', color: '#666' }}>
                    Defines the base analysis format and rules. Keep the JSON output format.
                  </p>
                  <textarea
                    value={systemPrompt}
                    onChange={(e) => onSystemPromptChange(e.target.value)}
                    style={{
                      width: '100%',
                      height: '350px',
                      padding: '12px',
                      border: '1px solid #ced4da',
                      borderRadius: '8px',
                      fontSize: '13px',
                      fontFamily: 'monospace',
                      resize: 'vertical',
                      boxSizing: 'border-box'
                    }}
                    placeholder="Enter system prompt..."
                  />
                </div>
              )}

              {/* User Prompt */}
              {activePromptTab === 'user' && (
                <div>
                  <p style={{ margin: '0 0 8px 0', fontSize: '0.9em', color: '#666' }}>
                    User prompt sent with each analysis request.
                  </p>
                  <textarea
                    value={userPrompt}
                    onChange={(e) => onUserPromptChange(e.target.value)}
                    style={{
                      width: '100%',
                      height: '350px',
                      padding: '12px',
                      border: '1px solid #ced4da',
                      borderRadius: '8px',
                      fontSize: '13px',
                      fontFamily: 'monospace',
                      resize: 'vertical',
                      boxSizing: 'border-box'
                    }}
                    placeholder="Enter user prompt..."
                  />
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

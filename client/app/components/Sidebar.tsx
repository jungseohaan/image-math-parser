'use client';

import { Session } from '../lib/types';
import SessionList from './SessionList';

interface SidebarProps {
  isOpen: boolean;
  sessions: Session[];
  currentSessionId: string | null;
  isLoadingSessions: boolean;
  isReanalyzing: boolean;
  onLoadSessions: () => void;
  onSelectSession: (sessionId: string) => void;
  onUpdateSessionName: (sessionId: string, name: string) => void;
  onReanalyzeSession: (sessionId: string) => void;
  onDeleteSession: (sessionId: string) => void;
  onToggle: () => void;
}

export default function Sidebar({
  isOpen,
  sessions,
  currentSessionId,
  isLoadingSessions,
  isReanalyzing,
  onLoadSessions,
  onSelectSession,
  onUpdateSessionName,
  onReanalyzeSession,
  onDeleteSession,
  onToggle
}: SidebarProps) {
  return (
    <>
      {/* 사이드바 */}
      {isOpen && (
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
              onClick={onLoadSessions}
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
            <SessionList
              sessions={sessions}
              currentSessionId={currentSessionId}
              isReanalyzing={isReanalyzing}
              onSelectSession={onSelectSession}
              onUpdateSessionName={onUpdateSessionName}
              onReanalyzeSession={onReanalyzeSession}
              onDeleteSession={onDeleteSession}
            />
          </div>
        </div>
      )}

      {/* 사이드바 토글 버튼 */}
      <button
        onClick={onToggle}
        style={{
          position: 'absolute',
          left: isOpen ? '280px' : '0',
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
        {isOpen ? '◀' : '▶'}
      </button>
    </>
  );
}

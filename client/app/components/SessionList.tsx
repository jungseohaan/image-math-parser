'use client';

import { useState } from 'react';
import { Session } from '../lib/types';

interface SessionListProps {
  sessions: Session[];
  currentSessionId: string | null;
  isReanalyzing: boolean;
  onSelectSession: (sessionId: string) => void;
  onUpdateSessionName: (sessionId: string, name: string) => void;
  onReanalyzeSession: (sessionId: string) => void;
  onDeleteSession: (sessionId: string) => void;
}

export default function SessionList({
  sessions,
  currentSessionId,
  isReanalyzing,
  onSelectSession,
  onUpdateSessionName,
  onReanalyzeSession,
  onDeleteSession
}: SessionListProps) {
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [editingSessionName, setEditingSessionName] = useState('');

  if (sessions.length === 0) {
    return (
      <div style={{
        padding: '20px',
        textAlign: 'center',
        color: '#999',
        fontSize: '0.9em'
      }}>
        No analysis records.
        <br />Please upload a new image.
      </div>
    );
  }

  return (
    <>
      {sessions.map(session => (
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
          onClick={() => onSelectSession(session.id)}
        >
          {/* Session Thumbnail */}
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

          {/* Session Name (Edit Mode) */}
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
                    onUpdateSessionName(session.id, editingSessionName);
                    setEditingSessionId(null);
                  } else if (e.key === 'Escape') {
                    setEditingSessionId(null);
                  }
                }}
              />
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onUpdateSessionName(session.id, editingSessionName);
                  setEditingSessionId(null);
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
                OK
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

          {/* Session Info */}
          <div style={{ fontSize: '0.75em', color: '#666' }}>
            {session.question_count} questions - {new Date(session.created_at).toLocaleDateString()}
          </div>

          {/* Session Action Buttons */}
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
              title="Rename"
            >
              Edit
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onReanalyzeSession(session.id);
              }}
              disabled={isReanalyzing}
              style={{
                flex: 1,
                padding: '4px',
                backgroundColor: '#f8f9fa',
                border: '1px solid #dee2e6',
                borderRadius: '4px',
                fontSize: '11px',
                cursor: isReanalyzing ? 'not-allowed' : 'pointer',
                opacity: isReanalyzing ? 0.5 : 1
              }}
              title="Reanalyze"
            >
              Redo
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDeleteSession(session.id);
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
              title="Delete"
            >
              Del
            </button>
          </div>
        </div>
      ))}
    </>
  );
}

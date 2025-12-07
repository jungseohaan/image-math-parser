'use client';

interface HeaderProps {
  geminiApiKey: string;
  onOpenSettings: () => void;
}

export default function Header({ geminiApiKey, onOpenSettings }: HeaderProps) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '30px' }}>
      <h1 style={{ margin: 0 }}>시험 문항 분석기</h1>
      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
        {/* API 키 상태 표시 (간소화) */}
        {!geminiApiKey && (
          <span style={{ fontSize: '12px', color: '#856404', marginRight: '4px' }}>
            ⚠️ API 키 필요
          </span>
        )}
        {/* 설정 버튼 */}
        <button
          onClick={onOpenSettings}
          style={{
            padding: '10px',
            backgroundColor: '#495057',
            color: 'white',
            border: 'none',
            borderRadius: '8px',
            cursor: 'pointer',
            fontSize: '18px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '42px',
            height: '42px'
          }}
          title="설정"
        >
          ⚙️
        </button>
      </div>
    </div>
  );
}

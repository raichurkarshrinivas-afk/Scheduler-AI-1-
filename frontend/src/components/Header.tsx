import React from 'react';
import { User } from '../types';

interface HeaderProps {
  currentUser: User | null;
  activeTab: string;
  setActiveTab: (tab: string) => void;
  onLogout: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  currentUser,
  activeTab,
  setActiveTab,
  onLogout,
}) => {
  return (
    <header className="app-header">
      <div className="brand-wrapper">
        <div className="brand-logo">S</div>
        <div>
          <h1 className="brand-title">Scheduler</h1>
          <div className="brand-subtitle">Educational Timetable & Seating Platform</div>
        </div>
      </div>

      <nav className="nav-links">
        <button
          className={`nav-btn ${activeTab === 'dashboard' ? 'active' : ''}`}
          onClick={() => setActiveTab('dashboard')}
          id="nav-dashboard-btn"
        >
          Dashboard
        </button>
        <button
          className={`nav-btn ${activeTab === 'timetable' ? 'active' : ''}`}
          onClick={() => setActiveTab('timetable')}
          id="nav-timetable-btn"
        >
          Timetable Matrix
        </button>
        <button
          className={`nav-btn ${activeTab === 'seating' ? 'active' : ''}`}
          onClick={() => setActiveTab('seating')}
          id="nav-seating-btn"
        >
          Exam Seating Plans
        </button>
        <button
          className={`nav-btn ${activeTab === 'facilities' ? 'active' : ''}`}
          onClick={() => setActiveTab('facilities')}
          id="nav-facilities-btn"
        >
          Facilities & Courses
        </button>
      </nav>

      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        {currentUser ? (
          <div className="user-badge">
            <span>{currentUser.full_name}</span>
            <span className="role-pill">{currentUser.role}</span>
            <button
              onClick={onLogout}
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--text-muted)',
                cursor: 'pointer',
                fontSize: '0.75rem',
                marginLeft: '0.5rem',
              }}
            >
              Sign Out
            </button>
          </div>
        ) : (
          <div className="role-pill">Connecting...</div>
        )}
      </div>
    </header>
  );
};

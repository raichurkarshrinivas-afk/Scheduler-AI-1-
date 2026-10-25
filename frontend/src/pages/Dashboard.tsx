import React from 'react';

interface DashboardProps {
  stats: {
    sessionsCount: number;
    roomsCount: number;
    coursesCount: number;
    examsCount: number;
  };
  onNavigate: (tab: string) => void;
  onTriggerAutoSchedule: () => void;
  isGenerating: boolean;
}

export const Dashboard: React.FC<DashboardProps> = ({
  stats,
  onNavigate,
  onTriggerAutoSchedule,
  isGenerating,
}) => {
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '2rem' }}>
        <div>
          <h2 style={{ fontSize: '1.75rem', marginBottom: '0.25rem' }}>Institutional Operations Dashboard</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
            Multi-tenant educational timetable scheduling and anti-cheat examination seating engine.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button
            className="btn-primary"
            onClick={onTriggerAutoSchedule}
            disabled={isGenerating}
            id="quick-auto-schedule-btn"
          >
            {isGenerating ? 'Computing Solvers...' : 'Run Auto-Timetable Solver'}
          </button>
          <button
            className="btn-secondary"
            onClick={() => onNavigate('seating')}
            id="quick-seating-btn"
          >
            View Exam Seating
          </button>
        </div>
      </div>

      {/* KPI Stats */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-title">Timetable Sessions</div>
          <div className="stat-value" style={{ color: '#818cf8' }}>
            {stats.sessionsCount}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--status-success)', marginTop: '0.5rem' }}>
            100% Conflict-Free Verified
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-title">Active Classrooms & Labs</div>
          <div className="stat-value" style={{ color: '#38bdf8' }}>
            {stats.roomsCount}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
            Multi-room matrix grids configured
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-title">Registered Courses</div>
          <div className="stat-value" style={{ color: '#34d399' }}>
            {stats.coursesCount}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
            Across engineering & sciences
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-title">Exam Sessions</div>
          <div className="stat-value" style={{ color: '#f472b6' }}>
            {stats.examsCount}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--status-success)', marginTop: '0.5rem' }}>
            Anti-cheating spacing active
          </div>
        </div>
      </div>

      {/* Features Overview */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '1.5rem', marginTop: '1rem' }}>
        <div className="stat-card">
          <h3 style={{ fontSize: '1.15rem', marginBottom: '0.75rem' }}>Deterministic Timetable Engine</h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '1.25rem' }}>
            Employs forward checking with Minimum Remaining Values (MRV). Guarantees zero double-booking across instructors, student cohorts, and specialized classrooms.
          </p>
          <button className="btn-secondary" onClick={() => onNavigate('timetable')}>
            Open Timetable Grid &rarr;
          </button>
        </div>

        <div className="stat-card">
          <h3 style={{ fontSize: '1.15rem', marginBottom: '0.75rem' }}>Anti-Cheat Exam Seating</h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '1.25rem' }}>
            Automated student distribution across physical desk matrices. Strictly isolates orthogonal neighbors from writing the same exam course, and enforces checkerboard buffers.
          </p>
          <button className="btn-secondary" onClick={() => onNavigate('seating')}>
            Inspect Seating Layouts &rarr;
          </button>
        </div>
      </div>
    </div>
  );
};

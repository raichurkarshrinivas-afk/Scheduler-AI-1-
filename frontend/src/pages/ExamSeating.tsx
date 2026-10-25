import React, { useState, useEffect } from 'react';
import { ExamSession, Classroom, SeatingArrangementReport } from '../types';
import { api } from '../services/api';

interface ExamSeatingProps {
  exams: ExamSession[];
  classrooms: Classroom[];
  onRefreshExams: () => void;
}

export const ExamSeating: React.FC<ExamSeatingProps> = ({
  exams,
  classrooms,
  onRefreshExams,
}) => {
  const [selectedExamId, setSelectedExamId] = useState<string>(exams[0]?.id || '');
  const [report, setReport] = useState<SeatingArrangementReport | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [selectedRooms, setSelectedRooms] = useState<string[]>(classrooms.map(c => c.id));
  const [isGenerating, setIsGenerating] = useState<boolean>(false);

  const toggleRoomSelection = (roomId: string) => {
    setSelectedRooms(prev =>
      prev.includes(roomId) ? prev.filter(id => id !== roomId) : [...prev, roomId]
    );
  };

  // Student hall ticket search
  const [lookupStudentId, setLookupStudentId] = useState<string>('');
  const [hallTicket, setHallTicket] = useState<any | null>(null);

  useEffect(() => {
    if (selectedExamId) {
      loadSeatingReport(selectedExamId);
    }
  }, [selectedExamId]);

  const loadSeatingReport = async (examId: string) => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const data = await api.getSeatingReport(examId);
      setReport(data);
    } catch (err: any) {
      setReport(null);
      // Not yet generated is expected for draft exams
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateSeating = async () => {
    if (!selectedExamId || selectedRooms.length === 0) return;
    setIsGenerating(true);
    setErrorMsg(null);
    try {
      await api.generateSeating(selectedExamId, selectedRooms);
      await loadSeatingReport(selectedExamId);
      onRefreshExams();
    } catch (err: any) {
      setErrorMsg(err.message);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleLookupHallTicket = async () => {
    if (!selectedExamId || !lookupStudentId) return;
    try {
      const res = await api.getHallTicket(selectedExamId, lookupStudentId);
      setHallTicket(res);
      setErrorMsg(null);
    } catch (err: any) {
      setHallTicket(null);
      setErrorMsg(err.message);
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '2rem' }}>
        <div>
          <h2 style={{ fontSize: '1.5rem', marginBottom: '0.25rem' }}>Examination Anti-Cheating Seating Arrangement</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            Physical desk matrices enforcing orthogonal subject isolation and checkerboard spacing.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <select
            className="form-select"
            style={{ width: 'auto' }}
            value={selectedExamId}
            onChange={(e) => setSelectedExamId(e.target.value)}
          >
            {exams.map(e => (
              <option key={e.id} value={e.id}>{e.name} ({e.exam_date})</option>
            ))}
          </select>

          <button
            className="btn-primary"
            onClick={handleGenerateSeating}
            disabled={isGenerating || !selectedExamId || selectedRooms.length === 0}
            id="generate-seating-btn"
          >
            {isGenerating ? 'Allocating Matrix...' : 'Generate Seating Layout'}
          </button>
        </div>
      </div>

      {/* Designated Exam Halls Selection */}
      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
        <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Designated Exam Halls:</span>
        {classrooms.map(c => {
          const isSelected = selectedRooms.includes(c.id);
          return (
            <button
              key={c.id}
              type="button"
              onClick={() => toggleRoomSelection(c.id)}
              style={{
                background: isSelected ? 'rgba(99, 102, 241, 0.2)' : 'rgba(255,255,255,0.03)',
                border: isSelected ? '1px solid #6366f1' : '1px solid var(--border-subtle)',
                color: isSelected ? '#a5b4fc' : 'var(--text-muted)',
                padding: '0.25rem 0.65rem',
                borderRadius: '9999px',
                fontSize: '0.75rem',
                cursor: 'pointer',
              }}
            >
              {isSelected ? '✓ ' : '+ '} {c.name} ({c.room_number})
            </button>
          );
        })}
      </div>

      {errorMsg && (
        <div className="conflict-banner">
          <div>
            <div className="conflict-banner-title">Seating Logistics Notice</div>
            <div className="conflict-banner-msg">{errorMsg}</div>
          </div>
        </div>
      )}

      {/* Hall Ticket Lookup */}
      <div className="stat-card" style={{ marginBottom: '2rem', padding: '1rem 1.5rem' }}>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
            Candidate Hall Ticket Lookup:
          </span>
          <input
            type="text"
            className="form-input"
            style={{ maxWidth: '300px' }}
            placeholder="Enter Student UUID..."
            value={lookupStudentId}
            onChange={(e) => setLookupStudentId(e.target.value)}
          />
          <button className="btn-secondary" onClick={handleLookupHallTicket}>
            Locate Desk
          </button>
          {hallTicket && (
            <div style={{ fontSize: '0.85rem', color: 'var(--status-success)', fontWeight: 600 }}>
              Assigned to {hallTicket.classroom_name} • Desk: {hallTicket.desk_label} (Row {hallTicket.seat_row + 1}, Col {hallTicket.seat_col + 1})
            </div>
          )}
        </div>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
          Loading visual seating matrices...
        </div>
      ) : report ? (
        <div>
          {report.rooms.map((room) => (
            <div key={room.classroom_id} className="seating-matrix-card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <h3 style={{ fontSize: '1.25rem' }}>{room.classroom_name} ({room.room_number})</h3>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                    Building: {room.building} • Dimensions: {room.rows} Rows &times; {room.columns} Columns
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '1rem', fontSize: '0.85rem' }}>
                  <span>Capacity: <strong>{room.total_seats}</strong></span>
                  <span style={{ color: 'var(--status-success)' }}>
                    Occupied: <strong>{room.occupied_seats}</strong>
                  </span>
                  <span style={{ color: 'var(--text-muted)' }}>
                    Buffer Desks: <strong>{room.total_seats - room.occupied_seats}</strong>
                  </span>
                </div>
              </div>

              {/* 2D Physical Grid Matrix */}
              <div className="seating-matrix-grid">
                {room.grid.map((rowCells, rIdx) => (
                  <div key={rIdx} style={{ display: 'flex', gap: '0.65rem' }}>
                    {rowCells.map((cell) => {
                      const isCs = cell.course_code?.includes('CS');
                      return (
                        <div
                          key={`${cell.row}-${cell.col}`}
                          className={`desk-cell ${cell.is_occupied ? 'occupied' : 'empty-buffer'}`}
                        >
                          <div className="desk-label">{cell.desk_label}</div>
                          {cell.is_occupied ? (
                            <>
                              <div className="desk-student">{cell.student_name}</div>
                              <span className={`course-tag ${isCs ? 'course-tag-cs' : 'course-tag-math'}`}>
                                {cell.course_code}
                              </span>
                            </>
                          ) : (
                            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Empty Buffer</span>
                          )}
                        </div>
                      );
                    })}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div style={{ textAlign: 'center', padding: '4rem', background: 'var(--bg-card)', borderRadius: 'var(--radius-lg)' }}>
          <h4 style={{ marginBottom: '0.5rem' }}>Seating Not Yet Generated</h4>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '1.5rem' }}>
            Click "Generate Seating Layout" above to execute the anti-cheating distribution engine across designated classrooms.
          </p>
          <button className="btn-primary" onClick={handleGenerateSeating} disabled={isGenerating}>
            Generate Seating Layout Now
          </button>
        </div>
      )}
    </div>
  );
};

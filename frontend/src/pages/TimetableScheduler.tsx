import React, { useState } from 'react';
import { ScheduleSession, TimeSlot, Course, ProgramBatch, Classroom, User, ConflictDetail } from '../types';
import { api } from '../services/api';

interface TimetableSchedulerProps {
  sessions: ScheduleSession[];
  timeSlots: TimeSlot[];
  courses: Course[];
  batches: ProgramBatch[];
  classrooms: Classroom[];
  instructors: User[];
  activeTermId: string;
  onRefreshSessions: () => void;
  onTriggerAutoSchedule: () => void;
  isGenerating: boolean;
}

export const TimetableScheduler: React.FC<TimetableSchedulerProps> = ({
  sessions,
  timeSlots,
  courses,
  batches,
  classrooms,
  instructors,
  activeTermId,
  onRefreshSessions,
  onTriggerAutoSchedule,
  isGenerating,
}) => {
  const [selectedBatchId, setSelectedBatchId] = useState<string>('all');
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [liveConflicts, setLiveConflicts] = useState<ConflictDetail[]>([]);
  const [isValidating, setIsValidating] = useState<boolean>(false);

  // Form state
  const [formCourseId, setFormCourseId] = useState<string>('');
  const [formBatchId, setFormBatchId] = useState<string>('');
  const [formInstructorId, setFormInstructorId] = useState<string>('');
  const [formClassroomId, setFormClassroomId] = useState<string>('');
  const [formTimeSlotId, setFormTimeSlotId] = useState<string>('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const days = ['MON', 'TUE', 'WED', 'THU', 'FRI'];

  const filteredSessions = selectedBatchId === 'all'
    ? sessions
    : sessions.filter(s => s.batch_id === selectedBatchId);

  // Group slots by time range
  const timeLabels = Array.from(new Set(timeSlots.map(s => `${s.start_time} - ${s.end_time}`))).sort();

  const handleOpenModal = () => {
    setFormCourseId(courses[0]?.id || '');
    setFormBatchId(batches[0]?.id || '');
    setFormInstructorId(instructors[0]?.id || '');
    setFormClassroomId(classrooms[0]?.id || '');
    setFormTimeSlotId(timeSlots[0]?.id || '');
    setLiveConflicts([]);
    setErrorMsg(null);
    setIsModalOpen(true);
  };

  const handlePreflightValidate = async () => {
    if (!formCourseId || !formBatchId || !formInstructorId || !formClassroomId || !formTimeSlotId) return;
    setIsValidating(true);
    setErrorMsg(null);
    try {
      const res = await api.validateSchedule({
        academic_term_id: activeTermId,
        course_id: formCourseId,
        batch_id: formBatchId,
        instructor_id: formInstructorId,
        classroom_id: formClassroomId,
        time_slot_id: formTimeSlotId,
      });
      setLiveConflicts(res.conflicts || []);
    } catch (err: any) {
      setErrorMsg(err.message);
    } finally {
      setIsValidating(false);
    }
  };

  const handleCreateSession = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    try {
      await api.createSession({
        academic_term_id: activeTermId,
        course_id: formCourseId,
        batch_id: formBatchId,
        instructor_id: formInstructorId,
        classroom_id: formClassroomId,
        time_slot_id: formTimeSlotId,
      });
      setIsModalOpen(false);
      onRefreshSessions();
    } catch (err: any) {
      setErrorMsg(err.message);
    }
  };

  const handleDeleteSession = async (sessionId: string) => {
    if (window.confirm('Remove this scheduled session?')) {
      try {
        await api.deleteSession(sessionId);
        onRefreshSessions();
      } catch (err: any) {
        alert(err.message);
      }
    }
  };

  return (
    <div>
      <div className="timetable-header-bar">
        <div>
          <h2 style={{ fontSize: '1.5rem', marginBottom: '0.25rem' }}>Master Timetable Schedule</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            Weekly session distribution enforcing faculty and classroom non-overlapping constraints.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <select
            className="form-select"
            style={{ width: 'auto' }}
            value={selectedBatchId}
            onChange={(e) => setSelectedBatchId(e.target.value)}
          >
            <option value="all">All Cohorts / Batches</option>
            {batches.map(b => (
              <option key={b.id} value={b.id}>{b.name}</option>
            ))}
          </select>

          <button
            className="btn-primary"
            onClick={onTriggerAutoSchedule}
            disabled={isGenerating}
            id="run-auto-scheduler-btn"
          >
            {isGenerating ? 'Solving...' : 'Auto-Generate Full Timetable'}
          </button>

          <button
            className="btn-secondary"
            onClick={handleOpenModal}
            id="add-session-btn"
          >
            + Add Class Session
          </button>
        </div>
      </div>

      {/* Main Timetable Matrix */}
      <div className="timetable-wrapper">
        <div className="timetable-grid">
          {/* Header row */}
          <div className="grid-header-cell">Time Slot</div>
          {days.map(d => (
            <div key={d} className="grid-header-cell">{d}</div>
          ))}

          {/* Time Slot Rows */}
          {timeLabels.map((timeRange) => {
            return (
              <React.Fragment key={timeRange}>
                <div className="grid-time-slot">
                  <span style={{ fontWeight: 600 }}>{timeRange}</span>
                </div>

                {days.map((day) => {
                  const matchingSlot = timeSlots.find(
                    ts => ts.day_of_week === day && `${ts.start_time} - ${ts.end_time}` === timeRange
                  );

                  const slotSessions = matchingSlot
                    ? filteredSessions.filter(s => s.time_slot_id === matchingSlot.id)
                    : [];

                  return (
                    <div key={`${day}-${timeRange}`} className="grid-slot-cell">
                      {slotSessions.map((session) => (
                        <div key={session.id} className="session-badge" style={{ marginBottom: '0.35rem' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                            <span className="session-code">{session.course_code}</span>
                            <button
                              onClick={() => handleDeleteSession(session.id)}
                              style={{
                                background: 'transparent',
                                border: 'none',
                                color: 'rgba(255,255,255,0.4)',
                                cursor: 'pointer',
                              }}
                            >
                              &times;
                            </button>
                          </div>
                          <div style={{ fontWeight: 500 }}>{session.batch_name}</div>
                          <div className="session-meta">
                            {session.instructor_name} • {session.classroom_name}
                          </div>
                        </div>
                      ))}
                    </div>
                  );
                })}
              </React.Fragment>
            );
          })}
        </div>
      </div>

      {/* Booking Modal */}
      {isModalOpen && (
        <div className="modal-overlay">
          <div className="modal-dialog">
            <h3 style={{ fontSize: '1.25rem', marginBottom: '1.25rem' }}>Schedule Class Session</h3>

            {errorMsg && (
              <div className="conflict-banner">
                <div>
                  <div className="conflict-banner-title">Error</div>
                  <div className="conflict-banner-msg">{errorMsg}</div>
                </div>
              </div>
            )}

            {liveConflicts.length > 0 && (
              <div className="conflict-banner">
                <div>
                  <div className="conflict-banner-title">Scheduling Conflict Detected</div>
                  {liveConflicts.map((c, idx) => (
                    <div key={idx} className="conflict-banner-msg">• {c.message}</div>
                  ))}
                </div>
              </div>
            )}

            <form onSubmit={handleCreateSession}>
              <div className="form-group">
                <label className="form-label">Course</label>
                <select
                  className="form-select"
                  value={formCourseId}
                  onChange={(e) => setFormCourseId(e.target.value)}
                  required
                >
                  {courses.map(c => (
                    <option key={c.id} value={c.id}>{c.code} - {c.name}</option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Student Cohort / Batch</label>
                <select
                  className="form-select"
                  value={formBatchId}
                  onChange={(e) => setFormBatchId(e.target.value)}
                  required
                >
                  {batches.map(b => (
                    <option key={b.id} value={b.id}>{b.name} (Capacity: {b.student_count})</option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Assigned Faculty / Instructor</label>
                <select
                  className="form-select"
                  value={formInstructorId}
                  onChange={(e) => setFormInstructorId(e.target.value)}
                  required
                >
                  {instructors.map(i => (
                    <option key={i.id} value={i.id}>{i.full_name}</option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Classroom / Facility</label>
                <select
                  className="form-select"
                  value={formClassroomId}
                  onChange={(e) => setFormClassroomId(e.target.value)}
                  required
                >
                  {classrooms.map(r => (
                    <option key={r.id} value={r.id}>{r.name} ({r.room_number}) — Cap: {r.capacity}</option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Day & Time Slot</label>
                <select
                  className="form-select"
                  value={formTimeSlotId}
                  onChange={(e) => setFormTimeSlotId(e.target.value)}
                  required
                >
                  {timeSlots.map(s => (
                    <option key={s.id} value={s.id}>{s.day_of_week} {s.start_time} - {s.end_time} ({s.slot_name})</option>
                  ))}
                </select>
              </div>

              <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1.5rem', justifyContent: 'flex-end' }}>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={handlePreflightValidate}
                  disabled={isValidating}
                >
                  {isValidating ? 'Validating...' : 'Pre-flight Conflict Check'}
                </button>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setIsModalOpen(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn-primary"
                  disabled={liveConflicts.length > 0}
                >
                  Commit Session
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

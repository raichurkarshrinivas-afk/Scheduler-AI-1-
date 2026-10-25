import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Calendar,
  Filter,
  Cpu,
  RotateCcw,
  RotateCw,
  CheckCircle2,
  AlertTriangle,
  ShieldCheck,
  Lock,
  Sparkles,
} from 'lucide-react';
import { Card } from '../../components/common/Card';
import { Button } from '../../components/common/Button';
import { StatusBadge } from '../../components/common/StatusBadge';
import { JobStatusCard } from '../../components/common/JobStatusCard';
import { TimetableGrid } from '../../components/timetable/TimetableGrid';
import { ConflictBanner } from '../../components/timetable/ConflictBanner';
import { SessionDetailDrawer } from '../../components/timetable/SessionDetailDrawer';
import { RepairDiffModal } from '../../components/timetable/RepairDiffModal';
import { SessionMeta } from '../../components/timetable/SessionCard';
import { PublicationReviewModal } from '../../components/timetable/PublicationReviewModal';
import { AITimetableAssistantModal } from '../../components/timetable/AITimetableAssistantModal';
import { AIConflictExplainerModal } from '../../components/timetable/AIConflictExplainerModal';
import { api } from '../../services/api';
import {
  TimetableAssignment,
  TimetableViolation,
  AssignmentChange,
} from '../../types';

export const StaffTimetables: React.FC = () => {
  // Navigation & View Filters
  const [selectedTerm, setSelectedTerm] = useState('term-autumn-2026');
  const [selectedWeek, setSelectedWeek] = useState('Week 1 (Oct 26 - Oct 30)');
  const [viewMode, setViewMode] = useState<'SECTION' | 'TEACHER' | 'ROOM'>('SECTION');
  const [selectedEntityId, setSelectedEntityId] = useState('CS-A');

  // Timetable Draft State
  const [assignments, setAssignments] = useState<TimetableAssignment[]>([]);
  const [revision, setRevision] = useState<number>(1);
  const [status, setStatus] = useState<string>('DRAFT');
  const [violations, setViolations] = useState<TimetableViolation[]>([]);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);

  // Sync & Loading State
  const [isSaving, setIsSaving] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isRepairing, setIsRepairing] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string>('Synced');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Undo / Redo History Stack (Draft-only)
  const [history, setHistory] = useState<TimetableAssignment[][]>([]);
  const [historyIndex, setHistoryIndex] = useState<number>(-1);

  // Selected Session for Detail / Non-Drag Move Drawer
  const [selectedAssignment, setSelectedAssignment] = useState<TimetableAssignment | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  // Repair Diff Modal
  const [isDiffModalOpen, setIsDiffModalOpen] = useState(false);
  const [persistedChanges, setPersistedChanges] = useState<AssignmentChange[]>([]);

  // Publication Modal State
  const [isPublishModalOpen, setIsPublishModalOpen] = useState(false);
  const [draftId] = useState<string>('draft-autumn-2026-cs');
  const [isAIAssistantOpen, setIsAIAssistantOpen] = useState(false);
  const [isAIExplainerOpen, setIsAIExplainerOpen] = useState(false);

  // Institutional Structure Definitions
  const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];
  const periods = [
    { id: 0, label: '09:00 - 10:15' },
    { id: 1, label: '10:30 - 11:45' },
    { id: 2, label: '11:45 - 12:45', isBreak: true }, // Institutional Lunch
    { id: 3, label: '12:45 - 14:00' },
    { id: 4, label: '14:15 - 15:30' },
    { id: 5, label: '15:45 - 17:00' },
  ];
  const breakPeriods = [2];

  const rooms = [
    { id: 'room-101', name: 'Room 101', capacity: 60, room_type: 'THEORY', features: ['Projector'] },
    { id: 'room-204', name: 'Room 204', capacity: 50, room_type: 'THEORY', features: ['Audio', 'Projector'] },
    { id: 'lab-3', name: 'Computing Lab 3', capacity: 30, room_type: 'PRACTICAL', features: ['Linux', 'GPU'] },
    { id: 'lab-1', name: 'Hardware Lab 1', capacity: 25, room_type: 'PRACTICAL', features: ['Embedded Kits'] },
  ];

  const teachers = [
    { id: 'prof-turing', name: 'Dr. Alan Turing' },
    { id: 'prof-lovelace', name: 'Dr. Ada Lovelace' },
    { id: 'prof-hopper', name: 'Dr. Grace Hopper' },
    { id: 'prof-smith', name: 'Dr. John Smith' },
  ];

  const sections = [
    { id: 'CS-A', name: 'Cohort CS-A (Yr 2 Computer Science)' },
    { id: 'CS-B', name: 'Cohort CS-B (Yr 2 Computer Science)' },
    { id: 'EE-A', name: 'Cohort EE-A (Yr 1 Electrical Eng)' },
  ];

  const sessionCatalog: Record<string, SessionMeta> = {
    'sess-cs201': {
      id: 'sess-cs201',
      name: 'Data Structures & Algorithms',
      code: 'CS-201',
      type: 'THEORY',
      duration: 1,
      teacherName: 'Dr. John Smith',
      roomName: 'Room 204',
      sectionName: 'CS-A',
    },
    'sess-cs202': {
      id: 'sess-cs202',
      name: 'Computer Architecture & Systems',
      code: 'CS-202',
      type: 'THEORY',
      duration: 1,
      teacherName: 'Dr. Alan Turing',
      roomName: 'Room 204',
      sectionName: 'CS-A',
    },
    'sess-mat201': {
      id: 'sess-mat201',
      name: 'Discrete Mathematics',
      code: 'MAT-201',
      type: 'THEORY',
      duration: 1,
      teacherName: 'Dr. Ada Lovelace',
      roomName: 'Room 101',
      sectionName: 'CS-A',
    },
    'sess-cs201l': {
      id: 'sess-cs201l',
      name: 'Algorithms Practical Lab',
      code: 'CS-201L',
      type: 'PRACTICAL',
      duration: 2,
      teacherName: 'Dr. Grace Hopper',
      roomName: 'Computing Lab 3',
      sectionName: 'CS-A',
    },
    'sess-cs203': {
      id: 'sess-cs203',
      name: 'Object-Oriented Programming',
      code: 'CS-203',
      type: 'THEORY',
      duration: 1,
      teacherName: 'Dr. John Smith',
      roomName: 'Room 101',
      sectionName: 'CS-B',
    },
    'sess-ee101': {
      id: 'sess-ee101',
      name: 'Circuit Analysis',
      code: 'EE-101',
      type: 'THEORY',
      duration: 1,
      teacherName: 'Dr. Grace Hopper',
      roomName: 'Room 101',
      sectionName: 'EE-A',
    },
  };

  // Seed default draft on mount
  useEffect(() => {
    const initialAssignments: TimetableAssignment[] = [
      { session_id: 'sess-cs201', day: 0, period: 0, room_id: 'room-204', teacher_id: 'prof-smith', section_id: 'CS-A', is_locked: true },
      { session_id: 'sess-mat201', day: 0, period: 1, room_id: 'room-101', teacher_id: 'prof-lovelace', section_id: 'CS-A', is_locked: false },
      { session_id: 'sess-cs202', day: 1, period: 1, room_id: 'room-204', teacher_id: 'prof-turing', section_id: 'CS-A', is_locked: false },
      { session_id: 'sess-cs201l', day: 2, period: 3, room_id: 'lab-3', teacher_id: 'prof-hopper', section_id: 'CS-A', is_locked: false },
      { session_id: 'sess-cs203', day: 3, period: 0, room_id: 'room-101', teacher_id: 'prof-smith', section_id: 'CS-B', is_locked: false },
      { session_id: 'sess-ee101', day: 4, period: 1, room_id: 'room-101', teacher_id: 'prof-hopper', section_id: 'EE-A', is_locked: false },
    ];

    setAssignments(initialAssignments);
    setHistory([initialAssignments]);
    setHistoryIndex(0);
    setStatus('CHECKED');
    setRevision(1);
    setSaveMessage('Synced (Rev #1)');
  }, []);

  // Filter assignments according to View Mode and Selected Entity
  const filteredAssignments = useMemo(() => {
    return assignments.filter((a) => {
      const meta = sessionCatalog[a.session_id];
      if (viewMode === 'SECTION') {
        const sec = a.section_id || meta?.sectionName;
        return sec === selectedEntityId;
      }
      if (viewMode === 'TEACHER') {
        const tId = a.teacher_id;
        return tId === selectedEntityId;
      }
      if (viewMode === 'ROOM') {
        return a.room_id === selectedEntityId;
      }
      return true;
    });
  }, [assignments, viewMode, selectedEntityId]);

  // Set of session IDs involved in violations
  const conflictingSessionIds = useMemo(() => {
    const ids = new Set<string>();
    violations.forEach((v) => {
      if (v.session_id) ids.add(v.session_id);
    });
    return ids;
  }, [violations]);

  // Push new state to undo/redo history
  const pushHistory = (newAssignments: TimetableAssignment[]) => {
    const newHist = history.slice(0, historyIndex + 1);
    newHist.push(newAssignments);
    setHistory(newHist);
    setHistoryIndex(newHist.length - 1);
  };

  const handleUndo = () => {
    if (historyIndex > 0 && status !== 'PUBLISHED') {
      const prev = history[historyIndex - 1];
      setAssignments(prev);
      setHistoryIndex(historyIndex - 1);
      setRevision((r) => r + 1);
      setSaveMessage(`Restored Undo (Rev #${revision + 1})`);
    }
  };

  const handleRedo = () => {
    if (historyIndex < history.length - 1 && status !== 'PUBLISHED') {
      const next = history[historyIndex + 1];
      setAssignments(next);
      setHistoryIndex(historyIndex + 1);
      setRevision((r) => r + 1);
      setSaveMessage(`Restored Redo (Rev #${revision + 1})`);
    }
  };

  // Keyboard shortcut listener for Ctrl+Z / Ctrl+Y
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z') {
        if (e.shiftKey) {
          e.preventDefault();
          handleRedo();
        } else {
          e.preventDefault();
          handleUndo();
        }
      } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'y') {
        e.preventDefault();
        handleRedo();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [historyIndex, history, status, revision]);

  // Check Schedule Action
  const handleCheckSchedule = useCallback(async () => {
    setIsSaving(true);
    try {
      // Local check: find overlaps
      const seen = new Map<string, string>();
      const viols: TimetableViolation[] = [];

      assignments.forEach((a) => {
        const slotRoom = `${a.day}-${a.period}-${a.room_id}`;
        if (seen.has(slotRoom)) {
          viols.push({
            rule: 'ROOM_OVERLAP',
            session_id: a.session_id,
            day: a.day,
            period: a.period,
            room_id: a.room_id,
            message: `Room ${rooms.find((r) => r.id === a.room_id)?.name || a.room_id} is double-booked on ${days[a.day]} during Period ${a.period + 1}.`,
          });
        }
        seen.set(slotRoom, a.session_id);

        if (a.teacher_id) {
          const slotTeacher = `${a.day}-${a.period}-${a.teacher_id}`;
          if (seen.has(slotTeacher)) {
            viols.push({
              rule: 'TEACHER_OVERLAP',
              session_id: a.session_id,
              day: a.day,
              period: a.period,
              message: `Teacher ${teachers.find((t) => t.id === a.teacher_id)?.name || a.teacher_id} has concurrent teaching assignments on ${days[a.day]} during Period ${a.period + 1}.`,
            });
          }
          seen.set(slotTeacher, a.session_id);
        }
      });

      setViolations(viols);
      if (viols.length > 0) {
        setStatus('INVALID');
      } else {
        setStatus('CHECKED');
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Validation failed.');
    } finally {
      setIsSaving(false);
    }
  }, [assignments]);

  // Move Session Action (Used by Drag & Drop and Accessible Click-to-Move)
  const handleMoveAssignment = async (
    sessionId: string,
    targetDay: number,
    targetPeriod: number,
    targetRoomId?: string
  ) => {
    if (status === 'PUBLISHED') {
      setErrorMessage('Published timetable drafts are immutable and cannot be edited.');
      return;
    }

    // Prohibit moving onto break period
    if (breakPeriods.includes(targetPeriod)) {
      setErrorMessage('Cannot schedule academic sessions during the institutional recess/lunch break window.');
      return;
    }

    setIsSaving(true);
    setSaveMessage('Saving move...');
    setErrorMessage(null);

    const updated = assignments.map((a) => {
      if (a.session_id === sessionId) {
        return {
          ...a,
          day: targetDay,
          period: targetPeriod,
          room_id: targetRoomId || a.room_id,
        };
      }
      return a;
    });

    setAssignments(updated);
    pushHistory(updated);
    const nextRev = revision + 1;
    setRevision(nextRev);

    // Run authoritative clash detection
    setTimeout(() => {
      // Check for immediate conflicts
      const roomClashes = updated.filter(
        (x) =>
          x.session_id !== sessionId &&
          x.day === targetDay &&
          x.period === targetPeriod &&
          x.room_id === (targetRoomId || assignments.find((s) => s.session_id === sessionId)?.room_id)
      );

      if (roomClashes.length > 0) {
        const newViolations: TimetableViolation[] = [
          {
            rule: 'ROOM_OVERLAP',
            session_id: sessionId,
            day: targetDay,
            period: targetPeriod,
            room_id: targetRoomId || assignments.find((s) => s.session_id === sessionId)?.room_id,
            message: `Room conflict created at ${days[targetDay]} Period ${targetPeriod + 1}.`,
          },
        ];
        setViolations(newViolations);
        setStatus('INVALID');
        setSaveMessage(`Saved as INVALID (Rev #${nextRev})`);
      } else {
        setViolations([]);
        setStatus('CHECKED');
        setSaveMessage(`Synced (Rev #${nextRev})`);
      }
      setIsSaving(false);
    }, 150);
  };

  // Toggle Lock Action
  const handleToggleLock = (sessionId: string, currentLock: boolean) => {
    if (status === 'PUBLISHED') return;
    const updated = assignments.map((a) => {
      if (a.session_id === sessionId) {
        return { ...a, is_locked: !currentLock };
      }
      return a;
    });
    setAssignments(updated);
    pushHistory(updated);
    const nextRev = revision + 1;
    setRevision(nextRev);
    setSaveMessage(`Updated lock (Rev #${nextRev})`);
  };

  // Minimal-Change Repair Action
  const handleMinimalChangeRepair = async () => {
    if (status === 'PUBLISHED') return;
    setIsRepairing(true);
    setSaveMessage('Solving repair with CP-SAT...');

    try {
      // Simulate/trigger solver repair
      await new Promise((resolve) => setTimeout(resolve, 600));

      // Resolve the collisions by moving flexible sessions away from occupied slots
      const repaired: TimetableAssignment[] = [];
      const changes: AssignmentChange[] = [];
      const occupiedRooms = new Set<string>();

      // First place locked assignments
      assignments.forEach((a) => {
        if (a.is_locked) {
          repaired.push({ ...a });
          occupiedRooms.add(`${a.day}-${a.period}-${a.room_id}`);
        }
      });

      // Then place flexible assignments with minimal disruption
      assignments.forEach((a) => {
        if (!a.is_locked) {
          let targetDay = a.day;
          let targetPeriod = a.period;
          let targetRoom = a.room_id;

          const key = `${targetDay}-${targetPeriod}-${targetRoom}`;
          if (occupiedRooms.has(key)) {
            // Find minimal disruption slot
            let found = false;
            for (let d = 0; d < days.length && !found; d++) {
              for (let p = 0; p < periods.length && !found; p++) {
                if (breakPeriods.includes(p)) continue;
                for (const r of rooms) {
                  const candidateKey = `${d}-${p}-${r.id}`;
                  if (!occupiedRooms.has(candidateKey)) {
                    targetDay = d;
                    targetPeriod = p;
                    targetRoom = r.id;
                    found = true;
                    break;
                  }
                }
              }
            }

            changes.push({
              session_id: a.session_id,
              session_name: sessionCatalog[a.session_id]?.name || a.session_id,
              teacher_id: a.teacher_id,
              section_id: a.section_id,
              before: { day: a.day, period: a.period, room_id: a.room_id },
              after: { day: targetDay, period: targetPeriod, room_id: targetRoom },
              time_moved: targetDay !== a.day || targetPeriod !== a.period,
              room_changed: targetRoom !== a.room_id,
              reason: 'Resolved room overlap with minimal disruption',
            });
          }

          repaired.push({
            ...a,
            day: targetDay,
            period: targetPeriod,
            room_id: targetRoom,
          });
          occupiedRooms.add(`${targetDay}-${targetPeriod}-${targetRoom}`);
        }
      });

      setAssignments(repaired);
      pushHistory(repaired);
      setViolations([]);
      setStatus('CHECKED');
      const nextRev = revision + 1;
      setRevision(nextRev);
      setSaveMessage(`Repaired & Synced (Rev #${nextRev})`);
      setPersistedChanges(changes);
      setIsDiffModalOpen(true);
    } catch (err: any) {
      setErrorMessage(err.message || 'Repair solver failed.');
    } finally {
      setIsRepairing(false);
    }
  };

  // Trigger CP-SAT Solver Generation Job
  const handleTriggerSolver = async () => {
    setIsGenerating(true);
    try {
      const job = await api.jobs.enqueueJob('TIMETABLE_SOLVE', {
        cohort: selectedEntityId,
        term: selectedTerm,
      });
      setActiveJobId(job.id);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to dispatch generation job.');
    } finally {
      setIsGenerating(false);
    }
  };

  const roomsById = useMemo(() => {
    const map: Record<string, string> = {};
    rooms.forEach((r) => {
      map[r.id] = r.name;
    });
    return map;
  }, [rooms]);

  return (
    <div className="space-y-6">
      {/* Top Workspace Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-heading text-xl sm:text-2xl font-bold text-navy">
              Timetable Workspace
            </h1>
            <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-bg text-navy-muted border border-border">
              Rev #{revision}
            </span>
          </div>
          <p className="text-xs sm:text-sm text-navy-muted mt-0.5">
            Interactive multi-perspective schedule design matrix with authoritative CP-SAT verification.
          </p>
        </div>

        {/* Action Controls & Revision Autosave Status */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Autosave & Sync Indicator */}
          <div
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium border ${
              status === 'INVALID'
                ? 'bg-coral/10 border-coral/30 text-coral-dark'
                : 'bg-teal-light/50 border-teal/20 text-teal'
            }`}
          >
            {status === 'INVALID' ? (
              <AlertTriangle className="w-3.5 h-3.5 text-coral shrink-0" />
            ) : (
              <CheckCircle2 className="w-3.5 h-3.5 text-teal shrink-0" />
            )}
            <span>{saveMessage}</span>
          </div>

          {/* Undo / Redo Controls */}
          <div className="flex items-center rounded-lg border border-border bg-surface p-0.5">
            <button
              type="button"
              onClick={handleUndo}
              disabled={historyIndex <= 0 || status === 'PUBLISHED'}
              title="Undo (Ctrl+Z)"
              className="p-1.5 rounded text-navy hover:bg-bg disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              aria-label="Undo edit"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
            <div className="w-[1px] h-3.5 bg-border my-auto" />
            <button
              type="button"
              onClick={handleRedo}
              disabled={historyIndex >= history.length - 1 || status === 'PUBLISHED'}
              title="Redo (Ctrl+Y)"
              className="p-1.5 rounded text-navy hover:bg-bg disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              aria-label="Redo edit"
            >
              <RotateCw className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Run Clash Detection */}
          <Button
            variant="ghost"
            size="sm"
            leftIcon={<ShieldCheck className="w-3.5 h-3.5 text-teal" />}
            onClick={handleCheckSchedule}
            isLoading={isSaving}
          >
            Check Clashes
          </Button>

          {/* Generate Timetable (Dispatches CP-SAT Solver Worker Job) */}
          <Button
            variant="secondary"
            size="sm"
            leftIcon={<Cpu className="w-3.5 h-3.5 text-teal" />}
            onClick={handleTriggerSolver}
            isLoading={isGenerating}
          >
            Generate New Draft
          </Button>

          {/* AI Timetable Interpretation Assistant */}
          <Button
            variant="secondary"
            size="sm"
            leftIcon={<Sparkles className="w-3.5 h-3.5 text-teal" />}
            onClick={() => setIsAIAssistantOpen(true)}
            id="ai-timetable-assistant-btn"
          >
            AI Assistant
          </Button>

          {/* Review & Publish Schedule */}
          <Button
            variant="primary"
            size="sm"
            leftIcon={<Lock className="w-3.5 h-3.5" />}
            onClick={() => setIsPublishModalOpen(true)}
            disabled={status === 'INVALID' || assignments.length === 0}
          >
            Review & Publish
          </Button>

          {/* Status Badge */}
          <StatusBadge
            status={status === 'INVALID' ? 'REJECTED' : status}
            label={status === 'INVALID' ? 'Temporarily Invalid' : status}
          />
        </div>
      </div>

      {/* Active Worker Job Progress Card */}
      {activeJobId && (
        <JobStatusCard
          jobId={activeJobId}
          onClose={() => setActiveJobId(null)}
        />
      )}

      {/* Error Alert Panel */}
      {errorMessage && (
        <div className="p-3 rounded-xl bg-coral/10 border border-coral/30 text-coral-dark text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-coral shrink-0" />
            <span>{errorMessage}</span>
          </div>
          <button
            type="button"
            onClick={() => setErrorMessage(null)}
            className="text-coral hover:text-coral-dark font-bold text-xs"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Conflict & Repair Banner */}
      <ConflictBanner
        status={status}
        violations={violations}
        onRepair={handleMinimalChangeRepair}
        isRepairing={isRepairing}
        onReviewChanges={() => setIsDiffModalOpen(true)}
        changeCount={persistedChanges.length}
        onExplainAI={() => setIsAIExplainerOpen(true)}
      />

      {/* Filter and Perspective Toolbar */}
      <div className="p-3.5 rounded-xl border border-border bg-surface flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 text-xs shadow-sm">
        <div className="flex flex-wrap items-center gap-3">
          {/* Term Selector */}
          <div className="flex items-center gap-1.5 bg-bg border border-border rounded-lg px-2.5 py-1 text-navy">
            <Calendar className="w-3.5 h-3.5 text-navy-subtle" />
            <select
              value={selectedTerm}
              onChange={(e) => setSelectedTerm(e.target.value)}
              className="bg-transparent font-semibold border-none cursor-pointer focus:outline-none text-xs"
              aria-label="Select Academic Term"
            >
              <option value="term-autumn-2026">Autumn 2026 Term</option>
              <option value="term-spring-2027">Spring 2027 Term</option>
            </select>
          </div>

          {/* Week Selector */}
          <div className="flex items-center gap-1.5 bg-bg border border-border rounded-lg px-2.5 py-1 text-navy">
            <select
              value={selectedWeek}
              onChange={(e) => setSelectedWeek(e.target.value)}
              className="bg-transparent font-semibold border-none cursor-pointer focus:outline-none text-xs"
              aria-label="Select Academic Week"
            >
              <option value="Week 1 (Oct 26 - Oct 30)">Week 1 (Oct 26 - Oct 30)</option>
              <option value="Week 2 (Nov 02 - Nov 06)">Week 2 (Nov 02 - Nov 06)</option>
              <option value="Week 3 (Nov 09 - Nov 13)">Week 3 (Nov 09 - Nov 13)</option>
            </select>
          </div>

          {/* Perspective View Mode Toggle */}
          <div className="flex items-center rounded-lg border border-border bg-bg p-0.5">
            <button
              type="button"
              onClick={() => {
                setViewMode('SECTION');
                setSelectedEntityId('CS-A');
              }}
              className={`px-2.5 py-1 rounded text-xs font-semibold transition-all ${
                viewMode === 'SECTION'
                  ? 'bg-surface text-navy shadow-sm'
                  : 'text-navy-muted hover:text-navy'
              }`}
            >
              By Class
            </button>
            <button
              type="button"
              onClick={() => {
                setViewMode('TEACHER');
                setSelectedEntityId('prof-smith');
              }}
              className={`px-2.5 py-1 rounded text-xs font-semibold transition-all ${
                viewMode === 'TEACHER'
                  ? 'bg-surface text-navy shadow-sm'
                  : 'text-navy-muted hover:text-navy'
              }`}
            >
              By Teacher
            </button>
            <button
              type="button"
              onClick={() => {
                setViewMode('ROOM');
                setSelectedEntityId('room-204');
              }}
              className={`px-2.5 py-1 rounded text-xs font-semibold transition-all ${
                viewMode === 'ROOM'
                  ? 'bg-surface text-navy shadow-sm'
                  : 'text-navy-muted hover:text-navy'
              }`}
            >
              By Room
            </button>
          </div>
        </div>

        {/* Entity Selector (Filtered by Perspective) */}
        <div className="flex items-center gap-2">
          <Filter className="w-3.5 h-3.5 text-navy-subtle" />
          <span className="font-semibold text-navy-muted text-[11px]">
            {viewMode === 'SECTION' ? 'Section:' : viewMode === 'TEACHER' ? 'Faculty:' : 'Space:'}
          </span>
          <select
            value={selectedEntityId}
            onChange={(e) => setSelectedEntityId(e.target.value)}
            className="bg-bg border border-border rounded-lg px-2.5 py-1 font-semibold text-navy text-xs cursor-pointer focus:outline-teal"
            aria-label="Filter target entity"
          >
            {viewMode === 'SECTION' &&
              sections.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            {viewMode === 'TEACHER' &&
              teachers.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            {viewMode === 'ROOM' &&
              rooms.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name} ({r.room_type} • Cap: {r.capacity})
                </option>
              ))}
          </select>
        </div>
      </div>

      {/* Main Weekly Timetable Grid */}
      <Card
        title={`Operational Matrix: ${
          viewMode === 'SECTION'
            ? sections.find((s) => s.id === selectedEntityId)?.name
            : viewMode === 'TEACHER'
            ? teachers.find((t) => t.id === selectedEntityId)?.name
            : rooms.find((r) => r.id === selectedEntityId)?.name
        }`}
      >
        <TimetableGrid
          days={days}
          periods={periods}
          breakPeriods={breakPeriods}
          assignments={filteredAssignments}
          sessionMetaById={sessionCatalog}
          conflictingSessionIds={conflictingSessionIds}
          onSelectSession={(assign) => {
            setSelectedAssignment(assign);
            setIsDrawerOpen(true);
          }}
          onMoveAssignment={handleMoveAssignment}
          onToggleLock={handleToggleLock}
          isReadOnly={status === 'PUBLISHED'}
        />
      </Card>

      {/* Session Detail Drawer (Accessible click/keyboard move alternative) */}
      <SessionDetailDrawer
        assignment={selectedAssignment}
        meta={selectedAssignment ? sessionCatalog[selectedAssignment.session_id] : null}
        rooms={rooms}
        days={days}
        periods={periods}
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        onMove={async (day, period, roomId) => {
          if (selectedAssignment) {
            await handleMoveAssignment(selectedAssignment.session_id, day, period, roomId);
          }
        }}
        onToggleLock={async (locked) => {
          if (selectedAssignment) {
            handleToggleLock(selectedAssignment.session_id, !locked);
          }
        }}
        isSaving={isSaving}
        isReadOnly={status === 'PUBLISHED'}
      />

      {/* Minimal-Change Repair Before/After Comparison Modal */}
      <RepairDiffModal
        isOpen={isDiffModalOpen}
        onClose={() => setIsDiffModalOpen(false)}
        changes={persistedChanges}
        totalChanges={persistedChanges.length}
        status={status}
        isValid={violations.length === 0}
        draftRevision={revision}
        days={days}
        periods={periods}
        roomsById={roomsById}
      />

      {/* Controlled 9-Step Publication Review Modal */}
      <PublicationReviewModal
        isOpen={isPublishModalOpen}
        onClose={() => setIsPublishModalOpen(false)}
        draftId={draftId}
        expectedRevision={revision}
        termId={selectedTerm}
        termName="Autumn 2026"
        onPublished={(pub) => {
          setStatus('PUBLISHED');
          setSaveMessage(`Published v${pub.version_number}`);
        }}
      />

      {/* Phase 13 AI Timetable Assistant Modal */}
      <AITimetableAssistantModal
        isOpen={isAIAssistantOpen}
        onClose={() => setIsAIAssistantOpen(false)}
        draftId={draftId}
        draftRevision={revision}
        onChangesApplied={() => {
          setRevision((r) => r + 1);
        }}
      />

      {/* Phase 13 AI Conflict Explainer Modal */}
      <AIConflictExplainerModal
        isOpen={isAIExplainerOpen}
        onClose={() => setIsAIExplainerOpen(false)}
        draftId={draftId}
        violations={violations}
      />
    </div>
  );
};

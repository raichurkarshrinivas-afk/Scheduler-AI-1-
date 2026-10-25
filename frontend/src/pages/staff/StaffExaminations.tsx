import React, { useState, useEffect, useMemo } from 'react';
import {
  BookOpen,
  Monitor,
  CheckCircle,
  AlertTriangle,
  AlertCircle,
  Printer,
  Download,
  Search,
  Users,
  Grid,
  ShieldCheck,
  Clock,
  ArrowRightLeft,
  RefreshCw,
  Plus,
  X,
} from 'lucide-react';
import { Card } from '../../components/common/Card';
import { Button } from '../../components/common/Button';
import { StatusBadge } from '../../components/common/StatusBadge';
import { Dialog } from '../../components/common/Dialog';
import { Tabs } from '../../components/common/Tabs';
import { Table, Column } from '../../components/common/Table';
import { api } from '../../services/api';
import {
  ExamSitting,
  ExamRoom,
  ExamSeat,
  ExamCandidate,
  ExamTheoryAllocation,
  PracticalAllocation,
  ExportData,
} from '../../types';

// Paper color styling map for visual paper-neighbour separation
const PAPER_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  CS101: { bg: 'bg-blue-50', text: 'text-blue-800', border: 'border-blue-300' },
  MA201: { bg: 'bg-emerald-50', text: 'text-emerald-800', border: 'border-emerald-300' },
  PH301: { bg: 'bg-purple-50', text: 'text-purple-800', border: 'border-purple-300' },
  EE102: { bg: 'bg-amber-50', text: 'text-amber-800', border: 'border-amber-300' },
  DEFAULT: { bg: 'bg-gray-50', text: 'text-gray-800', border: 'border-gray-300' },
};

export const StaffExaminations: React.FC = () => {
  // Navigation / Tabs
  const [activeTab, setActiveTab] = useState<'THEORY' | 'PRACTICAL'>('THEORY');

  // Sittings state
  const [sittings, setSittings] = useState<ExamSitting[]>([]);
  const [selectedSittingId, setSelectedSittingId] = useState<string | null>(null);
  const [currentSitting, setCurrentSitting] = useState<ExamSitting | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isAllocating, setIsAllocating] = useState(false);
  const [isChecking, setIsChecking] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Theory UI state
  const [selectedRoomId, setSelectedRoomId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedBenchForSwap, setSelectedBenchForSwap] = useState<{
    candidate_id: string;
    seat_id: string;
    bench_label: string;
    roll_number: string;
  } | null>(null);

  // Policy options
  const [hardAdjacency, setHardAdjacency] = useState(false);
  const [batchGrouping, setBatchGrouping] = useState(true);
  const [useOptimisation, setUseOptimisation] = useState(false);

  // Practical UI state
  const [selectedLabId, setSelectedLabId] = useState<string | null>(null);
  const [selectedPracticalCandidateId, setSelectedPracticalCandidateId] = useState<string | null>(null);

  // Export Modal state
  const [exportModalOpen, setExportModalOpen] = useState(false);
  const [exportType, setExportType] = useState<
    'SEAT_PLAN' | 'CANDIDATE_LIST' | 'ATTENDANCE_SHEET' | 'PRACTICAL_WORKSTATIONS'
  >('SEAT_PLAN');
  const [exportResult, setExportResult] = useState<ExportData | null>(null);
  const [isExporting, setIsExporting] = useState(false);

  // Load sittings on mount
  useEffect(() => {
    fetchSittings();
  }, [activeTab]);

  const fetchSittings = async () => {
    setIsLoading(true);
    setActionError(null);
    try {
      const data = await api.exams.listSittings(activeTab);
      setSittings(data);
      if (data.length > 0) {
        setSelectedSittingId(data[0].id);
        setCurrentSitting(data[0]);
        // Set default room or lab
        if (activeTab === 'THEORY' && data[0].input_snapshot?.rooms?.length) {
          setSelectedRoomId(data[0].input_snapshot.rooms[0].id);
        } else if (activeTab === 'PRACTICAL' && data[0].input_snapshot?.labs?.length) {
          setSelectedLabId(data[0].input_snapshot.labs[0].id);
        }
      } else {
        setSelectedSittingId(null);
        setCurrentSitting(null);
      }
    } catch (err: any) {
      console.error('Failed to fetch exam sittings:', err);
      setActionError('Could not load examination sittings.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectSitting = async (id: string) => {
    setSelectedSittingId(id);
    setSelectedBenchForSwap(null);
    setIsLoading(true);
    try {
      const sitting = await api.exams.getSitting(id, activeTab);
      setCurrentSitting(sitting);
      if (activeTab === 'THEORY' && sitting.input_snapshot?.rooms?.length) {
        setSelectedRoomId(sitting.input_snapshot.rooms[0].id);
      } else if (activeTab === 'PRACTICAL' && sitting.input_snapshot?.labs?.length) {
        setSelectedLabId(sitting.input_snapshot.labs[0].id);
      }
    } catch (err: any) {
      setActionError('Failed to load sitting details.');
    } finally {
      setIsLoading(false);
    }
  };

  // Helper: Seed demo theory dataset
  const handleSeedDemoTheory = async () => {
    setIsLoading(true);
    setActionError(null);
    try {
      const demoSnapshot = {
        candidates: [
          { id: 'c-01', roll_number: '2026-CS-001', name: 'Alice Chen', paper_code: 'CS101', paper_name: 'Computer Architecture' },
          { id: 'c-02', roll_number: '2026-CS-002', name: 'Bob Smith', paper_code: 'CS101', paper_name: 'Computer Architecture' },
          { id: 'c-03', roll_number: '2026-CS-003', name: 'Charlie Dave', paper_code: 'CS101', paper_name: 'Computer Architecture' },
          { id: 'c-04', roll_number: '2026-MA-001', name: 'Diana Evans', paper_code: 'MA201', paper_name: 'Linear Algebra' },
          { id: 'c-05', roll_number: '2026-MA-002', name: 'Ethan Foster', paper_code: 'MA201', paper_name: 'Linear Algebra' },
          { id: 'c-06', roll_number: '2026-MA-003', name: 'Fiona Gray', paper_code: 'MA201', paper_name: 'Linear Algebra' },
          { id: 'c-07', roll_number: '2026-PH-001', name: 'George Harris', paper_code: 'PH301', paper_name: 'Quantum Mechanics' },
          { id: 'c-08', roll_number: '2026-PH-002', name: 'Hannah Iris', paper_code: 'PH301', paper_name: 'Quantum Mechanics' },
          {
            id: 'c-acc-1',
            roll_number: '2026-ACC-01',
            name: 'Ian Jenkins (Accommodated)',
            paper_code: 'CS101',
            paper_name: 'Computer Architecture',
            requires_accessible_seat: true,
            accessibility_notes: 'Ground floor accessible desk required',
            private_accommodations: 'CONFIDENTIAL: Extra 30 mins, wheelchair access',
          },
          {
            id: 'c-acc-2',
            roll_number: '2026-ACC-02',
            name: 'Julia Kim (Accommodated)',
            paper_code: 'MA201',
            paper_name: 'Linear Algebra',
            requires_accessible_seat: true,
            accessibility_notes: 'Wide aisle accessibility bench',
            private_accommodations: 'CONFIDENTIAL: Ergonomic seating requirement',
          },
        ],
        rooms: [
          {
            id: 'hall-alpha',
            name: 'Examination Hall Alpha (East Wing)',
            code: 'HAL-A',
            seats: [
              // Row 1
              { id: 'h-a-r1-c1', row_num: 1, col_num: 1, bench_label: 'A1', is_usable_for_exam: true, is_blocked: false, is_accessible: true },
              { id: 'h-a-r1-c2', row_num: 1, col_num: 2, bench_label: 'A2', is_usable_for_exam: true, is_blocked: false, is_accessible: false },
              { id: 'h-a-r1-c3', row_num: 1, col_num: 3, bench_label: 'A3', is_usable_for_exam: true, is_blocked: false, is_accessible: false },
              { id: 'h-a-r1-c4', row_num: 1, col_num: 4, bench_label: 'A4', is_usable_for_exam: false, is_blocked: true, is_accessible: false, notes: 'Repairs pending' },
              // Row 2
              { id: 'h-a-r2-c1', row_num: 2, col_num: 1, bench_label: 'B1', is_usable_for_exam: true, is_blocked: false, is_accessible: true },
              { id: 'h-a-r2-c2', row_num: 2, col_num: 2, bench_label: 'B2', is_usable_for_exam: true, is_blocked: false, is_accessible: false },
              { id: 'h-a-r2-c3', row_num: 2, col_num: 3, bench_label: 'B3', is_usable_for_exam: true, is_blocked: false, is_accessible: false },
              { id: 'h-a-r2-c4', row_num: 2, col_num: 4, bench_label: 'B4', is_usable_for_exam: true, is_blocked: false, is_accessible: false },
              // Row 3
              { id: 'h-a-r3-c1', row_num: 3, col_num: 1, bench_label: 'C1', is_usable_for_exam: true, is_blocked: false, is_accessible: false },
              { id: 'h-a-r3-c2', row_num: 3, col_num: 2, bench_label: 'C2', is_usable_for_exam: true, is_blocked: false, is_accessible: false },
              { id: 'h-a-r3-c3', row_num: 3, col_num: 3, bench_label: 'C3', is_usable_for_exam: true, is_blocked: false, is_accessible: false },
              { id: 'h-a-r3-c4', row_num: 3, col_num: 4, bench_label: 'C4', is_usable_for_exam: true, is_blocked: false, is_accessible: false },
            ],
          },
          {
            id: 'hall-beta',
            name: 'Auditorium Floor (Main Hall)',
            code: 'AUD-M',
            seats: [
              { id: 'h-b-r1-c1', row_num: 1, col_num: 1, bench_label: 'M-01', is_usable_for_exam: true, is_blocked: false, is_accessible: true },
              { id: 'h-b-r1-c2', row_num: 1, col_num: 2, bench_label: 'M-02', is_usable_for_exam: true, is_blocked: false, is_accessible: false },
              { id: 'h-b-r1-c3', row_num: 1, col_num: 3, bench_label: 'M-03', is_usable_for_exam: true, is_blocked: false, is_accessible: false },
              { id: 'h-b-r1-c4', row_num: 1, col_num: 4, bench_label: 'M-04', is_usable_for_exam: true, is_blocked: false, is_accessible: false },
            ],
          },
        ],
      };

      const created = await api.exams.createTheorySitting({
        name: `End-Term Theory Examination ${new Date().toLocaleDateString()}`,
        academic_term_id: 'a23c5614-8329-4cc9-92af-07570424ba45',
        exam_type: 'THEORY',
        duration_minutes: 180,
        buffer_minutes: 15,
        input_snapshot: demoSnapshot,
        parameters: {
          hard_paper_adjacency: hardAdjacency,
          batch_grouping_policy: batchGrouping,
          use_optimisation: useOptimisation,
        },
      });

      setActionSuccess('Demo Theory Examination sitting created successfully.');
      await fetchSittings();
      setSelectedSittingId(created.id);
      setCurrentSitting(created);
      setSelectedRoomId('hall-alpha');
    } catch (err: any) {
      console.error('Failed to create demo theory sitting:', err);
      setActionError('Could not initialize demo dataset.');
    } finally {
      setIsLoading(false);
    }
  };

  // Helper: Seed demo practical dataset
  const handleSeedDemoPractical = async () => {
    setIsLoading(true);
    setActionError(null);
    try {
      const demoSnapshot = {
        candidates: [
          { id: 'p-01', roll_number: '2026-PR-01', name: 'Liam Vance', required_os: 'Linux', required_features: ['CUDA', 'GPU'] },
          { id: 'p-02', roll_number: '2026-PR-02', name: 'Maya Lin', required_os: 'Linux', required_features: ['CUDA', 'GPU'] },
          { id: 'p-03', roll_number: '2026-PR-03', name: 'Noah Reed', required_os: 'Windows', required_features: ['MATLAB'] },
          { id: 'p-04', roll_number: '2026-PR-04', name: 'Olivia Scott', required_os: 'Windows', required_features: ['MATLAB'] },
          { id: 'p-05', roll_number: '2026-PR-05', name: 'Peter Ward', required_os: 'Linux', required_features: ['Wireshark'] },
          { id: 'p-06', roll_number: '2026-PR-06', name: 'Quinn Adams', required_os: 'Linux', required_features: ['Wireshark'] },
        ],
        labs: [
          {
            id: 'lab-cs1',
            name: 'Advanced Systems Lab 1 (Level 3)',
            code: 'LAB-CS1',
            effective_capacity_limit: 4,
            workstations: [
              { id: 'ws-01', station_code: 'WS-01', is_usable: true, os: 'Linux', installed_features: ['CUDA', 'GPU', 'Wireshark'] },
              { id: 'ws-02', station_code: 'WS-02', is_usable: true, os: 'Linux', installed_features: ['CUDA', 'GPU', 'Wireshark'] },
              { id: 'ws-03', station_code: 'WS-03', is_usable: true, os: 'Windows', installed_features: ['MATLAB', 'Office'] },
              { id: 'ws-04', station_code: 'WS-04', is_usable: true, os: 'Windows', installed_features: ['MATLAB', 'Office'] },
            ],
          },
        ],
        sittings: [
          {
            batch_id: 'batch-morning',
            batch_name: 'Batch 1 (Morning Session)',
            lab_id: 'lab-cs1',
            start_time: '09:00',
            duration_minutes: 120,
            turnaround_buffer_minutes: 20,
            examiner_id: 'prof-taylor',
            assistant_id: 'ta-alex',
          },
          {
            batch_id: 'batch-afternoon',
            batch_name: 'Batch 2 (Afternoon Session)',
            lab_id: 'lab-cs1',
            start_time: '12:00',
            duration_minutes: 120,
            turnaround_buffer_minutes: 20,
            examiner_id: 'prof-taylor',
            assistant_id: 'ta-sarah',
          },
        ],
      };

      const created = await api.exams.createPracticalSitting({
        name: `OS & Systems Lab Practicals ${new Date().toLocaleDateString()}`,
        academic_term_id: 'a23c5614-8329-4cc9-92af-07570424ba45',
        exam_type: 'PRACTICAL',
        duration_minutes: 120,
        buffer_minutes: 20,
        input_snapshot: demoSnapshot,
      });

      setActionSuccess('Demo Practical Lab sitting created successfully.');
      await fetchSittings();
      setSelectedSittingId(created.id);
      setCurrentSitting(created);
      setSelectedLabId('lab-cs1');
    } catch (err: any) {
      console.error('Failed to create demo practical sitting:', err);
      setActionError('Could not initialize practical demo dataset.');
    } finally {
      setIsLoading(false);
    }
  };

  // Run Allocation
  const handleAllocate = async () => {
    if (!currentSitting) return;
    setIsAllocating(true);
    setActionError(null);
    setActionSuccess(null);
    try {
      let updated: ExamSitting;
      if (activeTab === 'THEORY') {
        updated = await api.exams.allocateTheorySeating(currentSitting.id);
      } else {
        updated = await api.exams.allocatePracticalWorkstations(currentSitting.id);
      }
      setCurrentSitting(updated);
      setSelectedBenchForSwap(null);
      setActionSuccess('Allocation generated and authoritatively checked!');
    } catch (err: any) {
      console.error('Allocation error:', err);
      const detail = err.detail || {};
      const msg = typeof detail === 'string' ? detail : detail.message || 'Allocation could not be satisfied.';
      setActionError(msg);
      // Refresh sitting if updated to invalid state
      if (currentSitting) {
        handleSelectSitting(currentSitting.id);
      }
    } finally {
      setIsAllocating(false);
    }
  };

  // Independent verification check
  const handleValidateRules = async () => {
    if (!currentSitting) return;
    setIsChecking(true);
    setActionError(null);
    setActionSuccess(null);
    try {
      let report: any;
      if (activeTab === 'THEORY') {
        report = await api.exams.validateTheorySeating(currentSitting.id);
      } else {
        report = await api.exams.validatePracticalAllocation(currentSitting.id);
      }
      if (report.is_valid) {
        setActionSuccess('Independent verifier confirmed: All rules and constraints satisfied!');
      } else {
        const violations = (report.violations || []).map((v: any) => v.message).join('; ');
        setActionError(`Constraint violations detected: ${violations}`);
      }
      handleSelectSitting(currentSitting.id);
    } catch (err: any) {
      setActionError('Validation failed to execute.');
    } finally {
      setIsChecking(false);
    }
  };

  // Move or swap bench interaction in Theory mode
  const handleBenchClick = async (seat: ExamSeat, room: ExamRoom, allocatedCand?: ExamTheoryAllocation) => {
    if (!currentSitting || currentSitting.is_published) return;
    if (!seat.is_usable_for_exam || seat.is_blocked) {
      setActionError(`Bench ${seat.bench_label} is blocked/unusable for exams.`);
      return;
    }

    if (!selectedBenchForSwap) {
      // First click: select candidate if occupied
      if (allocatedCand) {
        setSelectedBenchForSwap({
          candidate_id: allocatedCand.candidate_id,
          seat_id: seat.id,
          bench_label: seat.bench_label,
          roll_number: allocatedCand.roll_number,
        });
        setActionSuccess(`Selected candidate ${allocatedCand.roll_number} at ${seat.bench_label}. Click a vacant bench to move, or another candidate to swap.`);
      } else {
        setActionError('Select an occupied bench first to initiate a move or swap.');
      }
    } else {
      // Second click: either move to vacant seat or swap with target candidate
      const candId = selectedBenchForSwap.candidate_id;
      const expRev = currentSitting.revision;

      setIsLoading(true);
      setActionError(null);
      setActionSuccess(null);

      try {
        if (allocatedCand) {
          // Swap two candidates
          if (allocatedCand.candidate_id === candId) {
            setSelectedBenchForSwap(null);
            setActionSuccess('Selection cleared.');
            setIsLoading(false);
            return;
          }
          const updated = await api.exams.reassignTheorySeat(currentSitting.id, candId, {
            expected_revision: expRev,
            target_candidate_id: allocatedCand.candidate_id,
          });
          setCurrentSitting(updated);
          setSelectedBenchForSwap(null);
          setActionSuccess(`Swapped seat ${selectedBenchForSwap.bench_label} with ${seat.bench_label}. Revision updated to ${updated.revision}.`);
        } else {
          // Move candidate to empty seat
          const updated = await api.exams.reassignTheorySeat(currentSitting.id, candId, {
            expected_revision: expRev,
            seat_id: seat.id,
            room_id: room.id,
          });
          setCurrentSitting(updated);
          setSelectedBenchForSwap(null);
          setActionSuccess(`Candidate moved to bench ${seat.bench_label}. Revision updated to ${updated.revision}.`);
        }
      } catch (err: any) {
        console.error('Reassign error:', err);
        setActionError(err.detail || 'Failed to move/swap candidate. Please check revision conflict or constraint violation.');
        if (currentSitting) handleSelectSitting(currentSitting.id);
      } finally {
        setIsLoading(false);
      }
    }
  };

  // Move practical candidate workstation
  const handlePracticalWorkstationReassign = async (candidateId: string, newWorkstationId: string) => {
    if (!currentSitting) return;
    setIsLoading(true);
    setActionError(null);
    try {
      const updated = await api.exams.reassignPracticalWorkstation(currentSitting.id, candidateId, {
        expected_revision: currentSitting.revision,
        workstation_id: newWorkstationId,
      });
      setCurrentSitting(updated);
      setSelectedPracticalCandidateId(null);
      setActionSuccess('Workstation reassigned and validated.');
    } catch (err: any) {
      setActionError(err.detail || 'Failed to reassign workstation.');
    } finally {
      setIsLoading(false);
    }
  };

  // Open Export Modal & fetch export preview
  const handleOpenExport = async () => {
    if (!currentSitting) return;
    setExportModalOpen(true);
    fetchExportDocument(exportType);
  };

  const fetchExportDocument = async (type: typeof exportType) => {
    if (!currentSitting) return;
    setIsExporting(true);
    try {
      let data: ExportData;
      if (type === 'SEAT_PLAN') {
        data = await api.exams.exportSeatPlan(currentSitting.id, selectedRoomId || undefined);
      } else if (type === 'CANDIDATE_LIST') {
        data = await api.exams.exportCandidateList(currentSitting.id);
      } else if (type === 'ATTENDANCE_SHEET') {
        data = await api.exams.exportAttendanceSheet(currentSitting.id, selectedRoomId || undefined);
      } else {
        data = await api.exams.exportPracticalWorkstations(currentSitting.id);
      }
      setExportResult(data);
    } catch (err: any) {
      console.error('Export error:', err);
      setActionError('Failed to fetch export document.');
    } finally {
      setIsExporting(false);
    }
  };

  // =========================================================================
  // CALCULATED METRICS & SEAT MAP DATA (THEORY)
  // =========================================================================
  const currentRoom = useMemo(() => {
    if (!currentSitting?.input_snapshot?.rooms) return null;
    return currentSitting.input_snapshot.rooms.find((r) => r.id === selectedRoomId) || currentSitting.input_snapshot.rooms[0] || null;
  }, [currentSitting, selectedRoomId]);

  const theoryAllocations = useMemo(() => {
    if (!currentSitting?.output_allocations) return [];
    return currentSitting.output_allocations as ExamTheoryAllocation[];
  }, [currentSitting]);

  const allocationBySeatId = useMemo(() => {
    const map = new Map<string, ExamTheoryAllocation>();
    theoryAllocations.forEach((alloc) => {
      map.set(alloc.seat_id, alloc);
    });
    return map;
  }, [theoryAllocations]);

  const candidateById = useMemo(() => {
    const map = new Map<string, ExamCandidate>();
    currentSitting?.input_snapshot?.candidates?.forEach((c) => {
      map.set(c.id, c);
    });
    return map;
  }, [currentSitting]);

  // Capacity calculations
  const totalBenches = currentRoom?.seats?.length || 0;
  const usableBenches = currentRoom?.seats?.filter((s) => s.is_usable_for_exam && !s.is_blocked).length || 0;
  const roomAllocatedBenches = currentRoom?.seats?.filter((s) => allocationBySeatId.has(s.id)).length || 0;
  const remainingBenches = Math.max(0, usableBenches - roomAllocatedBenches);

  const accessibleCandidates = useMemo(() => {
    return currentSitting?.input_snapshot?.candidates?.filter((c) => c.requires_accessible_seat) || [];
  }, [currentSitting]);

  const unassignedCandidates = useMemo(() => {
    const assignedIds = new Set(theoryAllocations.map((a) => a.candidate_id));
    return (currentSitting?.input_snapshot?.candidates || []).filter((c) => !assignedIds.has(c.id));
  }, [currentSitting, theoryAllocations]);

  // Accessible candidate columns for Table component
  const accessibleColumns: Column<ExamCandidate>[] = [
    {
      key: 'roll_number',
      header: 'Roll Number',
      render: (c) => <span className="font-mono font-semibold text-navy">{c.roll_number}</span>,
    },
    {
      key: 'name',
      header: 'Candidate Name',
      render: (c) => <span className="text-navy">{c.name}</span>,
    },
    {
      key: 'paper_code',
      header: 'Paper Code',
      render: (c) => (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
          {c.paper_code}
        </span>
      ),
    },
    {
      key: 'accommodation_public',
      header: 'Required Accommodation',
      render: (c) => (
        <span className="text-xs text-navy-muted">
          {c.accessibility_notes || 'Wheelchair accessible / Ground floor'}
        </span>
      ),
    },
    {
      key: 'assigned_seat',
      header: 'Assigned Bench',
      render: (c) => {
        const alloc = theoryAllocations.find((a) => a.candidate_id === c.id);
        if (!alloc) {
          return <span className="text-xs font-medium text-amber-600">Unassigned</span>;
        }
        return (
          <span className="inline-flex items-center gap-1 text-xs font-semibold text-teal">
            <CheckCircle className="w-3.5 h-3.5 text-teal" />
            {alloc.bench_label} ({alloc.is_accessible_seat ? 'Accessible Desk' : 'Standard'})
          </span>
        );
      },
    },
    {
      key: 'privacy_status',
      header: 'Privacy Protection',
      render: () => (
        <span className="inline-flex items-center gap-1 text-xs text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
          <ShieldCheck className="w-3 h-3 text-emerald-600" />
          Notes Omitted from Public Plans
        </span>
      ),
    },
  ];

  // Grid dimensions
  const maxRow = currentRoom?.seats ? Math.max(...currentRoom.seats.map((s) => s.row_num), 1) : 1;
  const maxCol = currentRoom?.seats ? Math.max(...currentRoom.seats.map((s) => s.col_num), 1) : 1;

  // Practical variables
  const currentLab = useMemo(() => {
    if (!currentSitting?.input_snapshot?.labs) return null;
    return currentSitting.input_snapshot.labs.find((l) => l.id === selectedLabId) || currentSitting.input_snapshot.labs[0] || null;
  }, [currentSitting, selectedLabId]);

  const practicalAllocations = useMemo(() => {
    if (!currentSitting?.output_allocations) return [];
    return currentSitting.output_allocations as PracticalAllocation[];
  }, [currentSitting]);

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-heading text-xl sm:text-2xl font-bold text-navy">
              Examination Allocation & Logistics
            </h1>
            {currentSitting && (
              <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-teal-light text-teal border border-teal/20">
                Revision {currentSitting.revision}
              </span>
            )}
          </div>
          <p className="text-xs sm:text-sm text-navy-muted">
            Phase 9: Theory seating plans, orthogonal paper separation, accessibility compliance, and practical lab workstation logistics.
          </p>
        </div>

        {/* Global Action Buttons */}
        <div className="flex flex-wrap items-center gap-2">
          {activeTab === 'THEORY' ? (
            <Button
              variant="secondary"
              size="sm"
              leftIcon={<Plus className="w-3.5 h-3.5" />}
              onClick={handleSeedDemoTheory}
              isLoading={isLoading}
            >
              Load Demo Theory Exam
            </Button>
          ) : (
            <Button
              variant="secondary"
              size="sm"
              leftIcon={<Plus className="w-3.5 h-3.5" />}
              onClick={handleSeedDemoPractical}
              isLoading={isLoading}
            >
              Load Demo Practical Exam
            </Button>
          )}

          <Button
            variant="secondary"
            size="sm"
            leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
            onClick={handleValidateRules}
            isLoading={isChecking}
            disabled={!currentSitting}
          >
            Verify Constraints
          </Button>

          <Button
            variant="primary"
            size="sm"
            leftIcon={<Users className="w-3.5 h-3.5" />}
            onClick={handleAllocate}
            isLoading={isAllocating}
            disabled={!currentSitting || currentSitting.is_published}
          >
            Allocate Seats
          </Button>

          <Button
            variant="outline"
            size="sm"
            leftIcon={<Printer className="w-3.5 h-3.5" />}
            onClick={handleOpenExport}
            disabled={!currentSitting}
          >
            Export Documents
          </Button>
        </div>
      </div>

      {/* Main Mode Tabs */}
      <Tabs
        tabs={[
          { id: 'THEORY', label: 'Theory Seating Plans', icon: <BookOpen className="w-4 h-4" /> },
          { id: 'PRACTICAL', label: 'Practical Laboratory Sittings', icon: <Monitor className="w-4 h-4" /> },
        ]}
        activeTab={activeTab}
        onChange={(tabId) => {
          setActiveTab(tabId as 'THEORY' | 'PRACTICAL');
          setSelectedBenchForSwap(null);
        }}
      />

      {/* Active Sitting Selector & Notification Alerts */}
      <Card className="p-4 bg-white shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <span className="text-xs font-bold text-navy-muted uppercase tracking-wider">Active Sitting:</span>
            {sittings.length > 0 ? (
              <select
                aria-label="Active Examination Sitting"
                className="bg-bg border border-border text-navy text-sm rounded-md px-3 py-1.5 focus:ring-1 focus:ring-teal focus:border-teal outline-none"
                value={selectedSittingId || ''}
                onChange={(e) => handleSelectSitting(e.target.value)}
              >
                {sittings.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name} ({s.status}) - Rev {s.revision}
                  </option>
                ))}
              </select>
            ) : (
              <span className="text-xs text-navy-subtle">No sittings found. Click "Load Demo" above to create one.</span>
            )}
          </div>

          {currentSitting && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-navy-muted">Status:</span>
              <StatusBadge
                status={
                  currentSitting.status === 'CHECKED'
                    ? 'PUBLISHED'
                    : currentSitting.status === 'INVALID'
                    ? 'ERROR'
                    : 'DRAFT'
                }
              />
              <span className="text-xs font-mono text-navy-subtle ml-2">
                Duration: {currentSitting.duration_minutes}m (+{currentSitting.buffer_minutes}m buffer)
              </span>
            </div>
          )}
        </div>

        {/* Action Banners */}
        {actionError && (
          <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-md flex items-start gap-2 text-xs text-red-800">
            <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
            <div className="flex-1 font-medium">{actionError}</div>
            <button aria-label="Dismiss error notification" onClick={() => setActionError(null)} className="text-red-500 hover:text-red-700">
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {actionSuccess && (
          <div className="mt-3 p-3 bg-emerald-50 border border-emerald-200 rounded-md flex items-start gap-2 text-xs text-emerald-800">
            <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
            <div className="flex-1 font-medium">{actionSuccess}</div>
            <button aria-label="Dismiss success notification" onClick={() => setActionSuccess(null)} className="text-emerald-500 hover:text-emerald-700">
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {/* Policy Warnings from validation report */}
        {currentSitting?.validation_report?.warnings && currentSitting.validation_report.warnings.length > 0 && (
          <div className="mt-3 p-3 bg-amber-50 border border-amber-200 rounded-md space-y-1">
            <div className="flex items-center gap-1.5 text-xs font-bold text-amber-800">
              <AlertTriangle className="w-4 h-4 text-amber-600" />
              Policy Warnings ({currentSitting.validation_report.warnings.length}):
            </div>
            {currentSitting.validation_report.warnings.map((w, idx) => (
              <div key={idx} className="text-xs text-amber-700 pl-5">
                • <span className="font-semibold">{w.code}:</span> {w.message}
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* ========================================================================= */}
      {/* THEORY EXAMINATION TAB CONTENT */}
      {/* ========================================================================= */}
      {activeTab === 'THEORY' && currentSitting && (
        <div className="space-y-6">
          {/* Hall Selector & Capacity Cards */}
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
            {/* Hall selector card */}
            <Card className="p-4 bg-white flex flex-col justify-between">
              <div>
                <span className="text-xs font-bold text-navy-muted uppercase tracking-wider block mb-2">
                  Select Examination Hall
                </span>
                <div className="space-y-2">
                  {(currentSitting.input_snapshot?.rooms || []).map((room) => (
                    <button
                      key={room.id}
                      onClick={() => {
                        setSelectedRoomId(room.id);
                        setSelectedBenchForSwap(null);
                      }}
                      className={`w-full text-left p-2.5 rounded-lg border text-xs font-medium transition-all ${
                        selectedRoomId === room.id
                          ? 'bg-teal-light/40 border-teal text-navy font-semibold shadow-xs'
                          : 'bg-bg/50 border-border text-navy-muted hover:border-border-strong hover:text-navy'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span>{room.name}</span>
                        <span className="text-2xs font-mono px-1.5 py-0.5 rounded bg-white border border-border">
                          {room.seats?.length || 0} seats
                        </span>
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Policy Options */}
              <div className="mt-4 pt-4 border-t border-border space-y-2">
                <span className="text-2xs font-bold text-navy-muted uppercase tracking-wider block">
                  Configured Allocation Policies
                </span>
                <label className="flex items-center gap-2 text-xs text-navy cursor-pointer">
                  <input
                    type="checkbox"
                    className="rounded text-teal focus:ring-teal"
                    checked={hardAdjacency}
                    onChange={(e) => setHardAdjacency(e.target.checked)}
                  />
                  <span>Hard Orthogonal Paper Separation</span>
                </label>
                <label className="flex items-center gap-2 text-xs text-navy cursor-pointer">
                  <input
                    type="checkbox"
                    className="rounded text-teal focus:ring-teal"
                    checked={batchGrouping}
                    onChange={(e) => setBatchGrouping(e.target.checked)}
                  />
                  <span>Batch Grouping Policy</span>
                </label>
                <label className="flex items-center gap-2 text-xs text-navy cursor-pointer">
                  <input
                    type="checkbox"
                    className="rounded text-teal focus:ring-teal"
                    checked={useOptimisation}
                    onChange={(e) => setUseOptimisation(e.target.checked)}
                  />
                  <span>CP-SAT Constraint Optimisation</span>
                </label>
              </div>
            </Card>

            {/* 4 Capacity Stat Cards */}
            <div className="lg:col-span-3 grid grid-cols-2 sm:grid-cols-4 gap-3">
              <Card className="p-4 bg-white flex flex-col justify-between">
                <span className="text-xs font-medium text-navy-muted">Total Benches</span>
                <div className="mt-2 text-2xl font-bold font-mono text-navy">{totalBenches}</div>
                <span className="text-2xs text-navy-subtle mt-1">{currentRoom?.name || 'Selected Hall'}</span>
              </Card>

              <Card className="p-4 bg-white flex flex-col justify-between">
                <span className="text-xs font-medium text-navy-muted">Usable / Eligible</span>
                <div className="mt-2 text-2xl font-bold font-mono text-teal">{usableBenches}</div>
                <span className="text-2xs text-navy-subtle mt-1">Excludes blocked / reserved</span>
              </Card>

              <Card className="p-4 bg-white flex flex-col justify-between">
                <span className="text-xs font-medium text-navy-muted">Allocated Candidates</span>
                <div className="mt-2 text-2xl font-bold font-mono text-blue-600">{roomAllocatedBenches}</div>
                <span className="text-2xs text-navy-subtle mt-1">Registered & Seated</span>
              </Card>

              <Card className="p-4 bg-white flex flex-col justify-between">
                <span className="text-xs font-medium text-navy-muted">Remaining Capacity</span>
                <div className="mt-2 text-2xl font-bold font-mono text-navy">{remainingBenches}</div>
                <span className="text-2xs text-emerald-600 font-medium mt-1">
                  {accessibleCandidates.length} Accessible Accommodated
                </span>
              </Card>
            </div>
          </div>

          {/* Seat Map Controls & Search */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="relative flex-1 max-w-sm">
              <Search className="w-4 h-4 text-navy-muted absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Search candidate roll number or paper..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-white border border-border rounded-lg pl-9 pr-3 py-1.5 text-xs text-navy placeholder:text-navy-subtle focus:ring-1 focus:ring-teal focus:border-teal outline-none"
              />
            </div>

            {selectedBenchForSwap && (
              <div className="flex items-center gap-2 bg-teal-light/40 border border-teal text-navy text-xs px-3 py-1.5 rounded-lg animate-pulse">
                <ArrowRightLeft className="w-3.5 h-3.5 text-teal" />
                <span>
                  Moving candidate <strong>{selectedBenchForSwap.roll_number}</strong> from <strong>{selectedBenchForSwap.bench_label}</strong>. Click target bench!
                </span>
                <button
                  aria-label="Cancel candidate move or swap"
                  onClick={() => setSelectedBenchForSwap(null)}
                  className="ml-2 text-navy-muted hover:text-navy"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            )}
          </div>

          {/* Interactive Seat Map Matrix */}
          <Card className="p-5 bg-white">
            <div className="flex items-center justify-between mb-4 pb-3 border-b border-border">
              <div>
                <h3 className="text-sm font-bold text-navy flex items-center gap-2">
                  <Grid className="w-4 h-4 text-teal" />
                  {currentRoom?.name || 'Hall'} — Physical Bench Matrix
                </h3>
                <span className="text-2xs text-navy-muted">
                  Click an occupied bench to select, then click another bench to move or swap candidate.
                </span>
              </div>

              {/* Legend */}
              <div className="flex flex-wrap items-center gap-3 text-2xs">
                <span className="flex items-center gap-1">
                  <span className="w-3 h-3 rounded bg-blue-100 border border-blue-300 inline-block" /> CS101
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-3 h-3 rounded bg-emerald-100 border border-emerald-300 inline-block" /> MA201
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-3 h-3 rounded bg-purple-100 border border-purple-300 inline-block" /> PH301
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-3 h-3 rounded bg-amber-100 border border-amber-300 inline-block" /> Accessible
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-3 h-3 rounded bg-gray-200 border border-dashed border-gray-400 inline-block" /> Blocked
                </span>
              </div>
            </div>

            {/* Matrix Rows and Columns */}
            <div className="overflow-x-auto pb-4">
              <div
                className="grid gap-3 min-w-[640px]"
                style={{
                  gridTemplateColumns: `repeat(${maxCol}, minmax(130px, 1fr))`,
                }}
              >
                {Array.from({ length: maxRow }).map((_, rIdx) => {
                  const rowNum = rIdx + 1;
                  return Array.from({ length: maxCol }).map((_, cIdx) => {
                    const colNum = cIdx + 1;
                    const seat = currentRoom?.seats?.find((s) => s.row_num === rowNum && s.col_num === colNum);
                    if (!seat) {
                      return (
                        <div
                          key={`empty-${rowNum}-${colNum}`}
                          className="h-28 rounded-lg border border-dashed border-border/50 bg-bg/20 flex items-center justify-center text-navy-subtle text-2xs"
                        >
                          Aisle
                        </div>
                      );
                    }

                    const alloc = allocationBySeatId.get(seat.id);
                    const cand = alloc ? candidateById.get(alloc.candidate_id) : null;
                    const isSelected = selectedBenchForSwap?.seat_id === seat.id;
                    const isMatchSearch =
                      searchQuery.trim().length > 0 &&
                      (alloc?.roll_number.toLowerCase().includes(searchQuery.toLowerCase()) ||
                        alloc?.paper_code.toLowerCase().includes(searchQuery.toLowerCase()) ||
                        cand?.name.toLowerCase().includes(searchQuery.toLowerCase()));

                    // Styling based on state
                    let benchStyle = 'bg-white border-border hover:border-teal/50';
                    if (seat.is_blocked || !seat.is_usable_for_exam) {
                      benchStyle = 'bg-gray-100 border-gray-300 text-gray-400 cursor-not-allowed opacity-75';
                    } else if (isSelected) {
                      benchStyle = 'bg-teal-light/50 border-teal ring-2 ring-teal shadow-md';
                    } else if (isMatchSearch) {
                      benchStyle = 'bg-amber-50 border-amber-400 ring-2 ring-amber-400 shadow-md';
                    } else if (alloc) {
                      const color = PAPER_COLORS[alloc.paper_code] || PAPER_COLORS.DEFAULT;
                      benchStyle = `${color.bg} ${color.border} shadow-xs hover:shadow-sm`;
                    }

                    return (
                      <button
                        key={seat.id}
                        disabled={seat.is_blocked || !seat.is_usable_for_exam}
                        onClick={() => handleBenchClick(seat, currentRoom!, alloc)}
                        className={`h-28 p-2.5 rounded-lg border text-left transition-all flex flex-col justify-between relative group ${benchStyle}`}
                      >
                        {/* Top: Bench label & tags */}
                        <div className="flex items-center justify-between w-full">
                          <span className="font-mono font-bold text-xs text-navy">
                            {seat.bench_label}
                          </span>
                          <div className="flex items-center gap-1">
                            {seat.is_accessible && (
                              <span
                                title="Accessible Bench"
                                className="px-1 py-0.2 bg-amber-100 text-amber-800 rounded text-2xs font-bold border border-amber-300"
                              >
                                Acc
                              </span>
                            )}
                            {seat.is_blocked && (
                              <span
                                title="Blocked Bench"
                                className="px-1 py-0.2 bg-red-100 text-red-800 rounded text-2xs font-bold border border-red-300"
                              >
                                Blocked
                              </span>
                            )}
                          </div>
                        </div>

                        {/* Middle: Candidate Allocation or Vacant */}
                        {alloc ? (
                          <div className="my-auto space-y-0.5">
                            <div className="font-mono font-bold text-xs text-navy truncate">
                              {alloc.roll_number}
                            </div>
                            <div className="text-2xs text-navy-muted truncate">
                              {cand?.name || alloc.name || 'Candidate'}
                            </div>
                            <div className="inline-block px-1.5 py-0.2 rounded text-2xs font-semibold bg-white border border-border-strong text-navy">
                              {alloc.paper_code}
                            </div>
                          </div>
                        ) : (
                          <div className="my-auto text-center text-navy-subtle text-xs font-medium">
                            {seat.is_blocked ? 'Unavailable' : 'Vacant Bench'}
                          </div>
                        )}

                        {/* Bottom: Coords */}
                        <div className="text-3xs text-navy-subtle">
                          Row {seat.row_num}, Col {seat.col_num}
                        </div>
                      </button>
                    );
                  });
                })}
              </div>
            </div>
          </Card>

          {/* Unassigned Candidates Tray (if any) */}
          {unassignedCandidates.length > 0 && (
            <Card className="p-4 bg-amber-50/50 border-amber-200">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 text-amber-600" />
                  <h4 className="text-xs font-bold text-amber-900 uppercase tracking-wider">
                    Unassigned Candidates ({unassignedCandidates.length})
                  </h4>
                </div>
                <span className="text-2xs text-amber-800">
                  Registered candidates pending desk allocation. Click a vacant bench to allocate manually.
                </span>
              </div>
              <div className="flex flex-wrap gap-2">
                {unassignedCandidates.map((cand) => (
                  <div
                    key={cand.id}
                    className="p-2 bg-white rounded border border-amber-300 text-xs text-navy flex items-center gap-2 shadow-xs"
                  >
                    <span className="font-mono font-bold text-navy">{cand.roll_number}</span>
                    <span className="text-navy-muted">{cand.name}</span>
                    <span className="px-1.5 py-0.5 text-2xs rounded bg-blue-50 text-blue-700 font-semibold">
                      {cand.paper_code}
                    </span>
                    {cand.requires_accessible_seat && (
                      <span className="px-1.5 py-0.5 text-2xs rounded bg-amber-100 text-amber-800 font-semibold">
                        Accessible Req.
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Accessible Candidates Table (Equivalent Accessible View) */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-navy flex items-center gap-2">
                  <Users className="w-4 h-4 text-teal" />
                  Equivalent Accessible Candidate Accommodations
                </h3>
                <p className="text-2xs text-navy-muted">
                  Accessibility verification table showing compliant ground-floor / wide-aisle seating. Private medical details remain restricted.
                </p>
              </div>
            </div>

            <Card className="overflow-hidden bg-white">
              <Table
                columns={accessibleColumns}
                data={accessibleCandidates}
                keyExtractor={(item) => item.id}
                emptyMessage="No accessible candidates registered for this sitting."
              />
            </Card>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* PRACTICAL EXAMINATION TAB CONTENT */}
      {/* ========================================================================= */}
      {activeTab === 'PRACTICAL' && currentSitting && (
        <div className="space-y-6">
          {/* Top Labs and Timeline */}
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
            <Card className="p-4 bg-white">
              <span className="text-xs font-bold text-navy-muted uppercase tracking-wider block mb-2">
                Select Computer / Hardware Lab
              </span>
              <div className="space-y-2">
                {(currentSitting.input_snapshot?.labs || []).map((lab) => (
                  <button
                    key={lab.id}
                    onClick={() => setSelectedLabId(lab.id)}
                    className={`w-full text-left p-2.5 rounded-lg border text-xs font-medium transition-all ${
                      selectedLabId === lab.id
                        ? 'bg-teal-light/40 border-teal text-navy font-semibold shadow-xs'
                        : 'bg-bg/50 border-border text-navy-muted hover:border-border-strong hover:text-navy'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span>{lab.name}</span>
                      <span className="text-2xs font-mono px-1.5 py-0.5 rounded bg-white border border-border">
                        {lab.workstations?.length || 0} stations
                      </span>
                    </div>
                  </button>
                ))}
              </div>

              {/* Lab Policy Limits */}
              {currentLab && (
                <div className="mt-4 pt-4 border-t border-border space-y-1 text-2xs text-navy-muted">
                  <div>
                    <span className="font-semibold text-navy">Effective Capacity Policy:</span>{' '}
                    {currentLab.effective_capacity_limit || currentLab.workstations.length} candidates per batch
                  </div>
                  <div>
                    <span className="font-semibold text-navy">Physical Workstations:</span>{' '}
                    {currentLab.workstations.length} installed
                  </div>
                </div>
              )}
            </Card>

            {/* Sittings Timeline with Turnaround Buffers */}
            <div className="lg:col-span-3 space-y-3">
              <Card className="p-4 bg-white">
                <h3 className="text-xs font-bold text-navy uppercase tracking-wider mb-3 flex items-center gap-2">
                  <Clock className="w-4 h-4 text-teal" />
                  Practical Batches & Turnaround Buffers Schedule
                </h3>

                <div className="space-y-3">
                  {(currentSitting.input_snapshot?.sittings || []).map((batch) => {
                    const duration = batch.duration_minutes || 120;
                    const buffer = batch.turnaround_buffer_minutes || 20;
                    return (
                      <div
                        key={batch.batch_id}
                        className="p-3 bg-bg rounded-lg border border-border flex flex-col md:flex-row md:items-center justify-between gap-3"
                      >
                        <div className="space-y-0.5">
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-xs text-navy">{batch.batch_name || batch.batch_id}</span>
                            <span className="text-2xs font-mono bg-white px-1.5 py-0.5 rounded border border-border text-navy">
                              {batch.start_time} (Duration: {duration} mins)
                            </span>
                          </div>
                          <div className="text-2xs text-navy-muted flex items-center gap-3">
                            <span>Examiner: <strong>{batch.examiner_id}</strong></span>
                            {batch.assistant_id && <span>Assistant: <strong>{batch.assistant_id}</strong></span>}
                          </div>
                        </div>

                        {/* Turnaround Buffer Badge */}
                        <div className="flex items-center gap-2">
                          <div className="px-2.5 py-1 rounded-md text-2xs font-semibold bg-amber-50 text-amber-800 border border-amber-300 flex items-center gap-1.5">
                            <RefreshCw className="w-3 h-3 text-amber-600" />
                            Turnaround Buffer: {buffer}m (Disinfection & Reboot)
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </Card>
            </div>
          </div>

          {/* Workstations Grid */}
          <Card className="p-5 bg-white">
            <div className="flex items-center justify-between mb-4 pb-3 border-b border-border">
              <div>
                <h3 className="text-sm font-bold text-navy flex items-center gap-2">
                  <Monitor className="w-4 h-4 text-teal" />
                  {currentLab?.name || 'Lab'} — Workstation Roster & Compatibility
                </h3>
                <span className="text-2xs text-navy-muted">
                  OS requirements (Linux/Windows) and hardware tags (CUDA, GPU, MATLAB) matched against registered candidates.
                </span>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {(currentLab?.workstations || []).map((ws) => {
                const alloc = practicalAllocations.find((a) => a.workstation_id === ws.id);
                const cand = alloc
                  ? currentSitting.input_snapshot?.candidates?.find((c) => c.id === alloc.candidate_id)
                  : null;

                return (
                  <div
                    key={ws.id}
                    className={`p-3.5 rounded-lg border flex flex-col justify-between ${
                      alloc ? 'bg-teal-light/20 border-teal/40' : 'bg-bg/40 border-border'
                    }`}
                  >
                    <div>
                      <div className="flex items-center justify-between">
                        <span className="font-mono font-bold text-sm text-navy">{ws.station_code}</span>
                        <span className="text-2xs font-mono font-semibold px-1.5 py-0.5 rounded bg-white border border-border text-navy">
                          {ws.os}
                        </span>
                      </div>

                      {/* Installed features */}
                      <div className="flex flex-wrap gap-1 mt-2">
                        {ws.installed_features.map((feat) => (
                          <span
                            key={feat}
                            className="px-1.5 py-0.2 text-3xs font-medium rounded bg-gray-100 text-gray-700 border border-gray-200"
                          >
                            {feat}
                          </span>
                        ))}
                      </div>

                      {/* Assigned Candidate */}
                      {alloc && (
                        <div className="mt-3 pt-3 border-t border-border-strong/40 space-y-1">
                          <div className="font-mono font-bold text-xs text-navy">{alloc.roll_number}</div>
                          <div className="text-2xs text-navy-muted truncate">{cand?.name || 'Candidate'}</div>
                          <div className="flex items-center gap-1 text-2xs text-emerald-700 font-medium">
                            <CheckCircle className="w-3 h-3 text-emerald-600" />
                            Hardware Compatible
                          </div>

                          {/* Quick Reassign Workstation Action */}
                          <div className="mt-2 pt-2 border-t border-border/40">
                            {selectedPracticalCandidateId === alloc.candidate_id ? (
                              <div className="space-y-1">
                                <span className="text-3xs text-navy-muted block">Move to station:</span>
                                <div className="flex flex-wrap gap-1">
                                  {currentLab?.workstations
                                    .filter((w) => w.id !== ws.id)
                                    .map((targetWs) => (
                                      <button
                                        key={targetWs.id}
                                        onClick={() => handlePracticalWorkstationReassign(alloc.candidate_id, targetWs.id)}
                                        className="text-3xs font-mono px-1.5 py-0.5 rounded bg-white border border-border hover:border-teal hover:text-teal"
                                      >
                                        {targetWs.station_code}
                                      </button>
                                    ))}
                                </div>
                                <button
                                  onClick={() => setSelectedPracticalCandidateId(null)}
                                  className="text-3xs text-navy-subtle hover:text-navy underline block mt-1"
                                >
                                  Cancel
                                </button>
                              </div>
                            ) : (
                              <button
                                onClick={() => setSelectedPracticalCandidateId(alloc.candidate_id)}
                                className="text-3xs text-teal font-semibold hover:underline flex items-center gap-1"
                              >
                                <ArrowRightLeft className="w-3 h-3" /> Reassign Station
                              </button>
                            )}
                          </div>
                        </div>
                      )}
                    </div>

                    {!alloc && (
                      <div className="mt-4 text-center text-2xs text-navy-subtle italic">
                        Available Station
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </Card>
        </div>
      )}

      {/* ========================================================================= */}
      {/* EXPORT DOCUMENTS MODAL (PROTECTED & PRIVACY SAFEGUARDED) */}
      {/* ========================================================================= */}
      <Dialog
        isOpen={exportModalOpen}
        onClose={() => setExportModalOpen(false)}
        title="Authorised Examination Export Documents"
        description="Official cryptographic snapshot documents with authentication tokens and expiration timers."
        maxWidth="lg"
      >
        <div className="space-y-4">
          {/* Document Type Selector */}
          <div className="flex flex-wrap gap-2">
            {[
              { id: 'SEAT_PLAN', label: 'Hall Seat Plan (Public Chart)' },
              { id: 'CANDIDATE_LIST', label: 'Candidate Desk List' },
              { id: 'ATTENDANCE_SHEET', label: 'Attendance Sheet (Signatures)' },
              { id: 'PRACTICAL_WORKSTATIONS', label: 'Practical Workstation Roster' },
            ].map((d) => (
              <button
                key={d.id}
                onClick={() => {
                  setExportType(d.id as any);
                  fetchExportDocument(d.id as any);
                }}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                  exportType === d.id
                    ? 'bg-teal text-white border-teal shadow-xs'
                    : 'bg-white border-border text-navy-muted hover:border-border-strong hover:text-navy'
                }`}
              >
                {d.label}
              </button>
            ))}
          </div>

          {/* Export Document Live Preview */}
          <Card className="p-4 bg-bg/50 border-border">
            {isExporting ? (
              <div className="py-8 text-center text-xs text-navy-muted animate-pulse">
                Generating authenticated document snapshot...
              </div>
            ) : exportResult ? (
              <div className="space-y-3 font-sans">
                {/* Header with labels & timestamps */}
                <div className="p-3 bg-white rounded-lg border border-border space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-sm text-navy uppercase tracking-wider">
                      {exportResult.sitting_name}
                    </span>
                    <span className="px-2 py-0.5 rounded text-2xs font-bold bg-amber-100 text-amber-900 border border-amber-300">
                      {exportResult.status_label} — Revision {exportResult.revision}
                    </span>
                  </div>

                  <div className="flex flex-wrap items-center gap-4 text-2xs text-navy-muted font-mono">
                    <span>Generated At: {new Date(exportResult.generated_at).toLocaleString()}</span>
                    <span>Document: {exportResult.document_type}</span>
                  </div>

                  {/* Cryptographic token expiration notice */}
                  <div className="pt-2 border-t border-border flex items-center justify-between text-2xs">
                    <span className="font-mono text-navy-subtle truncate max-w-sm">
                      Signed Token: {exportResult.export_token}
                    </span>
                    <span className="text-teal font-semibold">
                      Valid until {new Date(exportResult.expires_at).toLocaleTimeString()}
                    </span>
                  </div>
                </div>

                {/* Privacy Safeguard Seal */}
                <div className="p-2.5 bg-emerald-50 border border-emerald-200 rounded-md flex items-center gap-2 text-2xs text-emerald-800">
                  <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>
                    <strong>Strict Privacy Safeguard Active:</strong> Private candidate accommodation notes are verified to be completely excluded from this public distribution.
                  </span>
                </div>

                {/* Document preview table */}
                <div className="max-h-64 overflow-y-auto bg-white rounded-lg border border-border p-3 text-xs">
                  {exportResult.seats && exportResult.seats.length > 0 ? (
                    <table className="w-full text-left text-2xs font-mono">
                      <thead>
                        <tr className="border-b border-border text-navy-muted">
                          <th className="pb-1">Bench</th>
                          <th className="pb-1">Roll Number</th>
                          <th className="pb-1">Paper Code</th>
                          <th className="pb-1">Accessible</th>
                        </tr>
                      </thead>
                      <tbody>
                        {exportResult.seats.map((st: any, idx: number) => (
                          <tr key={idx} className="border-b border-border/40 py-1">
                            <td className="py-1 font-bold text-navy">{st.bench_label}</td>
                            <td className="py-1 text-navy">{st.roll_number}</td>
                            <td className="py-1 text-navy-muted">{st.paper_code}</td>
                            <td className="py-1">{st.is_accessible ? 'Yes' : 'No'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  ) : exportResult.candidates && exportResult.candidates.length > 0 ? (
                    <table className="w-full text-left text-2xs font-mono">
                      <thead>
                        <tr className="border-b border-border text-navy-muted">
                          <th className="pb-1">Roll Number</th>
                          <th className="pb-1">Candidate Name</th>
                          <th className="pb-1">Bench</th>
                          <th className="pb-1">Signature</th>
                        </tr>
                      </thead>
                      <tbody>
                        {exportResult.candidates.map((c: any, idx: number) => (
                          <tr key={idx} className="border-b border-border/40 py-1">
                            <td className="py-1 font-bold text-navy">{c.roll_number}</td>
                            <td className="py-1 text-navy">{c.name}</td>
                            <td className="py-1 text-teal font-semibold">{c.bench_label}</td>
                            <td className="py-1 text-navy-subtle">____________________</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  ) : exportResult.allocations && exportResult.allocations.length > 0 ? (
                    <table className="w-full text-left text-2xs font-mono">
                      <thead>
                        <tr className="border-b border-border text-navy-muted">
                          <th className="pb-1">Batch</th>
                          <th className="pb-1">Station</th>
                          <th className="pb-1">Roll Number</th>
                          <th className="pb-1">OS</th>
                        </tr>
                      </thead>
                      <tbody>
                        {exportResult.allocations.map((a: any, idx: number) => (
                          <tr key={idx} className="border-b border-border/40 py-1">
                            <td className="py-1 text-navy-muted">{a.batch_id}</td>
                            <td className="py-1 font-bold text-navy">{a.station_code}</td>
                            <td className="py-1 text-teal">{a.roll_number}</td>
                            <td className="py-1">{a.os || 'Linux'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  ) : (
                    <div className="text-center py-4 text-navy-subtle">No allocation entries found in snapshot.</div>
                  )}
                </div>
              </div>
            ) : null}
          </Card>

          <div className="flex items-center justify-end gap-2 pt-2">
            <Button variant="secondary" size="sm" onClick={() => setExportModalOpen(false)}>
              Close
            </Button>
            <Button
              variant="primary"
              size="sm"
              leftIcon={<Download className="w-3.5 h-3.5" />}
              onClick={() => {
                window.print();
              }}
            >
              Print / Save Official Document
            </Button>
          </div>
        </div>
      </Dialog>
    </div>
  );
};

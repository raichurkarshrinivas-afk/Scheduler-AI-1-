import React, { useState } from 'react';
import { Tabs } from '../../components/common/Tabs';
import { Table } from '../../components/common/Table';
import { StatusBadge } from '../../components/common/StatusBadge';

export const StaffResources: React.FC = () => {
  const [activeTab, setActiveTab] = useState('rooms');

  const tabs = [
    { id: 'rooms', label: 'Instructional Rooms & Exam Benches', count: 4 },
    { id: 'labs', label: 'Practical Workstations', count: 12 },
    { id: 'teachers', label: 'Faculty Qualifications', count: 6 },
  ];

  const roomsData = [
    {
      id: 'r1',
      name: 'Classroom 204',
      code: 'R-204',
      building: 'Science Block',
      physicalCap: 60,
      examBenches: 30,
      type: 'THEORY',
    },
    {
      id: 'r2',
      name: 'Lecture Theatre 1',
      code: 'LT-01',
      building: 'Academic Hall',
      physicalCap: 120,
      examBenches: 60,
      type: 'THEORY',
    },
    {
      id: 'r3',
      name: 'Computing Laboratory 3',
      code: 'LAB-03',
      building: 'Turing Complex',
      physicalCap: 35,
      examBenches: 24,
      type: 'PRACTICAL',
    },
    {
      id: 'r4',
      name: 'Auditorium Main Floor',
      code: 'AUD-01',
      building: 'Central Pavilion',
      physicalCap: 300,
      examBenches: 120,
      type: 'THEORY',
    },
  ];

  const workstationsData = [
    { id: 'ws1', room: 'Lab 3', code: 'WS-01', os: 'Linux Ubuntu 24.04', gpu: 'NVIDIA RTX 4080', ram: '32GB' },
    { id: 'ws2', room: 'Lab 3', code: 'WS-02', os: 'Linux Ubuntu 24.04', gpu: 'NVIDIA RTX 4080', ram: '32GB' },
    { id: 'ws3', room: 'Lab 3', code: 'WS-03', os: 'Linux Ubuntu 24.04', gpu: 'NVIDIA RTX 4080', ram: '32GB' },
    { id: 'ws4', room: 'Lab 3', code: 'WS-04', os: 'Windows 11 Pro', gpu: 'Integrated UHD', ram: '16GB' },
  ];

  const teachersData = [
    { id: 't1', name: 'Dr. Emily Smith', empId: 'APEX-FAC-101', dept: 'Computer Science', maxHrs: 16, verified: true },
    { id: 't2', name: 'Prof. Carl Gauss', empId: 'APEX-FAC-102', dept: 'Mathematics', maxHrs: 14, verified: true },
    { id: 't3', name: 'Dr. Alan Turing', empId: 'APEX-FAC-103', dept: 'Computer Science', maxHrs: 16, verified: true },
    { id: 't4', name: 'Dr. Marie Curie', empId: 'APEX-FAC-104', dept: 'Physics', maxHrs: 12, verified: true },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-heading text-xl sm:text-2xl font-bold text-navy">
          Institutional Resources & Facilities
        </h1>
        <p className="text-xs sm:text-sm text-navy-muted">
          Manage campus instructional facilities, examination desks, and computing lab terminals.
        </p>
      </div>

      <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />

      {activeTab === 'rooms' && (
        <Table
          columns={[
            { key: 'name', header: 'Facility Name', render: (r) => <span className="font-semibold text-navy">{r.name} ({r.code})</span> },
            { key: 'building', header: 'Campus Building' },
            { key: 'type', header: 'Room Type', render: (r) => <StatusBadge status={r.type === 'PRACTICAL' ? 'ACTIVE' : 'DRAFT'} label={r.type} size="sm" /> },
            { key: 'physicalCap', header: 'Physical Capacity', render: (r) => <span>{r.physicalCap} Students</span> },
            {
              key: 'examBenches',
              header: 'Usable Exam Benches',
              render: (r) => (
                <span className="font-semibold text-teal bg-teal-light px-2 py-0.5 rounded border border-teal/20 text-xs">
                  {r.examBenches} Single Benches
                </span>
              ),
            },
          ]}
          data={roomsData}
          keyExtractor={(r) => r.id}
        />
      )}

      {activeTab === 'labs' && (
        <Table
          columns={[
            { key: 'code', header: 'Workstation Terminal', render: (w) => <span className="font-semibold text-navy">{w.code}</span> },
            { key: 'room', header: 'Laboratory Room' },
            { key: 'os', header: 'Operating System' },
            { key: 'gpu', header: 'Graphics & Acceleration', render: (w) => <span className="text-teal font-medium">{w.gpu}</span> },
            { key: 'ram', header: 'RAM Memory' },
          ]}
          data={workstationsData}
          keyExtractor={(w) => w.id}
        />
      )}

      {activeTab === 'teachers' && (
        <Table
          columns={[
            { key: 'name', header: 'Faculty Member', render: (t) => <span className="font-semibold text-navy">{t.name}</span> },
            { key: 'empId', header: 'Employee ID', render: (t) => <code className="bg-bg px-1.5 py-0.5 rounded text-xs">{t.empId}</code> },
            { key: 'dept', header: 'Department' },
            { key: 'maxHrs', header: 'Max Contact Load', render: (t) => <span>{t.maxHrs} hrs / week</span> },
            { key: 'verified', header: 'Eligibility Status', render: () => <StatusBadge status="PUBLISHED" label="Eligible" size="sm" /> },
          ]}
          data={teachersData}
          keyExtractor={(t) => t.id}
        />
      )}
    </div>
  );
};

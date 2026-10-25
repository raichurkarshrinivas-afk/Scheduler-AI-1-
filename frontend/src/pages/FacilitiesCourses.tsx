import React, { useState } from 'react';
import { Classroom, Course, Department, User } from '../types';
import { api } from '../services/api';

interface FacilitiesCoursesProps {
  classrooms: Classroom[];
  courses: Course[];
  departments: Department[];
  instructors: User[];
  onRefreshData: () => void;
}

export const FacilitiesCourses: React.FC<FacilitiesCoursesProps> = ({
  classrooms,
  courses,
  departments,
  onRefreshData,
}) => {
  const [activeSubTab, setActiveSubTab] = useState<'classrooms' | 'courses'>('classrooms');

  // New Classroom State
  const [cName, setCName] = useState('');
  const [cBuilding, setCBuilding] = useState('');
  const [cRoomNumber, setCRoomNumber] = useState('');
  const [cCapacity, setCCapacity] = useState(30);
  const [cType, setCType] = useState('LECTURE_HALL');
  const [cRows, setCRows] = useState(5);
  const [cCols, setCCols] = useState(6);
  const [cError, setCError] = useState<string | null>(null);

  // New Course State
  const [courseCode, setCourseCode] = useState('');
  const [courseName, setCourseName] = useState('');
  const [courseDeptId, setCourseDeptId] = useState(departments[0]?.id || '');
  const [courseHours, setCourseHours] = useState(3);
  const [courseType, setCourseType] = useState('LECTURE');
  const [courseError, setCourseError] = useState<string | null>(null);

  const handleCreateClassroom = async (e: React.FormEvent) => {
    e.preventDefault();
    setCError(null);
    if (cRows * cCols < cCapacity) {
      setCError(`Physical grid dimensions (${cRows}x${cCols}=${cRows * cCols}) cannot be smaller than capacity (${cCapacity})`);
      return;
    }
    try {
      await api.createClassroom({
        name: cName,
        building: cBuilding,
        room_number: cRoomNumber,
        capacity: Number(cCapacity),
        room_type: cType,
        rows: Number(cRows),
        columns: Number(cCols),
      });
      setCName('');
      setCBuilding('');
      setCRoomNumber('');
      onRefreshData();
    } catch (err: any) {
      setCError(err.message);
    }
  };

  const handleCreateCourse = async (e: React.FormEvent) => {
    e.preventDefault();
    setCourseError(null);
    try {
      await api.createCourse({
        department_id: courseDeptId || departments[0]?.id,
        code: courseCode,
        name: courseName,
        weekly_hours: Number(courseHours),
        course_type: courseType,
      });
      setCourseCode('');
      setCourseName('');
      onRefreshData();
    } catch (err: any) {
      setCourseError(err.message);
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <div>
          <h2 style={{ fontSize: '1.5rem', marginBottom: '0.25rem' }}>Facilities, Curriculum & Academic Structure</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            Configure classroom grid matrices, laboratories, courses, and department offerings.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            className={`btn-secondary ${activeSubTab === 'classrooms' ? 'active' : ''}`}
            onClick={() => setActiveSubTab('classrooms')}
          >
            Classrooms & Labs ({classrooms.length})
          </button>
          <button
            className={`btn-secondary ${activeSubTab === 'courses' ? 'active' : ''}`}
            onClick={() => setActiveSubTab('courses')}
          >
            Courses & Curriculum ({courses.length})
          </button>
        </div>
      </div>

      {activeSubTab === 'classrooms' ? (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: '2rem' }}>
          {/* Classrooms List */}
          <div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1rem' }}>
              {classrooms.map(c => (
                <div key={c.id} className="stat-card">
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                    <span style={{ fontWeight: 600, fontSize: '1.1rem' }}>{c.name}</span>
                    <span className="role-pill">{c.room_type}</span>
                  </div>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                    {c.building} • Room {c.room_number}
                  </div>
                  <div style={{ marginTop: '1rem', display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    <span>Capacity: <strong style={{ color: 'white' }}>{c.capacity}</strong></span>
                    <span>Grid: <strong style={{ color: 'white' }}>{c.rows}&times;{c.columns}</strong> ({c.rows * c.columns} desks)</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* New Classroom Form */}
          <div className="stat-card">
            <h3 style={{ fontSize: '1.1rem', marginBottom: '1rem' }}>Add Facility / Classroom</h3>
            {cError && (
              <div className="conflict-banner" style={{ padding: '0.75rem' }}>
                <div className="conflict-banner-msg">{cError}</div>
              </div>
            )}
            <form onSubmit={handleCreateClassroom}>
              <div className="form-group">
                <label className="form-label">Room Name</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. Computing Lab B"
                  value={cName}
                  onChange={(e) => setCName(e.target.value)}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">Building / Wing</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. Science Complex"
                  value={cBuilding}
                  onChange={(e) => setCBuilding(e.target.value)}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">Room Number</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. SC-301"
                  value={cRoomNumber}
                  onChange={(e) => setCRoomNumber(e.target.value)}
                  required
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                <div className="form-group">
                  <label className="form-label">Capacity</label>
                  <input
                    type="number"
                    className="form-input"
                    value={cCapacity}
                    onChange={(e) => setCCapacity(Number(e.target.value))}
                    min={1}
                    required
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Type</label>
                  <select
                    className="form-select"
                    value={cType}
                    onChange={(e) => setCType(e.target.value)}
                  >
                    <option value="LECTURE_HALL">Lecture Hall</option>
                    <option value="COMPUTER_LAB">Computer Lab</option>
                    <option value="SEMINAR_ROOM">Seminar Room</option>
                  </select>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                <div className="form-group">
                  <label className="form-label">Matrix Rows</label>
                  <input
                    type="number"
                    className="form-input"
                    value={cRows}
                    onChange={(e) => setCRows(Number(e.target.value))}
                    min={1}
                    required
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Matrix Columns</label>
                  <input
                    type="number"
                    className="form-input"
                    value={cCols}
                    onChange={(e) => setCCols(Number(e.target.value))}
                    min={1}
                    required
                  />
                </div>
              </div>

              <button type="submit" className="btn-primary" style={{ width: '100%', marginTop: '0.5rem' }}>
                Create Classroom
              </button>
            </form>
          </div>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: '2rem' }}>
          {/* Courses List */}
          <div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1rem' }}>
              {courses.map(course => (
                <div key={course.id} className="stat-card">
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                    <span style={{ fontWeight: 700, fontSize: '1.1rem', color: '#818cf8' }}>{course.code}</span>
                    <span className="role-pill">{course.course_type}</span>
                  </div>
                  <div style={{ fontWeight: 600, fontSize: '0.95rem', marginBottom: '0.5rem' }}>
                    {course.name}
                  </div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    Weekly Lecture Hours: <strong style={{ color: 'white' }}>{course.weekly_hours} hrs</strong>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* New Course Form */}
          <div className="stat-card">
            <h3 style={{ fontSize: '1.1rem', marginBottom: '1rem' }}>Register Course</h3>
            {courseError && (
              <div className="conflict-banner" style={{ padding: '0.75rem' }}>
                <div className="conflict-banner-msg">{courseError}</div>
              </div>
            )}
            <form onSubmit={handleCreateCourse}>
              <div className="form-group">
                <label className="form-label">Course Code</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. CS401"
                  value={courseCode}
                  onChange={(e) => setCourseCode(e.target.value)}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">Course Name</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. Distributed Systems"
                  value={courseName}
                  onChange={(e) => setCourseName(e.target.value)}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">Department</label>
                <select
                  className="form-select"
                  value={courseDeptId}
                  onChange={(e) => setCourseDeptId(e.target.value)}
                >
                  {departments.map(d => (
                    <option key={d.id} value={d.id}>{d.code} - {d.name}</option>
                  ))}
                </select>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                <div className="form-group">
                  <label className="form-label">Weekly Hours</label>
                  <input
                    type="number"
                    className="form-input"
                    value={courseHours}
                    onChange={(e) => setCourseHours(Number(e.target.value))}
                    min={1}
                    max={12}
                    required
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Format</label>
                  <select
                    className="form-select"
                    value={courseType}
                    onChange={(e) => setCourseType(e.target.value)}
                  >
                    <option value="LECTURE">Lecture</option>
                    <option value="LAB">Lab Session</option>
                  </select>
                </div>
              </div>

              <button type="submit" className="btn-primary" style={{ width: '100%', marginTop: '0.5rem' }}>
                Register Course
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

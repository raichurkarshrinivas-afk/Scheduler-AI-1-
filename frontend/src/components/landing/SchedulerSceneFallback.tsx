import React from 'react';

export interface SchedulerSceneFallbackProps {
  activeFocus?: 'timetables' | 'practicals' | 'seating';
  className?: string;
}

export const SchedulerSceneFallback: React.FC<SchedulerSceneFallbackProps> = ({
  activeFocus = 'timetables',
  className = '',
}) => {
  return (
    <div
      className={`relative w-full aspect-[4/3] max-w-[560px] mx-auto flex items-center justify-center p-4 ${className}`}
      role="img"
      aria-label="Illustrative spatial diagram of Scheduler: weekly timetable board, examination seating grid, and practical lab workstations"
    >
      <svg
        viewBox="0 0 540 420"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="w-full h-full drop-shadow-elevated select-none"
      >
        <defs>
          <linearGradient id="boardGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#FFFFFF" />
            <stop offset="100%" stopColor="#F7F8FA" />
          </linearGradient>
          <linearGradient id="navyEdge" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#1E2E4E" />
            <stop offset="100%" stopColor="#14213D" />
          </linearGradient>
          <filter id="softShadow" x="-10%" y="-10%" width="125%" height="125%">
            <feDropShadow dx="0" dy="12" stdDeviation="16" floodColor="#14213D" floodOpacity="0.08" />
          </filter>
        </defs>

        {/* Ambient Ground Glow */}
        <ellipse cx="270" cy="380" rx="210" ry="24" fill="#14213D" fillOpacity="0.04" />

        {/* 1. SEATING BOARD (Background Right) */}
        <g
          transform="translate(320, 45) scale(0.85)"
          opacity={activeFocus === 'seating' ? '1' : '0.75'}
          className="transition-all duration-300"
        >
          {/* Base Board */}
          <rect x="0" y="8" width="200" height="150" rx="14" fill="#CBD2DC" />
          <rect x="0" y="0" width="200" height="150" rx="14" fill="#FFFFFF" stroke="#E2E6EC" strokeWidth="2" filter="url(#softShadow)" />
          
          {/* Header pill */}
          <rect x="20" y="16" width="90" height="14" rx="7" fill="#E6F4F1" />
          <circle cx="28" cy="23" r="3.5" fill="#0E7C66" />
          <line x1="36" y1="23" x2="95" y2="23" stroke="#0E7C66" strokeWidth="2" strokeLinecap="round" />

          {/* Exam Benches Grid (4 rows x 5 cols) */}
          {[0, 1, 2, 3].map((r) =>
            [0, 1, 2, 3, 4].map((c) => {
              const isHighlight = (r === 1 && c === 2) || (activeFocus === 'seating' && r === 2 && c === 1);
              return (
                <rect
                  key={`b-${r}-${c}`}
                  x={22 + c * 32}
                  y={46 + r * 24}
                  width="22"
                  height="14"
                  rx="4"
                  fill={isHighlight ? '#0E7C66' : '#F7F8FA'}
                  stroke={isHighlight ? '#0E7C66' : '#CBD2DC'}
                  strokeWidth="1.5"
                />
              );
            })
          )}
          <rect x="140" y="16" width="40" height="10" rx="5" fill="#FEF7E8" />
        </g>

        {/* 2. PRACTICAL LAB BOARD (Background Left) */}
        <g
          transform="translate(10, 180) scale(0.85)"
          opacity={activeFocus === 'practicals' ? '1' : '0.8'}
          className="transition-all duration-300"
        >
          <rect x="0" y="8" width="190" height="140" rx="14" fill="#CBD2DC" />
          <rect x="0" y="0" width="190" height="140" rx="14" fill="#FFFFFF" stroke="#E2E6EC" strokeWidth="2" filter="url(#softShadow)" />
          
          <rect x="18" y="16" width="80" height="14" rx="7" fill="#EDF5FA" />
          <circle cx="26" cy="23" r="3.5" fill="#7EB8DA" />
          <line x1="34" y1="23" x2="85" y2="23" stroke="#7EB8DA" strokeWidth="2" strokeLinecap="round" />

          {/* Lab Workstations (3 rows x 3 cols) */}
          {[0, 1, 2].map((r) =>
            [0, 1, 2].map((c) => (
              <g key={`ws-${r}-${c}`} transform={`translate(${24 + c * 50}, ${44 + r * 28})`}>
                <rect x="0" y="0" width="36" height="18" rx="4" fill="#F7F8FA" stroke="#A89FD8" strokeWidth="1.5" />
                <rect x="8" y="4" width="20" height="10" rx="2" fill="#A89FD8" fillOpacity="0.4" />
              </g>
            ))
          )}
        </g>

        {/* 3. DOMINANT WEEKLY TIMETABLE BOARD (Center Foreground) */}
        <g
          transform="translate(70, 75)"
          opacity={activeFocus === 'timetables' ? '1' : '0.95'}
          className="transition-all duration-300"
        >
          {/* Subtle 3D extrusion slab (navy edge) */}
          <rect x="0" y="12" width="380" height="250" rx="18" fill="url(#navyEdge)" />
          {/* Main White Board Face */}
          <rect
            x="0"
            y="0"
            width="380"
            height="250"
            rx="18"
            fill="url(#boardGrad)"
            stroke="#E2E6EC"
            strokeWidth="2"
            filter="url(#softShadow)"
          />

          {/* Timetable Header Bar */}
          <rect x="18" y="16" width="344" height="26" rx="8" fill="#F7F8FA" stroke="#E2E6EC" strokeWidth="1" />
          <circle cx="32" cy="29" r="4.5" fill="#0E7C66" />
          <rect x="44" y="24" width="70" height="10" rx="5" fill="#14213D" fillOpacity="0.8" />
          <rect x="124" y="25" width="45" height="8" rx="4" fill="#CBD2DC" />

          {/* Validation Tag on Board */}
          <g transform="translate(290, 20)">
            <rect x="0" y="0" width="62" height="18" rx="9" fill="#E6F4F1" stroke="#0E7C66" strokeWidth="1" />
            <circle cx="10" cy="9" r="3" fill="#0E7C66" />
            <line x1="16" y1="9" x2="52" y2="9" stroke="#0E7C66" strokeWidth="1.5" strokeLinecap="round" />
          </g>

          {/* 5 Day Column Lines & Header indicators */}
          {[0, 1, 2, 3, 4].map((d) => (
            <g key={`day-${d}`} transform={`translate(${22 + d * 68}, 52)`}>
              {/* Day title pill */}
              <rect x="0" y="0" width="62" height="12" rx="6" fill="#F1F3F6" />
              {/* Column divider */}
              {d < 4 && <line x1="65" y1="0" x2="65" y2="185" stroke="#E2E6EC" strokeWidth="1" strokeDasharray="3 3" />}
            </g>
          ))}

          {/* Scheduled Session Blocks */}
          {/* Monday: Teal + Lavender */}
          <rect x="22" y="70" width="62" height="34" rx="6" fill="#0E7C66" />
          <rect x="30" y="76" width="32" height="6" rx="3" fill="#FFFFFF" fillOpacity="0.8" />
          <rect x="30" y="86" width="44" height="5" rx="2.5" fill="#E6F4F1" fillOpacity="0.6" />

          <rect x="22" y="112" width="62" height="28" rx="6" fill="#A89FD8" />
          <rect x="30" y="118" width="36" height="5" rx="2.5" fill="#FFFFFF" fillOpacity="0.9" />

          {/* Tuesday: Ice Blue + Amber + Teal */}
          <rect x="90" y="70" width="62" height="28" rx="6" fill="#7EB8DA" />
          <rect x="98" y="76" width="40" height="5" rx="2.5" fill="#FFFFFF" fillOpacity="0.9" />

          <rect x="90" y="106" width="62" height="28" rx="6" fill="#F2B134" />
          <rect x="98" y="112" width="34" height="5" rx="2.5" fill="#FFFFFF" fillOpacity="0.9" />

          <rect x="90" y="142" width="62" height="42" rx="6" fill="#0E7C66" />
          <rect x="98" y="148" width="38" height="6" rx="3" fill="#FFFFFF" fillOpacity="0.8" />

          {/* Wednesday: Double-length Practical Block (Featured) */}
          <rect x="158" y="70" width="62" height="74" rx="8" fill="#14213D" stroke="#0E7C66" strokeWidth="1.5" />
          <rect x="166" y="78" width="30" height="7" rx="3.5" fill="#0E7C66" />
          <rect x="166" y="90" width="44" height="6" rx="3" fill="#FFFFFF" fillOpacity="0.9" />
          <rect x="166" y="100" width="38" height="5" rx="2.5" fill="#CBD2DC" />
          <circle cx="172" cy="126" r="3.5" fill="#F2B134" />
          <rect x="180" y="123" width="30" height="5" rx="2.5" fill="#FFFFFF" fillOpacity="0.7" />

          {/* Lunch / Break Bar (Horizontal band) */}
          <rect x="18" y="192" width="344" height="8" rx="4" fill="#F1F3F6" stroke="#CBD2DC" strokeWidth="0.8" strokeDasharray="4 2" />

          {/* Thursday: Lavender + Ice Blue */}
          <rect x="226" y="70" width="62" height="34" rx="6" fill="#A89FD8" />
          <rect x="234" y="77" width="36" height="5" rx="2.5" fill="#FFFFFF" fillOpacity="0.9" />

          <rect x="226" y="112" width="62" height="32" rx="6" fill="#7EB8DA" />
          <rect x="234" y="119" width="40" height="5" rx="2.5" fill="#FFFFFF" fillOpacity="0.9" />

          {/* Friday: Amber + Teal */}
          <rect x="294" y="70" width="62" height="30" rx="6" fill="#F2B134" />
          <rect x="302" y="77" width="36" height="5" rx="2.5" fill="#FFFFFF" fillOpacity="0.9" />

          <rect x="294" y="108" width="62" height="40" rx="6" fill="#0E7C66" />
          <rect x="302" y="115" width="42" height="6" rx="3" fill="#FFFFFF" fillOpacity="0.8" />
        </g>

        {/* 4. VALIDATION TOKEN BADGE (Foreground Accent) */}
        <g transform="translate(390, 275)" filter="url(#softShadow)">
          <rect x="0" y="6" width="95" height="48" rx="14" fill="#CBD2DC" />
          <rect x="0" y="0" width="95" height="48" rx="14" fill="#FFFFFF" stroke="#0E7C66" strokeWidth="2" />
          <circle cx="26" cy="24" r="13" fill="#E6F4F1" />
          {/* Checkmark icon */}
          <path d="M20 24L24 28L32 19" stroke="#0E7C66" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
          {/* Status text bars */}
          <rect x="46" y="17" width="38" height="6" rx="3" fill="#14213D" />
          <rect x="46" y="27" width="28" height="5" rx="2.5" fill="#0E7C66" />
        </g>
      </svg>
    </div>
  );
};

import React, { useState, useRef } from 'react';
import { ArrowDown, LogIn } from 'lucide-react';
import { Button } from '../common/Button';
import { SchedulerSceneContainer } from './SchedulerSceneContainer';
import { useReducedMotion } from '../../hooks/useReducedMotion';
import { useElementVisibility } from '../../hooks/useElementVisibility';

export interface HeroSectionProps {
  onLoginClick: () => void;
}

export const HeroSection: React.FC<HeroSectionProps> = ({ onLoginClick }) => {
  const [activeFocus, setActiveFocus] = useState<'timetables' | 'practicals' | 'seating'>('timetables');
  const heroRef = useRef<HTMLDivElement>(null);
  const isVisible = useElementVisibility(heroRef);
  const reducedMotion = useReducedMotion();

  const handleExploreClick = () => {
    const el = document.querySelector('#product-modules');
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const sceneExplanations = {
    timetables: {
      title: 'Weekly Academic Schedule',
      desc: 'Floating 5-day timetable slab with lecture, tutorial, and double-length practical session allocations.',
      color: 'border-teal/30 bg-teal-light text-teal',
    },
    practicals: {
      title: 'Practical Laboratory Matrix',
      desc: 'Workstation terminal grid mapping hardware features, GPU capabilities, and software assignments.',
      color: 'border-ice/40 bg-ice-light text-navy',
    },
    seating: {
      title: 'Theory Examination Desks',
      desc: 'Orthogonal anti-cheating seating plan allocating one candidate per usable bench with spacing safeguards.',
      color: 'border-amber/40 bg-amber-light text-navy',
    },
  };

  return (
    <section
      ref={heroRef}
      className="relative overflow-hidden pt-8 pb-16 lg:pt-14 lg:pb-24 border-b border-border/70"
      aria-labelledby="hero-heading"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-8 items-center">
          {/* Left Column: Semantic Headline & Direct Actions */}
          <div className="lg:col-span-6 space-y-6 text-center lg:text-left">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white border border-border text-xs font-medium text-navy-muted shadow-subtle">
              <span className="w-2 h-2 rounded-full bg-teal" aria-hidden="true" />
              <span>Multi-Tenant Educational Scheduling Engine</span>
            </div>

            <h1
              id="hero-heading"
              className="font-heading text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-navy leading-[1.12]"
            >
              Less scheduling.
              <br />
              <span className="text-teal">More teaching.</span>
            </h1>

            <p className="text-base sm:text-lg text-navy-muted leading-relaxed max-w-xl mx-auto lg:mx-0">
              Plan classes, organise practicals, and assign exam seats in one clear, connected workspace.
            </p>

            <div className="flex flex-wrap items-center justify-center lg:justify-start gap-3.5 pt-2">
              <Button
                variant="primary"
                size="lg"
                onClick={handleExploreClick}
                rightIcon={<ArrowDown className="w-4 h-4" />}
                id="hero-explore-btn"
              >
                Explore Scheduler
              </Button>

              <Button
                variant="secondary"
                size="lg"
                onClick={onLoginClick}
                leftIcon={<LogIn className="w-4 h-4" />}
                id="hero-login-btn"
              >
                Log in
              </Button>
            </div>

            <div className="pt-2 text-xs text-navy-subtle flex items-center justify-center lg:justify-start gap-2 select-none">
              <span className="w-1.5 h-1.5 rounded-full bg-navy-subtle" aria-hidden="true" />
              <span>Deterministic constraint solving &bull; Zero external AI dependencies</span>
            </div>
          </div>

          {/* Right Column: 3D Composition & Scene Controls */}
          <div className="lg:col-span-6 flex flex-col items-center">
            {/* Illustrative Product Preview Label */}
            <div className="w-full flex items-center justify-between mb-2 px-2 text-xs text-navy-subtle">
              <span className="font-medium tracking-wide uppercase text-[11px] bg-bg px-2.5 py-0.5 rounded border border-border">
                Illustrative product preview
              </span>
              <span className="hidden sm:inline text-navy-subtle/80">
                {reducedMotion ? 'Static presentation' : 'Interactive spatial scene'}
              </span>
            </div>

            {/* 3D Scene Viewport / Fallback */}
            <div className="w-full bg-white/70 border border-border rounded-2xl p-2 sm:p-4 shadow-card backdrop-blur-sm">
              <SchedulerSceneContainer
                activeFocus={activeFocus}
                reducedMotion={reducedMotion}
                isVisible={isVisible}
              />

              {/* Accessible Interactive Scene Controls */}
              <div className="mt-3 pt-3 border-t border-border/80 flex flex-col sm:flex-row items-center justify-between gap-3">
                <div
                  className="flex items-center gap-1.5 bg-bg p-1 rounded-lg border border-border"
                  role="group"
                  aria-label="3D scene inspection perspective"
                >
                  <button
                    type="button"
                    onClick={() => setActiveFocus('timetables')}
                    className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all focus-visible:outline-2 focus-visible:outline-teal ${
                      activeFocus === 'timetables'
                        ? 'bg-white text-teal shadow-subtle font-semibold'
                        : 'text-navy-muted hover:text-navy'
                    }`}
                    aria-pressed={activeFocus === 'timetables'}
                  >
                    Timetables
                  </button>

                  <button
                    type="button"
                    onClick={() => setActiveFocus('practicals')}
                    className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all focus-visible:outline-2 focus-visible:outline-teal ${
                      activeFocus === 'practicals'
                        ? 'bg-white text-navy shadow-subtle font-semibold'
                        : 'text-navy-muted hover:text-navy'
                    }`}
                    aria-pressed={activeFocus === 'practicals'}
                  >
                    Practical exams
                  </button>

                  <button
                    type="button"
                    onClick={() => setActiveFocus('seating')}
                    className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all focus-visible:outline-2 focus-visible:outline-teal ${
                      activeFocus === 'seating'
                        ? 'bg-white text-teal shadow-subtle font-semibold'
                        : 'text-navy-muted hover:text-navy'
                    }`}
                    aria-pressed={activeFocus === 'seating'}
                  >
                    Theory seating
                  </button>
                </div>

                {/* Nearby Active HTML Explanation */}
                <div
                  className={`text-xs px-3 py-1.5 rounded-lg border max-w-xs transition-all ${sceneExplanations[activeFocus].color}`}
                  role="status"
                  aria-live="polite"
                >
                  <strong className="block font-semibold">{sceneExplanations[activeFocus].title}</strong>
                  <span className="opacity-90 leading-tight block">{sceneExplanations[activeFocus].desc}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

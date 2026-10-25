import React, { Suspense, lazy, useState, useEffect } from 'react';
import { SchedulerSceneFallback } from './SchedulerSceneFallback';
import { Skeleton } from '../common/Skeleton';

// Lazy-load the 3D scene to keep Three.js out of the initial critical render and authenticated bundles
const SchedulerSceneLazy = lazy(() => import('./SchedulerScene'));

interface ErrorBoundaryProps {
  fallback: React.ReactNode;
  children: React.ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
}

class SceneErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: any) {
    // Graceful fallback without crashing page
    console.warn('WebGL/3D Scene initialization notice: Falling back to vector illustration.', error);
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback;
    }
    return this.props.children;
  }
}

export interface SchedulerSceneContainerProps {
  activeFocus: 'timetables' | 'practicals' | 'seating';
  reducedMotion: boolean;
  isVisible: boolean;
}

export const SchedulerSceneContainer: React.FC<SchedulerSceneContainerProps> = (props) => {
  const [hasWebGL, setHasWebGL] = useState<boolean>(true);

  useEffect(() => {
    try {
      const canvas = document.createElement('canvas');
      const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
      setHasWebGL(Boolean(gl));
    } catch {
      setHasWebGL(false);
    }
  }, []);

  // When WebGL is unsupported or reduced motion is requested, provide the local high-fidelity SVG illustration
  if (!hasWebGL || props.reducedMotion) {
    return <SchedulerSceneFallback activeFocus={props.activeFocus} />;
  }

  return (
    <SceneErrorBoundary fallback={<SchedulerSceneFallback activeFocus={props.activeFocus} />}>
      <Suspense
        fallback={
          <div className="relative w-full h-[400px] sm:h-[460px] md:h-[500px] max-w-[620px] mx-auto flex items-center justify-center p-6">
            <Skeleton variant="rect" className="w-full h-full max-w-[540px] max-h-[380px]" />
          </div>
        }
      >
        <SchedulerSceneLazy {...props} />
      </Suspense>
    </SceneErrorBoundary>
  );
};

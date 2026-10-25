import React, { useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import * as THREE from 'three';

export interface SchedulerSceneProps {
  activeFocus: 'timetables' | 'practicals' | 'seating';
  reducedMotion: boolean;
  isVisible: boolean;
}

// 1. Dominant Weekly Timetable Board (Procedural)
function TimetableBoard({ isFocused }: { isFocused: boolean }) {
  const groupRef = useRef<THREE.Group>(null);

  // Materials memoized to avoid GPU churn
  const materials = useMemo(() => {
    return {
      face: new THREE.MeshStandardMaterial({ color: '#FFFFFF', roughness: 0.3, metalness: 0.05 }),
      frame: new THREE.MeshStandardMaterial({ color: '#14213D', roughness: 0.4, metalness: 0.1 }),
      teal: new THREE.MeshStandardMaterial({ color: '#0E7C66', roughness: 0.35 }),
      ice: new THREE.MeshStandardMaterial({ color: '#7EB8DA', roughness: 0.4 }),
      amber: new THREE.MeshStandardMaterial({ color: '#F2B134', roughness: 0.35 }),
      lavender: new THREE.MeshStandardMaterial({ color: '#A89FD8', roughness: 0.4 }),
      breakBar: new THREE.MeshStandardMaterial({ color: '#E2E6EC', roughness: 0.6 }),
      header: new THREE.MeshStandardMaterial({ color: '#F7F8FA', roughness: 0.5 }),
    };
  }, []);

  useFrame(() => {
    if (!groupRef.current) return;
    const targetScale = isFocused ? 1.03 : 0.98;
    groupRef.current.scale.lerp(new THREE.Vector3(targetScale, targetScale, targetScale), 0.08);
  });

  return (
    <group ref={groupRef} position={[0, -0.1, 0.4]} rotation={[-0.15, 0.22, 0.06]}>
      {/* Navy Backing / Frame Extrusion */}
      <mesh position={[0, 0, -0.08]}>
        <boxGeometry args={[4.4, 2.9, 0.16]} />
        <primitive object={materials.frame} attach="material" />
      </mesh>

      {/* Main White Board Face */}
      <mesh position={[0, 0, 0.02]}>
        <boxGeometry args={[4.3, 2.8, 0.08]} />
        <primitive object={materials.face} attach="material" />
      </mesh>

      {/* Top Header Track */}
      <mesh position={[0, 1.15, 0.07]}>
        <boxGeometry args={[4.0, 0.28, 0.02]} />
        <primitive object={materials.header} attach="material" />
      </mesh>

      {/* 5 Day Column Background Tracks */}
      {[-1.56, -0.78, 0, 0.78, 1.56].map((x, idx) => (
        <group key={`col-${idx}`} position={[x, 0, 0.06]}>
          {/* Day Header Pill */}
          <mesh position={[0, 1.15, 0.02]}>
            <boxGeometry args={[0.68, 0.16, 0.02]} />
            <primitive object={materials.breakBar} attach="material" />
          </mesh>
        </group>
      ))}

      {/* Column 1 (Monday): Teal + Lavender */}
      <mesh position={[-1.56, 0.72, 0.1]}>
        <boxGeometry args={[0.7, 0.48, 0.06]} />
        <primitive object={materials.teal} attach="material" />
      </mesh>
      <mesh position={[-1.56, 0.15, 0.1]}>
        <boxGeometry args={[0.7, 0.42, 0.06]} />
        <primitive object={materials.lavender} attach="material" />
      </mesh>

      {/* Column 2 (Tuesday): Ice Blue + Amber */}
      <mesh position={[-0.78, 0.75, 0.1]}>
        <boxGeometry args={[0.7, 0.4, 0.06]} />
        <primitive object={materials.ice} attach="material" />
      </mesh>
      <mesh position={[-0.78, 0.22, 0.1]}>
        <boxGeometry args={[0.7, 0.42, 0.06]} />
        <primitive object={materials.amber} attach="material" />
      </mesh>
      <mesh position={[-0.78, -0.32, 0.1]}>
        <boxGeometry args={[0.7, 0.45, 0.06]} />
        <primitive object={materials.teal} attach="material" />
      </mesh>

      {/* Column 3 (Wednesday): Double-length Featured Practical Block */}
      <mesh position={[0, 0.46, 0.12]}>
        <boxGeometry args={[0.72, 0.98, 0.08]} />
        <primitive object={materials.frame} attach="material" />
      </mesh>
      {/* Accent badge inside double-length block */}
      <mesh position={[0, 0.75, 0.17]}>
        <boxGeometry args={[0.45, 0.14, 0.02]} />
        <primitive object={materials.teal} attach="material" />
      </mesh>

      {/* Lunch / Break Bar (Horizontal band) */}
      <mesh position={[0, -0.62, 0.07]}>
        <boxGeometry args={[4.0, 0.08, 0.02]} />
        <primitive object={materials.breakBar} attach="material" />
      </mesh>

      {/* Column 4 (Thursday): Lavender + Ice */}
      <mesh position={[0.78, 0.72, 0.1]}>
        <boxGeometry args={[0.7, 0.46, 0.06]} />
        <primitive object={materials.lavender} attach="material" />
      </mesh>
      <mesh position={[0.78, 0.16, 0.1]}>
        <boxGeometry args={[0.7, 0.42, 0.06]} />
        <primitive object={materials.ice} attach="material" />
      </mesh>

      {/* Column 5 (Friday): Amber + Teal */}
      <mesh position={[1.56, 0.74, 0.1]}>
        <boxGeometry args={[0.7, 0.42, 0.06]} />
        <primitive object={materials.amber} attach="material" />
      </mesh>
      <mesh position={[1.56, 0.18, 0.1]}>
        <boxGeometry args={[0.7, 0.52, 0.06]} />
        <primitive object={materials.teal} attach="material" />
      </mesh>
    </group>
  );
}

// 2. Supporting Examination Seating Board (Rear Right)
function SeatingBoard({ isFocused }: { isFocused: boolean }) {
  const groupRef = useRef<THREE.Group>(null);

  const materials = useMemo(() => {
    return {
      face: new THREE.MeshStandardMaterial({ color: '#FFFFFF', roughness: 0.35 }),
      frame: new THREE.MeshStandardMaterial({ color: '#CBD2DC', roughness: 0.5 }),
      benchNormal: new THREE.MeshStandardMaterial({ color: '#F1F3F6', roughness: 0.4 }),
      benchHighlight: new THREE.MeshStandardMaterial({ color: '#0E7C66', roughness: 0.25 }),
    };
  }, []);

  useFrame(() => {
    if (!groupRef.current) return;
    const targetScale = isFocused ? 1.12 : 0.9;
    const targetZ = isFocused ? 0.3 : -0.7;
    groupRef.current.scale.lerp(new THREE.Vector3(targetScale, targetScale, targetScale), 0.08);
    groupRef.current.position.z = THREE.MathUtils.lerp(groupRef.current.position.z, targetZ, 0.08);
  });

  return (
    <group ref={groupRef} position={[2.5, 0.8, -0.7]} rotation={[-0.2, -0.28, 0.08]}>
      {/* Board Slab */}
      <mesh position={[0, 0, 0]}>
        <boxGeometry args={[2.4, 1.8, 0.1]} />
        <primitive object={materials.face} attach="material" />
      </mesh>
      <mesh position={[0, 0, -0.06]}>
        <boxGeometry args={[2.46, 1.86, 0.06]} />
        <primitive object={materials.frame} attach="material" />
      </mesh>

      {/* Grid of Exam Desks / Benches */}
      {[-0.8, -0.26, 0.28, 0.8].map((x, c) =>
        [-0.55, -0.15, 0.25, 0.65].map((y, r) => {
          const isHighlight = c === 1 && r === 2;
          return (
            <mesh key={`desk-${c}-${r}`} position={[x, y, 0.08]}>
              <boxGeometry args={[0.38, 0.22, 0.05]} />
              <primitive object={isHighlight ? materials.benchHighlight : materials.benchNormal} attach="material" />
            </mesh>
          );
        })
      )}
    </group>
  );
}

// 3. Supporting Practical Lab Board (Bottom Left)
function LabBoard({ isFocused }: { isFocused: boolean }) {
  const groupRef = useRef<THREE.Group>(null);

  const materials = useMemo(() => {
    return {
      face: new THREE.MeshStandardMaterial({ color: '#FFFFFF', roughness: 0.35 }),
      frame: new THREE.MeshStandardMaterial({ color: '#CBD2DC', roughness: 0.5 }),
      terminal: new THREE.MeshStandardMaterial({ color: '#F1F3F6', roughness: 0.4 }),
      screen: new THREE.MeshStandardMaterial({ color: '#A89FD8', roughness: 0.3 }),
      accent: new THREE.MeshStandardMaterial({ color: '#7EB8DA', roughness: 0.3 }),
    };
  }, []);

  useFrame(() => {
    if (!groupRef.current) return;
    const targetScale = isFocused ? 1.12 : 0.88;
    const targetZ = isFocused ? 0.35 : -0.5;
    groupRef.current.scale.lerp(new THREE.Vector3(targetScale, targetScale, targetScale), 0.08);
    groupRef.current.position.z = THREE.MathUtils.lerp(groupRef.current.position.z, targetZ, 0.08);
  });

  return (
    <group ref={groupRef} position={[-2.4, -0.85, -0.5]} rotation={[-0.1, 0.35, -0.06]}>
      {/* Board Base */}
      <mesh position={[0, 0, 0]}>
        <boxGeometry args={[2.3, 1.7, 0.1]} />
        <primitive object={materials.face} attach="material" />
      </mesh>
      <mesh position={[0, 0, -0.06]}>
        <boxGeometry args={[2.36, 1.76, 0.06]} />
        <primitive object={materials.frame} attach="material" />
      </mesh>

      {/* Workstation Terminals (3 x 3) */}
      {[-0.7, 0, 0.7].map((x, c) =>
        [-0.45, 0.05, 0.55].map((y, r) => (
          <group key={`ws-${c}-${r}`} position={[x, y, 0.08]}>
            <mesh position={[0, 0, 0]}>
              <boxGeometry args={[0.42, 0.24, 0.04]} />
              <primitive object={materials.terminal} attach="material" />
            </mesh>
            <mesh position={[0, 0.03, 0.03]}>
              <boxGeometry args={[0.26, 0.14, 0.02]} />
              <primitive object={r === 1 && c === 1 ? materials.accent : materials.screen} attach="material" />
            </mesh>
          </group>
        ))
      )}
    </group>
  );
}

// 4. Validation Badge Tile (Floating Foreground)
function ValidationTile() {
  const materials = useMemo(() => {
    return {
      badge: new THREE.MeshStandardMaterial({ color: '#FFFFFF', roughness: 0.2 }),
      teal: new THREE.MeshStandardMaterial({ color: '#0E7C66', roughness: 0.3 }),
      ring: new THREE.MeshStandardMaterial({ color: '#E6F4F1', roughness: 0.4 }),
    };
  }, []);

  return (
    <group position={[1.9, -1.1, 0.9]} rotation={[-0.12, 0.1, 0.04]}>
      {/* Base Badge */}
      <mesh position={[0, 0, 0]}>
        <boxGeometry args={[1.1, 0.65, 0.08]} />
        <primitive object={materials.badge} attach="material" />
      </mesh>
      {/* Check Circle */}
      <mesh position={[-0.26, 0, 0.05]}>
        <cylinderGeometry args={[0.18, 0.18, 0.03, 24]} />
        <primitive object={materials.ring} attach="material" />
      </mesh>
      {/* Checkmark Core */}
      <mesh position={[-0.26, 0, 0.07]}>
        <boxGeometry args={[0.12, 0.12, 0.02]} />
        <primitive object={materials.teal} attach="material" />
      </mesh>
      {/* Text Indicator Bar */}
      <mesh position={[0.18, 0.06, 0.05]}>
        <boxGeometry args={[0.42, 0.08, 0.02]} />
        <primitive object={materials.teal} attach="material" />
      </mesh>
      <mesh position={[0.18, -0.08, 0.05]}>
        <boxGeometry args={[0.3, 0.06, 0.02]} />
        <primitive object={materials.ring} attach="material" />
      </mesh>
    </group>
  );
}

// 5. Root Scene Assembly with Pointer Parallax & Idle Floating
function SceneContent({ activeFocus, reducedMotion, isVisible }: SchedulerSceneProps) {
  const sceneGroupRef = useRef<THREE.Group>(null);
  const pointerTarget = useRef<{ x: number; y: number }>({ x: 0, y: 0 });

  // Listen to clamped pointer motion on window
  React.useEffect(() => {
    if (reducedMotion || !isVisible) return;

    const handlePointerMove = (e: PointerEvent) => {
      // Normalize to -1 ... 1
      const x = (e.clientX / window.innerWidth) * 2 - 1;
      const y = -(e.clientY / window.innerHeight) * 2 + 1;
      // Clamp to subtle rotation range (max ~0.12 rad / 7 degrees)
      pointerTarget.current.x = Math.max(-0.12, Math.min(0.12, x * 0.12));
      pointerTarget.current.y = Math.max(-0.1, Math.min(0.1, y * 0.1));
    };

    window.addEventListener('pointermove', handlePointerMove, { passive: true });
    return () => window.removeEventListener('pointermove', handlePointerMove);
  }, [reducedMotion, isVisible]);

  useFrame((state) => {
    if (!sceneGroupRef.current) return;

    if (!reducedMotion && isVisible) {
      // Smooth pointer parallax damping
      sceneGroupRef.current.rotation.y = THREE.MathUtils.lerp(
        sceneGroupRef.current.rotation.y,
        pointerTarget.current.x,
        0.05
      );
      sceneGroupRef.current.rotation.x = THREE.MathUtils.lerp(
        sceneGroupRef.current.rotation.x,
        -pointerTarget.current.y * 0.8,
        0.05
      );

      // Subtle idle breathing float
      const t = state.clock.getElapsedTime();
      sceneGroupRef.current.position.y = Math.sin(t * 1.2) * 0.04;
    }
  });

  return (
    <group ref={sceneGroupRef}>
      <ambientLight intensity={1.1} />
      <directionalLight position={[5, 8, 6]} intensity={1.4} castShadow={false} />
      <directionalLight position={[-6, -4, -3]} intensity={0.5} color="#EDF5FA" />

      {/* Main Dominant Board */}
      <TimetableBoard isFocused={activeFocus === 'timetables'} />

      {/* Supporting Boards */}
      <SeatingBoard isFocused={activeFocus === 'seating'} />
      <LabBoard isFocused={activeFocus === 'practicals'} />

      {/* Validation Badge */}
      <ValidationTile />
    </group>
  );
}

export const SchedulerScene: React.FC<SchedulerSceneProps> = (props) => {
  return (
    <div
      className="relative w-full h-[400px] sm:h-[460px] md:h-[500px] max-w-[620px] mx-auto select-none"
      tabIndex={-1}
      aria-hidden="true"
    >
      <Canvas
        camera={{ position: [0, 0.4, 6.8], fov: 38 }}
        dpr={[1, 1.5]}
        gl={{ antialias: true, alpha: true, powerPreference: 'high-performance' }}
        frameloop={props.isVisible && !props.reducedMotion ? 'always' : 'demand'}
        style={{ pointerEvents: 'none' }}
      >
        <SceneContent {...props} />
      </Canvas>
    </div>
  );
};

export default SchedulerScene;

import React, { useRef } from 'react';
import { useCurrentFrame, useVideoConfig } from 'remotion';
import { ThreeCanvas } from '@remotion/three';
import * as THREE from 'three';
import { ThreeParams, ThemeTokens } from '../types';
import { frameToRadian } from '../utils/math';

interface ThreeSceneProps {
  threeParams?: ThreeParams;
  theme: ThemeTokens;
  width: number;
  height: number;
}

/**
 * Inner mesh component evaluated deterministically.
 * Prohibits useFrame() (which uses requestAnimationFrame).
 * Instead, extracts useCurrentFrame() from Remotion context to compute angles.
 */
const DeterministicMesh: React.FC<{
  params: ThreeParams;
  theme: ThemeTokens;
}> = ({ params, theme }) => {
  const meshRef = useRef<THREE.Mesh>(null);
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Pure function: rotation = frameToRadian(frame, fps, speed)
  const rotX = frameToRadian(frame, fps, params.rotation_speed_x);
  const rotY = frameToRadian(frame, fps, params.rotation_speed_y);
  const rotZ = frameToRadian(frame, fps, params.rotation_speed_z);

  const meshColor = params.color || theme.accent_color;

  const renderGeometry = () => {
    switch (params.geometry) {
      case 'box':
        return <boxGeometry args={[1.8, 1.8, 1.8]} />;
      case 'sphere':
        return <sphereGeometry args={[1.3, 32, 32]} />;
      case 'torus':
        return <torusGeometry args={[1.2, 0.45, 24, 64]} />;
      case 'icosahedron':
        return <icosahedronGeometry args={[1.4, 1]} />;
      case 'cylinder':
        return <cylinderGeometry args={[1.0, 1.0, 2.0, 32]} />;
      default:
        return <torusGeometry args={[1.2, 0.45, 24, 64]} />;
    }
  };

  return (
    <mesh
      ref={meshRef}
      position={params.mesh_position}
      scale={params.mesh_scale}
      rotation={[rotX, rotY, rotZ]}
    >
      {renderGeometry()}
      <meshStandardMaterial
        color={meshColor}
        wireframe={params.wireframe}
        roughness={0.2}
        metalness={0.8}
        emissive={theme.primary_color}
        emissiveIntensity={0.3}
      />
    </mesh>
  );
};

export const ThreeScene: React.FC<ThreeSceneProps> = ({
  threeParams,
  theme,
  width,
  height,
}) => {
  const params: ThreeParams = threeParams || {
    geometry: 'torus',
    wireframe: true,
    camera_fov: 45,
    camera_position: [0, 0, 5],
    mesh_position: [0, 0, 0],
    mesh_scale: [1, 1, 1],
    rotation_speed_x: 0.2,
    rotation_speed_y: 0.5,
    rotation_speed_z: 0.0,
  };

  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        position: 'absolute',
        top: 0,
        left: 0,
        pointerEvents: 'none',
      }}
    >
      <ThreeCanvas
        width={width}
        height={height}
        camera={{
          fov: params.camera_fov,
          position: params.camera_position,
          near: 0.1,
          far: 1000,
        }}
        style={{
          width: '100%',
          height: '100%',
        }}
      >
        <ambientLight intensity={0.6} />
        <directionalLight position={[10, 10, 5]} intensity={1.5} color="#FFFFFF" />
        <pointLight position={[-10, -10, -5]} intensity={1.0} color={theme.primary_color} />
        <pointLight position={[5, -5, 5]} intensity={0.8} color={theme.accent_color} />

        <DeterministicMesh params={params} theme={theme} />
      </ThreeCanvas>
    </div>
  );
};

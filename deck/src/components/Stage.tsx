import { ContactShadows, Environment, Grid, Lightformer } from "@react-three/drei";
import { C } from "../lib";

// Lights, floor and a local environment (Lightformers, no HDR download) shared by every 3D scene.
export function Stage() {
  return (
    <>
      <color attach="background" args={[C.bg]} />
      <fog attach="fog" args={[C.bg, 12, 30]} />
      <ambientLight intensity={0.35} />
      <directionalLight position={[4, 8, 5]} intensity={1.6} castShadow shadow-mapSize={[2048, 2048]} />
      <pointLight position={[-4, 3, 3]} intensity={18} color={C.accent} distance={12} />
      <Environment resolution={256}>
        <Lightformer intensity={2} position={[0, 5, -6]} scale={[12, 4, 1]} />
        <Lightformer intensity={1} position={[-6, 2, 2]} rotation-y={Math.PI / 2} scale={[8, 2, 1]} color={C.accent} />
        <Lightformer intensity={0.8} position={[6, 2, 2]} rotation-y={-Math.PI / 2} scale={[8, 2, 1]} />
      </Environment>
      <Grid
        position={[0, -0.001, 0]}
        args={[40, 40]}
        cellSize={0.5}
        cellThickness={0.5}
        cellColor={C.border}
        sectionSize={2.5}
        sectionThickness={1}
        sectionColor={C.accentDim}
        fadeDistance={22}
        fadeStrength={1.5}
        infiniteGrid
      />
      <ContactShadows position={[0, 0.002, 0]} opacity={0.55} scale={16} blur={2.4} far={6} />
    </>
  );
}

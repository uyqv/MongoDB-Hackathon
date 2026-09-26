import { useMemo, useRef } from "react";
import { useFrame, type ThreeElements } from "@react-three/fiber";
import * as THREE from "three";
import { C, campaign, useClock } from "../lib";

// Real C3/Cz/C4 trace from PhysioNet eegmmidb S001 run 6 (via /api/eeg/preview, display only),
// scrolled past the camera as three glowing lines.
export function EegRibbons({ width = 18, amp = 0.012, speed = 0.35, ...props }: {
  width?: number; amp?: number; speed?: number;
} & ThreeElements["group"]) {
  const channels = campaign.eeg ? Object.entries(campaign.eeg.channels) : [];
  const getT = useClock();
  const group = useRef<THREE.Group>(null);
  const lines = useMemo(
    () =>
      channels.map(([name, raw], k) => {
        const vals = raw as number[];
        const pts: THREE.Vector3[] = [];
        // two copies back to back so the scroll can wrap seamlessly
        for (let r = 0; r < 2; r++)
          vals.forEach((v, i) => pts.push(new THREE.Vector3((r * vals.length + i) / vals.length * width, v * amp + k * 0.9, 0)));
        const geo = new THREE.BufferGeometry().setFromPoints(pts);
        const mat = new THREE.LineBasicMaterial({ color: k === 1 ? C.accent : C.accentDim, transparent: true, opacity: 0.55 });
        return { name, line: new THREE.Line(geo, mat) };
      }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );
  useFrame(() => {
    if (!group.current) return;
    group.current.position.x = -((getT() * speed * width * 0.25) % width) - width / 2;
  });
  return (
    <group {...props}>
      <group ref={group}>
        {lines.map(({ name, line }) => (
          <primitive key={name} object={line} />
        ))}
      </group>
    </group>
  );
}

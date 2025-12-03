// src/lib/SMPLBotLoader.ts
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";

export const DEFAULT_BOT_PATH = "/models/SMPL_BOT.glb";

// Canonical SMPL 24-joint order used by your backend,
// but with your backend's short names (l_hip, r_hip, etc).
export const SMPL_JOINT_ORDER = [
  "pelvis",      // 0
  "l_hip",       // 1
  "r_hip",       // 2
  "spine1",      // 3
  "l_knee",      // 4
  "r_knee",      // 5
  "spine2",      // 6
  "l_ankle",     // 7
  "r_ankle",     // 8
  "spine3",      // 9
  "l_foot",      // 10 (no bone on bot – ignored)
  "r_foot",      // 11 (no bone on bot – ignored)
  "neck",        // 12
  "l_collar",    // 13 (no bone on bot – ignored)
  "r_collar",    // 14 (no bone on bot – ignored)
  "head",        // 15
  "l_shoulder",  // 16
  "r_shoulder",  // 17
  "l_elbow",     // 18
  "r_elbow",     // 19
  "l_wrist",     // 20
  "r_wrist",     // 21
  "l_hand",      // 22 (no bone on bot – ignored)
  "r_hand"       // 23 (no bone on bot – ignored)
] as const;

export type SmplJointName = (typeof SMPL_JOINT_ORDER)[number];

// SMPL → bot mapping.
// Keys = your backend's SMPL names (l_hip, r_hip...)
// Values = bone names in the bot GLB (left_hip, right_hip...).
export const SMPL_TO_BOT: Record<string, string> = {
  pelvis: "Pelvis",
  l_hip: "L_Hip",
  r_hip: "R_Hip",
  spine1: "Spine1",
  l_knee: "L_Knee",
  r_knee: "R_Knee",
  spine2: "Spine2",
  l_ankle: "L_Ankle",
  r_ankle: "R_Ankle",
  spine3: "Spine3",
  neck: "Neck",
  head: "Head",
  l_shoulder: "L_Shoulder",
  r_shoulder: "R_Shoulder",
  l_elbow: "L_Elbow",
  r_elbow: "R_Elbow",
  l_wrist: "L_Wrist",
  r_wrist: "R_Wrist",
};

export type BoneMap = Record<string, THREE.Bone>;

export type LoadedBot = {
  scene: THREE.Group;
  skeleton: THREE.Skeleton | null;
  boneMap: Record<string, THREE.Bone>;
};

/**
 * Load the SMPL-aligned bot GLB and return scene, skeleton, and a name→bone map.
 */
export async function loadSmplBot(
  path: string = DEFAULT_BOT_PATH
): Promise<LoadedBot> {
  const loader = new GLTFLoader();
  const gltf = await loader.loadAsync(path);

  const scene: THREE.Group = gltf.scene;
  let skeleton: THREE.Skeleton | null = null;
  const boneMap: Record<string, THREE.Bone> = {};

  scene.traverse((obj) => {
    if ((obj as any).isSkinnedMesh && (obj as THREE.SkinnedMesh).skeleton) {
      skeleton = (obj as THREE.SkinnedMesh).skeleton;
    }
    if ((obj as any).isBone) {
      boneMap[obj.name] = obj as THREE.Bone;
    }
  });

  return { scene, skeleton, boneMap };
}

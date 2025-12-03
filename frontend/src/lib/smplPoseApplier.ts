import * as THREE from "three";
import { SMPL_JOINT_ORDER, SMPL_TO_BOT } from "./smplBotLoader";

export type BoneMap = Record<string, THREE.Bone>;

/**
 * Convert a 3x3 matrix (row-major) into a quaternion.
 */
export function mat3ToQuat(m: number[][]): THREE.Quaternion {
  const mat4 = new THREE.Matrix4().set(
    m[0][0], m[0][1], m[0][2], 0,
    m[1][0], m[1][1], m[1][2], 0,
    m[2][0], m[2][1], m[2][2], 0,
    0, 0, 0, 1,
  );
  return new THREE.Quaternion().setFromRotationMatrix(mat4);
}

/**
 * Normalize backend SMPL pose (24 × 3 × 3 matrices) into a
 * map<string, Quaternion> using SMPL_JOINT_ORDER with l_hip / r_hip names.
 */
export function normalizePoseToQuatMap(
  smplPose: number[][][],
  jointOrder: readonly string[] = SMPL_JOINT_ORDER,
): Record<string, THREE.Quaternion> {
  const out: Record<string, THREE.Quaternion> = {};

  if (!Array.isArray(smplPose) || smplPose.length < jointOrder.length) {
    console.warn("SMPL pose has wrong length:", smplPose?.length);
    return out;
  }

  for (let i = 0; i < jointOrder.length; i++) {
    const name = jointOrder[i];
    const entry = smplPose[i];
    if (!entry) continue;

    out[name] = mat3ToQuat(entry as number[][]);
  }

  return out;
}

export type ApplyOptions = {
  rootCorrection?: THREE.Quaternion;
  /**
   * Rest/bind quaternions, captured once after load.
   * If provided, we always multiply pose on top of these.
   */
  restQuats?: Record<string, THREE.Quaternion>;
};

/**
 * Apply a SMPL pose (as local quaternions) to the SMPL skeleton.
 *
 * Assumes:
 *  - poseQuatMap keys use backend names: pelvis, l_hip, r_hip, ...
 *  - SMPL_TO_BOT maps those names to GLB bone names: Pelvis, L_Hip, ...
 *  - restQuats[boneName] is the bind/rest quaternion from the GLB.
 */
export function applySmplPose(
  poseQuatMap: Record<string, THREE.Quaternion>,
  boneMap: BoneMap,
  options: ApplyOptions = {},
) {
  const rootCorrection = options.rootCorrection ?? new THREE.Quaternion();
  const restQuats = options.restQuats ?? {};

  for (const [smplName, botName] of Object.entries(SMPL_TO_BOT)) {
    const q = poseQuatMap[smplName];
    if (!q) continue;

    const bone = boneMap[botName];
    if (!bone) continue;

    const rest = restQuats[botName];

    // If for some reason restQuats is missing a bone, fall back to identity.
    const base = rest ? rest.clone() : new THREE.Quaternion();

    if (smplName === "pelvis") {
      // Pelvis: Rest * RootCorrection * Pose
      bone.quaternion.copy(base.multiply(rootCorrection).multiply(q));
    } else {
      // Others: Rest * Pose
      bone.quaternion.copy(base.multiply(q));
    }
  }
}

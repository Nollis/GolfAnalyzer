<script lang="ts">
  import { onMount, onDestroy, createEventDispatcher } from "svelte";
  import * as THREE from "three";
  import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
  import {
    loadSmplBot,
    SMPL_JOINT_ORDER,
    SMPL_TO_BOT,
  } from "$lib/smplBotLoader";
  import { applySmplPose, normalizePoseToQuatMap } from "$lib/smplPoseApplier";

  export let pose: any = null;
  export let backgroundImage: string = "";
  export let selectedJointIndex: number = -1;
  export let jointRotations: Record<
    number,
    { x: number; y: number; z: number }
  > = {};

  const dispatch = createEventDispatcher();

  let container: HTMLDivElement;
  let scene: THREE.Scene;
  let camera: THREE.PerspectiveCamera;
  let renderer: THREE.WebGLRenderer;
  let controls: OrbitControls;
  let skeleton: THREE.Group;
  let jointMeshes: Map<number, THREE.Mesh> = new Map();
  let boneMeshes: THREE.Line[] = [];
  let backgroundPlane: THREE.Mesh | null = null;
  let animationId: number;
  let botModel: THREE.Group | null = null;
  let botSkeleton: THREE.Skeleton | null = null;
  let boneMap: Record<string, THREE.Bone> = {};
  let restQuats: Record<string, THREE.Quaternion> = {};

  let modelScale = 1.5;

  // Root correction: flip 180° around X to fix upside-down orientation.
  const ROOT_CORRECTION = new THREE.Quaternion().setFromAxisAngle(
    new THREE.Vector3(1, 0, 0),
    Math.PI,
  );

  // Key joints for golf swing analysis
  // Key joints for MediaPipe skeleton visualization
  // smplIndex is used to map MP joints to SMPL bones for selection/highlighting
  const KEY_JOINTS = [
    { index: 11, name: "L Shoulder", smplIndex: 16 },
    { index: 12, name: "R Shoulder", smplIndex: 17 },
    { index: 13, name: "L Elbow", smplIndex: 18 },
    { index: 14, name: "R Elbow", smplIndex: 19 },
    { index: 15, name: "L Wrist", smplIndex: 20 },
    { index: 16, name: "R Wrist", smplIndex: 21 },
    { index: 23, name: "L Hip", smplIndex: 1 },
    { index: 24, name: "R Hip", smplIndex: 2 },
    { index: 25, name: "L Knee", smplIndex: 4 },
    { index: 26, name: "R Knee", smplIndex: 5 },
    { index: 27, name: "L Ankle", smplIndex: 7 },
    { index: 28, name: "R Ankle", smplIndex: 8 },
    { index: 0, name: "Nose/Head", smplIndex: 15 },
  ];

  // MediaPipe landmark connections
  const POSE_CONNECTIONS = [
    [11, 12],
    [11, 23],
    [12, 24],
    [23, 24], // torso
    [11, 13],
    [13, 15], // left arm
    [12, 14],
    [14, 16], // right arm
    [23, 25],
    [25, 27], // left leg
    [24, 26],
    [26, 28], // right leg
    [0, 11],
    [0, 12], // head to shoulders
  ];

  onMount(() => {
    initThree();
    animate();
  });

  onDestroy(() => {
    cleanup();
  });

  function cleanup() {
    if (animationId) cancelAnimationFrame(animationId);
    if (renderer) {
      renderer.dispose();
      container?.removeChild(renderer.domElement);
    }
    if (controls) controls.dispose();
    window.removeEventListener("resize", onResize);
  }

  function initThree() {
    if (!container) return;

    const w = container.clientWidth || 800;
    const h = container.clientHeight || 600;

    // Scene
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x1a1a2e);

    // Camera
    camera = new THREE.PerspectiveCamera(50, w / h, 0.1, 1000);
    camera.position.set(0, 0, 2.5);

    // Renderer
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(w, h);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);

    // Controls
    controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.minDistance = 1;
    controls.maxDistance = 5;

    // Lights
    scene.add(new THREE.AmbientLight(0xffffff, 0.5));
    const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
    dirLight.position.set(2, 3, 4);
    scene.add(dirLight);

    // Grid
    const grid = new THREE.GridHelper(3, 30, 0x333355, 0x222244);
    grid.rotation.x = Math.PI / 2;
    grid.position.z = -1;
    scene.add(grid);

    // Skeleton group
    skeleton = new THREE.Group();
    scene.add(skeleton);

    // Event listeners
    window.addEventListener("resize", onResize);
    renderer.domElement.addEventListener("click", onCanvasClick);
    renderer.domElement.addEventListener("dblclick", onCanvasDoubleClick);

    if (pose) updatePose(pose);
    if (backgroundImage) updateBackground(backgroundImage);

    // Load Bot Model
    initBotModel();
  }

  async function initBotModel() {
    try {
      const {
        scene: botScene,
        skeleton: skel,
        boneMap: map,
      } = await loadSmplBot();
      botModel = botScene;
      botSkeleton = skel;
      boneMap = map;

      // Cache rest quaternions
      restQuats = {};
      Object.values(boneMap).forEach((b) => {
        restQuats[b.name] = b.quaternion.clone();
      });

      // Compute bbox, scale, center
      const bbox = new THREE.Box3().setFromObject(botModel);
      const size = new THREE.Vector3();
      bbox.getSize(size);
      const maxDim = Math.max(size.x, size.y, size.z);
      const targetSize = 2.0;
      const scale = maxDim > 0 ? targetSize / maxDim : 1.0;
      botModel.scale.setScalar(scale);
      modelScale = scale;

      const bboxScaled = new THREE.Box3().setFromObject(botModel);
      const centerScaled = bboxScaled.getCenter(new THREE.Vector3());
      botModel.position.sub(centerScaled);

      // IMPORTANT: DO NOT rotate botModel.x here.
      // The SMPL_BOT.glb is already exported in Three.js Y-up.
      scene.add(botModel);

      // Camera fit
      if (camera) {
        const finalSize = bboxScaled.getSize(new THREE.Vector3());
        const finalMaxDim = Math.max(finalSize.x, finalSize.y, finalSize.z);
        const fov = THREE.MathUtils.degToRad(camera.fov);
        let dist = finalMaxDim / (2 * Math.tan(fov / 2));
        dist *= 1.5;
        camera.position.set(0, finalMaxDim * 0.3, dist);
        camera.lookAt(0, 0, 0);
        camera.updateProjectionMatrix();
      }

      if (skeleton) skeleton.visible = false;
      if (pose) updateBotPose(pose);
    } catch (error) {
      console.error("Failed to load SMPL bot", error);
    }
  }

  // Apply a SMPL pose from the backend.
  function updateBotPose(poseData: any) {
    if (!botSkeleton || !boneMap || !poseData?.smpl_pose) return;

    const poseQuatMap = normalizePoseToQuatMap(
      poseData.smpl_pose,
      SMPL_JOINT_ORDER,
    );

    // Allow manual scale tweaks from the debug slider without tying scale to the pose data.
    if (botModel) botModel.scale.setScalar(modelScale);

    // Apply manual overrides
    // jointRotations keys are now SMPL indices
    Object.entries(jointRotations).forEach(([indexStr, rotation]) => {
      const index = parseInt(indexStr);
      const smplName = SMPL_JOINT_ORDER[index];

      if (smplName && poseQuatMap[smplName]) {
        const adjustment = new THREE.Quaternion().setFromEuler(
          new THREE.Euler(
            THREE.MathUtils.degToRad(rotation.x),
            THREE.MathUtils.degToRad(rotation.y),
            THREE.MathUtils.degToRad(rotation.z),
          ),
        );
        // Apply adjustment on top of existing pose
        poseQuatMap[smplName].multiply(adjustment);
      }
    });

    applySmplPose(poseQuatMap, boneMap, {
      rootCorrection: ROOT_CORRECTION,
      restQuats: restQuats,
    });
  }

  function onResize() {
    if (!container || !camera || !renderer) return;
    const w = container.clientWidth || 800;
    const h = container.clientHeight || 600;
    if (w <= 0 || h <= 0) return;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
  }

  function onCanvasClick(event: MouseEvent) {
    const rect = renderer.domElement.getBoundingClientRect();
    const mouse = new THREE.Vector2(
      ((event.clientX - rect.left) / rect.width) * 2 - 1,
      -((event.clientY - rect.top) / rect.height) * 2 + 1,
    );

    const raycaster = new THREE.Raycaster();
    raycaster.setFromCamera(mouse, camera);

    const meshes = Array.from(jointMeshes.values());
    const intersects = raycaster.intersectObjects(meshes);

    if (intersects.length > 0) {
      const mesh = intersects[0].object as THREE.Mesh;
      // Dispatch the SMPL index if available, otherwise the MP index
      const jointIndex =
        mesh.userData.smplIndex !== undefined
          ? mesh.userData.smplIndex
          : mesh.userData.index;
      dispatch("jointSelect", { index: jointIndex, name: mesh.userData.name });
    }
  }

  function onCanvasDoubleClick() {
    // Reset camera view
    camera.position.set(0, 0, 2.5);
    camera.lookAt(0, 0, 0);
    controls.reset();
  }

  function updatePose(poseData: any) {
    if (!skeleton) return;

    // Clear existing
    skeleton.clear();
    jointMeshes.clear();
    boneMeshes = [];

    if (!poseData?.landmarks?.length) return;

    const landmarks = poseData.landmarks;

    // Calculate bounds for normalization
    let bounds = {
      minX: Infinity,
      maxX: -Infinity,
      minY: Infinity,
      maxY: -Infinity,
    };
    landmarks.forEach((lm: any) => {
      if (lm.visibility > 0.3) {
        bounds.minX = Math.min(bounds.minX, lm.x);
        bounds.maxX = Math.max(bounds.maxX, lm.x);
        bounds.minY = Math.min(bounds.minY, lm.y);
        bounds.maxY = Math.max(bounds.maxY, lm.y);
      }
    });

    const centerX = (bounds.minX + bounds.maxX) / 2;
    const centerY = (bounds.minY + bounds.maxY) / 2;
    const scale =
      2.5 / Math.max(bounds.maxX - bounds.minX, bounds.maxY - bounds.minY);

    // 1. Calculate base positions
    const jointPositions = new Map<number, THREE.Vector3>();

    KEY_JOINTS.forEach(({ index }) => {
      const lm = landmarks[index];
      if (!lm || lm.visibility < 0.3) return;

      let x = (lm.x - centerX) * scale;
      let y = -(lm.y - centerY) * scale;
      let z = (lm.z || 0) * scale * 2;

      jointPositions.set(index, new THREE.Vector3(x, y, z));
    });

    // 2. Apply hierarchical rotations (REMOVED: drawn skeleton is independent)
    // We are now using SMPL indices for jointRotations, which don't map directly
    // to the MediaPipe hierarchy used here. To avoid confusion, we disable
    // rotation application on the drawn skeleton.
    /*
    const ROTATION_CHAINS = [
       ...
    ];
    ROTATION_CHAINS.forEach(...)
    */

    // 3. Create meshes
    KEY_JOINTS.forEach(({ index, name }) => {
      const pos = jointPositions.get(index);
      if (!pos) return;

      const isSelected = index === selectedJointIndex;
      const hasCorrection = jointRotations[index] !== undefined;

      const geometry = new THREE.SphereGeometry(
        isSelected ? 0.045 : 0.035,
        24,
        24,
      );
      const material = new THREE.MeshStandardMaterial({
        color: isSelected ? 0x00ff88 : hasCorrection ? 0xffaa00 : 0x4f8cff,
        emissive: isSelected ? 0x00ff88 : 0x000000,
        emissiveIntensity: isSelected ? 0.3 : 0,
        metalness: 0.3,
        roughness: 0.6,
      });

      const mesh = new THREE.Mesh(geometry, material);
      mesh.position.copy(pos);
      // Store smplIndex in userData for click handling
      const smplIndex = KEY_JOINTS.find((k) => k.index === index)?.smplIndex;
      mesh.userData = { index, name, smplIndex, originalPosition: pos.clone() };

      skeleton.add(mesh);
      jointMeshes.set(index, mesh);
    });

    // Create bones
    const boneMaterial = new THREE.LineBasicMaterial({
      color: 0x6688cc,
      linewidth: 2,
    });

    POSE_CONNECTIONS.forEach(([startIdx, endIdx]) => {
      const startMesh = jointMeshes.get(startIdx);
      const endMesh = jointMeshes.get(endIdx);
      if (!startMesh || !endMesh) return;

      const points = [startMesh.position.clone(), endMesh.position.clone()];
      const geometry = new THREE.BufferGeometry().setFromPoints(points);
      const bone = new THREE.Line(geometry, boneMaterial);
      skeleton.add(bone);
      boneMeshes.push(bone);
    });

    // Add torso mesh
    createTorsoMesh(scale);
  }

  function createTorsoMesh(scale: number) {
    const lShoulder = jointMeshes.get(11);
    const rShoulder = jointMeshes.get(12);
    const lHip = jointMeshes.get(23);
    const rHip = jointMeshes.get(24);

    if (!lShoulder || !rShoulder || !lHip || !rHip) return;

    const vertices = new Float32Array([
      lShoulder.position.x,
      lShoulder.position.y,
      lShoulder.position.z,
      rShoulder.position.x,
      rShoulder.position.y,
      rShoulder.position.z,
      rHip.position.x,
      rHip.position.y,
      rHip.position.z,
      lHip.position.x,
      lHip.position.y,
      lHip.position.z,
    ]);

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.BufferAttribute(vertices, 3));
    geometry.setIndex(
      new THREE.BufferAttribute(new Uint16Array([0, 1, 2, 0, 2, 3]), 1),
    );
    geometry.computeVertexNormals();

    const material = new THREE.MeshStandardMaterial({
      color: 0x4f8cff,
      transparent: true,
      opacity: 0.15,
      side: THREE.DoubleSide,
    });

    skeleton.add(new THREE.Mesh(geometry, material));
  }

  function updateBackground(imageUrl: string) {
    if (!scene) return;

    // Remove existing background
    if (backgroundPlane) {
      scene.remove(backgroundPlane);
      backgroundPlane = null;
    }

    if (!imageUrl) return;

    const loader = new THREE.TextureLoader();
    loader.load(imageUrl, (texture) => {
      const aspect = texture.image.width / texture.image.height;
      const planeHeight = 3;
      const planeWidth = planeHeight * aspect;

      const geometry = new THREE.PlaneGeometry(planeWidth, planeHeight);
      const material = new THREE.MeshBasicMaterial({
        map: texture,
        transparent: true,
        opacity: 0.4,
        side: THREE.DoubleSide,
      });

      backgroundPlane = new THREE.Mesh(geometry, material);
      backgroundPlane.position.z = -1.5;
      scene.add(backgroundPlane);
    });
  }

  function animate() {
    animationId = requestAnimationFrame(animate);
    controls?.update();
    renderer?.render(scene, camera);
  }

  // Update highlight when selected joint changes
  // Update highlight when selected joint changes
  function updateJointHighlight() {
    jointMeshes.forEach((mesh, index) => {
      const mat = mesh.material as THREE.MeshStandardMaterial;
      // Check if this mesh corresponds to the selected SMPL index
      const meshSmplIndex = mesh.userData.smplIndex;
      const isSelected =
        meshSmplIndex !== undefined && meshSmplIndex === selectedJointIndex;
      const hasCorrection =
        meshSmplIndex !== undefined &&
        jointRotations[meshSmplIndex] !== undefined;

      mat.color.setHex(
        isSelected ? 0x00ff88 : hasCorrection ? 0xffaa00 : 0x4f8cff,
      );
      mat.emissive.setHex(isSelected ? 0x00ff88 : 0x000000);
      mat.emissiveIntensity = isSelected ? 0.3 : 0;

      // Scale selected joint
      const scale = isSelected ? 1.3 : 1;
      mesh.scale.setScalar(scale);
    });
  }

  // Reactive updates
  $: if (pose && scene) {
    updatePose(pose);
    if (botModel) updateBotPose(pose);
  }
  $: if (backgroundImage !== undefined && scene)
    updateBackground(backgroundImage);
  $: if (scene && jointMeshes.size > 0) updateJointHighlight();

  // Trigger bot update when rotations change
  $: if (pose && jointRotations && botModel) updateBotPose(pose);
</script>

<div bind:this={container} class="w-full h-full relative bg-gray-900">
  {#if !pose}
    <div class="absolute inset-0 flex items-center justify-center">
      <div class="text-center text-gray-500">
        <svg
          class="w-16 h-16 mx-auto mb-4 opacity-50"
          fill="none"
          stroke="currentColor"
          stroke-width="1.5"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M14.828 14.828a4 4 0 01-5.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
        <p>Select a frame to view pose</p>
      </div>
    </div>
  {/if}

  <!-- Overlay info -->
  <div
    class="absolute top-3 left-3 text-xs text-gray-400 bg-gray-800/80 px-2 py-1 rounded"
  >
    Double-click to reset view
  </div>
</div>

<style>
  div :global(canvas) {
    outline: none;
    cursor: grab;
  }
  div :global(canvas:active) {
    cursor: grabbing;
  }
</style>

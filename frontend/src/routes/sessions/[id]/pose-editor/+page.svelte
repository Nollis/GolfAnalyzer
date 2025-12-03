<script lang="ts">
  import { page } from "$app/stores";
  import { token } from "$lib/stores/auth";
  import { onMount } from "svelte";
  import { goto } from "$app/navigation";
  import SMPLViewer from "$lib/components/SMPLViewer.svelte";
  import PoseImageSkeletonOverlay from "$lib/components/PoseImageSkeletonOverlay.svelte";

  const sessionId = $page.params.id;

  let session: any = null;
  let poses: any[] = [];
  let keyFrames: any[] = [];
  let selectedFrameIndex = 0;
  let loading = true;
  let error = "";
  let saving = false;

  // Video frame extraction
  let videoElement: HTMLVideoElement;
  let frameCanvas: HTMLCanvasElement;
  let frameImageUrl = "";

  // Joint selection and correction
  let selectedJointIndex = -1;
  let selectedJointName = "";
  let jointRotations: Record<
    number,
    Record<number, { x: number; y: number; z: number }>
  > = {}; // frameIndex -> jointIndex -> rotation

  // Key joints for golf analysis
  // Key joints for golf analysis (using SMPL indices)
  const GOLF_JOINTS = [
    { index: 16, name: "L Shoulder" },
    { index: 17, name: "R Shoulder" },
    { index: 18, name: "L Elbow" },
    { index: 19, name: "R Elbow" },
    { index: 1, name: "L Hip" },
    { index: 2, name: "R Hip" },
    { index: 4, name: "L Knee" },
    { index: 5, name: "R Knee" },
    { index: 15, name: "Head" },
  ];

  const AXES = [
    { axis: "x", label: "X", color: "red" },
    { axis: "y", label: "Y", color: "green" },
    { axis: "z", label: "Z", color: "blue" },
  ] as const;

  onMount(async () => {
    await loadSession();
    await loadPoses();
    await loadKeyFrames();
    loading = false;

    // Extract first frame after video loads
    if (keyFrames.length > 0) {
      setTimeout(() => selectFrame(0), 500);
    }
  });

  async function loadSession() {
    try {
      const res = await fetch(`/api/v1/sessions/${sessionId}`, {
        headers: { Authorization: `Bearer ${$token}` },
      });
      if (!res.ok) throw new Error("Failed to load session");
      session = await res.json();
    } catch (e: any) {
      error = e.message;
    }
  }

  async function loadPoses() {
    try {
      const res = await fetch(`/api/v1/sessions/${sessionId}/poses`, {
        headers: { Authorization: `Bearer ${$token}` },
      });
      if (res.ok) {
        poses = await res.json();
      }
    } catch (e) {
      console.error("Failed to load poses", e);
    }
  }

  async function loadKeyFrames() {
    try {
      const res = await fetch(`/api/v1/sessions/${sessionId}/key-frames`, {
        headers: { Authorization: `Bearer ${$token}` },
      });
      if (res.ok) {
        keyFrames = await res.json();
      }
    } catch (e) {
      console.error("Failed to load key frames", e);
    }
  }

  function selectFrame(index: number) {
    selectedFrameIndex = index;
    selectedJointIndex = -1;
    selectedJointName = "";

    const frame = keyFrames[index];
    console.log(`Selected frame ${index}:`, frame);
    if (frame && frame.image_url) {
      frameImageUrl = `${frame.image_url}?token=${$token}`;
      console.log("Setting frameImageUrl:", frameImageUrl);
    } else {
      console.warn("No image_url for frame", index);
      frameImageUrl = null;
    }
  }

  function handleJointSelect(event: CustomEvent) {
    selectedJointIndex = event.detail.index;
    selectedJointName = event.detail.name;
  }

  function getCurrentFrameRotations(
    rotations: Record<
      number,
      Record<number, { x: number; y: number; z: number }>
    >,
  ): Record<number, { x: number; y: number; z: number }> {
    const frameIdx = currentKeyFrame?.frame_index;
    if (frameIdx === undefined) return {};
    return rotations[frameIdx] || {};
  }

  function setJointRotation(
    jointIndex: number,
    axis: "x" | "y" | "z",
    value: number,
  ) {
    const frameIdx = currentKeyFrame?.frame_index;
    if (frameIdx === undefined) return;

    const newFrameRotations = { ...(jointRotations[frameIdx] || {}) };
    const newJointRotation = {
      ...(newFrameRotations[jointIndex] || { x: 0, y: 0, z: 0 }),
    };

    newJointRotation[axis] = value;
    newFrameRotations[jointIndex] = newJointRotation;

    console.log(
      `Setting rotation for frame ${frameIdx}, joint ${jointIndex}, axis ${axis} to ${value}`,
    );

    jointRotations = {
      ...jointRotations,
      [frameIdx]: newFrameRotations,
    };
    console.log("New jointRotations:", jointRotations);
  }

  function getJointRotation(
    jointIndex: number,
    axis: "x" | "y" | "z",
    rotations: Record<
      number,
      Record<number, { x: number; y: number; z: number }>
    >,
  ): number {
    const frameIdx = currentKeyFrame?.frame_index;
    if (frameIdx === undefined) return 0;
    const val = rotations[frameIdx]?.[jointIndex]?.[axis] || 0;
    console.log(
      `Get rotation: frame ${frameIdx}, joint ${jointIndex}, axis ${axis} = ${val}`,
    );
    return val;
  }

  function resetJoint(jointIndex: number) {
    const frameIdx = currentKeyFrame?.frame_index;
    if (frameIdx === undefined) return;

    if (jointRotations[frameIdx]) {
      const newFrameRotations = { ...jointRotations[frameIdx] };
      delete newFrameRotations[jointIndex];

      jointRotations = {
        ...jointRotations,
        [frameIdx]: newFrameRotations,
      };
    }
  }

  function resetAllCorrections() {
    const frameIdx = currentKeyFrame?.frame_index;
    if (frameIdx === undefined) return;

    delete jointRotations[frameIdx];
    jointRotations = { ...jointRotations };
  }

  let recalculationResult: any = null;

  async function saveCorrections() {
    saving = true;
    recalculationResult = null;

    try {
      const res = await fetch(
        `/api/v1/sessions/${sessionId}/pose-corrections`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${$token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ corrections: jointRotations }),
        },
      );

      if (!res.ok) throw new Error("Failed to save corrections");

      const result = await res.json();
      recalculationResult = result;

      if (result.status === "success") {
        // Clear local corrections since they're now saved
        jointRotations = {};

        // Reload poses and keyframes to show updated state
        await loadPoses();
        await loadKeyFrames();
      }
    } catch (e: any) {
      alert("Error saving: " + e.message);
    } finally {
      saving = false;
    }
  }

  function goBack() {
    goto(`/sessions/${sessionId}`);
  }

  $: currentKeyFrame = keyFrames[selectedFrameIndex];
  $: currentPose = currentKeyFrame
    ? poses.find((p) => p.frame_index === currentKeyFrame.frame_index) ||
      keyFrames[selectedFrameIndex]
    : null;
  $: currentRotations = getCurrentFrameRotations(jointRotations);
  $: hasCorrections = Object.keys(jointRotations).length > 0;
  $: frameHasCorrections =
    currentKeyFrame &&
    jointRotations[currentKeyFrame.frame_index] &&
    Object.keys(jointRotations[currentKeyFrame.frame_index]).length > 0;
</script>

<svelte:head>
  <title>Pose Editor | GolfAnalyzer</title>
</svelte:head>

<div class="min-h-screen bg-gray-900 text-white">
  <!-- Header -->
  <header class="bg-gray-800 border-b border-gray-700 px-6 py-3">
    <div class="flex items-center justify-between max-w-full">
      <div class="flex items-center gap-4">
        <button
          on:click={goBack}
          class="text-gray-400 hover:text-white transition-colors flex items-center gap-2"
        >
          <svg
            class="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M15 19l-7-7 7-7"
            />
          </svg>
          Back
        </button>
        <div class="h-6 w-px bg-gray-700"></div>
        <h1 class="text-lg font-semibold">3D Pose Editor</h1>
        {#if session}
          <span class="text-gray-500 text-sm">
            {session.metadata?.club_type} • {session.metadata?.view?.replace(
              "_",
              " ",
            )}
          </span>
        {/if}
      </div>

      <div class="flex items-center gap-3">
        {#if recalculationResult?.status === "success"}
          <span
            class="text-green-400 text-sm flex items-center gap-2 bg-green-900/30 px-3 py-1 rounded-lg"
          >
            <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path
                fill-rule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                clip-rule="evenodd"
              />
            </svg>
            Recalculated! New score: {recalculationResult.new_overall_score?.toFixed(
              1,
            )}
          </span>
        {:else if hasCorrections}
          <span class="text-yellow-400 text-sm flex items-center gap-1">
            <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path
                fill-rule="evenodd"
                d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                clip-rule="evenodd"
              />
            </svg>
            Unsaved changes
          </span>
        {/if}

        <button
          on:click={saveCorrections}
          disabled={!hasCorrections || saving}
          class="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-700
                 disabled:text-gray-500 disabled:cursor-not-allowed rounded-lg
                 transition-colors text-sm font-medium flex items-center gap-2"
        >
          {#if saving}
            <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle
                class="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                stroke-width="4"
              ></circle>
              <path
                class="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              ></path>
            </svg>
            Saving...
          {:else}
            <svg
              class="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M5 13l4 4L19 7"
              />
            </svg>
            Save & Recalculate
          {/if}
        </button>
      </div>
    </div>
  </header>

  {#if loading}
    <div class="flex items-center justify-center h-[calc(100vh-60px)]">
      <div class="text-center">
        <div
          class="animate-spin w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full mx-auto mb-4"
        ></div>
        <p class="text-gray-400">Loading pose data...</p>
      </div>
    </div>
  {:else if error}
    <div class="flex items-center justify-center h-[calc(100vh-60px)]">
      <div class="text-center text-red-400">
        <p>{error}</p>
        <button on:click={goBack} class="mt-4 text-blue-400 hover:underline"
          >Go back</button
        >
      </div>
    </div>
  {:else}
    <div class="flex h-[calc(100vh-60px)]">
      <!-- Left: Frame selector (compact) -->
      <div class="w-56 bg-gray-800 border-r border-gray-700 p-2 flex flex-col">
        <h2
          class="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3"
        >
          Key Frames
        </h2>

        <div class="space-y-2 flex-1">
          {#each keyFrames as frame, idx}
            <button
              on:click={() => selectFrame(idx)}
              class="w-full text-left px-3 py-2.5 rounded-lg transition-all
                     {selectedFrameIndex === idx
                ? 'bg-blue-600 text-white shadow-lg'
                : 'bg-gray-700/50 hover:bg-gray-700 text-gray-300'}"
            >
              <div class="font-medium capitalize text-sm">{frame.phase}</div>
              <div class="text-xs opacity-70 mt-0.5">
                {frame.timestamp_sec.toFixed(2)}s
                {#if jointRotations[frame.frame_index]}
                  <span class="text-yellow-400 ml-1">• edited</span>
                {/if}
              </div>
            </button>
          {/each}

          <div class="mt-4 pt-4 border-t border-gray-700">
            <h3
              class="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2"
            >
              Controls
            </h3>
            <div class="text-xs text-gray-500 space-y-1">
              <p>🖱️ Rotate: Left drag</p>
              <p>🔍 Zoom: Scroll</p>
              <p>✋ Pan: Right drag</p>
              <p>🎯 Select: Click joint</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Center: 3D Viewer + Controls -->
      <div class="flex-1 flex flex-col min-w-0">
        <!-- Viewers -->
        <div class="h-[35%] min-h-[250px] relative grid grid-cols-2 gap-2">
          <div class="relative">
            {#if currentPose}
              <SMPLViewer
                pose={currentPose}
                backgroundImage=""
                {selectedJointIndex}
                jointRotations={currentRotations}
                on:jointSelect={handleJointSelect}
              />
            {:else}
              <div class="flex items-center justify-center h-full bg-gray-800">
                <p class="text-gray-500">Select a frame to view</p>
              </div>
            {/if}

            {#if selectedJointName}
              <div
                class="absolute top-3 right-3 bg-green-600/90 px-3 py-1.5 rounded-lg text-sm font-medium"
              >
                Selected: {selectedJointName}
              </div>
            {/if}
          </div>

          <div class="relative">
            {#if currentPose}
              <PoseImageSkeletonOverlay
                pose={currentPose}
                imageUrl={frameImageUrl}
              />
            {:else}
              <div class="flex items-center justify-center h-full bg-gray-800">
                <p class="text-gray-500">Select a frame to view</p>
              </div>
            {/if}
          </div>
        </div>

        <!-- Joint Controls (full width row layout) -->
        <div
          class="flex-1 bg-gray-900 border-t border-gray-700 p-3 overflow-auto"
        >
          <div class="flex items-center justify-between mb-2">
            <h3
              class="text-xs font-semibold text-gray-400 uppercase tracking-wide"
            >
              Joint Adjustments
              {#if selectedJointName}
                <span class="text-green-400 normal-case ml-1"
                  >• {selectedJointName}</span
                >
              {/if}
            </h3>

            {#if frameHasCorrections}
              <button
                on:click={resetAllCorrections}
                class="text-xs text-red-400 hover:text-red-300 transition-colors"
              >
                Reset all
              </button>
            {/if}
          </div>

          <!-- Single row of all joints -->
          <div class="flex gap-2 min-w-max">
            {#each GOLF_JOINTS as joint}
              {@const isSelected = joint.index === selectedJointIndex}
              {@const hasCorrection =
                currentRotations[joint.index] !== undefined}
              <div
                class="flex-1 min-w-[140px] bg-gray-700/40 rounded-lg p-2 transition-all cursor-pointer hover:bg-gray-700/60
                       {isSelected
                  ? 'ring-2 ring-green-500 bg-gray-700/80'
                  : ''}
                       {hasCorrection && !isSelected
                  ? 'ring-1 ring-yellow-500/40'
                  : ''}"
                on:click={() => {
                  selectedJointIndex = joint.index;
                  selectedJointName = joint.name;
                }}
                on:keydown={(e) =>
                  e.key === "Enter" && (selectedJointIndex = joint.index)}
                role="button"
                tabindex="0"
              >
                <div class="flex items-center justify-between mb-2">
                  <span class="text-xs font-medium text-gray-300"
                    >{joint.name}</span
                  >
                  {#if hasCorrection}
                    <button
                      on:click|stopPropagation={() => resetJoint(joint.index)}
                      class="text-yellow-500 hover:text-yellow-400 text-xs leading-none"
                      title="Reset">↺</button
                    >
                  {/if}
                </div>

                <div class="space-y-1.5">
                  {#each AXES as { axis, label, color }}
                    <div class="flex items-center gap-1.5">
                      <span
                        class="text-[10px] w-3 font-bold {color === 'red'
                          ? 'text-red-400'
                          : color === 'green'
                            ? 'text-green-400'
                            : 'text-blue-400'}">{label}</span
                      >
                      <input
                        type="range"
                        min="-45"
                        max="45"
                        step="1"
                        value={getJointRotation(
                          joint.index,
                          axis,
                          jointRotations,
                        )}
                        on:input={(e) =>
                          setJointRotation(
                            joint.index,
                            axis,
                            parseInt(e.currentTarget.value),
                          )}
                        class="flex-1 h-1.5 bg-gray-600 rounded appearance-none cursor-pointer slider-{color}"
                      />
                      <span
                        class="text-[10px] w-7 text-right font-mono text-gray-500"
                      >
                        {getJointRotation(joint.index, axis, jointRotations)}°
                      </span>
                    </div>
                  {/each}
                </div>
              </div>
            {/each}
          </div>
        </div>
      </div>

      <!-- Right: Info panel (compact) -->
      <div
        class="w-44 bg-gray-800 border-l border-gray-700 p-2 overflow-y-auto text-xs"
      >
        <h2
          class="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3"
        >
          Frame Info
        </h2>

        {#if currentKeyFrame}
          <div class="bg-gray-700/50 rounded-lg p-3 mb-4">
            <div class="text-xl font-bold capitalize text-white">
              {currentKeyFrame.phase}
            </div>
            <div class="text-sm text-gray-400 mt-1">
              Frame #{currentKeyFrame.frame_index}
            </div>
            <div class="text-sm text-gray-400">
              Time: {currentKeyFrame.timestamp_sec.toFixed(3)}s
            </div>
          </div>

          {#if frameHasCorrections}
            <div
              class="bg-yellow-900/30 border border-yellow-600/30 rounded-lg p-3 mb-4"
            >
              <div class="text-sm font-medium text-yellow-400 mb-1">
                ⚠️ Manual Corrections
              </div>
              <div class="text-xs text-gray-400">
                {Object.keys(currentRotations).length} joint(s) modified
              </div>
            </div>
          {/if}

          {#if recalculationResult}
            <div
              class="bg-green-900/30 border border-green-600/30 rounded-lg p-3 mb-4"
            >
              <div class="text-sm font-medium text-green-400 mb-2">
                ✅ Metrics Updated
              </div>
              <div class="space-y-1 text-xs">
                <div class="flex justify-between">
                  <span class="text-gray-400">Status:</span>
                  <span class="text-green-400"
                    >{recalculationResult.status}</span
                  >
                </div>
                {#if recalculationResult.new_overall_score !== undefined}
                  <div class="flex justify-between">
                    <span class="text-gray-400">New Score:</span>
                    <span class="text-white font-bold"
                      >{recalculationResult.new_overall_score?.toFixed(1)}</span
                    >
                  </div>
                {/if}
                <div class="flex justify-between">
                  <span class="text-gray-400">Corrections:</span>
                  <span class="text-white"
                    >{recalculationResult.corrections_count}</span
                  >
                </div>
              </div>
              <a
                href="/sessions/{sessionId}"
                class="mt-3 block text-center text-xs text-blue-400 hover:text-blue-300"
              >
                View Updated Analysis →
              </a>
            </div>
          {/if}
        {/if}

        <h2
          class="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3 mt-6"
        >
          Tips
        </h2>
        <div class="space-y-3 text-xs text-gray-500">
          <p>
            • <strong class="text-gray-400">Click a joint</strong> in the 3D view
            or panel to select it
          </p>
          <p>
            • <strong class="text-gray-400">Adjust sliders</strong> to rotate joints
            in X/Y/Z axes
          </p>
          <p>
            • <strong class="text-gray-400">Yellow border</strong> indicates modified
            joints
          </p>
          <p>
            • <strong class="text-gray-400">Save</strong> to recalculate metrics
            with corrections
          </p>
        </div>

        <h2
          class="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3 mt-6"
        >
          Key Angles
        </h2>
        <div class="space-y-2 text-xs">
          <div class="flex justify-between text-gray-400">
            <span>Shoulder Turn</span>
            <span class="text-white">Focus: L/R Shoulder</span>
          </div>
          <div class="flex justify-between text-gray-400">
            <span>Hip Rotation</span>
            <span class="text-white">Focus: L/R Hip</span>
          </div>
          <div class="flex justify-between text-gray-400">
            <span>Spine Angle</span>
            <span class="text-white">Focus: Hips + Shoulders</span>
          </div>
          <div class="flex justify-between text-gray-400">
            <span>Elbow Position</span>
            <span class="text-white">Focus: L/R Elbow</span>
          </div>
        </div>
      </div>
    </div>
  {/if}

  <!-- Hidden video for frame extraction -->
</div>

<style>
  input[type="range"] {
    -webkit-appearance: none;
    appearance: none;
    background: transparent;
  }

  input[type="range"]::-webkit-slider-runnable-track {
    height: 6px;
    background: #374151;
    border-radius: 3px;
  }

  input[type="range"]::-webkit-slider-thumb {
    -webkit-appearance: none;
    appearance: none;
    width: 14px;
    height: 14px;
    border-radius: 50%;
    margin-top: -4px;
    cursor: pointer;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
  }

  input[type="range"]::-moz-range-track {
    height: 6px;
    background: #374151;
    border-radius: 3px;
  }

  input[type="range"]::-moz-range-thumb {
    width: 14px;
    height: 14px;
    border-radius: 50%;
    border: none;
    cursor: pointer;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
  }

  .slider-red::-webkit-slider-thumb {
    background: #ef4444;
  }
  .slider-green::-webkit-slider-thumb {
    background: #22c55e;
  }
  .slider-blue::-webkit-slider-thumb {
    background: #3b82f6;
  }

  .slider-red::-moz-range-thumb {
    background: #ef4444;
  }
  .slider-green::-moz-range-thumb {
    background: #22c55e;
  }
  .slider-blue::-moz-range-thumb {
    background: #3b82f6;
  }

  .slider-red::-webkit-slider-runnable-track {
    background: linear-gradient(to right, #374151, #7f1d1d);
  }
  .slider-green::-webkit-slider-runnable-track {
    background: linear-gradient(to right, #374151, #14532d);
  }
  .slider-blue::-webkit-slider-runnable-track {
    background: linear-gradient(to right, #374151, #1e3a5f);
  }
</style>

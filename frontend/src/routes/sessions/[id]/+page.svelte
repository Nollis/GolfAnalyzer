<script lang="ts">
  import { goto } from "$app/navigation";
  import { page } from "$app/stores";
  import { onMount } from "svelte";
  import {
    initializeAuth,
    isAuthenticated,
    token,
    waitForAuthReady,
  } from "$lib/stores/auth";
  import MetricExplainer from "$lib/components/MetricExplainer.svelte";
  import MetricCard from "$lib/components/MetricCard.svelte";
  import PositionAnalysis from "$lib/components/PositionAnalysis.svelte";
  import SkeletonViewer from "$lib/components/SkeletonViewer.svelte";

  interface Session {
    session_id: string;
    video_url?: string;
    metadata: { club_type: string; view: string };
    phases: {
      address_frame: number;
      top_frame: number;
      impact_frame: number;
      finish_frame: number;
    };
    metrics?: {
      tempo_ratio?: number;
      backswing_duration_ms?: number;
      downswing_duration_ms?: number;
      chest_turn_top_deg?: number;
      pelvis_turn_top_deg?: number;
      x_factor_top_deg?: number;
      spine_angle_address_deg?: number;
      spine_angle_impact_deg?: number;
      lead_arm_address_deg?: number;
      lead_arm_top_deg?: number;
      lead_arm_impact_deg?: number;
      trail_elbow_address_deg?: number;
      trail_elbow_top_deg?: number;
      trail_elbow_impact_deg?: number;
      knee_flex_left_address_deg?: number;
      knee_flex_right_address_deg?: number;
      head_sway_range?: number;
      early_extension_amount?: number;
      swing_path_index?: number;
      // MHR 3D metrics
      head_drop_cm?: number;
      head_rise_cm?: number;
      hand_height_at_top_index?: number;
      hand_width_at_top_index?: number;
      // Extended MHR metrics (finish, sway, plane)
      finish_balance?: number;
      chest_turn_finish_deg?: number;
      pelvis_turn_finish_deg?: number;
      spine_angle_finish_deg?: number;
      extension_from_address_deg?: number;
      head_rise_top_to_finish_cm?: number;
      head_lateral_shift_address_to_finish_cm?: number;
      hand_height_finish_norm?: number;
      hand_depth_finish_norm?: number;
      hand_height_finish_label?: string;
      hand_depth_finish_label?: string;
      pelvis_sway_top_cm?: number;
      pelvis_sway_impact_cm?: number;
      pelvis_sway_finish_cm?: number;
      shoulder_sway_top_cm?: number;
      shoulder_sway_impact_cm?: number;
      shoulder_sway_finish_cm?: number;
      swing_plane_top_deg?: number;
      swing_plane_impact_deg?: number;
      swing_plane_deviation_top_deg?: number;
      swing_plane_shift_top_to_impact_deg?: number;
      // Backward compatibility
      shoulder_turn_top_deg?: number;
      hip_turn_top_deg?: number;
    };
    scores: {
      overall_score: number;
      metric_scores: Record<string, { value: number; score: string }>;
    };
    feedback: {
      summary: string;
      priority_issues: string[];
      drills: {
        title: string;
        description: string;
        category?: string;
        video_url?: string;
        difficulty?: string;
      }[];
      phase_feedback?: Record<string, string>;
    };
    is_personal_best: boolean;
    created_at?: string;
  }

  interface PersonalBest {
    metrics: Record<string, number | string>;
  }

  let session: Session | null = null;
  let personalBest: PersonalBest | null = null;
  let loading = true;
  let error = "";
  let regeneratingFeedback = false;

  let poses: any[] = [];
  let keyFrames: any[] = [];
  let selectedFrame: any = null;
  let videoElement: HTMLVideoElement;
  let activeTab: "overview" | "address" | "top" | "impact" | "finish" =
    "overview";

  const poseHighlights: Record<string, string[]> = {
    address: [
      "Balanced stance with weight centered and athletic knee flex.",
      "Spine tilt set to your target angle; head quiet and eyes on the ball.",
      "Arms relaxed; hands under the shoulder line for a neutral takeaway.",
    ],
    top: [
      "Chest and pelvis separation (X-factor) without losing spine angle.",
      "Lead arm extended; trail elbow around 90° for structure.",
      "Head stays centered—avoid swaying off the ball.",
    ],
    impact: [
      "Lead side posted up; hips clearing before the chest.",
      "Hands ahead of the ball with forward shaft lean.",
      "Head steady; minimal early extension toward the ball.",
    ],
    finish: [
      "Weight fully to lead side; belt buckle facing target.",
      "Chest and shoulders fully rotated with balanced posture.",
      "Head and spine tall—no falling back or excessive sway.",
    ],
  };

  onMount(async () => {
    const id = $page.params.id;

    await initializeAuth();
    await waitForAuthReady();

    if (!$isAuthenticated) {
      const redirectParam = encodeURIComponent(
        $page.url.pathname + $page.url.search,
      );
      goto(`/login?redirectTo=${redirectParam}`);
      return;
    }

    try {
      const res = await fetch(`/api/v1/sessions/${id}`, {
        headers: { Authorization: `Bearer ${$token}` },
      });
      if (!res.ok) throw new Error("Session not found");
      session = (await res.json()) as Session;

      // Fetch poses
      try {
        const posesRes = await fetch(`/api/v1/sessions/${id}/poses`, {
          headers: { Authorization: `Bearer ${$token}` },
        });
        if (posesRes.ok) {
          poses = await posesRes.json();
        }
      } catch (e) {
        console.error("Failed to fetch poses", e);
      }

      // Fetch key frames for skeleton visualization
      try {
        const keyFramesRes = await fetch(`/api/v1/sessions/${id}/key-frames`, {
          headers: { Authorization: `Bearer ${$token}` },
        });
        if (keyFramesRes.ok) {
          keyFrames = await keyFramesRes.json();
        }
      } catch (e) {
        console.error("Failed to fetch key frames", e);
      }

      // Fetch personal best for comparison (always show for reference)
      try {
        const pbRes = await fetch(
          `/api/v1/personal-best?club_type=${session.metadata.club_type}&view=${session.metadata.view}`,
          { headers: { Authorization: `Bearer ${$token}` } },
        );
        if (pbRes.ok) {
          const pbData = await pbRes.json();
          if (pbData) personalBest = pbData as PersonalBest;
        }
      } catch (e) {
        console.error("Failed to fetch personal best", e);
      }
    } catch (e: unknown) {
      error = (e as Error).message;
    } finally {
      loading = false;
    }
  });

  function getScoreColor(score: string) {
    if (score === "green") return "bg-green-100 text-green-800";
    if (score === "yellow") return "bg-yellow-100 text-yellow-800";
    return "bg-red-100 text-red-800";
  }

  let shareMessage = "";
  let showShareMessage = false;

  async function shareSession() {
    const shareUrl = window.location.href;
    try {
      await navigator.clipboard.writeText(shareUrl);
      shareMessage = "Link copied to clipboard!";
      showShareMessage = true;
      setTimeout(() => {
        showShareMessage = false;
      }, 3000);
    } catch (e) {
      shareMessage = "Failed to copy link";
      showShareMessage = true;
      setTimeout(() => {
        showShareMessage = false;
      }, 3000);
    }
  }

  async function deleteSession() {
    if (
      !confirm(
        "Are you sure you want to delete this session? This action cannot be undone.",
      )
    ) {
      return;
    }

    try {
      const res = await fetch(`/api/v1/sessions/${session.session_id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${$token}` },
      });

      if (!res.ok) throw new Error("Failed to delete session");

      // Redirect to dashboard after successful deletion
      goto("/dashboard");
    } catch (e) {
      alert("Failed to delete session. Please try again.");
      console.error(e);
    }
  }

  function selectFrame(keyFrame: any) {
    selectedFrame = keyFrame;
    // Optionally seek video to this frame
    if (videoElement && keyFrame.timestamp_sec !== undefined) {
      videoElement.currentTime = keyFrame.timestamp_sec;
    }
  }

  function seekToPhase(phase: string) {
    const phaseFrame = keyFrames.find((kf) => kf.phase === phase);
    if (videoElement && phaseFrame?.timestamp_sec !== undefined) {
      videoElement.currentTime = phaseFrame.timestamp_sec;
    }
  }

  function setActivePhaseTab(phase: "address" | "top" | "impact" | "finish") {
    activeTab = phase;
    seekToPhase(phase);
  }

  async function regenerateFeedback() {
    if (!session) return;
    regeneratingFeedback = true;
    try {
      const res = await fetch(
        `/api/v1/sessions/${session.session_id}/regenerate-feedback`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${$token}` },
        },
      );
      if (!res.ok) throw new Error("Failed to regenerate feedback");
      const newFeedback = await res.json();
      session.feedback = newFeedback;
    } catch (e) {
      alert("Failed to regenerate feedback. Please try again.");
      console.error(e);
    } finally {
      regeneratingFeedback = false;
    }
  }
</script>

{#if loading}
  <div class="text-center py-12 text-gray-500 dark:text-slate-400">
    Loading...
  </div>
{:else if error}
  <div class="text-center py-12 text-red-600 dark:text-red-500">{error}</div>
{:else if session}
  <div class="space-y-8">
    <!-- Video Player -->
    {#if session.video_url}
      <div class="bg-black rounded-lg overflow-hidden shadow-lg relative group">
        <video
          bind:this={videoElement}
          src={`${session.video_url}?token=${$token}`}
          controls
          class="w-full max-h-[600px] mx-auto"
        >
          <track kind="captions" />
        </video>
      </div>
    {/if}

    <!-- Header -->
    <div
      class="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 p-6 rounded-lg shadow-md dark:shadow-xl flex justify-between items-center transition-colors duration-300"
    >
      <div>
        <h1 class="text-3xl font-bold text-gray-900 dark:text-slate-50">
          Swing Analysis
        </h1>
        {#if session.is_personal_best}
          <span
            class="inline-block mt-2 px-3 py-1 bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-500 border border-yellow-200 dark:border-yellow-700/50 rounded-full text-sm font-medium"
          >
            ⭐ Personal Best!
          </span>
        {/if}
      </div>
      <div class="flex items-center gap-4">
        <a
          href={`/api/v1/sessions/${session.session_id}/report`}
          target="_blank"
          class="inline-flex items-center px-4 py-2 border border-gray-300 dark:border-slate-700 text-sm font-medium rounded-md shadow-sm text-gray-700 dark:text-slate-300 bg-white dark:bg-slate-800 hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors"
        >
          <svg
            class="w-4 h-4 mr-2"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
          Report
        </a>
        <button
          on:click={shareSession}
          class="inline-flex items-center px-4 py-2 border border-gray-300 dark:border-slate-700 text-sm font-medium rounded-md shadow-sm text-gray-700 dark:text-slate-300 bg-white dark:bg-slate-800 hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors"
        >
          <svg
            class="w-4 h-4 mr-2"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z"
            />
          </svg>
          Share
        </button>
        <button
          on:click={deleteSession}
          class="inline-flex items-center px-4 py-2 border border-red-200 dark:border-red-900/50 text-sm font-medium rounded-md shadow-sm text-red-600 dark:text-red-400 bg-white dark:bg-slate-800 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
        >
          <svg
            class="w-4 h-4 mr-2"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
            />
          </svg>
          Delete
        </button>
        {#if showShareMessage}
          <div
            class="absolute mt-12 right-0 bg-green-600 dark:bg-emerald-600 text-white px-4 py-2 rounded shadow-lg text-sm"
          >
            {shareMessage}
          </div>
        {/if}
        <div class="text-right">
          <div class="text-4xl font-bold text-green-600 dark:text-emerald-400">
            {session.scores.overall_score}
          </div>
          <div class="text-sm text-gray-500 dark:text-slate-400">
            Overall Score
          </div>
        </div>
      </div>
    </div>

    <!-- Tab Navigation -->
    <div
      class="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-lg shadow-md dark:shadow-xl mb-6 transition-colors duration-300"
    >
      <div class="border-b border-gray-200 dark:border-slate-800">
        <nav class="-mb-px flex space-x-8 px-6" aria-label="Tabs">
          <button
            on:click={() => (activeTab = "overview")}
            class={`${activeTab === "overview" ? "border-green-500 text-green-600 dark:border-emerald-500 dark:text-emerald-400" : "border-transparent text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200 hover:border-gray-300 dark:hover:border-slate-600"} whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-colors`}
          >
            Overview
          </button>
          <button
            on:click={() => setActivePhaseTab("address")}
            class={`${activeTab === "address" ? "border-green-500 text-green-600 dark:border-emerald-500 dark:text-emerald-400" : "border-transparent text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200 hover:border-gray-300 dark:hover:border-slate-600"} whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-colors`}
          >
            Address
          </button>
          <button
            on:click={() => setActivePhaseTab("top")}
            class={`${activeTab === "top" ? "border-green-500 text-green-600 dark:border-emerald-500 dark:text-emerald-400" : "border-transparent text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200 hover:border-gray-300 dark:hover:border-slate-600"} whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-colors`}
          >
            Top
          </button>
          <button
            on:click={() => setActivePhaseTab("impact")}
            class={`${activeTab === "impact" ? "border-green-500 text-green-600 dark:border-emerald-500 dark:text-emerald-400" : "border-transparent text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200 hover:border-gray-300 dark:hover:border-slate-600"} whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-colors`}
          >
            Impact
          </button>
          <button
            on:click={() => setActivePhaseTab("finish")}
            class={`${activeTab === "finish" ? "border-green-500 text-green-600 dark:border-emerald-500 dark:text-emerald-400" : "border-transparent text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200 hover:border-gray-300 dark:hover:border-slate-600"} whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-colors`}
          >
            Finish
          </button>
        </nav>
      </div>

      <!-- Tab Content -->
      <div class="p-6">
        {#if activeTab === "overview"}
          <!-- Feedback -->
          <!-- Feedback -->
          <div
            class="mb-8 bg-gray-50 dark:bg-slate-900 rounded-xl p-6 border border-gray-200 dark:border-slate-800 transition-colors duration-300"
          >
            <div class="flex justify-between items-start mb-4">
              <div>
                <h2
                  class="text-xl font-bold text-gray-900 dark:text-slate-50 flex items-center gap-2"
                >
                  🤖 Coach's Feedback
                </h2>
                <p class="text-sm text-gray-500 dark:text-slate-400 mt-1">
                  AI-powered analysis of your swing mechanics
                </p>
              </div>
              <button
                on:click={regenerateFeedback}
                disabled={regeneratingFeedback}
                class="inline-flex items-center px-3 py-1.5 border border-gray-300 dark:border-slate-700 text-sm font-medium rounded-md text-gray-700 dark:text-slate-300 bg-white dark:bg-slate-800 hover:bg-gray-50 dark:hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 dark:focus:ring-emerald-500 disabled:opacity-50 transition-colors"
                title="Regenerate Feedback"
              >
                {#if regeneratingFeedback}
                  <svg
                    class="animate-spin -ml-1 mr-2 h-4 w-4 text-green-500 dark:text-emerald-500"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
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
                  Updating...
                {:else}
                  <svg
                    class="w-4 h-4 mr-2 text-gray-400 dark:text-slate-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                    />
                  </svg>
                  Regenerate
                {/if}
              </button>
            </div>

            <div class="prose dark:prose-invert max-w-none">
              <p class="text-gray-700 dark:text-slate-300 leading-relaxed mb-6">
                {session.feedback.summary}
              </p>
            </div>

            {#if session.feedback.priority_issues.length > 0}
              <div class="mb-6">
                <h3
                  class="font-semibold text-red-600 dark:text-red-400 mb-3 flex items-center gap-2"
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
                      d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                    />
                  </svg>
                  Priority Issues
                </h3>
                <ul class="space-y-2">
                  {#each session.feedback.priority_issues as issue}
                    <li
                      class="flex items-start gap-2 text-gray-700 dark:text-slate-300 bg-red-50 dark:bg-slate-800 p-3 rounded-lg border border-red-200 dark:border-red-900/30 shadow-sm"
                    >
                      <span class="text-red-500 dark:text-red-400 mt-0.5"
                        >•</span
                      >
                      <span>{issue}</span>
                    </li>
                  {/each}
                </ul>
              </div>
            {/if}

            {#if session.feedback.drills.length > 0}
              <div>
                <h3
                  class="font-semibold text-green-600 dark:text-emerald-400 mb-3 flex items-center gap-2"
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
                      d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
                    />
                  </svg>
                  Recommended Drills
                </h3>
                <div class="grid gap-4 sm:grid-cols-2">
                  {#each session.feedback.drills as drill}
                    <div
                      class="bg-white dark:bg-slate-800 border border-green-200 dark:border-emerald-900/30 rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow hover:bg-gray-50 dark:hover:bg-slate-750 flex flex-col h-full"
                    >
                      <div class="flex justify-between items-start mb-2 gap-2">
                        <div
                          class="font-bold text-gray-900 dark:text-slate-200"
                        >
                          {drill.title}
                        </div>
                        {#if drill.category && drill.category !== "General"}
                          <span
                            class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800 dark:bg-slate-700 dark:text-slate-300 whitespace-nowrap"
                          >
                            {drill.category}
                          </span>
                        {/if}
                      </div>

                      <div
                        class="text-sm text-gray-600 dark:text-slate-400 leading-relaxed flex-grow mb-3"
                      >
                        {drill.description}
                      </div>

                      {#if drill.video_url}
                        <a
                          href={drill.video_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          class="inline-flex items-center text-sm font-medium text-green-600 dark:text-emerald-400 hover:text-green-700 dark:hover:text-emerald-300 mt-auto"
                        >
                          <svg
                            class="w-4 h-4 mr-1"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              stroke-linecap="round"
                              stroke-linejoin="round"
                              stroke-width="2"
                              d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"
                            ></path>
                            <path
                              stroke-linecap="round"
                              stroke-linejoin="round"
                              stroke-width="2"
                              d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                            ></path>
                          </svg>
                          Watch Video
                        </a>
                      {/if}
                    </div>
                  {/each}
                </div>
              </div>
            {/if}
          </div>

          <!-- Metrics Grid -->
          <div>
            <h2
              class="text-lg font-semibold mb-4 text-gray-900 dark:text-slate-50"
            >
              Swing Metrics
            </h2>
            <div class="metrics-container">
              <!-- 1. TEMPO -->
              {#if true}
                {@const metricKey = "tempo_ratio"}
                {@const metricData = session.scores.metric_scores[metricKey]}
                <MetricCard
                  metricName="tempo_ratio"
                  metricValue={session.metrics.tempo_ratio}
                  metricScore={metricData?.score}
                  personalBest={personalBest?.metrics?.[metricKey]}
                  description="Swing timing and rhythm"
                  breakdown={[
                    {
                      label: "Backswing",
                      value: session.metrics?.backswing_duration_ms
                        ? (
                            session.metrics.backswing_duration_ms / 1000
                          ).toFixed(2) + "s"
                        : "-",
                    },
                    {
                      label: "Downswing",
                      value: session.metrics?.downswing_duration_ms
                        ? (
                            session.metrics.downswing_duration_ms / 1000
                          ).toFixed(2) + "s"
                        : "-",
                    },
                  ]}
                />
              {/if}

              <!-- 9. HEAD STABILITY -->
              {#if true}
                {@const metricKey = "head_sway_range"}
                {@const metricData = session.scores.metric_scores[metricKey]}
                <MetricCard
                  metricName="head_sway_range"
                  metricValue={session.metrics.head_sway_range}
                  metricScore={metricData?.score}
                  personalBest={personalBest?.metrics?.[metricKey]}
                  description="Lateral head movement (lower = more stable)"
                />
              {/if}

              <!-- 10. EARLY EXTENSION -->
              {#if true}
                {@const metricKey = "early_extension_amount"}
                {@const metricData = session.scores.metric_scores[metricKey]}
                {@const hasEarlyExtension =
                  session.metrics.early_extension_amount > 0}
                <MetricCard
                  metricName="early_extension_amount"
                  metricValue={session.metrics.early_extension_amount}
                  metricScore={metricData?.score}
                  personalBest={personalBest?.metrics?.[metricKey]}
                  description="Hip thrust toward ball (common fault)"
                />
              {/if}

              <!-- 11. HEAD DROP (Address to Top) -->
              {#if session.metrics?.head_drop_cm !== undefined && session.metrics?.head_drop_cm !== null}
                {@const metricKey = "head_drop_cm"}
                {@const metricData = session.scores.metric_scores[metricKey]}
                <MetricCard
                  metricName="head_drop_cm"
                  metricValue={session.metrics.head_drop_cm.toFixed(1) + " cm"}
                  metricScore={metricData?.score}
                  personalBest={personalBest?.metrics?.[metricKey]}
                  description="Head drop in backswing (0-5cm OK)"
                />
              {/if}

              <!-- 12. HEAD RISE (Top to Impact) -->
              {#if session.metrics?.head_rise_cm !== undefined && session.metrics?.head_rise_cm !== null}
                {@const metricKey = "head_rise_cm"}
                {@const metricData = session.scores.metric_scores[metricKey]}
                <MetricCard
                  metricName="head_rise_cm"
                  metricValue={session.metrics.head_rise_cm.toFixed(1) + " cm"}
                  metricScore={metricData?.score}
                  personalBest={personalBest?.metrics?.[metricKey]}
                  description="Head lift relative to top (<2cm Ideal)"
                />
              {/if}

              <!-- 11. SWING PATH -->
              {#if session.metrics.swing_path_index !== undefined && session.metrics.swing_path_index !== null}
                {@const metricKey = "swing_path_index"}
                {@const metricData = session.scores.metric_scores[metricKey]}
                {@const pathValue = session.metrics.swing_path_index}
                {@const pathLabel =
                  pathValue < -0.1
                    ? "Shallow"
                    : pathValue > 0.1
                      ? "Over-the-Top"
                      : "Neutral"}
                <MetricCard
                  metricName="swing_path"
                  metricValue={pathLabel}
                  metricScore={metricData?.score}
                  personalBest={personalBest?.metrics?.[metricKey]}
                  description="Downswing path (shallow = good)"
                  breakdown={[
                    {
                      label: "Index",
                      value: pathValue.toFixed(2),
                    },
                  ]}
                />
              {/if}
            </div>
          </div>
        {:else}
          <!-- Position Analysis & Metrics -->
          {@const phaseName = activeTab}
          {@const phaseFrame = keyFrames.find((kf) => kf.phase === phaseName)}

          <div class="flex flex-col gap-6 w-full">
            <!-- Phase Feedback (if available) -->
            {#if session.feedback?.phase_feedback?.[phaseName]}
              <div
                class="bg-blue-50 dark:bg-blue-900/20 border border-blue-100 dark:border-blue-900/30 rounded-xl p-6 shadow-sm mb-2"
              >
                <h3
                  class="text-lg font-bold text-blue-900 dark:text-blue-300 flex items-center gap-2 mb-2"
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
                      d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                  {phaseName.charAt(0).toUpperCase() + phaseName.slice(1)} Feedback
                </h3>
                <p class="text-blue-800 dark:text-blue-200 leading-relaxed">
                  {session.feedback.phase_feedback[phaseName]}
                </p>
              </div>
            {/if}

            <div
              class="grid grid-cols-1 lg:grid-cols-[minmax(0,550px)_minmax(0,1fr)] gap-8 items-start"
            >
              <!-- Visualization -->
              <div>
                {#if phaseFrame}
                  <div
                    class="rounded-2xl bg-slate-900 shadow-xl p-3 md:p-4 border border-slate-800"
                  >
                    <SkeletonViewer
                      keyFrame={phaseFrame}
                      width={500}
                      height={600}
                      imageUrl={phaseFrame.image_url
                        ? `${phaseFrame.image_url}?token=${$token}`
                        : null}
                    />

                    <!-- Badge for MHR usage -->
                    {#if phaseFrame.landmarks_3d && phaseFrame.landmarks_3d.length > 0}
                      <div class="mt-4 text-center">
                        <span
                          class="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 dark:bg-emerald-900/30 text-green-800 dark:text-emerald-400 border border-green-200 dark:border-emerald-700/50"
                        >
                          <svg
                            class="w-4 h-4 mr-1"
                            fill="currentColor"
                            viewBox="0 0 20 20"
                            ><path
                              fill-rule="evenodd"
                              d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 01-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                              clip-rule="evenodd"
                            /></svg
                          >
                          3D MHR Skeleton
                        </span>
                      </div>
                    {/if}
                  </div>
                {:else}
                  <div
                    class="h-[600px] bg-gray-100 dark:bg-slate-800 rounded-lg flex items-center justify-center text-gray-500 dark:text-slate-500"
                  >
                    No frame found for {phaseName}
                  </div>
                {/if}
              </div>

              <!-- Highlights -->
              <div class="space-y-8 max-w-[520px] w-full mt-4 lg:mt-0">
                <div
                  class="bg-white dark:bg-slate-900 rounded-xl border border-gray-200 dark:border-slate-800 p-4 shadow-sm transition-colors duration-300"
                >
                  <h3
                    class="text-lg font-semibold text-gray-900 dark:text-slate-50 mb-2"
                  >
                    What to look for
                  </h3>
                  <ul
                    class="space-y-2 text-sm text-gray-600 dark:text-slate-300 leading-relaxed"
                  >
                    {#each poseHighlights[phaseName] || [] as point}
                      <li class="flex items-start gap-2">
                        <span
                          class="mt-1 h-2 w-2 rounded-full bg-green-500 dark:bg-emerald-500"
                        ></span>
                        <span>{point}</span>
                      </li>
                    {/each}
                  </ul>
                </div>

                <!-- Phase-specific metrics (Moved here) -->
                <div class="w-full">
                  <h3
                    class="text-lg font-semibold mb-4 capitalize text-gray-900 dark:text-slate-50"
                  >
                    {phaseName} Metrics
                  </h3>
                  <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    {#if phaseName === "address"}
                      <!-- ADDRESS METRICS -->
                      {#if session.metrics?.spine_angle_address_deg !== undefined}
                        <MetricCard
                          metricName="spine_angle_address_deg"
                          metricValue={session.metrics.spine_angle_address_deg}
                          metricScore={session.scores.metric_scores[
                            "spine_angle_address_deg"
                          ]?.score}
                          personalBest={personalBest?.metrics?.[
                            "spine_angle_address_deg"
                          ]}
                          description="Forward bend at setup"
                        />
                      {/if}
                      {#if session.metrics?.lead_arm_address_deg !== undefined}
                        <MetricCard
                          metricName="lead_arm_address_deg"
                          metricValue={session.metrics.lead_arm_address_deg}
                          metricScore={session.scores.metric_scores[
                            "lead_arm_address_deg"
                          ]?.score}
                          personalBest={personalBest?.metrics?.[
                            "lead_arm_address_deg"
                          ]}
                          description="Lead arm extension at setup"
                        />
                      {/if}
                      {#if session.metrics?.knee_flex_left_address_deg !== undefined}
                        <MetricCard
                          metricName="knee_flex_left_address_deg"
                          metricValue={session.metrics
                            .knee_flex_left_address_deg}
                          metricScore={session.scores.metric_scores[
                            "knee_flex_left_address_deg"
                          ]?.score}
                          personalBest={personalBest?.metrics?.[
                            "knee_flex_left_address_deg"
                          ]}
                          description="Knee flex at setup (athletic stance)"
                          breakdown={[
                            {
                              label: "Lead Knee",
                              value:
                                session.metrics?.knee_flex_left_address_deg?.toFixed(
                                  1,
                                ) + "°",
                            },
                            {
                              label: "Trail Knee",
                              value:
                                session.metrics?.knee_flex_right_address_deg?.toFixed(
                                  1,
                                ) + "°",
                            },
                          ]}
                        />
                      {/if}
                    {:else if phaseName === "top"}
                      <!-- TOP METRICS -->
                      {#if session.metrics?.chest_turn_top_deg !== undefined}
                        <MetricCard
                          metricName="chest_turn_top_deg"
                          metricValue={session.metrics.chest_turn_top_deg}
                          metricScore={session.scores.metric_scores[
                            "chest_turn_top_deg"
                          ]?.score}
                          personalBest={personalBest?.metrics?.[
                            "chest_turn_top_deg"
                          ]}
                          description="Upper body rotation at top"
                        />
                      {/if}
                      {#if session.metrics?.pelvis_turn_top_deg !== undefined}
                        <MetricCard
                          metricName="pelvis_turn_top_deg"
                          metricValue={session.metrics.pelvis_turn_top_deg}
                          metricScore={session.scores.metric_scores[
                            "pelvis_turn_top_deg"
                          ]?.score}
                          personalBest={personalBest?.metrics?.[
                            "pelvis_turn_top_deg"
                          ]}
                          description="Hip rotation at top"
                        />
                      {/if}
                      {#if session.metrics?.x_factor_top_deg !== undefined}
                        <MetricCard
                          metricName="x_factor_top_deg"
                          metricValue={session.metrics.x_factor_top_deg}
                          metricScore={session.scores.metric_scores[
                            "x_factor_top_deg"
                          ]?.score}
                          personalBest={personalBest?.metrics?.[
                            "x_factor_top_deg"
                          ]}
                          description="Separation between chest and pelvis"
                        />
                      {/if}
                      {#if session.metrics?.lead_arm_top_deg !== undefined}
                        <MetricCard
                          metricName="lead_arm_top_deg"
                          metricValue={session.metrics.lead_arm_top_deg}
                          metricScore={session.scores.metric_scores[
                            "lead_arm_top_deg"
                          ]?.score}
                          personalBest={personalBest?.metrics?.[
                            "lead_arm_top_deg"
                          ]}
                          description="Lead arm extension at top"
                        />
                      {/if}
                      {#if session.metrics?.trail_elbow_top_deg !== undefined}
                        <MetricCard
                          metricName="trail_elbow_top_deg"
                          metricValue={session.metrics.trail_elbow_top_deg}
                          metricScore={session.scores.metric_scores[
                            "trail_elbow_top_deg"
                          ]?.score}
                          personalBest={personalBest?.metrics?.[
                            "trail_elbow_top_deg"
                          ]}
                          description="Trail elbow angle (~90° ideal)"
                        />
                      {/if}
                      {#if session.metrics?.hand_height_at_top_index !== undefined}
                        <MetricCard
                          metricName="hand_height_at_top_index"
                          metricValue={session.metrics
                            .hand_height_at_top_index < 0.3
                            ? "Low"
                            : session.metrics.hand_height_at_top_index > 0.6
                              ? "High"
                              : "Medium"}
                          metricScore={session.scores.metric_scores[
                            "hand_height_at_top_index"
                          ]?.score}
                          personalBest={personalBest?.metrics?.[
                            "hand_height_at_top_index"
                          ]}
                          description="Hand position relative to shoulder"
                        />
                      {/if}
                    {:else if phaseName === "impact"}
                      <!-- IMPACT METRICS -->
                      {#if session.metrics?.spine_angle_impact_deg !== undefined}
                        <MetricCard
                          metricName="spine_angle_impact_deg"
                          metricValue={session.metrics.spine_angle_impact_deg}
                          metricScore={session.scores.metric_scores[
                            "spine_angle_impact_deg"
                          ]?.score}
                          personalBest={personalBest?.metrics?.[
                            "spine_angle_impact_deg"
                          ]}
                          description="Forward bend at impact"
                        />
                      {/if}
                      {#if session.metrics?.lead_arm_impact_deg !== undefined}
                        <MetricCard
                          metricName="lead_arm_impact_deg"
                          metricValue={session.metrics.lead_arm_impact_deg}
                          metricScore={session.scores.metric_scores[
                            "lead_arm_impact_deg"
                          ]?.score}
                          personalBest={personalBest?.metrics?.[
                            "lead_arm_impact_deg"
                          ]}
                          description="Lead arm extension at impact"
                        />
                      {/if}
                      {#if session.metrics?.pelvis_sway_impact_cm !== undefined}
                        <MetricCard
                          metricName="pelvis_sway_impact_cm"
                          metricValue={Math.abs(
                            session.metrics.pelvis_sway_impact_cm,
                          ).toFixed(1) + " cm"}
                          metricScore={Math.abs(
                            session.metrics.pelvis_sway_impact_cm,
                          ) < 3
                            ? "green"
                            : Math.abs(session.metrics.pelvis_sway_impact_cm) <
                                6
                              ? "yellow"
                              : "red"}
                          personalBest={personalBest?.metrics?.[
                            "pelvis_sway_impact_cm"
                          ]}
                          description="Hip lateral shift at impact"
                        />
                      {/if}
                      {#if session.metrics?.shoulder_sway_impact_cm !== undefined}
                        <MetricCard
                          metricName="shoulder_sway_impact_cm"
                          metricValue={Math.abs(
                            session.metrics.shoulder_sway_impact_cm,
                          ).toFixed(1) + " cm"}
                          metricScore={Math.abs(
                            session.metrics.shoulder_sway_impact_cm,
                          ) < 5
                            ? "green"
                            : Math.abs(
                                  session.metrics.shoulder_sway_impact_cm,
                                ) < 10
                              ? "yellow"
                              : "red"}
                          personalBest={personalBest?.metrics?.[
                            "shoulder_sway_impact_cm"
                          ]}
                          description="Shoulder lateral shift at impact"
                        />
                      {/if}
                    {:else if phaseName === "finish"}
                      <!-- FINISH METRICS -->
                      {#if session.metrics?.finish_balance != null}
                        <MetricCard
                          metricName="finish_balance"
                          metricValue={session.metrics.finish_balance > 0.7
                            ? "Excellent"
                            : session.metrics.finish_balance > 0.3
                              ? "Good"
                              : session.metrics.finish_balance > -0.3
                                ? "Neutral"
                                : "Trailing"}
                          metricScore={session.metrics.finish_balance > 0.5
                            ? "green"
                            : session.metrics.finish_balance > 0
                              ? "yellow"
                              : "red"}
                          personalBest={personalBest?.metrics?.[
                            "finish_balance"
                          ]}
                          description="Weight transfer to lead side"
                          breakdown={[
                            {
                              label: "Balance Index",
                              value: session.metrics.finish_balance.toFixed(2),
                            },
                          ]}
                        />
                      {/if}
                      {#if session.metrics?.chest_turn_finish_deg !== undefined}
                        <MetricCard
                          metricName="chest_turn_finish_deg"
                          metricValue={session.metrics.chest_turn_finish_deg}
                          metricScore={session.metrics.chest_turn_finish_deg >
                          120
                            ? "green"
                            : session.metrics.chest_turn_finish_deg > 90
                              ? "yellow"
                              : "red"}
                          personalBest={personalBest?.metrics?.[
                            "chest_turn_finish_deg"
                          ]}
                          description="Chest rotation at finish (facing target)"
                        />
                      {/if}
                      {#if session.metrics?.head_rise_top_to_finish_cm != null}
                        <MetricCard
                          metricName="head_recovery"
                          metricValue={session.metrics.head_rise_top_to_finish_cm.toFixed(
                            1,
                          ) + " cm"}
                          metricScore={Math.abs(
                            session.metrics.head_rise_top_to_finish_cm,
                          ) < 10
                            ? "green"
                            : Math.abs(
                                  session.metrics.head_rise_top_to_finish_cm,
                                ) < 20
                              ? "yellow"
                              : "red"}
                          personalBest={personalBest?.metrics?.[
                            "head_rise_top_to_finish_cm"
                          ]}
                          description="Head height change from top to finish"
                        />
                      {/if}
                      {#if session.metrics?.pelvis_sway_finish_cm != null}
                        <MetricCard
                          metricName="pelvis_sway_finish_cm"
                          metricValue={Math.abs(
                            session.metrics.pelvis_sway_finish_cm,
                          ).toFixed(1) + " cm"}
                          metricScore={Math.abs(
                            session.metrics.pelvis_sway_finish_cm,
                          ) < 3
                            ? "green"
                            : Math.abs(session.metrics.pelvis_sway_finish_cm) <
                                6
                              ? "yellow"
                              : "red"}
                          personalBest={personalBest?.metrics?.[
                            "pelvis_sway_finish_cm"
                          ]}
                          description="Hip lateral shift at finish"
                        />
                      {/if}
                    {/if}
                  </div>
                </div>
              </div>
            </div>
          </div>
        {/if}
      </div>
    </div>
  </div>
{/if}

<style>
  .metrics-container {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 1.5rem;
    margin-top: 1.5rem;
  }

  .skeleton-card {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.5rem;
    padding: 0;
    border: 2px solid transparent;
    border-radius: 8px;
    background: transparent;
    cursor: pointer;
    transition: all 0.2s;
  }

  .skeleton-card:hover {
    border-color: #007bff;
    transform: translateY(-2px);
  }

  .frame-label {
    font-size: 0.875rem;
    font-weight: 500;
    color: #94a3b8; /* slate-400 */
    text-transform: capitalize;
  }
</style>

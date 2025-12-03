<script lang="ts">
  import { page } from "$app/stores";
  import { onMount } from "svelte";
  import { token, isAuthenticated } from "$lib/stores/auth";
  import { goto } from "$app/navigation";
  import MetricExplainer from "$lib/components/MetricExplainer.svelte";
  import MetricCard from "$lib/components/MetricCard.svelte";
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
      drills: { title: string; description: string }[];
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
  let activeTab: "overview" | "positions" = "overview";

  onMount(async () => {
    const id = $page.params.id;
    if (!$isAuthenticated) {
      goto("/login");
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

      // Fetch personal best for comparison
      if (!session.is_personal_best) {
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
  <div class="text-center py-12">Loading...</div>
{:else if error}
  <div class="text-center py-12 text-red-600">{error}</div>
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
      class="bg-white p-6 rounded-lg shadow flex justify-between items-center"
    >
      <div>
        <h1 class="text-3xl font-bold text-gray-900">Swing Analysis</h1>
        {#if session.is_personal_best}
          <span
            class="inline-block mt-2 px-3 py-1 bg-yellow-100 text-yellow-800 rounded-full text-sm font-medium"
          >
            ⭐ Personal Best!
          </span>
        {/if}
      </div>
      <div class="flex items-center gap-4">
        <button
          on:click={shareSession}
          class="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md shadow-sm text-gray-700 bg-white hover:bg-gray-50"
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
          class="inline-flex items-center px-4 py-2 border border-red-300 text-sm font-medium rounded-md shadow-sm text-red-700 bg-white hover:bg-red-50"
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
            class="absolute mt-12 right-0 bg-green-600 text-white px-4 py-2 rounded shadow-lg text-sm"
          >
            {shareMessage}
          </div>
        {/if}
        <div class="text-right">
          <div class="text-4xl font-bold text-green-600">
            {session.scores.overall_score}
          </div>
          <div class="text-sm text-gray-500">Overall Score</div>
        </div>
      </div>
    </div>

    <!-- Tab Navigation -->
    <div class="bg-white rounded-lg shadow">
      <div class="border-b border-gray-200">
        <nav class="-mb-px flex space-x-8 px-6" aria-label="Tabs">
          <button
            on:click={() => (activeTab = "overview")}
            class={`${activeTab === "overview" ? "border-green-500 text-green-600" : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"} whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-colors`}
          >
            Overview
          </button>
          <button
            on:click={() => (activeTab = "positions")}
            class={`${activeTab === "positions" ? "border-green-500 text-green-600" : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"} whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-colors`}
          >
            <svg
              class="w-4 h-4 inline-block mr-1"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
              />
            </svg>
            Position Analysis
          </button>
        </nav>
      </div>

      <!-- Tab Content -->
      <div class="p-6">
        {#if activeTab === "overview"}
          <!-- Feedback -->
          <!-- Feedback -->
          <div class="mb-8 bg-gray-50 rounded-xl p-6 border border-gray-100">
            <div class="flex justify-between items-start mb-4">
              <div>
                <h2
                  class="text-xl font-bold text-gray-900 flex items-center gap-2"
                >
                  🤖 Coach's Feedback
                </h2>
                <p class="text-sm text-gray-500 mt-1">
                  AI-powered analysis of your swing mechanics
                </p>
              </div>
              <button
                on:click={regenerateFeedback}
                disabled={regeneratingFeedback}
                class="inline-flex items-center px-3 py-1.5 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 transition-colors"
                title="Regenerate Feedback"
              >
                {#if regeneratingFeedback}
                  <svg
                    class="animate-spin -ml-1 mr-2 h-4 w-4 text-indigo-600"
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
                    class="w-4 h-4 mr-2 text-gray-500"
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

            <div class="prose prose-indigo max-w-none">
              <p class="text-gray-700 leading-relaxed mb-6">
                {session.feedback.summary}
              </p>
            </div>

            {#if session.feedback.priority_issues.length > 0}
              <div class="mb-6">
                <h3
                  class="font-semibold text-red-700 mb-3 flex items-center gap-2"
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
                      class="flex items-start gap-2 text-gray-700 bg-white p-3 rounded-lg border border-red-100 shadow-sm"
                    >
                      <span class="text-red-500 mt-0.5">•</span>
                      <span>{issue}</span>
                    </li>
                  {/each}
                </ul>
              </div>
            {/if}

            {#if session.feedback.drills.length > 0}
              <div>
                <h3
                  class="font-semibold text-blue-700 mb-3 flex items-center gap-2"
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
                      class="bg-white border border-blue-100 rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow"
                    >
                      <div class="font-bold text-gray-900 mb-1">
                        {drill.title}
                      </div>
                      <div class="text-sm text-gray-600 leading-relaxed">
                        {drill.description}
                      </div>
                    </div>
                  {/each}
                </div>
              </div>
            {/if}
          </div>

          <!-- Metrics Grid -->
          <div>
            <h2 class="text-lg font-semibold mb-4">Swing Metrics</h2>
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
                  highlight={true}
                />
              {/if}

              <!-- 2. X-FACTOR -->
              {#if true}
                {@const metricKey = "x_factor_top_deg"}
                {@const metricData = session.scores.metric_scores[metricKey]}
                <MetricCard
                  metricName="x_factor_top_deg"
                  metricValue={session.metrics.x_factor_top_deg}
                  metricScore={metricData?.score}
                  personalBest={personalBest?.metrics?.[metricKey]}
                  description="Separation between chest and pelvis rotation"
                  breakdown={[
                    {
                      label: "Chest",
                      value:
                        (
                          session.metrics?.chest_turn_top_deg ??
                          session.metrics?.shoulder_turn_top_deg ??
                          0
                        ).toFixed(1) + "°",
                    },
                    {
                      label: "Pelvis",
                      value:
                        (
                          session.metrics?.pelvis_turn_top_deg ??
                          session.metrics?.hip_turn_top_deg ??
                          0
                        ).toFixed(1) + "°",
                    },
                  ]}
                  highlight={true}
                />
              {/if}

              <!-- 3. SPINE ANGLE -->
              {#if true}
                {@const metricKey = "spine_angle_address_deg"}
                {@const metricData =
                  session.scores.metric_scores[metricKey] ||
                  session.scores.metric_scores["spine_angle_impact_deg"]}
                <MetricCard
                  metricName="spine_angle_address_deg"
                  metricValue={session.metrics.spine_angle_address_deg ??
                    session.metrics.spine_angle_impact_deg}
                  metricScore={metricData?.score}
                  personalBest={personalBest?.metrics?.[metricKey]}
                  description="Forward bend (posture maintenance)"
                  breakdown={[
                    {
                      label: "Address",
                      value: session.metrics?.spine_angle_address_deg
                        ? session.metrics.spine_angle_address_deg.toFixed(1) +
                          "°"
                        : "-",
                    },
                    {
                      label: "Impact",
                      value: session.metrics?.spine_angle_impact_deg
                        ? session.metrics.spine_angle_impact_deg.toFixed(1) +
                          "°"
                        : "-",
                    },
                  ]}
                />
              {/if}

              <!-- 4. CHEST TURN -->
              {#if true}
                {@const metricKey = "chest_turn_top_deg"}
                {@const metricData =
                  session.scores.metric_scores[metricKey] ||
                  session.scores.metric_scores["shoulder_turn_top_deg"]}
                <MetricCard
                  metricName="chest_turn_top_deg"
                  metricValue={session.metrics.chest_turn_top_deg ??
                    session.metrics.shoulder_turn_top_deg}
                  metricScore={metricData?.score}
                  personalBest={personalBest?.metrics?.[metricKey] ??
                    personalBest?.metrics?.["shoulder_turn_top_deg"]}
                  description="Upper body rotation from address"
                  highlight={true}
                />
              {/if}

              <!-- 5. PELVIS TURN -->
              {#if true}
                {@const metricKey = "pelvis_turn_top_deg"}
                {@const metricData =
                  session.scores.metric_scores[metricKey] ||
                  session.scores.metric_scores["hip_turn_top_deg"]}
                <MetricCard
                  metricName="pelvis_turn_top_deg"
                  metricValue={session.metrics.pelvis_turn_top_deg ??
                    session.metrics.hip_turn_top_deg}
                  metricScore={metricData?.score}
                  personalBest={personalBest?.metrics?.[metricKey] ??
                    personalBest?.metrics?.["hip_turn_top_deg"]}
                  description="Lower body rotation from address"
                  highlight={true}
                />
              {/if}

              <!-- 6. LEAD ARM -->
              {#if true}
                {@const metricKey = "lead_arm_impact_deg"}
                {@const metricData =
                  session.scores.metric_scores[metricKey] ||
                  session.scores.metric_scores["lead_arm_top_deg"] ||
                  session.scores.metric_scores["lead_arm_address_deg"]}
                <MetricCard
                  metricName="lead_arm_impact_deg"
                  metricValue={session.metrics.lead_arm_impact_deg ??
                    session.metrics.lead_arm_top_deg ??
                    session.metrics.lead_arm_address_deg}
                  metricScore={metricData?.score}
                  personalBest={personalBest?.metrics?.[metricKey]}
                  description="Arm extension (180° = straight)"
                  breakdown={[
                    {
                      label: "Address",
                      value: session.metrics?.lead_arm_address_deg
                        ? session.metrics.lead_arm_address_deg.toFixed(1) + "°"
                        : "-",
                    },
                    {
                      label: "Top",
                      value: session.metrics?.lead_arm_top_deg
                        ? session.metrics.lead_arm_top_deg.toFixed(1) + "°"
                        : "-",
                    },
                    {
                      label: "Impact",
                      value: session.metrics?.lead_arm_impact_deg
                        ? session.metrics.lead_arm_impact_deg.toFixed(1) + "°"
                        : "-",
                    },
                  ]}
                  highlight={session.metrics.lead_arm_impact_deg !== undefined}
                />
              {/if}

              <!-- 7. TRAIL ELBOW -->
              {#if true}
                {@const metricKey = "trail_elbow_top_deg"}
                {@const metricData = session.scores.metric_scores[metricKey]}
                <MetricCard
                  metricName="trail_elbow_top_deg"
                  metricValue={session.metrics.trail_elbow_top_deg ??
                    session.metrics.trail_elbow_address_deg ??
                    session.metrics.trail_elbow_impact_deg}
                  metricScore={metricData?.score}
                  personalBest={personalBest?.metrics?.[metricKey]}
                  description="Power position (~90° at top is ideal)"
                  highlight={true}
                />
              {/if}

              <!-- 8. KNEE FLEX -->
              {#if true}
                {@const metricKey = "knee_flex_left_address_deg"}
                {@const metricData =
                  session.scores.metric_scores[metricKey] ||
                  session.scores.metric_scores["knee_flex_right_address_deg"]}
                <MetricCard
                  metricName="knee_flex_left_address_deg"
                  metricValue={session.metrics.knee_flex_left_address_deg ??
                    session.metrics.knee_flex_right_address_deg}
                  metricScore={metricData?.score}
                  personalBest={personalBest?.metrics?.[metricKey]}
                  description="Setup position (athletic stance)"
                  breakdown={[
                    {
                      label: "Lead Knee",
                      value: session.metrics?.knee_flex_left_address_deg
                        ? session.metrics.knee_flex_left_address_deg.toFixed(
                            1,
                          ) + "°"
                        : "-",
                    },
                    {
                      label: "Trail Knee",
                      value: session.metrics?.knee_flex_right_address_deg
                        ? session.metrics.knee_flex_right_address_deg.toFixed(
                            1,
                          ) + "°"
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
                  highlight={true}
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
                  warning={hasEarlyExtension}
                />
              {/if}
            </div>
          </div>
        {:else if activeTab === "positions"}
          <!-- Skeleton Visualization -->
          {#if keyFrames && keyFrames.length > 0}
            <div>
              <div class="flex items-center justify-between mb-4">
                <div>
                  <h2 class="text-lg font-semibold">Skeleton Visualization</h2>
                  <p class="text-gray-600 text-sm">
                    Key frames showing pose at critical swing positions ({keyFrames.length}
                    frame{keyFrames.length !== 1 ? "s" : ""})
                  </p>
                </div>
                <a
                  href="/sessions/{$page.params.id}/pose-editor"
                  class="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700
                         text-white rounded-lg transition-colors text-sm font-medium"
                >
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
                      d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                    />
                  </svg>
                  Open 3D Pose Editor
                </a>
              </div>
              <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                {#each keyFrames as keyFrame}
                  <button
                    type="button"
                    class="skeleton-card"
                    on:click={() => selectFrame(keyFrame)}
                  >
                    <SkeletonViewer
                      {keyFrame}
                      width={350}
                      height={500}
                      imageUrl={keyFrame.image_url
                        ? `${keyFrame.image_url}?token=${$token}`
                        : null}
                    />
                  </button>
                {/each}
              </div>
              {#if selectedFrame}
                <div class="mt-6 p-4 bg-gray-50 rounded-lg">
                  <h4 class="font-medium mb-2 capitalize">
                    {selectedFrame.phase} Frame Details
                  </h4>
                  <div class="text-sm text-gray-600">
                    <p>Frame: {selectedFrame.frame_index}</p>
                    <p>Time: {selectedFrame.timestamp_sec.toFixed(2)}s</p>
                  </div>
                </div>
              {/if}
            </div>
          {:else}
            <div
              class="text-center py-12 bg-yellow-50 rounded-lg border border-yellow-200"
            >
              <svg
                class="w-16 h-16 mx-auto text-yellow-500 mb-4"
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
              <p class="text-yellow-800 font-medium">
                Skeleton visualization not available for this session
              </p>
              <p class="text-yellow-600 text-sm mt-2">
                Upload a new swing to see skeleton visualization
              </p>
            </div>
          {/if}
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
    color: #666;
    text-transform: capitalize;
  }
</style>

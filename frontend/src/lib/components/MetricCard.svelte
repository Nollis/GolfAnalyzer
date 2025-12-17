<script lang="ts">
  import MetricExplainer from "./MetricExplainer.svelte";

  export let metricName: string;
  export let metricValue: number | string | null | undefined;
  export let metricScore: string | null = null; // "green", "yellow", "red"
  export let personalBest: number | string | null = null;
  export let description: string = "";
  export let breakdown: Array<{ label: string; value: number | string }> = [];

  function formatValue(value: number | string | null | undefined): string {
    if (value === null || value === undefined) return "-";
    if (typeof value === "number") {
      if (metricName.includes("ratio") || metricName.includes("tempo")) {
        return `${value.toFixed(2)}:1`;
      }
      if (metricName.includes("deg") || metricName.includes("angle")) {
        return `${value.toFixed(1)}°`;
      }
      if (metricName.includes("range") || metricName.includes("amount")) {
        return value.toFixed(3);
      }
      if (metricName.includes("duration") || metricName.includes("ms")) {
        return `${(value / 1000).toFixed(2)}s`;
      }
      return value.toFixed(1);
    }
    return String(value);
  }

  function getScoreClass(score: string | null): string {
    if (!score) return "neutral";
    return score; // "green", "yellow", "red"
  }

  function getDisplayName(name: string): string {
    const nameMap: Record<string, string> = {
      tempo_ratio: "Tempo",
      chest_turn_top_deg: "Chest Turn",
      pelvis_turn_top_deg: "Pelvis Turn",
      x_factor_top_deg: "X-Factor",
      spine_angle_address_deg: "Spine Angle",
      spine_angle_impact_deg: "Spine Angle",
      lead_arm_address_deg: "Lead Arm",
      lead_arm_top_deg: "Lead Arm",
      lead_arm_impact_deg: "Lead Arm",
      trail_elbow_address_deg: "Trail Elbow",
      trail_elbow_top_deg: "Trail Elbow",
      trail_elbow_impact_deg: "Trail Elbow",
      knee_flex_left_address_deg: "Knee Flex",
      knee_flex_right_address_deg: "Knee Flex",
      head_sway_range: "Head Stability",
      early_extension_amount: "Early Extension",
    };
    return (
      nameMap[name] ||
      name.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase())
    );
  }
</script>

<div
  class="p-6 border rounded-lg transition-all duration-200 {getScoreClass(
    metricScore,
  )}"
>
  <div class="flex justify-between items-center mb-2">
    <h3
      class="m-0 text-lg font-semibold text-gray-700 dark:text-slate-200 flex-1"
    >
      {getDisplayName(metricName)}
    </h3>
    {#if metricScore}
      <span
        class="text-[0.7rem] font-bold px-[0.6rem] py-[0.25rem] rounded-xl uppercase tracking-wider score-badge"
      >
        {metricScore.toUpperCase()}
      </span>
    {/if}
  </div>

  {#if description}
    <p class="text-sm text-gray-500 dark:text-slate-400 -mt-1 mb-4">
      {description}
    </p>
  {/if}

  <div class="grid grid-cols-[repeat(auto-fit,minmax(120px,1fr))] gap-4">
    <div class="metric-item">
      <span
        class="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-slate-400"
      >
        {#if metricName.includes("address")}
          Address
        {:else if metricName.includes("top")}
          At Top
        {:else if metricName.includes("impact")}
          Impact
        {:else}
          Value
        {/if}
      </span>
      <span
        class="text-3xl font-bold text-gray-900 dark:text-slate-50 metric-value"
      >
        {formatValue(metricValue)}
      </span>
    </div>

    {#if personalBest !== null && personalBest !== undefined}
      <div class="flex flex-col gap-1">
        <span
          class="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-slate-400"
          >Personal Best</span
        >
        <span class="text-xl font-bold text-yellow-600 dark:text-amber-400"
          >{formatValue(personalBest)}</span
        >
      </div>
    {/if}
  </div>

  {#if breakdown.length > 0}
    <div
      class="flex justify-between text-sm text-gray-500 dark:text-slate-400 mt-4 pt-3 border-t border-dashed border-gray-200 dark:border-white/10"
    >
      {#each breakdown as item}
        <span>{item.label}: {formatValue(item.value)}</span>
      {/each}
    </div>
  {/if}

  <div class="mt-3">
    <MetricExplainer {metricName} displayName={getDisplayName(metricName)} />
  </div>
</div>

<style>
  /* Base styles handled by utility classes now */

  /* Colored variants handling */
  div.green {
    background-color: #ecfdf5; /* emerald-50 */
    border-color: #d1fae5; /* emerald-100 */
  }
  :global(.dark) div.green {
    background-color: #022c22; /* emerald-950 */
    border-color: #064e3b; /* emerald-900 */
  }

  div.yellow {
    background-color: #fffbeb; /* amber-50 */
    border-color: #fef3c7; /* amber-100 */
  }
  :global(.dark) div.yellow {
    background-color: #451a03; /* amber-950 */
    border-color: #78350f; /* amber-900 */
  }

  div.red {
    background-color: #fef2f2; /* red-50 */
    border-color: #fee2e2; /* red-100 */
  }
  :global(.dark) div.red {
    background-color: #450a0a; /* red-950 */
    border-color: #7f1d1d; /* red-900 */
  }

  /* Fallback/Neutral */
  div.neutral {
    background-color: #ffffff;
    border-color: #e2e8f0; /* slate-200 */
  }
  :global(.dark) div.neutral {
    background-color: #0f172a; /* slate-950 */
    border-color: #1e293b; /* slate-800 */
  }

  div:hover {
    box-shadow:
      0 4px 6px -1px rgba(0, 0, 0, 0.1),
      0 2px 4px -1px rgba(0, 0, 0, 0.06);
  }
  :global(.dark) div:hover {
    border-color: #334155; /* slate-700 */
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
  }

  /* Badge Colors */
  .green .score-badge {
    background-color: #d1fae5; /* emerald-100 */
    color: #065f46; /* emerald-800 */
  }
  :global(.dark) .green .score-badge {
    background-color: #065f46; /* emerald-800 */
    color: #a7f3d0; /* emerald-200 */
  }

  .yellow .score-badge {
    background-color: #fef3c7; /* amber-100 */
    color: #92400e; /* amber-800 */
  }
  :global(.dark) .yellow .score-badge {
    background-color: #92400e; /* amber-800 */
    color: #fde68a; /* amber-200 */
  }

  .red .score-badge {
    background-color: #fee2e2; /* red-100 */
    color: #991b1b; /* red-800 */
  }
  :global(.dark) .red .score-badge {
    background-color: #991b1b; /* red-800 */
    color: #fca5a5; /* red-200 */
  }

  .neutral .score-badge {
    display: none;
  }

  /* Value Colors */
  .green .metric-value {
    color: #059669; /* emerald-600 */
  }
  :global(.dark) .green .metric-value {
    color: #34d399; /* emerald-400 */
  }

  .yellow .metric-value {
    color: #d97706; /* amber-600 */
  }
  :global(.dark) .yellow .metric-value {
    color: #fbbf24; /* amber-400 */
  }

  .red .metric-value {
    color: #dc2626; /* red-600 */
  }
  :global(.dark) .red .metric-value {
    color: #f87171; /* red-400 */
  }
</style>

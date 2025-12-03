<script lang="ts">
  import MetricExplainer from './MetricExplainer.svelte';

  export let metricName: string;
  export let metricValue: number | string | null | undefined;
  export let metricScore: string | null = null; // "green", "yellow", "red"
  export let personalBest: number | string | null = null;
  export let description: string = '';
  export let breakdown: Array<{ label: string; value: number | string }> = [];
  export let highlight: boolean = false;
  export let warning: boolean = false;

  function formatValue(value: number | string | null | undefined): string {
    if (value === null || value === undefined) return '-';
    if (typeof value === 'number') {
      // Format based on metric type
      if (metricName.includes('ratio') || metricName.includes('tempo')) {
        return `${value.toFixed(2)}:1`;
      }
      if (metricName.includes('deg') || metricName.includes('angle')) {
        return `${value.toFixed(1)}°`;
      }
      if (metricName.includes('range') || metricName.includes('amount')) {
        return value.toFixed(3);
      }
      if (metricName.includes('duration') || metricName.includes('ms')) {
        return `${(value / 1000).toFixed(2)}s`;
      }
      return value.toFixed(1);
    }
    return String(value);
  }

  function getScoreColor(score: string | null): string {
    if (!score) return '';
    if (score === 'green') return 'bg-green-100 text-green-800';
    if (score === 'yellow') return 'bg-yellow-100 text-yellow-800';
    return 'bg-red-100 text-red-800';
  }

  function getDisplayName(name: string): string {
    const nameMap: Record<string, string> = {
      tempo_ratio: 'Tempo',
      chest_turn_top_deg: 'Chest Turn',
      pelvis_turn_top_deg: 'Pelvis Turn',
      x_factor_top_deg: 'X-Factor',
      spine_angle_address_deg: 'Spine Angle',
      spine_angle_impact_deg: 'Spine Angle',
      lead_arm_address_deg: 'Lead Arm',
      lead_arm_top_deg: 'Lead Arm',
      lead_arm_impact_deg: 'Lead Arm',
      trail_elbow_address_deg: 'Trail Elbow',
      trail_elbow_top_deg: 'Trail Elbow',
      trail_elbow_impact_deg: 'Trail Elbow',
      knee_flex_left_address_deg: 'Knee Flex',
      knee_flex_right_address_deg: 'Knee Flex',
      head_sway_range: 'Head Stability',
      early_extension_amount: 'Early Extension',
    };
    return nameMap[name] || name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  }
</script>

<div class="metric-card" class:warning={warning} class:highlight={highlight}>
  <div class="metric-header">
    <h3>{getDisplayName(metricName)}</h3>
    {#if metricScore}
      <span class="score-badge {getScoreColor(metricScore)}">
        {metricScore}
      </span>
    {/if}
  </div>
  
  {#if description}
    <p class="metric-description">{description}</p>
  {/if}

  <div class="metric-grid">
    <div class="metric-item" class:highlight={highlight}>
      <span class="metric-label">
        {#if metricName.includes('address')}
          Address
        {:else if metricName.includes('top')}
          At Top
        {:else if metricName.includes('impact')}
          Impact
        {:else}
          Value
        {/if}
      </span>
      <span class="metric-value" class:large={highlight}>
        {formatValue(metricValue)}
      </span>
    </div>
    
    {#if personalBest !== null && personalBest !== undefined}
      <div class="metric-item">
        <span class="metric-label">Personal Best</span>
        <span class="metric-value personal-best">{formatValue(personalBest)}</span>
      </div>
    {/if}
  </div>

  {#if breakdown.length > 0}
    <div class="metric-breakdown">
      {#each breakdown as item}
        <span>{item.label}: {formatValue(item.value)}</span>
      {/each}
    </div>
  {/if}

  <div class="metric-explainer">
    <MetricExplainer {metricName} displayName={getDisplayName(metricName)} />
  </div>
</div>

<style>
  .metric-card {
    padding: 1.5rem;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    background: #fafafa;
    transition: all 0.2s;
  }

  .metric-card:hover {
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
  }

  .metric-card.warning {
    border-color: #f0ad4e;
    background: #fff8e6;
  }

  .metric-card.highlight {
    border-color: #007bff;
    background: #f0f8ff;
  }

  .metric-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
  }

  .metric-header h3 {
    margin: 0;
    font-size: 1.1rem;
    color: #333;
    border-bottom: 2px solid #007bff;
    padding-bottom: 0.5rem;
    flex: 1;
  }

  .score-badge {
    font-size: 0.75rem;
    font-weight: 600;
    padding: 0.25rem 0.5rem;
    border-radius: 12px;
    white-space: nowrap;
    margin-left: 0.5rem;
  }

  .metric-description {
    font-size: 0.85rem;
    color: #666;
    margin: -0.5rem 0 1rem 0;
  }

  .metric-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 1rem;
  }

  .metric-item {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .metric-item.highlight {
    background: #e8f5e9;
    padding: 0.75rem;
    border-radius: 6px;
    text-align: center;
  }

  .metric-label {
    font-size: 0.85rem;
    color: #666;
    font-weight: 500;
  }

  .metric-value {
    font-size: 1.4rem;
    font-weight: 700;
    color: #007bff;
  }

  .metric-value.large {
    font-size: 2rem;
    font-weight: 700;
    color: #2e7d32;
  }

  .metric-value.personal-best {
    color: #f59e0b;
    font-size: 1.2rem;
  }

  .metric-breakdown {
    display: flex;
    justify-content: space-between;
    font-size: 0.8rem;
    color: #666;
    margin-top: 0.5rem;
    padding-top: 0.5rem;
    border-top: 1px dashed #ddd;
  }

  .metric-explainer {
    margin-top: 0.5rem;
  }
</style>



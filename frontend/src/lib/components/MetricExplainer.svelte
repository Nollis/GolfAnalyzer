<script lang="ts">
    import MetricDiagram from "./MetricDiagram.svelte";

    export let metricName: string;
    export let displayName: string;

    let showTooltip = false;
    let showModal = false;

    const explanations: Record<string, string> = {
        tempo_ratio:
            "The ratio of backswing time to downswing time. Ideally 3.0 (3:1).",
        shoulder_turn_top_deg:
            "The angle of your shoulders relative to the target line at the top of the backswing. Ideally around 90 degrees.",
        hip_turn_top_deg:
            "The angle of your hips relative to the target line at the top of the backswing. Ideally around 45 degrees.",
        backswing_duration_ms:
            "Time taken from address to the top of the swing.",
        downswing_duration_ms:
            "Time taken from the top of the swing to impact.",
        spine_tilt_address_deg: "The angle of your spine at address.",
        spine_tilt_impact_deg: "The angle of your spine at impact.",
    };

    $: explanation = explanations[metricName] || "No explanation available.";
    $: hasDiagram = [
        "tempo_ratio",
        "shoulder_turn_top_deg",
        "hip_turn_top_deg",
    ].includes(metricName);
</script>

<div class="relative inline-block ml-1">
    <button
        class="text-gray-400 hover:text-gray-600 focus:outline-none"
        on:mouseenter={() => (showTooltip = true)}
        on:mouseleave={() => (showTooltip = false)}
        aria-label="Explain {displayName}"
    >
        <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-4 w-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
        >
            <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
        </svg>
    </button>

    {#if showTooltip}
        <div
            role="tooltip"
            class="absolute z-10 w-64 p-3 mt-1 -ml-32 text-sm text-white bg-gray-800 rounded shadow-lg bottom-full left-1/2 mb-2"
            on:mouseenter={() => (showTooltip = true)}
            on:mouseleave={() => (showTooltip = false)}
        >
            <p class="mb-2">{explanation}</p>
            {#if hasDiagram}
                <button
                    class="text-xs text-green-400 hover:text-green-300 underline focus:outline-none"
                    on:click={() => (showModal = true)}
                >
                    Visualize
                </button>
            {/if}
            <div
                class="absolute bottom-0 w-2 h-2 -mb-1 transform -translate-x-1/2 bg-gray-800 rotate-45 left-1/2"
            ></div>
        </div>
    {/if}

    {#if showModal}
        <div
            class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
        >
            <div class="bg-white rounded-lg shadow-xl p-6 max-w-sm w-full mx-4">
                <div class="flex justify-between items-center mb-4">
                    <h3 class="text-lg font-semibold text-gray-900">
                        {displayName}
                    </h3>
                    <button
                        class="text-gray-500 hover:text-gray-700"
                        on:click={() => (showModal = false)}
                    >
                        <svg
                            xmlns="http://www.w3.org/2000/svg"
                            class="h-6 w-6"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                        >
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                stroke-width="2"
                                d="M6 18L18 6M6 6l12 12"
                            />
                        </svg>
                    </button>
                </div>

                <div class="mb-4">
                    <p class="text-gray-600 mb-4">{explanation}</p>
                    <MetricDiagram {metricName} />
                </div>

                <div class="text-right">
                    <button
                        class="px-4 py-2 bg-gray-200 text-gray-800 rounded hover:bg-gray-300 transition-colors"
                        on:click={() => (showModal = false)}
                    >
                        Close
                    </button>
                </div>
            </div>
        </div>
    {/if}
</div>

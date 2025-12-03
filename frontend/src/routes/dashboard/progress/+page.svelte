<script lang="ts">
    import { onMount } from "svelte";
    import { token, isAuthenticated } from "$lib/stores/auth";
    import { goto } from "$app/navigation";
    import Chart from "$lib/components/Chart.svelte";

    interface TrendPoint {
        date: string;
        score: number;
        metrics: {
            [key: string]: number;
        };
    }

    interface TrendResponse {
        club_type: string;
        data: TrendPoint[];
    }

    let trends: TrendPoint[] = [];
    let loading = true;
    let selectedClub = "driver";
    let selectedMetric = "tempo_ratio";

    const metricsOptions = [
        { value: "tempo_ratio", label: "Tempo Ratio" },
        { value: "shoulder_turn", label: "Shoulder Turn (deg)" },
        { value: "hip_turn", label: "Hip Turn (deg)" },
    ];

    onMount(async () => {
        if (!$isAuthenticated) {
            goto("/login");
            return;
        }
        await fetchTrends();
    });

    async function fetchTrends() {
        loading = true;
        try {
            const res = await fetch(
                `/api/v1/analytics/trends?club_type=${selectedClub}`,
                {
                    headers: { Authorization: `Bearer ${$token}` },
                },
            );
            if (res.ok) {
                const data: TrendResponse[] = await res.json();
                const clubData = data.find((d) => d.club_type === selectedClub);
                trends = clubData ? clubData.data : [];
            }
        } catch (e) {
            console.error("Failed to load trends", e);
        } finally {
            loading = false;
        }
    }

    // Reactive chart data
    $: chartLabels = trends.map((t) => new Date(t.date).toLocaleDateString());

    $: scoreData = {
        labels: chartLabels,
        datasets: [
            {
                label: "Overall Score",
                data: trends.map((t) => t.score),
                borderColor: "rgb(22, 163, 74)", // green-600
                backgroundColor: "rgba(22, 163, 74, 0.1)",
                tension: 0.3,
                fill: true,
            },
        ],
    };

    $: metricData = {
        labels: chartLabels,
        datasets: [
            {
                label:
                    metricsOptions.find((m) => m.value === selectedMetric)
                        ?.label || selectedMetric,
                data: trends.map((t) => t.metrics[selectedMetric]),
                borderColor: "rgb(37, 99, 235)", // blue-600
                backgroundColor: "rgba(37, 99, 235, 0.1)",
                tension: 0.3,
                fill: true,
            },
        ],
    };

    function handleClubChange() {
        fetchTrends();
    }
</script>

<div class="space-y-8">
    <div class="flex justify-between items-center">
        <h1 class="text-3xl font-bold text-gray-900">Progress Tracking</h1>

        <select
            bind:value={selectedClub}
            on:change={handleClubChange}
            class="rounded-md border-gray-300 shadow-sm focus:border-green-500 focus:ring-green-500"
        >
            <option value="driver">Driver</option>
            <option value="iron">Iron</option>
            <option value="wedge">Wedge</option>
        </select>
    </div>

    {#if loading}
        <div class="text-center py-12">Loading charts...</div>
    {:else if trends.length === 0}
        <div class="text-center py-12 text-gray-500 bg-white rounded-lg shadow">
            No data available for {selectedClub} swings yet. Upload more videos to
            see your progress!
        </div>
    {:else}
        <!-- Score Chart -->
        <div class="bg-white p-6 rounded-lg shadow">
            <h2 class="text-lg font-semibold mb-4">Score History</h2>
            <div class="h-[300px]">
                <Chart
                    type="line"
                    data={scoreData}
                    options={{
                        scales: {
                            y: { beginAtZero: true, max: 100 },
                        },
                    }}
                />
            </div>
        </div>

        <!-- Metric Chart -->
        <div class="bg-white p-6 rounded-lg shadow">
            <div class="flex justify-between items-center mb-4">
                <h2 class="text-lg font-semibold">Metric Trends</h2>
                <select
                    bind:value={selectedMetric}
                    class="text-sm rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                >
                    {#each metricsOptions as option}
                        <option value={option.value}>{option.label}</option>
                    {/each}
                </select>
            </div>
            <div class="h-[300px]">
                <Chart type="line" data={metricData} />
            </div>
            <p class="mt-4 text-sm text-gray-500">
                Analyze how your technical metrics are changing over time.
                Consistency is key!
            </p>
        </div>
    {/if}
</div>

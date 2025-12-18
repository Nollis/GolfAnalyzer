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
        { value: "head_drop_cm", label: "Head Drop (cm)" },
        { value: "head_rise_cm", label: "Head Rise (cm)" },
        { value: "swing_path_index", label: "Swing Path Index" },
    ];

    onMount(async () => {
        await initializeAuth();
        await waitForAuthReady();

        if (!$isAuthenticated) {
            const redirectParam = encodeURIComponent(
                $page.url.pathname + $page.url.search,
            );
            goto(`/login?redirectTo=${redirectParam}`);
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

    // Chart styling helpers
    const gridColor = "rgba(100, 116, 139, 0.1)"; // slate-500 low opacity
    const tickColor = "#94a3b8"; // slate-400

    $: scoreData = {
        labels: chartLabels,
        datasets: [
            {
                label: "Overall Score",
                data: trends.map((t) => t.score),
                borderColor: "#10b981", // emerald-500
                backgroundColor: "rgba(16, 185, 129, 0.1)",
                borderWidth: 2,
                tension: 0.4,
                fill: true,
                pointBackgroundColor: "#10b981",
                pointBorderColor: "#fff",
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
                borderColor: "#3b82f6", // blue-500
                backgroundColor: "rgba(59, 130, 246, 0.1)",
                borderWidth: 2,
                tension: 0.4,
                fill: true,
                pointBackgroundColor: "#3b82f6",
                pointBorderColor: "#fff",
            },
        ],
    };

    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
            x: {
                grid: { color: gridColor },
                ticks: { color: tickColor },
            },
            y: {
                grid: { color: gridColor },
                ticks: { color: tickColor },
                beginAtZero: true,
            },
        },
        plugins: {
            legend: {
                labels: { color: tickColor },
            },
        },
    };

    function handleClubChange() {
        fetchTrends();
    }
</script>

<div class="space-y-8 animate-in fade-in duration-500">
    <div
        class="flex flex-col md:flex-row justify-between items-start md:items-center gap-4"
    >
        <div>
            <h1 class="text-3xl font-bold text-gray-900 dark:text-white">
                Progress Tracking
            </h1>
            <p class="text-gray-500 dark:text-slate-400 mt-1">
                Visualize your improvement over time
            </p>
        </div>

        <div class="relative">
            <select
                bind:value={selectedClub}
                on:change={handleClubChange}
                class="appearance-none bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 text-gray-900 dark:text-white py-2 pl-4 pr-10 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent cursor-pointer"
            >
                <option value="driver">Driver</option>
                <option value="iron">Iron</option>
                <option value="wedge">Wedge</option>
            </select>
            <div
                class="absolute inset-y-0 right-0 flex items-center px-2 pointer-events-none"
            >
                <svg
                    class="w-4 h-4 text-gray-500 dark:text-slate-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M19 9l-7 7-7-7"
                    />
                </svg>
            </div>
        </div>
    </div>

    {#if loading}
        <div class="flex flex-col items-center justify-center py-32 space-y-4">
            <div
                class="w-12 h-12 border-4 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin"
            ></div>
            <p class="text-gray-500 dark:text-slate-400">
                Loading your stats...
            </p>
        </div>
    {:else if trends.length === 0}
        <div
            class="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-2xl p-12 text-center shadow-sm"
        >
            <div
                class="w-20 h-20 bg-emerald-100 dark:bg-emerald-900/30 rounded-full flex items-center justify-center mx-auto mb-6"
            >
                <svg
                    class="w-10 h-10 text-emerald-600 dark:text-emerald-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"
                    />
                </svg>
            </div>
            <h3
                class="text-xl font-semibold text-gray-900 dark:text-white mb-2"
            >
                No Data for {selectedClub.charAt(0).toUpperCase() +
                    selectedClub.slice(1)}
            </h3>
            <p class="text-gray-500 dark:text-slate-400 max-w-md mx-auto mb-8">
                You haven't analyzed enough {selectedClub} swings yet. Upload more
                videos to see your consistency and score trends appear here!
            </p>
            <button
                on:click={() => goto("/analyze")}
                class="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-full shadow-sm text-white bg-emerald-600 hover:bg-emerald-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-emerald-500 transition-colors"
            >
                <svg
                    class="-ml-1 mr-3 h-5 w-5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"
                    />
                </svg>
                Upload New Swing
            </button>
        </div>
    {:else}
        <!-- Score Chart -->
        <div
            class="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 p-6 rounded-2xl shadow-sm"
        >
            <h2
                class="text-lg font-semibold text-gray-900 dark:text-white mb-6"
            >
                Overall Score History
            </h2>
            <div class="h-[350px]">
                <Chart type="line" data={scoreData} options={chartOptions} />
            </div>
        </div>

        <!-- Metric Chart -->
        <div
            class="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 p-6 rounded-2xl shadow-sm"
        >
            <div
                class="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-4"
            >
                <h2 class="text-lg font-semibold text-gray-900 dark:text-white">
                    Metric Trends
                </h2>
                <div class="relative">
                    <select
                        bind:value={selectedMetric}
                        class="appearance-none bg-gray-50 dark:bg-slate-800 border border-gray-200 dark:border-slate-700 text-gray-900 dark:text-white text-sm py-2 pl-3 pr-8 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent cursor-pointer"
                    >
                        {#each metricsOptions as option}
                            <option value={option.value}>{option.label}</option>
                        {/each}
                    </select>
                    <div
                        class="absolute inset-y-0 right-0 flex items-center px-2 pointer-events-none"
                    >
                        <svg
                            class="w-3 h-3 text-gray-500 dark:text-slate-400"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                        >
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                stroke-width="2"
                                d="M19 9l-7 7-7-7"
                            />
                        </svg>
                    </div>
                </div>
            </div>

            <div class="h-[350px]">
                <Chart type="line" data={metricData} options={chartOptions} />
            </div>
            <p class="mt-4 text-sm text-gray-500 dark:text-slate-500">
                Visualize how specific technical metrics are evolving. Flat
                lines mean consistency!
            </p>
        </div>
    {/if}
</div>

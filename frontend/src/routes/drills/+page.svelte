<script lang="ts">
    import { onMount } from "svelte";
    import { token } from "$lib/stores/auth";
    import { fade, fly } from "svelte/transition";

    interface Drill {
        id: string;
        title: string;
        description: string;
        category: string;
        difficulty: string;
        video_url?: string;
        target_metric?: string;
    }

    let drills: Drill[] = [];
    let loading = true;
    let error = "";

    // Filter State
    let selectedCategory = "";
    let selectedDifficulty = "";
    let searchQuery = "";
    let searchDebounceTimer: number;

    const categories = [
        "Tempo",
        "Rotation",
        "Posture",
        "Balance",
        "Arm Structure",
        "Impact",
        "Wrist Angles",
        "Path",
    ];

    const difficulties = ["Beginner", "Intermediate", "Advanced", "All Levels"];

    async function fetchDrills() {
        loading = true;
        error = "";
        try {
            let url = "http://localhost:8000/api/v1/drills/";
            const params = new URLSearchParams();

            if (selectedCategory) params.append("category", selectedCategory);
            if (selectedDifficulty)
                params.append("difficulty", selectedDifficulty);
            if (searchQuery) params.append("q", searchQuery);

            if (params.toString()) url += `?${params.toString()}`;

            const res = await fetch(url, {
                headers: {
                    Authorization: `Bearer ${$token}`,
                },
            });

            if (res.ok) {
                drills = await res.json();
            } else {
                error = "Failed to load drills";
            }
        } catch (e) {
            error = "Error connecting to server";
        } finally {
            loading = false;
        }
    }

    function selectCategory(cat: string) {
        selectedCategory = selectedCategory === cat ? "" : cat;
        fetchDrills();
    }

    function selectDifficulty(diff: string) {
        selectedDifficulty = selectedDifficulty === diff ? "" : diff;
        fetchDrills();
    }

    function clearFilters() {
        searchQuery = "";
        selectedCategory = "";
        selectedDifficulty = "";
        fetchDrills();
    }

    onMount(() => {
        fetchDrills();
    });
</script>

<div class="px-4 py-8 max-w-7xl mx-auto">
    <div
        class="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4"
    >
        <div>
            <h1 class="text-3xl font-bold text-gray-900 dark:text-slate-50">
                Drill Library
            </h1>
            <p class="text-gray-500 dark:text-slate-400 mt-1">
                Found {drills.length} drills for your game
            </p>
        </div>

        <!-- Search Bar -->
        <div class="relative w-full md:w-96">
            <div
                class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none"
            >
                <svg
                    class="h-5 w-5 text-gray-400"
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                >
                    <path
                        fill-rule="evenodd"
                        d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z"
                        clip-rule="evenodd"
                    />
                </svg>
            </div>
            <input
                type="text"
                bind:value={searchQuery}
                placeholder="Search drills (e.g., 'slice', 'posture')..."
                class="block w-full pl-10 pr-3 py-2 border border-gray-300 dark:border-slate-700 rounded-lg leading-5 bg-white dark:bg-slate-900 text-gray-900 dark:text-slate-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 sm:text-sm transition-colors"
                on:input={() => {
                    clearTimeout(searchDebounceTimer);
                    searchDebounceTimer = setTimeout(fetchDrills, 300);
                }}
            />
        </div>
    </div>

    <!-- Filter Pills -->
    <div class="space-y-4 mb-8">
        <!-- Categories -->
        <div class="flex flex-wrap gap-2">
            {#each categories as cat}
                <button
                    on:click={() => selectCategory(cat)}
                    class="px-3 py-1.5 rounded-full text-sm font-medium transition-all duration-200 border {selectedCategory ===
                    cat
                        ? 'bg-green-600 text-white border-green-600 shadow-md'
                        : 'bg-white dark:bg-slate-800 text-gray-700 dark:text-slate-300 border-gray-200 dark:border-slate-700 hover:border-green-500 dark:hover:border-emerald-500'}"
                >
                    {cat}
                </button>
            {/each}
        </div>

        <!-- Difficulties -->
        <div class="flex flex-wrap gap-2">
            {#each difficulties as diff}
                <button
                    on:click={() => selectDifficulty(diff)}
                    class="px-3 py-1.5 rounded-full text-xs font-medium uppercase tracking-wide transition-all duration-200 border {selectedDifficulty ===
                    diff
                        ? 'bg-blue-600 text-white border-blue-600 shadow-md'
                        : 'bg-white dark:bg-slate-800 text-gray-600 dark:text-slate-400 border-gray-200 dark:border-slate-700 hover:border-blue-500 dark:hover:border-blue-400'}"
                >
                    {diff}
                </button>
            {/each}
        </div>
    </div>

    {#if loading}
        <div class="text-center py-20">
            <div
                class="animate-spin rounded-full h-12 w-12 border-b-2 border-green-500 dark:border-emerald-500 mx-auto"
            ></div>
            <p class="mt-4 text-gray-500 dark:text-slate-400">
                Loading library...
            </p>
        </div>
    {:else if error}
        <div
            class="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-900/50 text-red-600 dark:text-red-400 px-4 py-3 rounded-lg relative"
            role="alert"
        >
            <strong class="font-bold">Error!</strong>
            <span class="block sm:inline">{error}</span>
        </div>
    {:else if drills.length === 0}
        <div
            class="text-center py-20 bg-gray-50 dark:bg-slate-900/50 rounded-xl border border-dashed border-gray-300 dark:border-slate-700"
        >
            <svg
                class="mx-auto h-12 w-12 text-gray-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
            >
                <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
            </svg>
            <h3
                class="mt-2 text-sm font-medium text-gray-900 dark:text-slate-200"
            >
                No drills found
            </h3>
            <p class="mt-1 text-sm text-gray-500 dark:text-slate-400">
                Try adjusting your search or filters.
            </p>
            <button
                on:click={clearFilters}
                class="mt-6 inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
            >
                Clear all filters
            </button>
        </div>
    {:else}
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {#each drills as drill (drill.id)}
                <div
                    in:fade={{ duration: 200 }}
                    class="group bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl shadow-sm hover:shadow-xl hover:border-green-500/30 dark:hover:border-emerald-500/30 transition-all duration-300 flex flex-col h-full"
                >
                    {#if drill.video_url}
                        <div
                            class="aspect-w-16 aspect-h-9 bg-gray-100 dark:bg-slate-800 relative overflow-hidden rounded-t-xl"
                        >
                            <!-- Placeholder -->
                            <div
                                class="absolute inset-0 flex items-center justify-center text-gray-400"
                            >
                                <span
                                    class="bg-black/50 px-3 py-1 rounded text-white text-xs font-medium"
                                    >Video Drill</span
                                >
                            </div>
                        </div>
                    {/if}

                    <div class="p-5 flex-1 flex flex-col">
                        <div class="flex justify-between items-start mb-3">
                            <span
                                class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-emerald-900/30 dark:text-emerald-300"
                            >
                                {drill.category}
                            </span>
                            <span
                                class="text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider"
                            >
                                {drill.difficulty}
                            </span>
                        </div>

                        <h3
                            class="text-lg font-bold text-gray-900 dark:text-slate-50 mb-2 group-hover:text-green-600 dark:group-hover:text-emerald-400 transition-colors"
                        >
                            {drill.title}
                        </h3>

                        <p
                            class="text-gray-600 dark:text-slate-400 text-sm mb-4 flex-1"
                        >
                            {drill.description}
                        </p>

                        {#if drill.target_metric}
                            <div
                                class="mb-4 pt-3 border-t border-gray-100 dark:border-slate-800"
                            >
                                <p
                                    class="text-xs text-gray-500 dark:text-slate-500 uppercase tracking-wide font-semibold mb-1"
                                >
                                    Targets Metric
                                </p>
                                <code
                                    class="text-xs bg-gray-100 dark:bg-slate-800 text-gray-700 dark:text-slate-300 px-2 py-1 rounded"
                                >
                                    {drill.target_metric.replace(/_/g, " ")}
                                </code>
                            </div>
                        {/if}

                        <a
                            href="/drills/{drill.id}"
                            class="mt-auto w-full flex items-center justify-center px-4 py-2 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-gray-900 dark:bg-slate-700 hover:bg-green-600 dark:hover:bg-emerald-600 focus:outline-none transition-colors"
                        >
                            View Details
                        </a>
                    </div>
                </div>
            {/each}
        </div>
    {/if}
</div>

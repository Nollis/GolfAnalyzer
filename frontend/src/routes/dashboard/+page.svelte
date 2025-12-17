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
    import OnboardingTour from "$lib/components/OnboardingTour.svelte";

    interface DashboardStats {
        total_sessions: number;
        average_score: number;
        last_session_date: string | null;
        personal_bests: {
            driver: number | null;
            iron: number | null;
            wedge: number | null;
        };
    }

    interface Session {
        session_id: string;
        scores: {
            overall_score: number;
        };
        metadata: {
            club_type: string;
            view: string;
        };
        is_personal_best: boolean;
        created_at?: string;
    }

    let stats: DashboardStats | null = null;
    let recentSessions: Session[] = [];
    let loading = true;

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

        try {
            // Fetch Stats
            const statsRes = await fetch("/api/v1/analytics/dashboard-stats", {
                headers: { Authorization: `Bearer ${$token}` },
            });
            if (statsRes.ok) stats = await statsRes.json();

            // Load initial sessions
            await loadSessions();
        } catch (e) {
            console.error("Failed to load dashboard data", e);
        } finally {
            loading = false;
        }
    });

    // Filtering & Pagination State
    let selectedView: string | null = null;
    let selectedClub: string | null = null;
    let currentPage = 1;
    const limit = 10;

    // Filter Options
    const viewOptions = [
        { id: "face_on", label: "Face On" },
        { id: "down_the_line", label: "Down the Line" },
    ];

    const clubOptions = [
        { id: "driver", label: "Driver" },
        { id: "iron", label: "Iron" },
        { id: "wedge", label: "Wedge" },
    ];

    async function loadSessions() {
        if (!$isAuthenticated) return;

        loading = true; // Show loading state while fetching
        try {
            const params = new URLSearchParams({
                limit: limit.toString(),
                skip: ((currentPage - 1) * limit).toString(),
            });

            if (selectedView) params.append("view", selectedView);
            if (selectedClub) params.append("club_type", selectedClub);

            const res = await fetch(`/api/v1/sessions?${params}`, {
                headers: { Authorization: `Bearer ${$token}` },
            });

            if (res.ok) {
                recentSessions = await res.json();
            }
        } finally {
            loading = false;
        }
    }

    function toggleView(view: string) {
        if (selectedView === view) selectedView = null;
        else selectedView = view;
        currentPage = 1;
        loadSessions();
    }

    function toggleClub(club: string) {
        if (selectedClub === club) selectedClub = null;
        else selectedClub = club;
        currentPage = 1;
        loadSessions();
    }

    function nextPage() {
        if (recentSessions.length === limit) {
            currentPage++;
            loadSessions();
        }
    }

    function prevPage() {
        if (currentPage > 1) {
            currentPage--;
            loadSessions();
        }
    }

    function formatDate(dateStr: string | null | undefined) {
        if (!dateStr) return "N/A";
        return new Date(dateStr).toLocaleDateString();
    }
</script>

<OnboardingTour />

<div class="space-y-8">
    <div class="flex justify-between items-center">
        <h1 class="text-3xl font-bold text-gray-900 dark:text-slate-50">
            Dashboard
        </h1>
        <div class="space-x-4">
            <a
                href="/dashboard/progress"
                class="text-green-600 hover:text-green-700 dark:text-emerald-400 dark:hover:text-emerald-300 font-medium"
            >
                View Progress
            </a>
            <a
                href="/analyze"
                class="bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 dark:bg-emerald-600 dark:hover:bg-emerald-500 font-medium transition-colors"
            >
                New Analysis
            </a>
        </div>
    </div>

    {#if loading}
        <div class="text-center py-12 text-gray-500 dark:text-slate-400">
            Loading dashboard...
        </div>
    {:else if stats}
        <!-- Stats Grid -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <!-- Quick Stats -->
            <div
                class="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 p-6 rounded-lg shadow-md dark:shadow-xl transition-colors duration-300"
            >
                <h3
                    class="text-gray-500 dark:text-slate-400 text-sm font-medium uppercase"
                >
                    Total Sessions
                </h3>
                <div
                    class="mt-2 text-3xl font-bold text-gray-900 dark:text-slate-50"
                >
                    {stats.total_sessions}
                </div>
                <div class="mt-1 text-sm text-gray-500 dark:text-slate-500">
                    Last: {formatDate(stats.last_session_date)}
                </div>
            </div>

            <div
                class="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 p-6 rounded-lg shadow-md dark:shadow-xl transition-colors duration-300"
            >
                <h3
                    class="text-gray-500 dark:text-slate-400 text-sm font-medium uppercase"
                >
                    Average Score
                </h3>
                <div
                    class="mt-2 text-3xl font-bold text-green-600 dark:text-emerald-400"
                >
                    {stats.average_score}
                </div>
                <div class="mt-1 text-sm text-gray-500 dark:text-slate-500">
                    Overall performance
                </div>
            </div>

            <div
                class="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 p-6 rounded-lg shadow-md dark:shadow-xl transition-colors duration-300"
            >
                <h3
                    class="text-gray-500 dark:text-slate-400 text-sm font-medium uppercase"
                >
                    Personal Bests
                </h3>
                <div class="mt-4 space-y-2">
                    <div class="flex justify-between items-center">
                        <span class="text-gray-500 dark:text-slate-400"
                            >Driver</span
                        >
                        <span class="font-bold text-gray-900 dark:text-slate-50"
                            >{stats.personal_bests.driver || "-"}</span
                        >
                    </div>
                    <div class="flex justify-between items-center">
                        <span class="text-gray-500 dark:text-slate-400"
                            >Iron</span
                        >
                        <span class="font-bold text-gray-900 dark:text-slate-50"
                            >{stats.personal_bests.iron || "-"}</span
                        >
                    </div>
                    <div class="flex justify-between items-center">
                        <span class="text-gray-500 dark:text-slate-400"
                            >Wedge</span
                        >
                        <span class="font-bold text-gray-900 dark:text-slate-50"
                            >{stats.personal_bests.wedge || "-"}</span
                        >
                    </div>
                </div>
            </div>
        </div>

        <!-- Filter Controls -->
        <div
            class="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-lg p-6 shadow-sm mb-6"
        >
            <h3
                class="text-sm font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-4"
            >
                Filters
            </h3>

            <div class="flex flex-col md:flex-row gap-6">
                <!-- View Filter -->
                <div>
                    <span class="text-sm text-gray-600 dark:text-slate-300 mr-3"
                        >View:</span
                    >
                    <div class="inline-flex flex-wrap gap-2">
                        {#each viewOptions as option}
                            <button
                                on:click={() => toggleView(option.id)}
                                class="px-3 py-1.5 rounded-full text-sm font-medium transition-colors border
                                {selectedView === option.id
                                    ? 'bg-green-100 dark:bg-emerald-900/40 text-green-800 dark:text-emerald-300 border-green-200 dark:border-emerald-700'
                                    : 'bg-gray-100 dark:bg-slate-800 text-gray-600 dark:text-slate-400 border-transparent hover:bg-gray-200 dark:hover:bg-slate-700'}"
                            >
                                {option.label}
                            </button>
                        {/each}
                    </div>
                </div>

                <!-- Club Filter -->
                <div>
                    <span class="text-sm text-gray-600 dark:text-slate-300 mr-3"
                        >Club:</span
                    >
                    <div class="inline-flex flex-wrap gap-2">
                        {#each clubOptions as option}
                            <button
                                on:click={() => toggleClub(option.id)}
                                class="px-3 py-1.5 rounded-full text-sm font-medium transition-colors border
                                {selectedClub === option.id
                                    ? 'bg-green-100 dark:bg-emerald-900/40 text-green-800 dark:text-emerald-300 border-green-200 dark:border-emerald-700'
                                    : 'bg-gray-100 dark:bg-slate-800 text-gray-600 dark:text-slate-400 border-transparent hover:bg-gray-200 dark:hover:bg-slate-700'}"
                            >
                                {option.label}
                            </button>
                        {/each}
                    </div>
                </div>
            </div>
        </div>

        <!-- Session History -->
        <div
            class="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-lg shadow-md dark:shadow-xl overflow-hidden transition-colors duration-300"
        >
            <div
                class="px-6 py-4 border-b border-gray-200 dark:border-slate-800 flex justify-between items-center"
            >
                <h2
                    class="text-lg font-semibold text-gray-900 dark:text-slate-50"
                >
                    Measurement History
                </h2>
                <span
                    class="text-sm text-gray-500 dark:text-slate-400 font-medium"
                >
                    Page {currentPage}
                </span>
            </div>
            <ul class="divide-y divide-gray-200 dark:divide-slate-800">
                {#each recentSessions as session}
                    <li>
                        <a
                            href={`/sessions/${session.session_id}`}
                            class="block hover:bg-gray-50 dark:hover:bg-slate-800/50 transition-colors"
                        >
                            <div
                                class="px-6 py-4 flex items-center justify-between"
                            >
                                <div class="flex items-center">
                                    <div
                                        class="flex-shrink-0 h-10 w-10 rounded-full bg-gray-100 dark:bg-slate-800 border border-gray-200 dark:border-slate-700 flex items-center justify-center text-green-600 dark:text-emerald-400 font-bold"
                                    >
                                        {session.scores.overall_score}
                                    </div>
                                    <div class="ml-4">
                                        <div
                                            class="text-sm font-medium text-gray-900 dark:text-slate-200 capitalize"
                                        >
                                            {session.metadata.club_type} Swing
                                        </div>
                                        <div
                                            class="text-sm text-gray-500 dark:text-slate-500"
                                        >
                                            {formatDate(session.created_at)} • {session.metadata.view.replace(
                                                "_",
                                                " ",
                                            )}
                                        </div>
                                    </div>
                                </div>
                                <div class="flex items-center">
                                    {#if session.is_personal_best}
                                        <span
                                            class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-500 border border-yellow-200 dark:border-yellow-700/50 mr-2"
                                        >
                                            PB
                                        </span>
                                    {/if}
                                    <svg
                                        class="h-5 w-5 text-gray-400 dark:text-slate-500"
                                        viewBox="0 0 20 20"
                                        fill="currentColor"
                                    >
                                        <path
                                            fill-rule="evenodd"
                                            d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"
                                            clip-rule="evenodd"
                                        />
                                    </svg>
                                </div>
                            </div>
                        </a>
                    </li>
                {/each}
                {#if recentSessions.length === 0}
                    <li
                        class="px-6 py-8 text-center text-gray-500 dark:text-slate-500"
                    >
                        No sessions found. Try adjusting your filters.
                    </li>
                {/if}
            </ul>

            <!-- Pagination Controls -->
            <div
                class="bg-gray-50 dark:bg-slate-800/50 px-6 py-3 border-t border-gray-200 dark:border-slate-800 flex items-center justify-between"
            >
                <button
                    on:click={prevPage}
                    disabled={currentPage === 1}
                    class="relative inline-flex items-center px-4 py-2 border border-gray-300 dark:border-slate-600 text-sm font-medium rounded-md text-gray-700 dark:text-slate-200 bg-white dark:bg-slate-800 hover:bg-gray-50 dark:hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    Previous
                </button>
                <div
                    class="hidden sm:flex-1 sm:flex sm:items-center sm:justify-center"
                >
                    <p class="text-sm text-gray-700 dark:text-slate-400">
                        Showing results for page <span class="font-medium"
                            >{currentPage}</span
                        >
                    </p>
                </div>
                <button
                    on:click={nextPage}
                    disabled={recentSessions.length < limit}
                    class="relative inline-flex items-center px-4 py-2 border border-gray-300 dark:border-slate-600 text-sm font-medium rounded-md text-gray-700 dark:text-slate-200 bg-white dark:bg-slate-800 hover:bg-gray-50 dark:hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    Next
                </button>
            </div>
        </div>
    {/if}
</div>

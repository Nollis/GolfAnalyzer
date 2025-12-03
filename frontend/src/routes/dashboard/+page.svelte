<script lang="ts">
    import { onMount } from "svelte";
    import { token, isAuthenticated } from "$lib/stores/auth";
    import { goto } from "$app/navigation";
    import OnboardingTour from "$lib/components/OnboardingTour.svelte";

    export let data;
    export let params;

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
        if (!$isAuthenticated) {
            goto("/login");
            return;
        }

        try {
            // Fetch Stats
            const statsRes = await fetch("/api/v1/analytics/dashboard-stats", {
                headers: { Authorization: `Bearer ${$token}` },
            });
            if (statsRes.ok) stats = await statsRes.json();

            // Fetch Recent Sessions
            const sessionsRes = await fetch("/api/v1/sessions?limit=5", {
                headers: { Authorization: `Bearer ${$token}` },
            });
            if (sessionsRes.ok) {
                recentSessions = await sessionsRes.json();
                console.log("Recent sessions:", recentSessions);
            }
        } catch (e) {
            console.error("Failed to load dashboard data", e);
        } finally {
            loading = false;
        }
    });

    function formatDate(dateStr: string | null | undefined) {
        if (!dateStr) return "N/A";
        return new Date(dateStr).toLocaleDateString();
    }
</script>

<OnboardingTour />

<div class="space-y-8">
    <div class="flex justify-between items-center">
        <h1 class="text-3xl font-bold text-gray-900">Dashboard</h1>
        <div class="space-x-4">
            <a
                href="/dashboard/progress"
                class="text-green-600 hover:text-green-800 font-medium"
            >
                View Progress
            </a>
            <a
                href="/"
                class="bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 font-medium"
            >
                New Analysis
            </a>
        </div>
    </div>

    {#if loading}
        <div class="text-center py-12">Loading dashboard...</div>
    {:else if stats}
        <!-- Stats Grid -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <!-- Quick Stats -->
            <div class="bg-white p-6 rounded-lg shadow">
                <h3 class="text-gray-500 text-sm font-medium uppercase">
                    Total Sessions
                </h3>
                <div class="mt-2 text-3xl font-bold text-gray-900">
                    {stats.total_sessions}
                </div>
                <div class="mt-1 text-sm text-gray-500">
                    Last: {formatDate(stats.last_session_date)}
                </div>
            </div>

            <div class="bg-white p-6 rounded-lg shadow">
                <h3 class="text-gray-500 text-sm font-medium uppercase">
                    Average Score
                </h3>
                <div class="mt-2 text-3xl font-bold text-green-600">
                    {stats.average_score}
                </div>
                <div class="mt-1 text-sm text-gray-500">
                    Overall performance
                </div>
            </div>

            <div class="bg-white p-6 rounded-lg shadow">
                <h3 class="text-gray-500 text-sm font-medium uppercase">
                    Personal Bests
                </h3>
                <div class="mt-4 space-y-2">
                    <div class="flex justify-between items-center">
                        <span class="text-gray-600">Driver</span>
                        <span class="font-bold text-gray-900"
                            >{stats.personal_bests.driver || "-"}</span
                        >
                    </div>
                    <div class="flex justify-between items-center">
                        <span class="text-gray-600">Iron</span>
                        <span class="font-bold text-gray-900"
                            >{stats.personal_bests.iron || "-"}</span
                        >
                    </div>
                    <div class="flex justify-between items-center">
                        <span class="text-gray-600">Wedge</span>
                        <span class="font-bold text-gray-900"
                            >{stats.personal_bests.wedge || "-"}</span
                        >
                    </div>
                </div>
            </div>
        </div>

        <!-- Recent Activity -->
        <div class="bg-white rounded-lg shadow overflow-hidden">
            <div
                class="px-6 py-4 border-b border-gray-200 flex justify-between items-center"
            >
                <h2 class="text-lg font-semibold text-gray-900">
                    Recent Activity
                </h2>
                <a
                    href="/sessions"
                    class="text-green-600 hover:text-green-800 text-sm font-medium"
                    >View All</a
                >
            </div>
            <ul class="divide-y divide-gray-200">
                {#each recentSessions as session}
                    <li>
                        <a
                            href={`/sessions/${session.session_id}`}
                            class="block hover:bg-gray-50"
                        >
                            <div
                                class="px-6 py-4 flex items-center justify-between"
                            >
                                <div class="flex items-center">
                                    <div
                                        class="flex-shrink-0 h-10 w-10 rounded-full bg-green-100 flex items-center justify-center text-green-600 font-bold"
                                    >
                                        {session.scores.overall_score}
                                    </div>
                                    <div class="ml-4">
                                        <div
                                            class="text-sm font-medium text-gray-900 capitalize"
                                        >
                                            {session.metadata.club_type} Swing
                                        </div>
                                        <div class="text-sm text-gray-500">
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
                                            class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-yellow-100 text-yellow-800 mr-2"
                                        >
                                            PB
                                        </span>
                                    {/if}
                                    <svg
                                        class="h-5 w-5 text-gray-400"
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
                    <li class="px-6 py-8 text-center text-gray-500">
                        No sessions yet. Upload your first video to get started!
                    </li>
                {/if}
            </ul>
        </div>
    {/if}
</div>

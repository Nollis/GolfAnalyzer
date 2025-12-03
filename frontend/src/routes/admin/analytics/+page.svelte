<script lang="ts">
    import { onMount } from "svelte";
    import { token } from "$lib/stores/auth";

    interface PlatformStats {
        total_users: number;
        active_users: number;
        total_sessions: number;
        sessions_by_club_type: Record<string, number>;
        recent_registrations: number;
    }

    let stats: PlatformStats | null = null;
    let loading = true;
    let error = "";

    onMount(async () => {
        try {
            const res = await fetch("/api/v1/admin/analytics/platform-stats", {
                headers: { Authorization: `Bearer ${$token}` },
            });

            if (!res.ok) {
                if (res.status === 403) {
                    error = "Access denied. Admin privileges required.";
                } else {
                    error = "Failed to load analytics";
                }
                return;
            }

            stats = await res.json();
        } catch (e) {
            error = "Error connecting to server";
        } finally {
            loading = false;
        }
    });
</script>

<div class="space-y-6">
    <h1 class="text-3xl font-bold text-gray-900">Platform Analytics</h1>

    {#if error}
        <div class="bg-red-100 text-red-700 p-4 rounded-md">{error}</div>
    {/if}

    {#if loading}
        <div class="text-center py-12">Loading analytics...</div>
    {:else if stats}
        <!-- Stats Grid -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div class="bg-white p-6 rounded-lg shadow">
                <div class="flex items-center">
                    <div class="flex-shrink-0 bg-blue-500 rounded-md p-3">
                        <svg
                            class="h-6 w-6 text-white"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                        >
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                stroke-width="2"
                                d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"
                            />
                        </svg>
                    </div>
                    <div class="ml-4">
                        <p class="text-sm font-medium text-gray-500">
                            Total Users
                        </p>
                        <p class="text-2xl font-semibold text-gray-900">
                            {stats.total_users}
                        </p>
                    </div>
                </div>
            </div>

            <div class="bg-white p-6 rounded-lg shadow">
                <div class="flex items-center">
                    <div class="flex-shrink-0 bg-green-500 rounded-md p-3">
                        <svg
                            class="h-6 w-6 text-white"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                        >
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                stroke-width="2"
                                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                            />
                        </svg>
                    </div>
                    <div class="ml-4">
                        <p class="text-sm font-medium text-gray-500">
                            Active Users (30d)
                        </p>
                        <p class="text-2xl font-semibold text-gray-900">
                            {stats.active_users}
                        </p>
                    </div>
                </div>
            </div>

            <div class="bg-white p-6 rounded-lg shadow">
                <div class="flex items-center">
                    <div class="flex-shrink-0 bg-purple-500 rounded-md p-3">
                        <svg
                            class="h-6 w-6 text-white"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                        >
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                stroke-width="2"
                                d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
                            />
                        </svg>
                    </div>
                    <div class="ml-4">
                        <p class="text-sm font-medium text-gray-500">
                            Total Sessions
                        </p>
                        <p class="text-2xl font-semibold text-gray-900">
                            {stats.total_sessions}
                        </p>
                    </div>
                </div>
            </div>

            <div class="bg-white p-6 rounded-lg shadow">
                <div class="flex items-center">
                    <div class="flex-shrink-0 bg-yellow-500 rounded-md p-3">
                        <svg
                            class="h-6 w-6 text-white"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                        >
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                stroke-width="2"
                                d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z"
                            />
                        </svg>
                    </div>
                    <div class="ml-4">
                        <p class="text-sm font-medium text-gray-500">
                            New Users (7d)
                        </p>
                        <p class="text-2xl font-semibold text-gray-900">
                            {stats.recent_registrations}
                        </p>
                    </div>
                </div>
            </div>
        </div>

        <!-- Sessions by Club Type -->
        <div class="bg-white p-6 rounded-lg shadow">
            <h2 class="text-lg font-semibold text-gray-900 mb-4">
                Sessions by Club Type
            </h2>
            <div class="space-y-4">
                {#each Object.entries(stats.sessions_by_club_type) as [club, count]}
                    <div>
                        <div class="flex justify-between items-center mb-1">
                            <span
                                class="text-sm font-medium text-gray-700 capitalize"
                                >{club}</span
                            >
                            <span class="text-sm font-semibold text-gray-900"
                                >{count}</span
                            >
                        </div>
                        <div class="w-full bg-gray-200 rounded-full h-2">
                            <div
                                class="bg-green-600 h-2 rounded-full"
                                style="width: {(count / stats.total_sessions) *
                                    100}%"
                            ></div>
                        </div>
                    </div>
                {/each}
            </div>
        </div>

        <!-- User Engagement -->
        <div class="bg-white p-6 rounded-lg shadow">
            <h2 class="text-lg font-semibold text-gray-900 mb-4">
                User Engagement
            </h2>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div>
                    <p class="text-sm text-gray-500">Avg Sessions per User</p>
                    <p class="text-2xl font-semibold text-gray-900">
                        {stats.total_users > 0
                            ? (
                                  stats.total_sessions / stats.total_users
                              ).toFixed(1)
                            : 0}
                    </p>
                </div>
                <div>
                    <p class="text-sm text-gray-500">Active User Rate</p>
                    <p class="text-2xl font-semibold text-gray-900">
                        {stats.total_users > 0
                            ? (
                                  (stats.active_users / stats.total_users) *
                                  100
                              ).toFixed(1)
                            : 0}%
                    </p>
                </div>
                <div>
                    <p class="text-sm text-gray-500">Growth Rate (7d)</p>
                    <p class="text-2xl font-semibold text-green-600">
                        +{stats.recent_registrations}
                    </p>
                </div>
            </div>
        </div>
    {/if}
</div>

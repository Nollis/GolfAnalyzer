<script lang="ts">
    import { onMount } from "svelte";
    import { page } from "$app/stores";
    import { token, isAuthenticated } from "$lib/stores/auth";
    import { goto } from "$app/navigation";

    interface Session {
        session_id: string;
        created_at: string;
        scores: {
            overall_score: number;
        };
        metadata: {
            club_type: string;
            view: string;
        };
    }

    interface MetricDiff {
        metric_name: string;
        session_1_value: number;
        session_2_value: number;
        diff: number;
        improvement: boolean;
    }

    interface ComparisonData {
        session_1: { created_at: string };
        session_2: { created_at: string };
        metrics: MetricDiff[];
    }

    let sessions: Session[] = [];
    let selectedSessionId1 = "";
    let selectedSessionId2 = "";
    let comparisonData: ComparisonData | null = null;
    let loading = true;
    let comparing = false;

    onMount(async () => {
        if (!$isAuthenticated) {
            goto("/login");
            return;
        }

        // Check for query params to pre-select
        const s1 = $page.url.searchParams.get("s1");
        if (s1) selectedSessionId1 = s1;

        await fetchSessions();
    });

    async function fetchSessions() {
        try {
            const res = await fetch("/api/v1/sessions?limit=50", {
                headers: { Authorization: `Bearer ${$token}` },
            });
            if (res.ok) {
                sessions = await res.json();
                // If we have a pre-selected s1, try to find a good default s2 (e.g. previous session of same club)
                if (selectedSessionId1 && !selectedSessionId2) {
                    const s1 = sessions.find(
                        (s) => s.session_id === selectedSessionId1,
                    );
                    if (s1) {
                        const sameClub = sessions.filter(
                            (s) =>
                                s.metadata.club_type ===
                                    s1.metadata.club_type &&
                                s.session_id !== s1.session_id,
                        );
                        if (sameClub.length > 0) {
                            selectedSessionId2 = sameClub[0].session_id;
                        }
                    }
                }
            }
        } catch (e) {
            console.error("Failed to load sessions", e);
        } finally {
            loading = false;
        }
    }

    async function compareSessions() {
        if (!selectedSessionId1 || !selectedSessionId2) return;

        comparing = true;
        try {
            const res = await fetch(
                `/api/v1/analytics/comparison?session_id_1=${selectedSessionId1}&session_id_2=${selectedSessionId2}`,
                {
                    headers: { Authorization: `Bearer ${$token}` },
                },
            );
            if (res.ok) {
                comparisonData = await res.json();
            }
        } catch (e) {
            console.error("Failed to compare", e);
        } finally {
            comparing = false;
        }
    }

    // Auto-compare if both selected
    $: if (selectedSessionId1 && selectedSessionId2 && !loading) {
        compareSessions();
    }

    function formatDate(dateStr: string) {
        if (!dateStr) return "N/A";
        return (
            new Date(dateStr).toLocaleDateString() +
            " " +
            new Date(dateStr).toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
            })
        );
    }
</script>

<div class="space-y-8">
    <h1 class="text-3xl font-bold text-gray-900">Session Comparison</h1>

    <!-- Selection Controls -->
    <div
        class="bg-white p-6 rounded-lg shadow grid grid-cols-1 md:grid-cols-2 gap-6"
    >
        <div>
            <label class="block text-sm font-medium text-gray-700 mb-2"
                >Session 1 (Baseline)</label
            >
            <select
                bind:value={selectedSessionId1}
                class="block w-full rounded-md border-gray-300 shadow-sm focus:border-green-500 focus:ring-green-500"
            >
                <option value="">Select a session...</option>
                {#each sessions as session}
                    <option value={session.session_id}>
                        {formatDate(session.created_at)} - {session.metadata
                            .club_type} ({session.scores.overall_score})
                    </option>
                {/each}
            </select>
        </div>

        <div>
            <label class="block text-sm font-medium text-gray-700 mb-2"
                >Session 2 (Comparison)</label
            >
            <select
                bind:value={selectedSessionId2}
                class="block w-full rounded-md border-gray-300 shadow-sm focus:border-green-500 focus:ring-green-500"
            >
                <option value="">Select a session...</option>
                {#each sessions as session}
                    <option value={session.session_id}>
                        {formatDate(session.created_at)} - {session.metadata
                            .club_type} ({session.scores.overall_score})
                    </option>
                {/each}
            </select>
        </div>
    </div>

    {#if comparing}
        <div class="text-center py-12">Comparing sessions...</div>
    {:else if comparisonData}
        <div class="bg-white shadow overflow-hidden sm:rounded-lg">
            <div class="px-4 py-5 sm:px-6">
                <h3 class="text-lg leading-6 font-medium text-gray-900">
                    Comparison Results
                </h3>
            </div>
            <div class="border-t border-gray-200">
                <table class="min-w-full divide-y divide-gray-200">
                    <thead class="bg-gray-50">
                        <tr>
                            <th
                                scope="col"
                                class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                                >Metric</th
                            >
                            <th
                                scope="col"
                                class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                            >
                                Session 1 <br />
                                <span class="text-gray-400 font-normal"
                                    >{formatDate(
                                        comparisonData.session_1.created_at,
                                    )}</span
                                >
                            </th>
                            <th
                                scope="col"
                                class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                            >
                                Session 2 <br />
                                <span class="text-gray-400 font-normal"
                                    >{formatDate(
                                        comparisonData.session_2.created_at,
                                    )}</span
                                >
                            </th>
                            <th
                                scope="col"
                                class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                                >Difference</th
                            >
                        </tr>
                    </thead>
                    <tbody class="bg-white divide-y divide-gray-200">
                        {#each comparisonData.metrics as metric}
                            <tr>
                                <td
                                    class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                                >
                                    {metric.metric_name}
                                </td>
                                <td
                                    class="px-6 py-4 whitespace-nowrap text-sm text-gray-500"
                                >
                                    {Number(metric.session_1_value).toFixed(2)}
                                </td>
                                <td
                                    class="px-6 py-4 whitespace-nowrap text-sm text-gray-500"
                                >
                                    {Number(metric.session_2_value).toFixed(2)}
                                </td>
                                <td
                                    class="px-6 py-4 whitespace-nowrap text-sm font-medium"
                                >
                                    <span
                                        class={metric.improvement
                                            ? "text-green-600"
                                            : "text-red-600"}
                                    >
                                        {metric.diff > 0 ? "+" : ""}{Number(
                                            metric.diff,
                                        ).toFixed(2)}
                                    </span>
                                </td>
                            </tr>
                        {/each}
                    </tbody>
                </table>
            </div>
        </div>
    {/if}
</div>

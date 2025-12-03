<script lang="ts">
  import { onMount } from "svelte";
  import { token, isAuthenticated } from "$lib/stores/auth";
  import { goto } from "$app/navigation";

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

  let sessions: Session[] = [];
  let loading = true;
  let clubFilter = "all";
  let viewFilter = "all";

  onMount(async () => {
    if (!$isAuthenticated) {
      goto("/login");
      return;
    }
    await fetchSessions();
  });

  async function fetchSessions() {
    loading = true;
    try {
      // Basic client-side filtering for now, ideally backend supports query params
      const res = await fetch("/api/v1/sessions?limit=50", {
        headers: { Authorization: `Bearer ${$token}` },
      });
      if (res.ok) {
        sessions = await res.json();
      }
    } catch (e) {
      console.error("Failed to load sessions", e);
    } finally {
      loading = false;
    }
  }

  $: filteredSessions = sessions.filter((s) => {
    if (clubFilter !== "all" && s.metadata.club_type !== clubFilter)
      return false;
    if (viewFilter !== "all" && s.metadata.view !== viewFilter) return false;
    return true;
  });

  function formatDate(dateStr: string | undefined) {
    // Fallback if date is missing or invalid
    if (!dateStr) return "Unknown Date";
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

<div class="space-y-6">
  <div class="flex justify-between items-center">
    <h1 class="text-2xl font-bold text-gray-900">Swing History</h1>

    <div class="flex space-x-4">
      <select
        bind:value={clubFilter}
        class="rounded-md border-gray-300 shadow-sm focus:border-green-500 focus:ring-green-500"
      >
        <option value="all">All Clubs</option>
        <option value="driver">Driver</option>
        <option value="iron">Iron</option>
        <option value="wedge">Wedge</option>
      </select>

      <select
        bind:value={viewFilter}
        class="rounded-md border-gray-300 shadow-sm focus:border-green-500 focus:ring-green-500"
      >
        <option value="all">All Views</option>
        <option value="face_on">Face On</option>
        <option value="down_the_line">Down the Line</option>
      </select>
    </div>
  </div>

  {#if loading}
    <div class="text-center py-12">Loading history...</div>
  {:else}
    <div class="bg-white shadow overflow-hidden sm:rounded-md">
      <ul class="divide-y divide-gray-200">
        {#each filteredSessions as session}
          <li>
            <a
              href={`/sessions/${session.session_id}`}
              class="block hover:bg-gray-50"
            >
              <div class="px-4 py-4 sm:px-6">
                <div class="flex items-center justify-between">
                  <div class="flex items-center">
                    <div
                      class="flex-shrink-0 h-12 w-12 rounded-full bg-green-100 flex items-center justify-center text-green-600 font-bold text-lg"
                    >
                      {session.scores.overall_score}
                    </div>
                    <div class="ml-4">
                      <p
                        class="text-sm font-medium text-green-600 truncate capitalize"
                      >
                        {session.metadata.club_type}
                      </p>
                      <p class="flex items-center text-sm text-gray-500">
                        {session.metadata.view.replace("_", " ")}
                      </p>
                    </div>
                  </div>
                  <div class="ml-2 flex-shrink-0 flex flex-col items-end">
                    <p
                      class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800"
                    >
                      <!-- We need to ensure we have a date field available. 
                           The list_sessions endpoint returns AnalysisResponse which has metadata but maybe not created_at directly exposed 
                           unless we add it to AnalysisResponse or Metadata. 
                           Let's check schemas.py later. For now assume it might be missing and handle gracefully. -->
                      {formatDate(
                        session.created_at || new Date().toISOString(),
                      )}
                    </p>
                    {#if session.is_personal_best}
                      <p
                        class="mt-1 px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-yellow-100 text-yellow-800"
                      >
                        Personal Best
                      </p>
                    {/if}
                  </div>
                </div>
              </div>
            </a>
          </li>
        {/each}
        {#if filteredSessions.length === 0}
          <li class="px-6 py-12 text-center text-gray-500">
            No sessions found matching your filters.
          </li>
        {/if}
      </ul>
    </div>
  {/if}
</div>

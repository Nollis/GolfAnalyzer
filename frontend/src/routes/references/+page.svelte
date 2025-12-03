<script lang="ts">
    import { onMount } from "svelte";

    let profiles = [];
    let loading = true;

    onMount(async () => {
        await loadProfiles();
    });

    async function loadProfiles() {
        loading = true;
        try {
            const res = await fetch("/api/v1/references");
            if (res.ok) {
                profiles = await res.json();
            }
        } catch (e) {
            console.error(e);
        } finally {
            loading = false;
        }
    }
</script>

<div class="space-y-6">
    <div class="flex justify-between items-center">
        <h1 class="text-2xl font-bold">Reference Profiles</h1>
        <p class="text-gray-500 text-sm">
            Saved ideal swings to compare against
        </p>
    </div>

    {#if loading}
        <p>Loading...</p>
    {:else if profiles.length === 0}
        <div class="bg-white p-8 rounded-lg shadow text-center">
            <p class="text-gray-500 mb-4">No reference profiles yet.</p>
            <p class="text-sm text-gray-400">
                Analyze a pro's swing and click "Save as Reference" to create
                one.
            </p>
        </div>
    {:else}
        <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {#each profiles as profile}
                <div
                    class="bg-white p-6 rounded-lg shadow hover:shadow-md transition-shadow"
                >
                    <div class="flex items-start justify-between mb-2">
                        <h3 class="text-lg font-semibold text-gray-900">
                            {profile.name}
                        </h3>
                        {#if profile.is_default}
                            <span
                                class="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded"
                            >
                                Default
                            </span>
                        {/if}
                    </div>
                    <p class="text-sm text-gray-500">
                        ID: {profile.id.substring(0, 8)}...
                    </p>
                </div>
            {/each}
        </div>
    {/if}
</div>

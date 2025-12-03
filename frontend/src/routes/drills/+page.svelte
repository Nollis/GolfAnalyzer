<script lang="ts">
    import { onMount } from "svelte";
    import { token } from "$lib/stores/auth";

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
    let selectedCategory = "";
    let selectedDifficulty = "";

    const categories = ["Tempo", "Rotation", "Setup", "Balance"];
    const difficulties = ["Beginner", "Intermediate", "Advanced"];

    async function fetchDrills() {
        loading = true;
        error = "";
        try {
            let url = "http://localhost:8000/api/v1/drills/";
            const params = new URLSearchParams();
            if (selectedCategory) params.append("category", selectedCategory);
            if (selectedDifficulty)
                params.append("difficulty", selectedDifficulty);
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

    onMount(() => {
        fetchDrills();
    });

    $: {
        if (
            selectedCategory !== undefined ||
            selectedDifficulty !== undefined
        ) {
            fetchDrills();
        }
    }
</script>

<div class="container mx-auto px-4 py-8">
    <h1 class="text-3xl font-bold mb-6 text-gray-800">Drill Library</h1>

    <!-- Filters -->
    <div class="mb-8 flex flex-wrap gap-4">
        <select
            bind:value={selectedCategory}
            class="p-2 border rounded shadow-sm"
        >
            <option value="">All Categories</option>
            {#each categories as cat}
                <option value={cat}>{cat}</option>
            {/each}
        </select>

        <select
            bind:value={selectedDifficulty}
            class="p-2 border rounded shadow-sm"
        >
            <option value="">All Difficulties</option>
            {#each difficulties as diff}
                <option value={diff}>{diff}</option>
            {/each}
        </select>
    </div>

    {#if loading}
        <div class="text-center py-12">
            <div
                class="animate-spin rounded-full h-12 w-12 border-b-2 border-green-500 mx-auto"
            ></div>
            <p class="mt-4 text-gray-600">Loading drills...</p>
        </div>
    {:else if error}
        <div
            class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative"
            role="alert"
        >
            <strong class="font-bold">Error!</strong>
            <span class="block sm:inline">{error}</span>
        </div>
    {:else if drills.length === 0}
        <p class="text-center text-gray-600">
            No drills found matching your criteria.
        </p>
    {:else}
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {#each drills as drill}
                <div
                    class="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition-shadow duration-300"
                >
                    {#if drill.video_url}
                        <!-- Simple placeholder for video thumbnail or embed -->
                        <div
                            class="aspect-w-16 aspect-h-9 bg-gray-200 flex items-center justify-center"
                        >
                            <span class="text-gray-500">Video Preview</span>
                        </div>
                    {/if}
                    <div class="p-6">
                        <div class="flex justify-between items-start mb-2">
                            <span
                                class="inline-block px-2 py-1 text-xs font-semibold tracking-wide text-green-800 uppercase bg-green-100 rounded-full"
                            >
                                {drill.category}
                            </span>
                            <span
                                class="inline-block px-2 py-1 text-xs font-semibold tracking-wide text-blue-800 uppercase bg-blue-100 rounded-full"
                            >
                                {drill.difficulty}
                            </span>
                        </div>
                        <h2 class="text-xl font-semibold mb-2 text-gray-800">
                            {drill.title}
                        </h2>
                        <p class="text-gray-600 mb-4 line-clamp-3">
                            {drill.description}
                        </p>
                        <a
                            href="/drills/{drill.id}"
                            class="text-green-600 hover:text-green-800 font-medium"
                            >View Drill &rarr;</a
                        >
                    </div>
                </div>
            {/each}
        </div>
    {/if}
</div>

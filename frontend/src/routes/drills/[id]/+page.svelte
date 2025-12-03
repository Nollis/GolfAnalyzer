<script lang="ts">
    import { page } from "$app/stores";
    import { onMount } from "svelte";
    import { token } from "$lib/stores/auth";

    let drill = null;
    let loading = true;
    let error = "";

    async function fetchDrill() {
        loading = true;
        try {
            const res = await fetch(
                `http://localhost:8000/api/v1/drills/${$page.params.id}`,
                {
                    headers: {
                        Authorization: `Bearer ${$token}`,
                    },
                },
            );

            if (res.ok) {
                drill = await res.json();
            } else {
                error = "Drill not found";
            }
        } catch (e) {
            error = "Error connecting to server";
        } finally {
            loading = false;
        }
    }

    onMount(() => {
        fetchDrill();
    });
</script>

<div class="container mx-auto px-4 py-8 max-w-4xl">
    <a
        href="/drills"
        class="text-green-600 hover:text-green-800 mb-4 inline-block"
        >&larr; Back to Library</a
    >

    {#if loading}
        <div class="text-center py-12">
            <div
                class="animate-spin rounded-full h-12 w-12 border-b-2 border-green-500 mx-auto"
            ></div>
        </div>
    {:else if error}
        <div
            class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative"
            role="alert"
        >
            <strong class="font-bold">Error!</strong>
            <span class="block sm:inline">{error}</span>
        </div>
    {:else if drill}
        <div class="bg-white rounded-lg shadow-lg overflow-hidden">
            <div class="p-8">
                <div class="flex justify-between items-start mb-4">
                    <h1 class="text-3xl font-bold text-gray-900">
                        {drill.title}
                    </h1>
                    <div class="flex gap-2">
                        <span
                            class="px-3 py-1 text-sm font-semibold text-green-800 bg-green-100 rounded-full"
                        >
                            {drill.category}
                        </span>
                        <span
                            class="px-3 py-1 text-sm font-semibold text-blue-800 bg-blue-100 rounded-full"
                        >
                            {drill.difficulty}
                        </span>
                    </div>
                </div>

                <p class="text-lg text-gray-700 mb-8">{drill.description}</p>

                {#if drill.video_url}
                    <div class="aspect-w-16 aspect-h-9 mb-8">
                        <iframe
                            src={drill.video_url}
                            title={drill.title}
                            frameborder="0"
                            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                            allowfullscreen
                            class="w-full h-[400px] rounded-lg shadow-md"
                        ></iframe>
                    </div>
                {/if}

                {#if drill.target_metric}
                    <div class="mt-6 p-4 bg-gray-50 rounded-lg">
                        <h3 class="font-semibold text-gray-900 mb-2">
                            Target Metric
                        </h3>
                        <p class="text-gray-600">
                            This drill is designed to help improve your <span
                                class="font-medium text-gray-900"
                                >{drill.target_metric.replace(/_/g, " ")}</span
                            >.
                        </p>
                    </div>
                {/if}
            </div>
        </div>
    {/if}
</div>

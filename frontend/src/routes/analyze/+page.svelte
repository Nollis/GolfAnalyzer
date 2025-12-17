<script lang="ts">
  import { goto } from "$app/navigation";
  import { page } from "$app/stores";
  import {
    initializeAuth,
    isAuthenticated,
    token,
    user,
    waitForAuthReady,
  } from "$lib/stores/auth";
  import { onMount } from "svelte";

  let files: FileList;
  let handedness = "right";
  let view = "face_on";
  let club_type = "driver";
  let loading = false;
  let error = "";

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

    if ($user?.handedness) {
      handedness = $user.handedness;
    }
  });

  async function handleSubmit() {
    if (!files || files.length === 0) {
      error = "Please select a video file.";
      return;
    }

    loading = true;
    error = "";

    const formData = new FormData();
    formData.append("video", files[0]);
    formData.append("handedness", handedness);
    formData.append("view", view);
    formData.append("club_type", club_type);

    try {
      const res = await fetch("/api/v1/analyze-swing", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${$token}`,
        },
        body: formData,
      });

      if (!res.ok) {
        throw new Error("Analysis failed");
      }

      const data = await res.json();
      goto(`/sessions/${data.session_id}`);
    } catch (e) {
      error = (e as Error).message;
    } finally {
      loading = false;
    }
  }
</script>

<div
  class="max-w-4xl mx-auto bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 p-8 rounded-lg shadow-md dark:shadow-xl transition-colors duration-300"
>
  <h1 class="text-2xl font-bold mb-6 text-gray-900 dark:text-slate-50">
    Analyze Your Swing
  </h1>

  {#if error}
    <div
      class="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-900/50 text-red-600 dark:text-red-400 p-4 rounded mb-4"
    >
      {error}
    </div>
  {/if}

  <form on:submit|preventDefault={handleSubmit} class="space-y-6">
    <div>
      <label
        class="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1"
      >
        Video File
        <input
          type="file"
          accept="video/*"
          bind:files
          class="mt-1 block w-full text-sm text-gray-500 dark:text-slate-400 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-green-100 dark:file:bg-emerald-900/30 file:text-green-700 dark:file:text-emerald-400 hover:file:bg-green-200 dark:hover:file:bg-emerald-900/50 cursor-pointer"
        />
      </label>
    </div>

    <div class="grid grid-cols-3 gap-4">
      <div>
        <label
          class="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1"
        >
          View
          <select
            bind:value={view}
            class="mt-1 block w-full rounded-md border-gray-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-gray-900 dark:text-slate-200 shadow-sm focus:border-green-500 dark:focus:border-emerald-500 focus:ring-green-500 dark:focus:ring-emerald-500 transition-colors"
          >
            <option value="face_on">Face On</option>
            <option value="down_the_line">Down the Line</option>
          </select>
        </label>
      </div>
      <div>
        <label
          class="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1"
        >
          Club
          <select
            bind:value={club_type}
            class="mt-1 block w-full rounded-md border-gray-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-gray-900 dark:text-slate-200 shadow-sm focus:border-green-500 dark:focus:border-emerald-500 focus:ring-green-500 dark:focus:ring-emerald-500 transition-colors"
          >
            <option value="driver">Driver</option>
            <option value="woods">Woods</option>
            <option value="iron">Iron</option>
            <option value="wedge">Wedge</option>
          </select>
        </label>
      </div>
    </div>

    <button
      type="submit"
      disabled={loading}
      class="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-green-600 dark:bg-emerald-600 hover:bg-green-700 dark:hover:bg-emerald-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 dark:focus:ring-emerald-500 disabled:opacity-50 transition-colors"
    >
      {#if loading}
        Analyzing...
      {:else}
        Start Analysis
      {/if}
    </button>
  </form>
</div>

<script lang="ts">
  import { goto } from "$app/navigation";
  import { token, isAuthenticated } from "$lib/stores/auth";
  import { onMount } from "svelte";

  let files: FileList;
  let handedness = "";
  let view = "face_on";
  let club_type = "";
  let loading = false;
  let error = "";

  onMount(() => {
    if (!$isAuthenticated) {
      goto("/login");
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
      // Redirect to results page (using session ID)
      goto(`/sessions/${data.session_id}`);
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }
</script>

<div class="max-w-2xl mx-auto bg-white p-8 rounded-lg shadow">
  <h1 class="text-2xl font-bold mb-6">Analyze Your Swing</h1>

  {#if error}
    <div class="bg-red-100 text-red-700 p-4 rounded mb-4">{error}</div>
  {/if}

  <form on:submit|preventDefault={handleSubmit} class="space-y-6">
    <div>
      <label class="block text-sm font-medium text-gray-700 mb-1">
        Video File
        <input
          type="file"
          accept="video/*"
          bind:files
          class="mt-1 block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-green-50 file:text-green-700 hover:file:bg-green-100"
        />
      </label>
    </div>

    <div class="grid grid-cols-3 gap-4">
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">
          Handedness
          <select
            bind:value={handedness}
            class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-green-500 focus:ring-green-500"
          >
            <option value="">Auto-detect</option>
            <option value="right">Right</option>
            <option value="left">Left</option>
          </select>
        </label>
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">
          View
          <select
            bind:value={view}
            class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-green-500 focus:ring-green-500"
          >
            <option value="face_on">Face On</option>
            <option value="down_the_line">Down the Line</option>
          </select>
        </label>
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">
          Club
          <select
            bind:value={club_type}
            class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-green-500 focus:ring-green-500"
          >
            <option value="">Auto-detect</option>
            <option value="driver">Driver</option>
            <option value="iron">Iron</option>
            <option value="wedge">Wedge</option>
          </select>
        </label>
      </div>
    </div>

    <button
      type="submit"
      disabled={loading}
      class="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50"
    >
      {#if loading}
        Analyzing...
      {:else}
        Start Analysis
      {/if}
    </button>
  </form>
</div>

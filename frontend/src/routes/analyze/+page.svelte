<script lang="ts">
  import { goto } from "$app/navigation";
  import { page } from "$app/stores";
  import { onMount } from "svelte";
  import { fade, slide } from "svelte/transition";
  import {
    initializeAuth,
    isAuthenticated,
    token,
    user,
    waitForAuthReady,
  } from "$lib/stores/auth";

  let files: FileList | null = null;
  let fileInput: HTMLInputElement;
  let handedness = "right";
  let view = "face_on";
  let club_type = "driver";
  let loading = false;
  let error = "";
  let isDragging = false; // For drag & drop visual state

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

  let jobStatus = "";

  async function pollJob(jobId: string) {
    const pollInterval = 1000; // 1s

    try {
      const res = await fetch(`/api/v1/jobs/${jobId}`, {
        headers: { Authorization: `Bearer ${$token}` },
      });

      if (!res.ok) throw new Error("Status check failed");

      const data = await res.json();
      jobStatus = data.status; // queued, processing, completed, failed

      if (data.status === "completed") {
        const sessionId = data.result.session_id;
        goto(`/sessions/${sessionId}`);
      } else if (data.status === "failed") {
        error = `Analysis failed: ${data.error}`;
        loading = false;
      } else {
        setTimeout(() => pollJob(jobId), pollInterval);
      }
    } catch (e) {
      console.error("Poll error", e);
      error = "Lost connection to server while polling.";
      loading = false;
    }
  }

  async function handleSubmit() {
    if (!files || files.length === 0) {
      error = "Please select a video file.";
      return;
    }

    loading = true;
    error = "";
    jobStatus = "uploading";

    const formData = new FormData();
    formData.append("video", files[0]);
    formData.append("handedness", handedness);
    formData.append("view", view);
    formData.append("club_type", club_type);

    try {
      const res = await fetch("/api/v1/jobs/analyze", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${$token}`,
        },
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Analysis failed");
      }

      const data = await res.json();
      const jobId = data.job_id;

      jobStatus = "queued";
      pollJob(jobId);
    } catch (e) {
      error = (e as Error).message;
      loading = false;
    }
  }

  // Drag and Drop Handlers
  function handleDragOver(e: DragEvent) {
    e.preventDefault();
    isDragging = true;
  }
  function handleDragLeave() {
    isDragging = false;
  }
  function handleDrop(e: DragEvent) {
    e.preventDefault();
    isDragging = false;
    if (e.dataTransfer?.files && e.dataTransfer.files.length > 0) {
      files = e.dataTransfer.files;
      error = "";
    }
  }
  function handleFileSelect(e: Event) {
    const target = e.target as HTMLInputElement;
    if (target.files && target.files.length > 0) {
      files = target.files;
      error = "";
    }
  }
</script>

<div
  class="min-h-screen py-12 px-4 sm:px-6 lg:px-8 flex items-start pt-20 justify-center"
>
  <div
    class="max-w-2xl w-full bg-white dark:bg-slate-900 rounded-2xl shadow-2xl dark:shadow-emerald-900/10 overflow-hidden border border-gray-100 dark:border-slate-800"
  >
    <!-- Header -->
    <div
      class="bg-gray-50 dark:bg-slate-800/50 px-8 py-6 border-b border-gray-100 dark:border-slate-800"
    >
      <h1 class="text-3xl font-bold text-gray-900 dark:text-slate-50">
        Analyze Your Swing
      </h1>
      <p class="mt-2 text-gray-500 dark:text-slate-400">
        Upload a video to get pro-level feedback in seconds.
      </p>
    </div>

    <div class="p-8">
      {#if error}
        <div
          transition:slide
          class="mb-6 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 px-4 py-3 rounded-lg flex items-start"
        >
          <svg
            class="h-5 w-5 mr-3 mt-0.5 flex-shrink-0"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <span>{error}</span>
        </div>
      {/if}

      <form on:submit|preventDefault={handleSubmit} class="space-y-8">
        <!-- Drag & Drop Zone -->
        <div class="space-y-2">
          <label
            for="video-upload"
            class="block text-sm font-semibold text-gray-700 dark:text-slate-300"
          >
            Swing Video
          </label>

          <!-- Hidden Input -->
          <input
            id="video-upload"
            type="file"
            accept="video/*"
            class="hidden"
            bind:this={fileInput}
            on:change={handleFileSelect}
          />

          {#if !files || files.length === 0}
            <div
              role="button"
              tabindex="0"
              on:dragover={handleDragOver}
              on:dragleave={handleDragLeave}
              on:drop={handleDrop}
              on:click={() => fileInput.click()}
              on:keydown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  fileInput.click();
                }
              }}
              class="relative border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-all duration-300 group outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 dark:focus:ring-offset-slate-900
                    {isDragging
                ? 'border-green-500 bg-green-50 dark:bg-green-900/10 dark:border-green-400'
                : 'border-gray-300 dark:border-slate-700 hover:border-green-400 dark:hover:border-emerald-500 hover:bg-gray-50 dark:hover:bg-slate-800/50'}"
            >
              <div class="space-y-2">
                <div
                  class="mx-auto h-12 w-12 text-gray-400 dark:text-slate-500 group-hover:text-green-500 dark:group-hover:text-emerald-400 transition-colors"
                >
                  <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="1.5"
                      d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                    />
                  </svg>
                </div>
                <div
                  class="text-base font-medium text-gray-900 dark:text-slate-200"
                >
                  Drop your video here, or <span
                    class="text-green-600 dark:text-emerald-400">browse</span
                  >
                </div>
                <p class="text-xs text-gray-500 dark:text-slate-500">
                  MP4, MOV, or AVI up to 100MB
                </p>
              </div>
            </div>
          {:else}
            <!-- Selected File State -->
            <div
              class="relative bg-gray-50 dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-xl p-6 flex items-center justify-between group"
            >
              <div class="flex items-center space-x-4">
                <div
                  class="h-10 w-10 bg-green-100 dark:bg-emerald-900/30 rounded-lg flex items-center justify-center text-green-600 dark:text-emerald-400"
                >
                  <svg
                    class="h-6 w-6"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"
                    />
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                </div>
                <div class="overflow-hidden">
                  <p
                    class="text-sm font-medium text-gray-900 dark:text-slate-200 truncate max-w-xs"
                  >
                    {files[0].name}
                  </p>
                  <p class="text-xs text-gray-500 dark:text-slate-400">
                    {(files[0].size / (1024 * 1024)).toFixed(2)} MB
                  </p>
                </div>
              </div>
              <button
                type="button"
                on:click|preventDefault={() => {
                  files = null;
                  error = "";
                }}
                class="text-gray-400 hover:text-red-500 dark:hover:text-red-400 transition-colors p-2"
                title="Remove file"
              >
                <svg
                  class="h-5 w-5"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
              <!-- Progress Bar Overlay if loading -->
              {#if loading && jobStatus === "uploading"}
                <div
                  class="absolute bottom-0 left-0 h-1 bg-green-500 animate-pulse rounded-b-xl w-full"
                ></div>
              {/if}
            </div>
          {/if}
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <!-- View Selector -->
          <div>
            <label
              for="camera-angle"
              class="block text-sm font-semibold text-gray-700 dark:text-slate-300 mb-2"
            >
              Camera Angle
            </label>
            <div class="relative">
              <select
                id="camera-angle"
                bind:value={view}
                class="block w-full pl-4 pr-10 py-3 text-base border-gray-300 dark:border-slate-700 focus:outline-none focus:ring-green-500 focus:border-green-500 sm:text-sm rounded-lg bg-white dark:bg-slate-800 text-gray-900 dark:text-slate-200 transition-shadow shadow-sm hover:shadow-md appearance-none"
              >
                <option value="face_on">Face On (Front)</option>
                <option value="down_the_line">Down the Line (Side)</option>
              </select>
              <div
                class="pointer-events-none absolute inset-y-0 right-0 flex items-center px-4 text-gray-500 dark:text-slate-400"
              >
                <svg
                  class="h-4 w-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  ><path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M19 9l-7 7-7-7"
                  /></svg
                >
              </div>
            </div>
          </div>

          <!-- Club Selector -->
          <div>
            <label
              for="club-used"
              class="block text-sm font-semibold text-gray-700 dark:text-slate-300 mb-2"
            >
              Club Used
            </label>
            <div class="relative">
              <select
                id="club-used"
                bind:value={club_type}
                class="block w-full pl-4 pr-10 py-3 text-base border-gray-300 dark:border-slate-700 focus:outline-none focus:ring-green-500 focus:border-green-500 sm:text-sm rounded-lg bg-white dark:bg-slate-800 text-gray-900 dark:text-slate-200 transition-shadow shadow-sm hover:shadow-md appearance-none"
              >
                <option value="driver">Driver</option>
                <option value="woods">Woods / Hybrid</option>
                <option value="iron">Iron</option>
                <option value="wedge">Wedge</option>
              </select>
              <div
                class="pointer-events-none absolute inset-y-0 right-0 flex items-center px-4 text-gray-500 dark:text-slate-400"
              >
                <svg
                  class="h-4 w-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  ><path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M19 9l-7 7-7-7"
                  /></svg
                >
              </div>
            </div>
          </div>
        </div>

        <!-- Submit Button -->
        <button
          type="submit"
          disabled={loading || !files}
          class="w-full relative flex items-center justify-center py-4 px-6 border border-transparent rounded-xl shadow-lg text-base font-bold text-white
          {loading || !files
            ? 'bg-gray-400 dark:bg-slate-700 cursor-not-allowed'
            : 'bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 hover:shadow-green-500/30 transform hover:-translate-y-0.5'}
          transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
        >
          {#if loading}
            <svg
              class="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                class="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                stroke-width="4"
              ></circle>
              <path
                class="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              ></path>
            </svg>
            <span class="animate-pulse">
              {#if jobStatus === "uploading"}Uploading Video...
              {:else if jobStatus === "queued"}Queued for Analysis...
              {:else if jobStatus === "processing"}Analyzing Mechanics...
              {:else}Processing...{/if}
            </span>
          {:else}
            Analyze Swing
          {/if}
        </button>
      </form>
    </div>
  </div>
</div>

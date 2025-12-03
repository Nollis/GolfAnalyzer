<script lang="ts">
    import { onMount } from "svelte";
    import { writable } from "svelte/store";

    export let onComplete: () => void = () => {};

    const TOUR_STORAGE_KEY = "golf_analyzer_tour_completed";

    let currentStep = 0;
    let showTour = false;

    const steps = [
        {
            title: "Welcome to Golf Swing Analyzer!",
            description:
                "Let's take a quick tour to help you get started with analyzing your golf swing.",
            target: null,
        },
        {
            title: "Upload Your Swing",
            description:
                "Click here to upload a video of your golf swing. We support MP4 and most common video formats.",
            target: "upload-section",
        },
        {
            title: "Auto-Detection",
            description:
                "Don't know your handedness or club type? No problem! Our AI can detect these automatically.",
            target: "auto-detect-info",
        },
        {
            title: "View Your Dashboard",
            description:
                "Track your progress over time with detailed statistics and charts showing your improvement.",
            target: "dashboard-link",
        },
        {
            title: "Explore Drills",
            description:
                "Access our library of practice drills tailored to improve specific aspects of your swing.",
            target: "drills-link",
        },
        {
            title: "You're All Set!",
            description:
                "Start uploading your swings to get personalized feedback and track your improvement. Happy golfing!",
            target: null,
        },
    ];

    onMount(() => {
        const tourCompleted = localStorage.getItem(TOUR_STORAGE_KEY);
        if (!tourCompleted) {
            showTour = true;
        }
    });

    function nextStep() {
        if (currentStep < steps.length - 1) {
            currentStep++;
        } else {
            completeTour();
        }
    }

    function previousStep() {
        if (currentStep > 0) {
            currentStep--;
        }
    }

    function skipTour() {
        completeTour();
    }

    function completeTour() {
        localStorage.setItem(TOUR_STORAGE_KEY, "true");
        showTour = false;
        onComplete();
    }

    $: currentStepData = steps[currentStep];
</script>

{#if showTour}
    <!-- Overlay -->
    <div
        class="fixed inset-0 bg-black bg-opacity-50 z-40"
        on:click={skipTour}
    ></div>

    <!-- Tour Card -->
    <div
        class="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-white rounded-lg shadow-2xl p-6 max-w-md w-full mx-4 z-50"
    >
        <!-- Progress Indicator -->
        <div class="mb-4">
            <div class="flex justify-between items-center mb-2">
                <span class="text-sm text-gray-600"
                    >Step {currentStep + 1} of {steps.length}</span
                >
                <button
                    on:click={skipTour}
                    class="text-gray-400 hover:text-gray-600 text-sm"
                >
                    Skip tour
                </button>
            </div>
            <div class="w-full bg-gray-200 rounded-full h-2">
                <div
                    class="bg-green-600 h-2 rounded-full transition-all duration-300"
                    style="width: {((currentStep + 1) / steps.length) * 100}%"
                ></div>
            </div>
        </div>

        <!-- Content -->
        <div class="mb-6">
            <h2 class="text-2xl font-bold text-gray-900 mb-3">
                {currentStepData.title}
            </h2>
            <p class="text-gray-600 leading-relaxed">
                {currentStepData.description}
            </p>
        </div>

        <!-- Icon/Illustration -->
        <div class="flex justify-center mb-6">
            {#if currentStep === 0}
                <svg
                    class="w-20 h-20 text-green-600"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5"
                    />
                </svg>
            {:else if currentStep === steps.length - 1}
                <svg
                    class="w-20 h-20 text-green-600"
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
            {:else}
                <svg
                    class="w-20 h-20 text-green-600"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                </svg>
            {/if}
        </div>

        <!-- Navigation -->
        <div class="flex justify-between items-center">
            <button
                on:click={previousStep}
                disabled={currentStep === 0}
                class="px-4 py-2 text-gray-600 hover:text-gray-900 disabled:opacity-50 disabled:cursor-not-allowed"
            >
                ← Previous
            </button>

            <button
                on:click={nextStep}
                class="px-6 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 font-medium"
            >
                {currentStep === steps.length - 1 ? "Get Started" : "Next →"}
            </button>
        </div>
    </div>
{/if}

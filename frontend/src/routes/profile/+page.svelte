<script lang="ts">
    import { onMount } from "svelte";
    import { token, user, fetchUser } from "$lib/stores/auth";
    import { goto } from "$app/navigation";

    let loading = false;
    let message = "";
    let error = "";

    let formData = {
        full_name: "",
        handicap: 0,
        handedness: "right",
        height_cm: null,
        age: null,
    };

    onMount(() => {
        if ($user) {
            formData.full_name = $user.full_name || "";
            formData.handicap = $user.handicap || 0;
            formData.handedness = $user.handedness || "right";
            formData.height_cm = $user.height_cm || null;
            formData.age = $user.age || null;
        }
    });

    async function handleSubmit() {
        loading = true;
        error = "";
        message = "";

        try {
            const res = await fetch("/api/v1/auth/me", {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${$token}`,
                },
                body: JSON.stringify(formData),
            });

            if (!res.ok) {
                throw new Error("Failed to update profile");
            }

            message = "Profile updated successfully!";
            await fetchUser(); // Refresh user data
        } catch (e) {
            error = e.message;
        } finally {
            loading = false;
        }
    }
</script>

<div class="max-w-4xl mx-auto px-4 py-8">
    <div class="mb-8">
        <h1 class="text-3xl font-bold text-gray-900 dark:text-white">
            Profile Settings
        </h1>
        <p class="mt-2 text-sm text-gray-600 dark:text-slate-400">
            Manage your personal information and preferences.
        </p>
    </div>

    <!-- Main Profile Card -->
    <div
        class="bg-white dark:bg-slate-900 rounded-xl shadow-lg border border-gray-100 dark:border-slate-800 overflow-hidden"
    >
        <!-- Header Gradient Line -->
        <div
            class="h-1 w-full bg-gradient-to-r from-green-500 to-emerald-400"
        ></div>

        <div class="p-8">
            {#if message}
                <div
                    class="mb-6 p-4 rounded-lg bg-green-50 dark:bg-emerald-900/20 border border-green-200 dark:border-emerald-800 text-green-700 dark:text-emerald-300 flex items-center"
                >
                    <svg
                        class="h-5 w-5 mr-2"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                    >
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M5 13l4 4L19 7"
                        />
                    </svg>
                    {message}
                </div>
            {/if}

            {#if error}
                <div
                    class="mb-6 p-4 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 flex items-center"
                >
                    <svg
                        class="h-5 w-5 mr-2"
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
                    {error}
                </div>
            {/if}

            <form on:submit|preventDefault={handleSubmit} class="space-y-8">
                <!-- Section: Personal Info -->
                <div>
                    <h2
                        class="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center"
                    >
                        <svg
                            class="w-5 h-5 mr-2 text-green-500"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                        >
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                stroke-width="2"
                                d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
                            />
                        </svg>
                        Personal Information
                    </h2>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div class="col-span-1 md:col-span-2">
                            <label
                                class="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-2"
                                >Full Name</label
                            >
                            <input
                                type="text"
                                bind:value={formData.full_name}
                                class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all"
                                placeholder="Enter your full name"
                            />
                        </div>

                        <div>
                            <label
                                class="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-2"
                                >Email Address</label
                            >
                            <input
                                type="email"
                                value={$user?.email}
                                disabled
                                class="w-full px-4 py-2 rounded-lg border border-gray-200 dark:border-slate-800 bg-gray-50 dark:bg-slate-900/50 text-gray-500 dark:text-slate-500 cursor-not-allowed"
                            />
                            <p
                                class="mt-1 text-xs text-gray-400 dark:text-slate-600"
                            >
                                Email cannot be changed
                            </p>
                        </div>

                        <div>
                            <label
                                class="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-2"
                                >Age</label
                            >
                            <input
                                type="number"
                                min="5"
                                max="100"
                                bind:value={formData.age}
                                class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all"
                                placeholder="e.g. 32"
                            />
                        </div>
                    </div>
                </div>

                <div
                    class="border-t border-gray-100 dark:border-slate-800 pt-8"
                ></div>

                <!-- Section: Golfer Stats -->
                <div>
                    <h2
                        class="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center"
                    >
                        <svg
                            class="w-5 h-5 mr-2 text-green-500"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                        >
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                stroke-width="2"
                                d="M13 10V3L4 14h7v7l9-11h-7z"
                            />
                        </svg>
                        Golfer Stats
                    </h2>
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <div>
                            <label
                                class="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-2"
                                >Handicap</label
                            >
                            <div class="relative">
                                <input
                                    type="number"
                                    step="0.1"
                                    bind:value={formData.handicap}
                                    class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all"
                                    placeholder="0.0"
                                />
                                <div
                                    class="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none"
                                >
                                    <span class="text-gray-400 sm:text-sm"
                                        >hcp</span
                                    >
                                </div>
                            </div>
                        </div>

                        <div>
                            <label
                                class="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-2"
                                >Height (cm)</label
                            >
                            <input
                                type="number"
                                step="0.5"
                                bind:value={formData.height_cm}
                                class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all"
                                placeholder="e.g. 180"
                            />
                        </div>

                        <div>
                            <label
                                class="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-2"
                                >Handedness</label
                            >
                            <select
                                bind:value={formData.handedness}
                                class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all"
                            >
                                <option value="right">Right-handed</option>
                                <option value="left">Left-handed</option>
                            </select>
                        </div>
                    </div>
                </div>

                <div class="pt-6 flex items-center justify-end">
                    <button
                        type="submit"
                        disabled={loading}
                        class="px-8 py-3 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 text-white font-medium rounded-lg shadow-lg hover:shadow-green-500/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed transform active:scale-95"
                    >
                        {loading ? "Saving Changes..." : "Save Profile"}
                    </button>
                </div>
            </form>
        </div>

        <!-- Account Footer -->
        <div
            class="bg-gray-50 dark:bg-slate-950/50 px-8 py-6 border-t border-gray-100 dark:border-slate-800"
        >
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <p
                        class="text-xs text-gray-500 dark:text-slate-500 uppercase tracking-wide font-semibold"
                    >
                        Account Type
                    </p>
                    <p
                        class="mt-1 text-sm font-medium text-gray-900 dark:text-white flex items-center"
                    >
                        {#if $user?.is_admin}
                            <span
                                class="inline-block w-2 h-2 rounded-full bg-purple-500 mr-2"
                            ></span> Admin
                        {:else}
                            <span
                                class="inline-block w-2 h-2 rounded-full bg-blue-500 mr-2"
                            ></span> Standard User
                        {/if}
                    </p>
                </div>
                <div>
                    <p
                        class="text-xs text-gray-500 dark:text-slate-500 uppercase tracking-wide font-semibold"
                    >
                        Skill Level
                    </p>
                    <p
                        class="mt-1 text-sm font-medium text-gray-900 dark:text-white bg-slate-200 dark:bg-slate-800 inline-block px-3 py-1 rounded-full text-xs"
                    >
                        {$user?.skill_level || "Not Assessed"}
                    </p>
                </div>
            </div>
        </div>
    </div>
</div>

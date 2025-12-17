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

<div class="max-w-2xl mx-auto">
    <div
        class="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 p-8 rounded-lg shadow-md dark:shadow-xl transition-colors duration-300"
    >
        <h1 class="text-3xl font-bold mb-6 text-gray-900 dark:text-slate-50">
            My Profile
        </h1>

        {#if message}
            <div
                class="bg-green-50 dark:bg-emerald-900/30 border border-green-200 dark:border-emerald-900/50 text-green-700 dark:text-emerald-400 p-4 rounded mb-4"
            >
                {message}
            </div>
        {/if}

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
                    Email
                    <input
                        type="email"
                        value={$user?.email}
                        disabled
                        class="mt-1 block w-full rounded-md border-gray-300 dark:border-slate-700 bg-gray-100 dark:bg-slate-800/50 text-gray-500 dark:text-slate-500 shadow-sm cursor-not-allowed transition-colors"
                    />
                </label>
                <p class="text-xs text-gray-500 dark:text-slate-500 mt-1">
                    Email cannot be changed
                </p>
            </div>

            <div>
                <label
                    class="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1"
                >
                    Full Name
                    <input
                        type="text"
                        bind:value={formData.full_name}
                        class="mt-1 block w-full rounded-md border-gray-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-gray-900 dark:text-slate-200 shadow-sm focus:border-green-500 dark:focus:border-emerald-500 focus:ring-green-500 dark:focus:ring-emerald-500 transition-colors"
                        placeholder="Your name"
                    />
                </label>
            </div>

            <div>
                <label
                    class="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1"
                >
                    Handicap
                    <input
                        type="number"
                        step="0.1"
                        bind:value={formData.handicap}
                        class="mt-1 block w-full rounded-md border-gray-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-gray-900 dark:text-slate-200 shadow-sm focus:border-green-500 dark:focus:border-emerald-500 focus:ring-green-500 dark:focus:ring-emerald-500 transition-colors"
                        placeholder="e.g., 15.5"
                    />
                </label>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                    <label
                        class="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1"
                    >
                        Height (cm)
                        <input
                            type="number"
                            step="0.5"
                            min="50"
                            max="250"
                            bind:value={formData.height_cm}
                            class="mt-1 block w-full rounded-md border-gray-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-gray-900 dark:text-slate-200 shadow-sm focus:border-green-500 dark:focus:border-emerald-500 focus:ring-green-500 dark:focus:ring-emerald-500 transition-colors"
                            placeholder="e.g., 180"
                        />
                    </label>
                </div>
                <div>
                    <label
                        class="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1"
                    >
                        Age
                        <input
                            type="number"
                            min="5"
                            max="100"
                            bind:value={formData.age}
                            class="mt-1 block w-full rounded-md border-gray-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-gray-900 dark:text-slate-200 shadow-sm focus:border-green-500 dark:focus:border-emerald-500 focus:ring-green-500 dark:focus:ring-emerald-500 transition-colors"
                            placeholder="e.g., 32"
                        />
                    </label>
                </div>
            </div>

            <div>
                <label
                    class="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1"
                >
                    Handedness
                    <select
                        bind:value={formData.handedness}
                        class="mt-1 block w-full rounded-md border-gray-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-gray-900 dark:text-slate-200 shadow-sm focus:border-green-500 dark:focus:border-emerald-500 focus:ring-green-500 dark:focus:ring-emerald-500 transition-colors"
                    >
                        <option value="right">Right-handed</option>
                        <option value="left">Left-handed</option>
                    </select>
                </label>
            </div>

            <div class="pt-4">
                <button
                    type="submit"
                    disabled={loading}
                    class="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-green-600 dark:bg-emerald-600 hover:bg-green-700 dark:hover:bg-emerald-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 dark:focus:ring-emerald-500 disabled:opacity-50 transition-colors"
                >
                    {loading ? "Saving..." : "Save Changes"}
                </button>
            </div>
        </form>

        <div class="mt-8 pt-6 border-t border-gray-200 dark:border-slate-800">
            <h2
                class="text-lg font-semibold text-gray-900 dark:text-slate-50 mb-4"
            >
                Account Info
            </h2>
            <dl class="space-y-2">
                <div class="flex justify-between">
                    <dt class="text-sm text-gray-500 dark:text-slate-400">
                        Skill Level:
                    </dt>
                    <dd
                        class="text-sm font-medium text-gray-900 dark:text-slate-200"
                    >
                        {$user?.skill_level || "Not assessed yet"}
                    </dd>
                </div>
                <div class="flex justify-between">
                    <dt class="text-sm text-slate-400">Account Type:</dt>
                    <dd class="text-sm font-medium text-slate-200">
                        {$user?.is_admin ? "Admin" : "User"}
                    </dd>
                </div>
            </dl>
        </div>
    </div>
</div>

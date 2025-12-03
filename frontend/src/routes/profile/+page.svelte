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
    };

    onMount(() => {
        if ($user) {
            formData.full_name = $user.full_name || "";
            formData.handicap = $user.handicap || 0;
            formData.handedness = $user.handedness || "right";
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
    <div class="bg-white p-8 rounded-lg shadow">
        <h1 class="text-3xl font-bold mb-6 text-gray-900">My Profile</h1>

        {#if message}
            <div class="bg-green-100 text-green-700 p-4 rounded mb-4">
                {message}
            </div>
        {/if}

        {#if error}
            <div class="bg-red-100 text-red-700 p-4 rounded mb-4">{error}</div>
        {/if}

        <form on:submit|preventDefault={handleSubmit} class="space-y-6">
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">
                    Email
                    <input
                        type="email"
                        value={$user?.email}
                        disabled
                        class="mt-1 block w-full rounded-md border-gray-300 bg-gray-100 shadow-sm cursor-not-allowed"
                    />
                </label>
                <p class="text-xs text-gray-500 mt-1">
                    Email cannot be changed
                </p>
            </div>

            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">
                    Full Name
                    <input
                        type="text"
                        bind:value={formData.full_name}
                        class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-green-500 focus:ring-green-500"
                        placeholder="Your name"
                    />
                </label>
            </div>

            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">
                    Handicap
                    <input
                        type="number"
                        step="0.1"
                        bind:value={formData.handicap}
                        class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-green-500 focus:ring-green-500"
                        placeholder="e.g., 15.5"
                    />
                </label>
            </div>

            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">
                    Handedness
                    <select
                        bind:value={formData.handedness}
                        class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-green-500 focus:ring-green-500"
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
                    class="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50"
                >
                    {loading ? "Saving..." : "Save Changes"}
                </button>
            </div>
        </form>

        <div class="mt-8 pt-6 border-t border-gray-200">
            <h2 class="text-lg font-semibold text-gray-900 mb-4">
                Account Info
            </h2>
            <dl class="space-y-2">
                <div class="flex justify-between">
                    <dt class="text-sm text-gray-600">Skill Level:</dt>
                    <dd class="text-sm font-medium text-gray-900">
                        {$user?.skill_level || "Not assessed yet"}
                    </dd>
                </div>
                <div class="flex justify-between">
                    <dt class="text-sm text-gray-600">Account Type:</dt>
                    <dd class="text-sm font-medium text-gray-900">
                        {$user?.is_admin ? "Admin" : "User"}
                    </dd>
                </div>
            </dl>
        </div>
    </div>
</div>

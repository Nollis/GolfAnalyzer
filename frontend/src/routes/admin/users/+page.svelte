<script lang="ts">
    import { onMount } from "svelte";
    import { token } from "$lib/stores/auth";

    interface User {
        id: string;
        email: string;
        full_name: string | null;
        handicap: number;
        skill_level: string;
        is_active: boolean;
        is_admin: boolean;
        created_at: string;
    }

    let users: User[] = [];
    let loading = true;
    let error = "";
    let searchTerm = "";

    onMount(async () => {
        await fetchUsers();
    });

    async function fetchUsers() {
        loading = true;
        try {
            const res = await fetch("/api/v1/admin/users", {
                headers: { Authorization: `Bearer ${$token}` },
            });

            if (!res.ok) {
                if (res.status === 403) {
                    error = "Access denied. Admin privileges required.";
                } else {
                    error = "Failed to load users";
                }
                return;
            }

            users = await res.json();
        } catch (e) {
            error = "Error connecting to server";
        } finally {
            loading = false;
        }
    }

    async function toggleUserActive(userId: string) {
        try {
            const res = await fetch(
                `/api/v1/admin/users/${userId}/toggle-active`,
                {
                    method: "PUT",
                    headers: { Authorization: `Bearer ${$token}` },
                },
            );

            if (res.ok) {
                await fetchUsers();
            }
        } catch (e) {
            console.error("Failed to toggle user status", e);
        }
    }

    async function deleteUser(userId: string, userEmail: string) {
        if (!confirm(`Are you sure you want to delete user ${userEmail}?`)) {
            return;
        }

        try {
            const res = await fetch(`/api/v1/admin/users/${userId}`, {
                method: "DELETE",
                headers: { Authorization: `Bearer ${$token}` },
            });

            if (res.ok) {
                await fetchUsers();
            } else {
                const data = await res.json();
                alert(data.detail || "Failed to delete user");
            }
        } catch (e) {
            console.error("Failed to delete user", e);
        }
    }

    $: filteredUsers = users.filter(
        (u) =>
            u.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
            (u.full_name &&
                u.full_name.toLowerCase().includes(searchTerm.toLowerCase())),
    );
</script>

<div class="space-y-6">
    <div class="flex justify-between items-center">
        <h1 class="text-3xl font-bold text-gray-900">User Management</h1>
        <div class="text-sm text-gray-600">
            Total Users: <span class="font-semibold">{users.length}</span>
        </div>
    </div>

    {#if error}
        <div class="bg-red-100 text-red-700 p-4 rounded-md">{error}</div>
    {/if}

    <!-- Search -->
    <div class="bg-white p-4 rounded-lg shadow">
        <input
            type="text"
            bind:value={searchTerm}
            placeholder="Search by email or name..."
            class="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-green-500 focus:border-transparent"
        />
    </div>

    {#if loading}
        <div class="text-center py-12">Loading users...</div>
    {:else}
        <!-- Users Table -->
        <div class="bg-white rounded-lg shadow overflow-hidden">
            <table class="min-w-full divide-y divide-gray-200">
                <thead class="bg-gray-50">
                    <tr>
                        <th
                            class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                        >
                            User
                        </th>
                        <th
                            class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                        >
                            Skill Level
                        </th>
                        <th
                            class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                        >
                            Handicap
                        </th>
                        <th
                            class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                        >
                            Status
                        </th>
                        <th
                            class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                        >
                            Joined
                        </th>
                        <th
                            class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider"
                        >
                            Actions
                        </th>
                    </tr>
                </thead>
                <tbody class="bg-white divide-y divide-gray-200">
                    {#each filteredUsers as user}
                        <tr class="hover:bg-gray-50">
                            <td class="px-6 py-4 whitespace-nowrap">
                                <div class="flex items-center">
                                    <div>
                                        <div
                                            class="text-sm font-medium text-gray-900"
                                        >
                                            {user.full_name || "N/A"}
                                            {#if user.is_admin}
                                                <span
                                                    class="ml-2 px-2 py-1 text-xs font-semibold text-purple-800 bg-purple-100 rounded-full"
                                                >
                                                    Admin
                                                </span>
                                            {/if}
                                        </div>
                                        <div class="text-sm text-gray-500">
                                            {user.email}
                                        </div>
                                    </div>
                                </div>
                            </td>
                            <td class="px-6 py-4 whitespace-nowrap">
                                <span
                                    class="px-2 py-1 text-xs font-semibold rounded-full {user.skill_level ===
                                    'Pro'
                                        ? 'bg-purple-100 text-purple-800'
                                        : user.skill_level === 'Advanced'
                                          ? 'bg-blue-100 text-blue-800'
                                          : user.skill_level === 'Intermediate'
                                            ? 'bg-green-100 text-green-800'
                                            : 'bg-gray-100 text-gray-800'}"
                                >
                                    {user.skill_level}
                                </span>
                            </td>
                            <td
                                class="px-6 py-4 whitespace-nowrap text-sm text-gray-900"
                            >
                                {user.handicap}
                            </td>
                            <td class="px-6 py-4 whitespace-nowrap">
                                <span
                                    class="px-2 py-1 text-xs font-semibold rounded-full {user.is_active
                                        ? 'bg-green-100 text-green-800'
                                        : 'bg-red-100 text-red-800'}"
                                >
                                    {user.is_active ? "Active" : "Inactive"}
                                </span>
                            </td>
                            <td
                                class="px-6 py-4 whitespace-nowrap text-sm text-gray-500"
                            >
                                {new Date(user.created_at).toLocaleDateString()}
                            </td>
                            <td
                                class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium space-x-2"
                            >
                                <button
                                    on:click={() => toggleUserActive(user.id)}
                                    class="text-blue-600 hover:text-blue-900"
                                    disabled={user.is_admin}
                                >
                                    {user.is_active ? "Deactivate" : "Activate"}
                                </button>
                                {#if !user.is_admin}
                                    <button
                                        on:click={() =>
                                            deleteUser(user.id, user.email)}
                                        class="text-red-600 hover:text-red-900"
                                    >
                                        Delete
                                    </button>
                                {/if}
                            </td>
                        </tr>
                    {/each}
                </tbody>
            </table>

            {#if filteredUsers.length === 0}
                <div class="text-center py-8 text-gray-500">
                    No users found matching your search.
                </div>
            {/if}
        </div>
    {/if}
</div>

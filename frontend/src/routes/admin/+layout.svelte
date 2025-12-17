<script lang="ts">
    import { goto } from "$app/navigation";
    import { page } from "$app/stores";
    import { onMount } from "svelte";
    import {
        initializeAuth,
        isAuthenticated,
        user,
        waitForAuthReady,
    } from "$lib/stores/auth";

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

        // Check if user is admin
        if (!$user?.is_admin) {
            goto("/dashboard");
        }
    });
</script>

<div class="min-h-screen bg-gray-100">
    <div class="flex">
        <!-- Sidebar -->
        <aside class="w-64 bg-white shadow-md min-h-screen">
            <div class="p-6">
                <h2 class="text-xl font-bold text-gray-900">Admin Panel</h2>
            </div>
            <nav class="mt-6">
                <a
                    href="/admin/users"
                    class="block px-6 py-3 text-gray-700 hover:bg-gray-100 hover:text-gray-900"
                >
                    <svg
                        class="inline-block w-5 h-5 mr-2"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                    >
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"
                        />
                    </svg>
                    Users
                </a>
                <a
                    href="/admin/analytics"
                    class="block px-6 py-3 text-gray-700 hover:bg-gray-100 hover:text-gray-900"
                >
                    <svg
                        class="inline-block w-5 h-5 mr-2"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                    >
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                        />
                    </svg>
                    Analytics
                </a>
                <a
                    href="/dashboard"
                    class="block px-6 py-3 text-gray-500 hover:bg-gray-100 hover:text-gray-900 mt-6 border-t border-gray-200"
                >
                    ← Back to Dashboard
                </a>
            </nav>
        </aside>

        <!-- Main Content -->
        <main class="flex-1 p-8">
            <slot />
        </main>
    </div>
</div>

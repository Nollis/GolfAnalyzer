<script lang="ts">
    import { goto } from "$app/navigation";
    import { page } from "$app/stores";
    import { onMount } from "svelte";
    import {
        initializeAuth,
        isAuthenticated,
        login,
        waitForAuthReady,
    } from "$lib/stores/auth";

    let email = "";
    let password = "";
    let error = "";
    let loading = false;
    let redirectTo = "/";

    $: redirectTo = $page.url.searchParams.get("redirectTo") || "/";

    onMount(async () => {
        await initializeAuth();
        await waitForAuthReady();

        if ($isAuthenticated) {
            goto(redirectTo);
        }
    });

    async function handleLogin() {
        loading = true;
        error = "";

        const result = await login(email.trim(), password);

        if (result.success) {
            goto(redirectTo);
        } else {
            error = result.message || "Invalid email or password";
        }

        loading = false;
    }
</script>

<div class="min-h-screen flex">
    <!-- Visual Side (Left) -->
    <div
        class="hidden lg:flex w-1/2 bg-slate-900 relative overflow-hidden items-center justify-center"
    >
        <!-- Abstract Pattern -->
        <div
            class="absolute inset-0 bg-gradient-to-br from-green-900 to-slate-900 opacity-90"
        ></div>
        <div
            class="absolute inset-0"
            style="background-image: radial-gradient(#10b981 1px, transparent 1px); background-size: 40px 40px; opacity: 0.1;"
        ></div>

        <div class="relative z-10 p-12 text-white max-w-lg">
            <h2 class="text-4xl font-bold mb-6">Analyze. Improve. Repeat.</h2>
            <p class="text-lg text-slate-300">
                Join thousands of golfers using AI to perfect their swing
                mechanics and lower their scores.
            </p>
        </div>

        <!-- Decorative Circles -->
        <div
            class="absolute -top-24 -left-24 w-96 h-96 bg-green-500/20 rounded-full blur-3xl"
        ></div>
        <div
            class="absolute -bottom-24 -right-24 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl"
        ></div>
    </div>

    <!-- Form Side (Right) -->
    <div
        class="flex-1 flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-20 xl:px-24 bg-white dark:bg-slate-950 transition-colors"
    >
        <div class="mx-auto w-full max-w-sm lg:w-96">
            <div>
                <h2
                    class="text-3xl font-extrabold text-gray-900 dark:text-white mb-2"
                >
                    Welcome back
                </h2>
                <p class="text-sm text-gray-600 dark:text-slate-400">
                    Sign in to your account to continue
                </p>
            </div>

            <div class="mt-8">
                <form on:submit|preventDefault={handleLogin} class="space-y-6">
                    <div>
                        <label
                            for="email"
                            class="block text-sm font-medium text-gray-700 dark:text-slate-300"
                        >
                            Email address
                        </label>
                        <div class="mt-1">
                            <input
                                id="email"
                                name="email"
                                type="email"
                                autocomplete="email"
                                required
                                bind:value={email}
                                class="appearance-none block w-full px-3 py-2 border border-gray-300 dark:border-slate-700 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-green-500 focus:border-green-500 dark:bg-slate-900 dark:text-white sm:text-sm transition-colors"
                            />
                        </div>
                    </div>

                    <div>
                        <label
                            for="password"
                            class="block text-sm font-medium text-gray-700 dark:text-slate-300"
                        >
                            Password
                        </label>
                        <div class="mt-1">
                            <input
                                id="password"
                                name="password"
                                type="password"
                                autocomplete="current-password"
                                required
                                bind:value={password}
                                class="appearance-none block w-full px-3 py-2 border border-gray-300 dark:border-slate-700 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-green-500 focus:border-green-500 dark:bg-slate-900 dark:text-white sm:text-sm transition-colors"
                            />
                        </div>
                    </div>

                    {#if error}
                        <div
                            class="rounded-md bg-red-50 dark:bg-red-900/30 p-4 border border-red-200 dark:border-red-900/50"
                        >
                            <div class="flex">
                                <div class="ml-3">
                                    <h3
                                        class="text-sm font-medium text-red-800 dark:text-red-400"
                                    >
                                        Login failed
                                    </h3>
                                    <div
                                        class="mt-2 text-sm text-red-700 dark:text-red-300"
                                    >
                                        <p>{error}</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    {/if}

                    <div class="flex items-center justify-between">
                        <div class="flex items-center">
                            <input
                                id="remember-me"
                                name="remember-me"
                                type="checkbox"
                                class="h-4 w-4 text-green-600 focus:ring-green-500 border-gray-300 rounded dark:border-slate-700 dark:bg-slate-900"
                            />
                            <label
                                for="remember-me"
                                class="ml-2 block text-sm text-gray-900 dark:text-slate-300"
                            >
                                Remember me
                            </label>
                        </div>

                        <div class="text-sm">
                            <button
                                type="button"
                                on:click={() =>
                                    alert(
                                        "Check server console for reset token simulation!",
                                    )}
                                class="font-medium text-green-600 hover:text-green-500 dark:text-emerald-400"
                            >
                                Forgot your password?
                            </button>
                        </div>
                    </div>

                    <div>
                        <button
                            type="submit"
                            disabled={loading}
                            class="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors dark:focus:ring-offset-slate-900"
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
                                Signing in...
                            {:else}
                                Sign in
                            {/if}
                        </button>
                    </div>

                    <div class="relative">
                        <div class="absolute inset-0 flex items-center">
                            <div
                                class="w-full border-t border-gray-300 dark:border-slate-800"
                            ></div>
                        </div>
                        <div class="relative flex justify-center text-sm">
                            <span
                                class="px-2 bg-white dark:bg-slate-950 text-gray-500 dark:text-slate-400"
                            >
                                Or continue with
                            </span>
                        </div>
                    </div>

                    <div>
                        <a
                            href="/api/v1/login/google"
                            class="w-full flex justify-center items-center py-2 px-4 border border-gray-300 dark:border-slate-700 rounded-md shadow-sm text-sm font-medium text-gray-700 dark:text-slate-200 bg-white dark:bg-slate-900 hover:bg-gray-50 dark:hover:bg-slate-800 transition-colors"
                        >
                            <svg
                                class="h-5 w-5 mr-2"
                                aria-hidden="true"
                                viewBox="0 0 24 24"
                            >
                                <path
                                    d="M12.0003 20.45c-4.6667 0-8.45-3.7833-8.45-8.45 0-4.6667 3.7833-8.45 8.45-8.45 2.0833 0 4.0833.6667 5.75 1.9167v-.0392l3.2083-3.2084c-2.4583-1.875-5.5416-3.0833-8.9583-3.0833-8.0833 0-14.65 6.5667-14.65 14.65s6.5667 14.65 14.65 14.65c7.375 0 13.5917-5.3834 14.5084-12.4417H12.0003v-4.1166h16.7c.1667 1.2916.2917 2.625.2917 4.0416 0 8.0834-5.4167 14.7334-17.0334 14.7334Z"
                                    fill="currentColor"
                                />
                            </svg>
                            Google
                        </a>
                    </div>

                    <div class="mt-6">
                        <div class="relative">
                            <div class="absolute inset-0 flex items-center">
                                <div
                                    class="w-full border-t border-gray-300 dark:border-slate-800"
                                ></div>
                            </div>
                            <div class="relative flex justify-center text-sm">
                                <span
                                    class="px-2 bg-white dark:bg-slate-950 text-gray-500 dark:text-slate-400"
                                >
                                    New to GolfAnalyzer?
                                </span>
                            </div>
                        </div>

                        <div class="mt-6">
                            <a
                                href="/register"
                                class="w-full flex justify-center py-2 px-4 border border-gray-300 dark:border-slate-700 rounded-md shadow-sm text-sm font-medium text-gray-700 dark:text-slate-200 bg-white dark:bg-slate-900 hover:bg-gray-50 dark:hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 transition-colors"
                            >
                                Create an account
                            </a>
                        </div>
                    </div>
                </form>
            </div>
        </div>
    </div>
</div>

<script>
    import { register } from "$lib/stores/auth";
    import { goto } from "$app/navigation";

    export let data;
    export let params;

    let email = "";
    let password = "";
    let fullName = "";
    let heightCm = "";
    let age = "";
    let error = "";

    async function handleRegister() {
        const heightNum = heightCm ? parseFloat(heightCm) : null;
        const ageNum = age ? parseInt(age) : null;
        const success = await register(
            email,
            password,
            fullName,
            heightNum,
            ageNum,
        );
        if (success) {
            goto("/login");
        } else {
            error = "Registration failed. Email might be already taken.";
        }
    }
</script>

<div class="min-h-screen flex">
    <!-- Visual Side (Left) -->
    <div
        class="hidden lg:flex w-1/2 bg-slate-900 relative overflow-hidden items-center justify-center"
    >
        <!-- Abstract Pattern -->
        <div
            class="absolute inset-0 bg-gradient-to-br from-emerald-900 to-slate-900 opacity-90"
        ></div>
        <div
            class="absolute inset-0"
            style="background-image: radial-gradient(#34d399 1px, transparent 1px); background-size: 40px 40px; opacity: 0.1;"
        ></div>

        <div class="relative z-10 p-12 text-white max-w-lg">
            <h2 class="text-4xl font-bold mb-6">Start Your Journey.</h2>
            <p class="text-lg text-slate-300">
                Create an account to track your progress, analyze your swing
                mechanics, and reach your potential.
            </p>
        </div>

        <!-- Decorative Circles -->
        <div
            class="absolute top-24 left-24 w-72 h-72 bg-green-500/20 rounded-full blur-3xl"
        ></div>
        <div
            class="absolute bottom-24 right-24 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl"
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
                    Create your account
                </h2>
                <p class="text-sm text-gray-600 dark:text-slate-400">
                    Get started with GolfAnalyzer today
                </p>
            </div>

            <div class="mt-8">
                <form
                    on:submit|preventDefault={handleRegister}
                    class="space-y-6"
                >
                    <div>
                        <label
                            for="full-name"
                            class="block text-sm font-medium text-gray-700 dark:text-slate-300"
                        >
                            Full Name
                        </label>
                        <div class="mt-1">
                            <input
                                id="full-name"
                                name="full-name"
                                type="text"
                                required
                                bind:value={fullName}
                                class="appearance-none block w-full px-3 py-2 border border-gray-300 dark:border-slate-700 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-green-500 focus:border-green-500 dark:bg-slate-900 dark:text-white sm:text-sm transition-colors"
                                placeholder="Tiger Woods"
                            />
                        </div>
                    </div>

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
                                placeholder="you@example.com"
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
                                autocomplete="new-password"
                                required
                                bind:value={password}
                                class="appearance-none block w-full px-3 py-2 border border-gray-300 dark:border-slate-700 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-green-500 focus:border-green-500 dark:bg-slate-900 dark:text-white sm:text-sm transition-colors"
                                placeholder="••••••••"
                            />
                        </div>
                    </div>

                    <div class="grid grid-cols-2 gap-4">
                        <div>
                            <label
                                for="height-cm"
                                class="block text-sm font-medium text-gray-700 dark:text-slate-300"
                            >
                                Height (cm)
                            </label>
                            <div class="mt-1">
                                <input
                                    id="height-cm"
                                    name="height"
                                    type="number"
                                    min="50"
                                    max="250"
                                    step="0.5"
                                    bind:value={heightCm}
                                    class="appearance-none block w-full px-3 py-2 border border-gray-300 dark:border-slate-700 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-green-500 focus:border-green-500 dark:bg-slate-900 dark:text-white sm:text-sm transition-colors"
                                    placeholder="180"
                                />
                            </div>
                        </div>
                        <div>
                            <label
                                for="age"
                                class="block text-sm font-medium text-gray-700 dark:text-slate-300"
                            >
                                Age
                            </label>
                            <div class="mt-1">
                                <input
                                    id="age"
                                    name="age"
                                    type="number"
                                    min="5"
                                    max="100"
                                    step="1"
                                    bind:value={age}
                                    class="appearance-none block w-full px-3 py-2 border border-gray-300 dark:border-slate-700 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-green-500 focus:border-green-500 dark:bg-slate-900 dark:text-white sm:text-sm transition-colors"
                                    placeholder="30"
                                />
                            </div>
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
                                        Registration failed
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

                    <div>
                        <button
                            type="submit"
                            class="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 transition-colors dark:focus:ring-offset-slate-900"
                        >
                            Register
                        </button>
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
                                    Already have an account?
                                </span>
                            </div>
                        </div>

                        <div class="mt-6">
                            <a
                                href="/login"
                                class="w-full flex justify-center py-2 px-4 border border-gray-300 dark:border-slate-700 rounded-md shadow-sm text-sm font-medium text-gray-700 dark:text-slate-200 bg-white dark:bg-slate-900 hover:bg-gray-50 dark:hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 transition-colors"
                            >
                                Sign in
                            </a>
                        </div>
                    </div>
                </form>
            </div>
        </div>
    </div>
</div>

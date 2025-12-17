<script lang="ts">
  import "../app.css";
  import {
    initializeAuth,
    logout,
    user,
    waitForAuthReady,
  } from "$lib/stores/auth";
  import { browser } from "$app/environment";
  import { onMount } from "svelte";

  import ThemeToggle from "$lib/components/ThemeToggle.svelte"; // Import ThemeToggle

  let mobileMenuOpen = false;
  let userMenuOpen = false;

  onMount(async () => {
    await initializeAuth();
    await waitForAuthReady();

    // Intercept 401s to force re-login when the session expires
    if (browser) {
      const originalFetch = window.fetch;
      window.fetch = async (...args) => {
        const res = await originalFetch(...args);
        try {
          let url = "";
          const target = args[0];
          if (typeof target === "string") url = target;
          else if (target instanceof Request) url = target.url;
          else if (target instanceof URL) url = target.toString();

          const isAuthEndpoint =
            url.includes("/api/v1/auth/login") ||
            url.includes("/api/v1/auth/register");
          if (res.status === 401 && !isAuthEndpoint) {
            const redirectTo = `${window.location.pathname}${window.location.search}`;
            logout(true, redirectTo);
          }
        } catch (err) {
          console.error("fetch interceptor error", err);
        }
        return res;
      };
    }
  });

  function toggleMobileMenu() {
    mobileMenuOpen = !mobileMenuOpen;
  }

  function closeMobileMenu() {
    mobileMenuOpen = false;
  }

  function toggleUserMenu() {
    userMenuOpen = !userMenuOpen;
  }

  function closeUserMenu() {
    userMenuOpen = false;
  }
</script>

<div
  class="min-h-screen bg-gray-50 text-gray-900 dark:bg-slate-950 dark:text-slate-50 font-sans transition-colors duration-300"
>
  <nav
    class="border-b border-gray-200 dark:border-slate-800 bg-white/80 dark:bg-slate-950/80 backdrop-blur-md sticky top-0 z-50 transition-colors"
  >
    <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
      <div class="flex h-16 items-center justify-between">
        <a
          href="/"
          class="text-xl font-bold text-green-600 dark:text-emerald-500"
        >
          Golf Swing Analyzer
        </a>
        <nav class="hidden md:flex space-x-4 items-center">
          {#if $user}
            <a
              href="/analyze"
              class="text-gray-500 hover:text-green-600 dark:text-slate-300 dark:hover:text-emerald-400"
              >Analyze</a
            >
            <a
              href="/dashboard"
              class="text-gray-500 hover:text-green-600 dark:text-slate-300 dark:hover:text-emerald-400"
              >Dashboard</a
            >
            <a
              href="/drills"
              class="text-gray-500 hover:text-green-600 dark:text-slate-300 dark:hover:text-emerald-400"
              >Drills</a
            >
          {/if}

          <div class="ml-2 border-l border-gray-200 dark:border-slate-700 pl-4">
            <ThemeToggle />
          </div>

          {#if $user}
            <!-- User Dropdown Menu -->
            <div class="relative">
              <button
                on:click={toggleUserMenu}
                class="flex items-center space-x-2 text-slate-200 hover:text-white font-medium"
              >
                <span>{$user.full_name || $user.email}</span>
                <svg
                  class="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M19 9l-7 7-7-7"
                  />
                </svg>
              </button>

              {#if userMenuOpen}
                <div
                  class="absolute right-0 mt-2 w-48 bg-slate-900 rounded-md shadow-xl py-1 z-50 border border-slate-700 ring-1 ring-black ring-opacity-5"
                >
                  <a
                    href="/profile"
                    on:click={closeUserMenu}
                    class="block px-4 py-2 text-sm text-slate-300 hover:bg-slate-800 hover:text-white"
                  >
                    Profile
                  </a>
                  <button
                    on:click={() => {
                      logout();
                      closeUserMenu();
                    }}
                    class="block w-full text-left px-4 py-2 text-sm text-red-400 hover:bg-slate-800 hover:text-red-300"
                  >
                    Logout
                  </button>
                </div>
              {/if}
            </div>
          {:else}
            <a
              href="/login"
              class="text-emerald-400 hover:text-emerald-300 font-medium"
              >Login</a
            >
            <a
              href="/register"
              class="bg-emerald-600 text-white px-3 py-1 rounded hover:bg-emerald-500 transition-colors"
              >Register</a
            >
          {/if}
        </nav>

        <!-- Mobile Menu Button -->
        <button
          class="md:hidden p-2 rounded-md text-slate-400 hover:text-white hover:bg-slate-800"
          on:click={toggleMobileMenu}
          aria-label="Toggle menu"
        >
          <svg
            class="h-6 w-6"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            {#if mobileMenuOpen}
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M6 18L18 6M6 6l12 12"
              />
            {:else}
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M4 6h16M4 12h16M4 18h16"
              />
            {/if}
          </svg>
        </button>
      </div>
    </div>

    <!-- Mobile Navigation Menu -->
    {#if mobileMenuOpen}
      <div class="md:hidden border-t border-slate-800 bg-slate-900">
        <nav class="px-4 py-4 space-y-3">
          {#if $user}
            <a
              href="/analyze"
              on:click={closeMobileMenu}
              class="block text-slate-300 hover:text-white py-2">Analyze</a
            >
            <a
              href="/dashboard"
              on:click={closeMobileMenu}
              class="block text-slate-300 hover:text-white py-2">Dashboard</a
            >
            <a
              href="/drills"
              on:click={closeMobileMenu}
              class="block text-slate-300 hover:text-white py-2">Drills</a
            >
          {/if}

          {#if $user}
            <div class="pt-3 border-t border-slate-800">
              <p class="text-slate-200 font-medium py-2">
                {$user.full_name || $user.email}
              </p>
              <a
                href="/profile"
                on:click={closeMobileMenu}
                class="block text-slate-400 hover:text-white py-2">Profile</a
              >
              <button
                on:click={() => {
                  logout();
                  closeMobileMenu();
                }}
                class="block w-full text-left text-red-400 hover:text-red-300 py-2"
                >Logout</button
              >
            </div>
          {:else}
            <div class="pt-3 border-t border-slate-800 space-y-2">
              <a
                href="/login"
                on:click={closeMobileMenu}
                class="block text-emerald-400 hover:text-emerald-300 font-medium py-2"
                >Login</a
              >
              <a
                href="/register"
                on:click={closeMobileMenu}
                class="block bg-emerald-600 text-white px-3 py-2 rounded hover:bg-emerald-500 text-center"
                >Register</a
              >
            </div>
          {/if}
        </nav>
      </div>
    {/if}
  </nav>
  <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <slot />
  </main>
</div>

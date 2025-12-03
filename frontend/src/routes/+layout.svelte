<script lang="ts">
  import "../app.css";
  import { user, logout, fetchUser } from "$lib/stores/auth";
  import { onMount } from "svelte";

  let mobileMenuOpen = false;
  let userMenuOpen = false;

  onMount(() => {
    fetchUser();
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

<div class="min-h-screen bg-gray-50 text-gray-900 font-sans">
  <header class="bg-white shadow-sm">
    <div
      class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between"
    >
      <a href="/" class="text-xl font-bold text-green-700"
        >Golf Swing Analyzer</a
      >

      <!-- Desktop Navigation -->
      <nav class="hidden md:flex space-x-4 items-center">
        <a href="/" class="text-gray-600 hover:text-gray-900">Analyze</a>
        <a href="/dashboard" class="text-gray-600 hover:text-gray-900"
          >Dashboard</a
        >
        <a href="/sessions" class="text-gray-600 hover:text-gray-900">History</a
        >
        <a href="/drills" class="text-gray-600 hover:text-gray-900">Drills</a>

        {#if $user}
          <!-- User Dropdown Menu -->
          <div class="relative">
            <button
              on:click={toggleUserMenu}
              class="flex items-center space-x-2 text-gray-800 hover:text-gray-900 font-medium"
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
                class="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg py-1 z-50 border border-gray-200"
              >
                <a
                  href="/profile"
                  on:click={closeUserMenu}
                  class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                >
                  Profile
                </a>
                <button
                  on:click={() => {
                    logout();
                    closeUserMenu();
                  }}
                  class="block w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-gray-100"
                >
                  Logout
                </button>
              </div>
            {/if}
          </div>
        {:else}
          <a
            href="/login"
            class="text-green-600 hover:text-green-800 font-medium">Login</a
          >
          <a
            href="/register"
            class="bg-green-600 text-white px-3 py-1 rounded hover:bg-green-700"
            >Register</a
          >
        {/if}
      </nav>

      <!-- Mobile Menu Button -->
      <button
        class="md:hidden p-2 rounded-md text-gray-600 hover:text-gray-900 hover:bg-gray-100"
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

    <!-- Mobile Navigation Menu -->
    {#if mobileMenuOpen}
      <div class="md:hidden border-t border-gray-200 bg-white">
        <nav class="px-4 py-4 space-y-3">
          <a
            href="/"
            on:click={closeMobileMenu}
            class="block text-gray-600 hover:text-gray-900 py-2">Analyze</a
          >
          <a
            href="/dashboard"
            on:click={closeMobileMenu}
            class="block text-gray-600 hover:text-gray-900 py-2">Dashboard</a
          >
          <a
            href="/sessions"
            on:click={closeMobileMenu}
            class="block text-gray-600 hover:text-gray-900 py-2">History</a
          >
          <a
            href="/drills"
            on:click={closeMobileMenu}
            class="block text-gray-600 hover:text-gray-900 py-2">Drills</a
          >

          {#if $user}
            <div class="pt-3 border-t border-gray-200">
              <p class="text-gray-800 font-medium py-2">
                {$user.full_name || $user.email}
              </p>
              <a
                href="/profile"
                on:click={closeMobileMenu}
                class="block text-gray-600 hover:text-gray-900 py-2">Profile</a
              >
              <button
                on:click={() => {
                  logout();
                  closeMobileMenu();
                }}
                class="block w-full text-left text-red-600 hover:text-red-800 py-2"
                >Logout</button
              >
            </div>
          {:else}
            <div class="pt-3 border-t border-gray-200 space-y-2">
              <a
                href="/login"
                on:click={closeMobileMenu}
                class="block text-green-600 hover:text-green-800 font-medium py-2"
                >Login</a
              >
              <a
                href="/register"
                on:click={closeMobileMenu}
                class="block bg-green-600 text-white px-3 py-2 rounded hover:bg-green-700 text-center"
                >Register</a
              >
            </div>
          {/if}
        </nav>
      </div>
    {/if}
  </header>
  <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <slot />
  </main>
</div>

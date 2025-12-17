<script lang="ts">
  import { Scan, Timer, Activity, FileText } from "lucide-svelte";

  const features = [
    {
      title: "Automatic swing phase detection",
      description:
        "Address, top, impact, and finish are detected automatically from your video—no manual tagging needed.",
      icon: Scan,
    },
    {
      title: "Tempo & timing metrics",
      description:
        "Backswing and downswing durations, tempo ratio, and overall rhythm based on frame-accurate timestamps.",
      icon: Timer,
    },
    {
      title: "Rotation & posture insights",
      description:
        "Chest and pelvis rotation, spine tilt, arm angles, head movement, and more—extracted directly from motion.",
      icon: Activity,
    },
    {
      title: "Clear, structured feedback",
      description:
        "Digestible summaries that highlight what is working in your swing and where consistency breaks down.",
      icon: FileText,
    },
  ];

  const partners = [
    {
      title: "Premium Golf Gear",
      description:
        "Shop the latest drivers, irons, and accessories from top brands.",
      image: "/images/partner-gear.png",
      cta: "Shop Now!",
    },
    {
      title: "Improve Your Game",
      description:
        "Personalized fitness plans designed specifically for golfers.",
      image: "/images/partner-fitness.png",
      cta: "Fitness Plans",
    },
    {
      title: "Virtual Coaching",
      description:
        "Get professional feedback from certified instructors anywhere.",
      image: "/images/partner-coaching.png",
      cta: "Try For Free",
    },
  ];

  const steps = [
    {
      label: "1",
      title: "Upload your swing",
      body: "Record a down-the-line or face-on swing on your phone and upload the clip.",
    },
    {
      label: "2",
      title: "Let the analyzer work",
      body: "The system runs pose estimation and extracts key positions and motion data.",
    },
    {
      label: "3",
      title: "Review the metrics",
      body: "Tempo, rotation, posture, and movement metrics are presented in a clean dashboard.",
    },
    {
      label: "4",
      title: "Track progress over time",
      body: "Compare multiple sessions to see if your changes actually show up in the numbers.",
    },
  ];
</script>

<svelte:head>
  <title>GolfAnalyzer – AI-powered golf swing analysis</title>
  <meta
    name="description"
    content="Upload your golf swing and get instant metrics, timing, and movement analysis—all in a clean, focused interface."
  />
</svelte:head>

<div class="pb-16 pt-12 lg:pt-16">
  <!-- HERO -->
  <section class="mb-20">
    <div class="flex flex-col gap-12 lg:flex-row lg:items-center">
      <div class="flex-1 space-y-8">
        <div
          class="inline-flex items-center gap-2 rounded-full border border-gray-200 dark:border-slate-800 bg-white dark:bg-slate-900/50 px-3 py-1 text-xs font-medium text-gray-600 dark:text-slate-300 transition-colors"
        >
          <span
            class="h-1.5 w-1.5 rounded-full bg-green-500 dark:bg-emerald-400"
          ></span>
          Early access · GolfAnalyzer
        </div>

        <div class="space-y-4">
          <h1
            class="text-balance text-4xl font-extrabold tracking-tight text-gray-900 dark:text-white sm:text-5xl lg:text-7xl transition-colors"
          >
            Unleash Your Perfect Swing
            <span
              class="block text-transparent bg-clip-text bg-gradient-to-r from-green-500 to-emerald-400"
              >with Real Motion Data.</span
            >
          </h1>

          <p
            class="max-w-xl text-base text-gray-600 dark:text-slate-300 sm:text-lg transition-colors"
          >
            GolfAnalyzer uses advanced motion capture to detail your swing
            timing, rotation, and posture, showing you exactly what to improve.
          </p>
        </div>

        <div class="flex flex-wrap items-center gap-4">
          <a
            href="/login"
            class="inline-flex items-center justify-center rounded-full bg-green-600 dark:bg-emerald-500 px-5 py-2.5 text-sm font-semibold text-white dark:text-slate-950 shadow-lg shadow-green-500/20 dark:shadow-emerald-500/20 transition hover:bg-green-700 dark:hover:bg-emerald-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-400 dark:focus-visible:ring-emerald-400 focus-visible:ring-offset-2 focus-visible:ring-offset-white dark:focus-visible:ring-offset-slate-950"
          >
            Get started
          </a>

          <a
            href="#demo"
            class="inline-flex items-center justify-center rounded-full border border-gray-300 dark:border-slate-700 px-5 py-2.5 text-sm font-medium text-gray-700 dark:text-slate-200 hover:border-gray-400 dark:hover:border-slate-500 hover:bg-gray-50 dark:hover:bg-slate-900/60 transition-colors"
          >
            View example session
          </a>
        </div>

        <div
          class="flex flex-wrap gap-4 text-xs text-gray-500 dark:text-slate-400 transition-colors"
        >
          <div class="flex items-center gap-2">
            <span class="h-1.5 w-1.5 rounded-full bg-gray-400 dark:bg-slate-500"
            ></span>
            Works with standard phone video
          </div>
          <div class="flex items-center gap-2">
            <span class="h-1.5 w-1.5 rounded-full bg-gray-400 dark:bg-slate-500"
            ></span>
            No launch monitor required
          </div>
        </div>
      </div>

      <!-- Right-side visual -->
      <div class="flex-1 w-full relative">
        <div
          class="relative w-full aspect-square md:aspect-auto md:h-[600px] flex items-center justify-center"
        >
          <!-- Glow effect behind the golfer -->
          <div
            class="absolute w-[80%] h-[80%] bg-green-500/20 dark:bg-emerald-500/10 blur-[100px] rounded-full"
          ></div>

          <img
            src="/images/golfer.png"
            alt="Golfer with biomechanical skeleton overlay"
            class="relative max-w-full max-h-full object-contain z-10 drop-shadow-2xl"
          />

          <!-- Floating UI Elements to match reference vibe -->
        </div>
      </div>
    </div>
  </section>

  <!-- FEATURES -->
  <section class="mb-20">
    <div class="space-y-12">
      <div class="text-center max-w-2xl mx-auto space-y-4">
        <h2
          class="text-3xl font-bold text-gray-900 dark:text-slate-50 sm:text-4xl transition-colors"
        >
          What GolfAnalyzer gives you
        </h2>
        <p
          class="text-base text-gray-600 dark:text-slate-400 sm:text-lg transition-colors"
        >
          You don’t need more swing tips—you need to know what your body is
          actually doing when you swing a club.
        </p>
      </div>

      <div class="grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
        {#each features as feature}
          <div class="flex flex-col items-center text-center gap-4 p-4">
            <div
              class="flex h-12 w-12 items-center justify-center rounded-xl bg-green-100 dark:bg-emerald-900/30 text-green-600 dark:text-emerald-400"
            >
              <svelte:component this={feature.icon} size={24} />
            </div>
            <div class="space-y-2">
              <h3
                class="text-lg font-semibold text-gray-900 dark:text-slate-100 transition-colors"
              >
                {feature.title}
              </h3>
              <p
                class="text-sm text-gray-600 dark:text-slate-400 transition-colors"
              >
                {feature.description}
              </p>
            </div>
          </div>
        {/each}
      </div>
    </div>
  </section>

  <!-- HOW IT WORKS -->
  <section id="demo" class="mb-20">
    <div class="space-y-8">
      <div
        class="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between"
      >
        <div>
          <h2
            class="text-lg font-semibold text-gray-900 dark:text-slate-50 sm:text-xl transition-colors"
          >
            How it works
          </h2>
          <p
            class="max-w-xl text-sm text-gray-600 dark:text-slate-400 sm:text-[15px] transition-colors"
          >
            From phone video to actionable metrics in a few simple steps.
          </p>
        </div>
      </div>

      <ol class="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {#each steps as step}
          <li
            class="flex flex-col gap-3 rounded-2xl border border-gray-200 dark:border-slate-800 bg-white dark:bg-slate-950/60 p-4 transition-colors"
          >
            <div
              class="flex h-7 w-7 items-center justify-center rounded-full bg-green-500 dark:bg-emerald-500 text-xs font-semibold text-white dark:text-slate-950 shadow-sm"
            >
              {step.label}
            </div>
            <div class="space-y-1">
              <h3
                class="text-sm font-semibold text-gray-900 dark:text-slate-100 transition-colors"
              >
                {step.title}
              </h3>
              <p
                class="text-xs text-gray-600 dark:text-slate-400 sm:text-[13px] transition-colors"
              >
                {step.body}
              </p>
            </div>
          </li>
        {/each}
      </ol>
    </div>
  </section>

  <!-- PARTNERS -->
  <section class="pb-20">
    <div class="space-y-12">
      <div class="text-center max-w-2xl mx-auto space-y-4">
        <h2
          class="text-3xl font-bold text-gray-900 dark:text-slate-50 sm:text-4xl transition-colors"
        >
          Our Partners & Featured Offers
        </h2>
      </div>

      <div class="grid gap-8 sm:grid-cols-2 lg:grid-cols-3 max-w-5xl mx-auto">
        {#each partners as partner}
          <div
            class="group relative overflow-hidden rounded-2xl bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 shadow-lg transition-all hover:shadow-xl dark:shadow-black/50 hover:-translate-y-1 duration-300"
          >
            <div
              class="aspect-[4/3] w-full overflow-hidden bg-gray-100 dark:bg-slate-800"
            >
              <img
                src={partner.image}
                alt={partner.title}
                class="h-full w-full object-cover object-center transition-transform duration-500 group-hover:scale-105"
              />
            </div>
            <div class="flex flex-col items-center text-center p-6 space-y-4">
              <h3 class="text-xl font-bold text-gray-900 dark:text-slate-50">
                {partner.title}
              </h3>
              <!-- 
                   Note: The reference image combines title/desc sometimes, 
                   but we'll keep it clean with a title + button layout 
                   or title + desc + button. 
                -->
              <!-- <p class="text-sm text-gray-600 dark:text-slate-400">
                  {partner.description}
                </p> -->

              <button
                class="inline-flex items-center justify-center rounded-lg bg-green-600 dark:bg-emerald-600 px-6 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-green-500 dark:hover:bg-emerald-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-600 dark:focus-visible:ring-emerald-600 focus-visible:ring-offset-2 transition-all w-full sm:w-auto"
              >
                {partner.cta}
              </button>
            </div>
          </div>
        {/each}
      </div>
    </div>
  </section>

  <!-- FOOTER -->
  <footer
    class="border-t border-gray-200 dark:border-slate-900 pt-8 mt-8 text-xs text-gray-500 dark:text-slate-500 transition-colors"
  >
    <div
      class="flex flex-col items-start justify-between gap-3 sm:flex-row sm:items-center"
    >
      <p>GolfAnalyzer · Experimental golf swing analysis tool.</p>
      <div class="flex gap-4">
        <a
          href="/login"
          class="hover:text-gray-900 dark:hover:text-slate-300 transition-colors"
          >Login</a
        >
        <a
          href="/register"
          class="hover:text-gray-900 dark:hover:text-slate-300 transition-colors"
          >Register</a
        >
      </div>
    </div>
  </footer>
</div>

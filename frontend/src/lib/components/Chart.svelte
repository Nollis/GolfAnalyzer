<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import Chart from "chart.js/auto";
    import type { ChartType, ChartData, ChartOptions } from "chart.js";

    export let type: ChartType = "line";
    export let data: ChartData = { labels: [], datasets: [] };
    export let options: ChartOptions = {};

    let canvas: HTMLCanvasElement;
    let chart: Chart | null = null;

    onMount(() => {
        if (canvas) {
            chart = new Chart(canvas, {
                type,
                data,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    ...options,
                },
            });
        }
    });

    onDestroy(() => {
        if (chart) {
            chart.destroy();
        }
    });

    // Update chart when data changes
    $: if (chart && data) {
        chart.data = data;
        chart.update();
    }
</script>

<div class="relative w-full h-full min-h-[300px]">
    <canvas bind:this={canvas}></canvas>
</div>

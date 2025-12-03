<script>
    import { onMount } from "svelte";

    let canvas;
    let ctx;

    // Mock data
    const width = 800;
    const height = 600;

    // Mock BBox (e.g. centered person)
    // Let's say image is 800x600
    // Person is in 200, 100, 600, 500 (400x400 box)
    const bbox = [200, 100, 600, 500];

    // Mock Landmarks (HybrIK style, 0-192, 0-256)
    // Let's put points at corners of the input space to see where they map
    const landmarks = [
        { x: 0, y: 0 }, // Top-Left
        { x: 192, y: 0 }, // Top-Right
        { x: 0, y: 256 }, // Bottom-Left
        { x: 192, y: 256 }, // Bottom-Right
        { x: 96, y: 128 }, // Center
    ];

    function draw() {
        if (!ctx) return;

        ctx.clearRect(0, 0, width, height);

        // Draw Image Border
        ctx.strokeStyle = "black";
        ctx.strokeRect(0, 0, width, height);

        // Draw BBox
        ctx.strokeStyle = "red";
        ctx.lineWidth = 2;
        ctx.strokeRect(bbox[0], bbox[1], bbox[2] - bbox[0], bbox[3] - bbox[1]);

        // Draw Landmarks with current logic (No Scaling)
        ctx.fillStyle = "blue";
        landmarks.forEach((lm) => {
            const x = bbox[0] + lm.x;
            const y = bbox[1] + lm.y;
            ctx.beginPath();
            ctx.arc(x, y, 5, 0, 2 * Math.PI);
            ctx.fill();
        });

        // Draw Landmarks with Scaling Logic
        ctx.fillStyle = "green";
        const inputW = 192;
        const inputH = 256;
        const bboxW = bbox[2] - bbox[0];
        const bboxH = bbox[3] - bbox[1];

        landmarks.forEach((lm) => {
            const x = bbox[0] + (lm.x / inputW) * bboxW;
            const y = bbox[1] + (lm.y / inputH) * bboxH;
            ctx.beginPath();
            ctx.arc(x, y, 5, 0, 2 * Math.PI);
            ctx.fill();
        });
    }

    onMount(() => {
        ctx = canvas.getContext("2d");
        draw();
    });
</script>

<div style="padding: 20px;">
    <h1>Skeleton Debug</h1>
    <p>Red Box: BBox</p>
    <p>Blue Dots: Current Logic (Offset only)</p>
    <p>Green Dots: Proposed Logic (Scaled)</p>
    <canvas bind:this={canvas} {width} {height} style="border: 1px solid #ccc;"
    ></canvas>
</div>

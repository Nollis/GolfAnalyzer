<script lang="ts">
    export let poses: any[] = [];
    export let phases: any;

    interface PhaseData {
        name: string;
        frame: number;
        description: string;
    }

    const phasesList: PhaseData[] = [
        {
            name: "Address",
            frame: phases?.address_frame || 0,
            description: "Setup position before swing",
        },
        {
            name: "Top",
            frame: phases?.top_frame || 0,
            description: "Peak of backswing",
        },
        {
            name: "Impact",
            frame: phases?.impact_frame || 0,
            description: "Club meets ball",
        },
        {
            name: "Finish",
            frame: phases?.finish_frame || 0,
            description: "End of follow-through",
        },
    ];

    const CONNECTIONS = [
        [11, 12],
        [11, 13],
        [13, 15],
        [12, 14],
        [14, 16], // Arms
        [11, 23],
        [12, 24],
        [23, 24], // Torso
        [23, 25],
        [25, 27],
        [24, 26],
        [26, 28], // Legs
        [27, 29],
        [29, 31],
        [28, 30],
        [30, 32], // Feet
    ];

    let showPro = true;

    // Hardcoded "Pro" reference poses (Face On view approximation)
    const PRO_POSES: Record<string, { landmarks: { x: number; y: number }[] }> =
        {
            Address: {
                landmarks: [
                    { x: 0.5, y: 0.15 }, // Nose
                    { x: 0.55, y: 0.25 },
                    { x: 0.45, y: 0.25 }, // Shoulders
                    { x: 0.55, y: 0.45 },
                    { x: 0.45, y: 0.45 }, // Elbows
                    { x: 0.52, y: 0.6 },
                    { x: 0.48, y: 0.6 }, // Wrists
                    { x: 0.53, y: 0.5 },
                    { x: 0.47, y: 0.5 }, // Hips
                    { x: 0.55, y: 0.75 },
                    { x: 0.45, y: 0.75 }, // Knees
                    { x: 0.55, y: 0.9 },
                    { x: 0.45, y: 0.9 }, // Ankles
                ],
            },
            Top: {
                landmarks: [
                    { x: 0.48, y: 0.15 }, // Nose (slight shift right)
                    { x: 0.4, y: 0.25 },
                    { x: 0.5, y: 0.28 }, // Shoulders (turned)
                    { x: 0.35, y: 0.4 },
                    { x: 0.6, y: 0.35 }, // Elbows
                    { x: 0.4, y: 0.2 },
                    { x: 0.4, y: 0.2 }, // Wrists (high)
                    { x: 0.5, y: 0.5 },
                    { x: 0.45, y: 0.5 }, // Hips (turned)
                    { x: 0.52, y: 0.75 },
                    { x: 0.45, y: 0.75 }, // Knees
                    { x: 0.55, y: 0.9 },
                    { x: 0.45, y: 0.9 }, // Ankles
                ],
            },
            Impact: {
                landmarks: [
                    { x: 0.48, y: 0.15 }, // Nose
                    { x: 0.45, y: 0.25 },
                    { x: 0.55, y: 0.28 }, // Shoulders (open)
                    { x: 0.45, y: 0.45 },
                    { x: 0.5, y: 0.4 }, // Elbows
                    { x: 0.42, y: 0.6 },
                    { x: 0.42, y: 0.6 }, // Wrists (ahead)
                    { x: 0.45, y: 0.5 },
                    { x: 0.55, y: 0.5 }, // Hips (open)
                    { x: 0.5, y: 0.75 },
                    { x: 0.55, y: 0.75 }, // Knees
                    { x: 0.55, y: 0.9 },
                    { x: 0.45, y: 0.9 }, // Ankles
                ],
            },
            Finish: {
                landmarks: [
                    { x: 0.5, y: 0.15 }, // Nose
                    { x: 0.4, y: 0.25 },
                    { x: 0.5, y: 0.25 }, // Shoulders (rotated)
                    { x: 0.35, y: 0.35 },
                    { x: 0.45, y: 0.3 }, // Elbows
                    { x: 0.3, y: 0.2 },
                    { x: 0.3, y: 0.2 }, // Wrists (high finish)
                    { x: 0.45, y: 0.5 },
                    { x: 0.5, y: 0.5 }, // Hips (rotated)
                    { x: 0.5, y: 0.75 },
                    { x: 0.52, y: 0.75 }, // Knees
                    { x: 0.5, y: 0.9 },
                    { x: 0.55, y: 0.9 }, // Ankles
                ],
            },
        };

    function getBoundingBox(landmarks: any[]) {
        let minX = 1,
            minY = 1,
            maxX = 0,
            maxY = 0;
        landmarks.forEach((lm) => {
            if (lm.visibility && lm.visibility < 0.5) return;
            if (lm.x < minX) minX = lm.x;
            if (lm.x > maxX) maxX = lm.x;
            if (lm.y < minY) minY = lm.y;
            if (lm.y > maxY) maxY = lm.y;
        });
        // Fallback if no landmarks visible
        if (minX > maxX)
            return {
                minX: 0.2,
                minY: 0.2,
                maxX: 0.8,
                maxY: 0.8,
                width: 0.6,
                height: 0.6,
            };
        return {
            minX,
            minY,
            maxX,
            maxY,
            width: maxX - minX,
            height: maxY - minY,
        };
    }

    function drawSkeleton(
        ctx: CanvasRenderingContext2D,
        landmarks: any[],
        color: string,
        width: number,
        height: number,
        transform: any,
        isPro = false,
    ) {
        // Transform function
        const drawX = (x: number) =>
            (x - transform.minX) * transform.scale * width + transform.paddingX;
        const drawY = (y: number) =>
            (y - transform.minY) * transform.scale * height +
            transform.paddingY;

        ctx.strokeStyle = color;
        ctx.lineWidth = isPro ? 2 : 3;
        if (isPro) ctx.setLineDash([5, 5]);
        else ctx.setLineDash([]);

        CONNECTIONS.forEach(([start, end]) => {
            const p1 = landmarks[start];
            const p2 = landmarks[end];
            // For Pro poses we assume indices map to our simplified list if we used indices,
            // BUT our PRO_POSES structure is just a list of points, not a full MediaPipe 33-point set.
            // Wait, my PRO_POSES just has 13 points. MediaPipe has 33.
            // The CONNECTIONS indices (11-32) won't match my 13-point Pro list!
            // I need to map my Pro points to the MediaPipe indices or use a different drawing logic for Pro.

            // Let's fix PRO_POSES to use a map or full array.
            // Or simpler: Just draw lines between the points I defined for Pro.
            // My Pro points: 0=Nose, 1,2=Shoulders, 3,4=Elbows, 5,6=Wrists, 7,8=Hips, 9,10=Knees, 11,12=Ankles.
            // Let's define PRO_CONNECTIONS.

            if (isPro) {
                // Custom Pro Drawing
                // 0-Nose
                // 1-LSh, 2-RSh
                // 3-LEl, 4-REl
                // 5-LWr, 6-RWr
                // 7-LHip, 8-RHip
                // 9-LKnee, 10-RKnee
                // 11-LAnk, 12-RAnk
                const proConns = [
                    [0, 1],
                    [0, 2], // Neck
                    [1, 3],
                    [3, 5], // Left Arm
                    [2, 4],
                    [4, 6], // Right Arm
                    [1, 7],
                    [2, 8], // Torso
                    [7, 8], // Hips
                    [7, 9],
                    [9, 11], // Left Leg
                    [8, 10],
                    [10, 12], // Right Leg
                ];

                const pp1 = landmarks[start]; // This won't work because 'start' is a MediaPipe index (e.g. 11)
                // We need separate logic.
            } else {
                if (p1 && p2 && p1.visibility > 0.5 && p2.visibility > 0.5) {
                    ctx.beginPath();
                    ctx.moveTo(drawX(p1.x), drawY(p1.y));
                    ctx.lineTo(drawX(p2.x), drawY(p2.y));
                    ctx.stroke();
                }
            }
        });

        // Separate loop for Pro connections to avoid complexity above
        if (isPro) {
            const proConns = [
                [0, 1],
                [0, 2],
                [1, 3],
                [3, 5],
                [2, 4],
                [4, 6],
                [1, 7],
                [2, 8],
                [7, 8],
                [7, 9],
                [9, 11],
                [8, 10],
                [10, 12],
            ];
            proConns.forEach(([s, e]) => {
                const p1 = landmarks[s];
                const p2 = landmarks[e];
                if (p1 && p2) {
                    ctx.beginPath();
                    ctx.moveTo(drawX(p1.x), drawY(p1.y));
                    ctx.lineTo(drawX(p2.x), drawY(p2.y));
                    ctx.stroke();
                }
            });
        }

        // Draw joints
        ctx.fillStyle = isPro ? "#9CA3AF" : "#059669";
        landmarks.forEach((lm: any) => {
            if (isPro || lm.visibility > 0.5) {
                ctx.beginPath();
                ctx.arc(
                    drawX(lm.x),
                    drawY(lm.y),
                    isPro ? 3 : 4,
                    0,
                    2 * Math.PI,
                );
                ctx.fill();
            }
        });
        ctx.setLineDash([]);
    }

    function drawPhase(
        canvas: HTMLCanvasElement,
        phaseFrame: number,
        phaseName: string,
    ) {
        if (!poses.length) return;

        const ctx = canvas.getContext("2d");
        if (!ctx) return;

        const pose =
            poses.find((p) => p.frame_index === phaseFrame) || poses[0];
        if (!pose || !pose.landmarks) return;

        const width = 300;
        const height = 400;
        canvas.width = width;
        canvas.height = height;

        ctx.clearRect(0, 0, width, height);

        // Calculate Auto-Zoom Transform
        const bbox = getBoundingBox(pose.landmarks);
        const padding = 0.15;
        const scaleX = width / (bbox.width * (1 + padding * 2));
        const scaleY = height / (bbox.height * (1 + padding * 2));
        const scale = Math.min(scaleX, scaleY);

        const transform = {
            minX: bbox.minX - bbox.width * padding,
            minY: bbox.minY - bbox.height * padding,
            scale: scale,
            paddingX: (width - bbox.width * scale) / 2,
            paddingY: (height - bbox.height * scale) / 2,
        };

        // Draw Reference Guidelines
        ctx.strokeStyle = "#F3F4F6";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(width / 2, 0);
        ctx.lineTo(width / 2, height);
        ctx.moveTo(0, height * 0.9);
        ctx.lineTo(width, height * 0.9);
        ctx.stroke();

        // Draw Pro Skeleton (Ghost)
        if (showPro && PRO_POSES[phaseName]) {
            const proLandmarks = PRO_POSES[phaseName].landmarks;
            const proBbox = {
                minX: Math.min(...proLandmarks.map((l) => l.x)),
                maxX: Math.max(...proLandmarks.map((l) => l.x)),
                minY: Math.min(...proLandmarks.map((l) => l.y)),
                maxY: Math.max(...proLandmarks.map((l) => l.y)),
                width: 0,
                height: 0,
            };
            proBbox.width = proBbox.maxX - proBbox.minX;
            proBbox.height = proBbox.maxY - proBbox.minY;

            const proScaleX = width / (proBbox.width * (1 + padding * 2));
            const proScaleY = height / (proBbox.height * (1 + padding * 2));
            const proScale = Math.min(proScaleX, proScaleY);

            const proTransform = {
                minX: proBbox.minX - proBbox.width * padding,
                minY: proBbox.minY - proBbox.height * padding,
                scale: proScale,
                paddingX: (width - proBbox.width * proScale) / 2,
                paddingY: (height - proBbox.height * proScale) / 2,
            };

            drawSkeleton(
                ctx,
                proLandmarks,
                "#D1D5DB",
                width,
                height,
                proTransform,
                true,
            );
        }

        // Draw User Skeleton
        drawSkeleton(
            ctx,
            pose.landmarks,
            "#10B981",
            width,
            height,
            transform,
            false,
        );
    }

    function initCanvas(canvas: HTMLCanvasElement, phase: any) {
        if (canvas) {
            drawPhase(canvas, phase.frame, phase.name);
        }
    }

    // Re-draw when toggle changes
    $: if (showPro !== undefined && poses.length) {
        phasesList.forEach((phase) => {
            const canvas = document.getElementById(
                `canvas-${phase.name}`,
            ) as HTMLCanvasElement;
            if (canvas) drawPhase(canvas, phase.frame, phase.name);
        });
    }
</script>

<div class="mb-6 flex justify-end">
    <label class="flex items-center cursor-pointer">
        <div class="relative">
            <input type="checkbox" class="sr-only" bind:checked={showPro} />
            <div class="block bg-gray-200 w-10 h-6 rounded-full"></div>
            <div
                class="dot absolute left-1 top-1 bg-white w-4 h-4 rounded-full transition {showPro
                    ? 'transform translate-x-4 bg-green-500'
                    : ''}"
            ></div>
        </div>
        <div class="ml-3 text-gray-700 font-medium">
            Pro Comparison <span class="text-xs text-gray-500">(Ghost)</span>
        </div>
    </label>
</div>

<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
    {#each phasesList as phase}
        <div
            class="bg-white rounded-lg shadow-md overflow-hidden border border-gray-100"
        >
            <div
                class="bg-gray-50 p-3 border-b border-gray-100 flex justify-between items-center"
            >
                <div>
                    <h3 class="font-bold text-gray-900">{phase.name}</h3>
                    <p class="text-gray-500 text-xs">{phase.description}</p>
                </div>
                <span class="text-xs font-mono text-gray-400"
                    >#{phase.frame}</span
                >
            </div>

            <div class="p-4 relative">
                <div
                    class="bg-white rounded-lg flex items-center justify-center border border-gray-100"
                    style="height: 350px;"
                >
                    {#if poses.length > 0}
                        <canvas
                            id={`canvas-${phase.name}`}
                            use:initCanvas={phase}
                            class="max-w-full"
                        ></canvas>
                    {:else}
                        <div class="text-gray-400 text-sm">No data</div>
                    {/if}
                </div>
            </div>
        </div>
    {/each}
</div>

{#if poses.length === 0}
    <div
        class="text-center py-12 bg-yellow-50 rounded-lg border border-yellow-200"
    >
        <svg
            class="w-16 h-16 mx-auto text-yellow-500 mb-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
        >
            <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
        </svg>
        <p class="text-yellow-800 font-medium">
            Position analysis not available for this session
        </p>
        <p class="text-yellow-600 text-sm mt-2">
            Upload a new swing to see phase-by-phase breakdown
        </p>
    </div>
{/if}

<style>
    input:checked ~ .dot {
        transform: translateX(100%);
        background-color: #10b981;
    }
    input:checked ~ .block {
        background-color: #d1fae5;
    }
</style>

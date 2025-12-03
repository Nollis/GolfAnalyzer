<script lang="ts">
    export let metricName: string;

    // Helper to convert degrees to radians
    const toRad = (deg: number) => (deg * Math.PI) / 180;

    // Calculate coordinates for an arc
    function describeArc(
        x: number,
        y: number,
        radius: number,
        startAngle: number,
        endAngle: number,
    ) {
        const start = {
            x: x + radius * Math.cos(toRad(startAngle)),
            y: y + radius * Math.sin(toRad(startAngle)),
        };
        const end = {
            x: x + radius * Math.cos(toRad(endAngle)),
            y: y + radius * Math.sin(toRad(endAngle)),
        };
        const largeArcFlag = endAngle - startAngle <= 180 ? "0" : "1";
        return [
            "M",
            start.x,
            start.y,
            "A",
            radius,
            radius,
            0,
            largeArcFlag,
            1,
            end.x,
            end.y,
        ].join(" ");
    }
</script>

<div class="flex justify-center items-center p-4 bg-gray-50 rounded-lg">
    {#if metricName === "tempo_ratio"}
        <!-- Tempo Visualization: 3:1 Ratio -->
        <svg width="150" height="60" viewBox="0 0 150 60">
            <!-- Backswing Bar -->
            <rect x="10" y="20" width="90" height="20" rx="4" fill="#3B82F6" />
            <text
                x="55"
                y="35"
                text-anchor="middle"
                fill="white"
                font-size="10"
                font-weight="bold">3.0 (Back)</text
            >

            <!-- Downswing Bar -->
            <rect x="105" y="20" width="30" height="20" rx="4" fill="#10B981" />
            <text
                x="120"
                y="35"
                text-anchor="middle"
                fill="white"
                font-size="10"
                font-weight="bold">1.0</text
            >

            <text
                x="75"
                y="55"
                text-anchor="middle"
                fill="#6B7280"
                font-size="10">Ideal Ratio 3:1</text
            >
        </svg>
    {:else if metricName.includes("turn") || metricName.includes("rotation")}
        <!-- Rotation Visualization: Angle Arc -->
        <svg width="100" height="100" viewBox="0 0 100 100">
            <!-- Torso/Body Reference -->
            <circle cx="50" cy="50" r="15" fill="#E5E7EB" />

            <!-- Target Line (Vertical) -->
            <line
                x1="50"
                y1="10"
                x2="50"
                y2="90"
                stroke="#9CA3AF"
                stroke-width="1"
                stroke-dasharray="4 2"
            />

            <!-- Angle Arc -->
            {#if metricName.includes("shoulder")}
                <!-- 90 degrees for shoulders -->
                <path
                    d={describeArc(50, 50, 35, -90, 0)}
                    fill="none"
                    stroke="#3B82F6"
                    stroke-width="3"
                />
                <line
                    x1="50"
                    y1="50"
                    x2="85"
                    y2="50"
                    stroke="#3B82F6"
                    stroke-width="2"
                    marker-end="url(#arrow)"
                />
                <text
                    x="70"
                    y="40"
                    fill="#3B82F6"
                    font-size="12"
                    font-weight="bold">90°</text
                >
            {:else}
                <!-- 45 degrees for hips -->
                <path
                    d={describeArc(50, 50, 35, -45, 0)}
                    fill="none"
                    stroke="#10B981"
                    stroke-width="3"
                />
                <line
                    x1="50"
                    y1="50"
                    x2="75"
                    y2="25"
                    stroke="#10B981"
                    stroke-width="2"
                    marker-end="url(#arrow)"
                />
                <text
                    x="70"
                    y="30"
                    fill="#10B981"
                    font-size="12"
                    font-weight="bold">45°</text
                >
            {/if}

            <defs>
                <marker
                    id="arrow"
                    markerWidth="10"
                    markerHeight="10"
                    refX="9"
                    refY="3"
                    orient="auto"
                    markerUnits="strokeWidth"
                >
                    <path d="M0,0 L0,6 L9,3 z" fill="currentColor" />
                </marker>
            </defs>
        </svg>
    {:else}
        <p class="text-xs text-gray-500">No diagram available.</p>
    {/if}
</div>

<!-- frontend/src/lib/components/SkeletonViewer.svelte -->
<script lang="ts">
  interface Landmark {
    x: number;
    y: number;
    z: number;
    visibility: number;
  }

  interface KeyFrame {
    frame_index: number;
    timestamp_sec: number;
    phase: string;
    landmarks: Landmark[] | number[][];
    smpl_joints_2d?: Landmark[] | number[][]; // SMPL joints if available
    smpl_joints_2d_orig?: Landmark[] | number[][]; // Fallback SMPL
    smpl_bbox?: number[]; // [x1, y1, x2, y2]
  }

  export let keyFrame: KeyFrame;
  export let width: number = 400;
  export let height: number = 600;
  export let imageUrl: string | null = null;

  // SMPL connections (24 joints)
  const SMPL_CONNECTIONS = [
    [0, 1],
    [0, 2],
    [0, 3], // Pelvis -> L_Hip, R_Hip, Spine1
    [1, 4],
    [2, 5], // Hips -> Knees
    [3, 6], // Spine1 -> Spine2
    [4, 7],
    [5, 8], // Knees -> Ankles
    [6, 9], // Spine2 -> Spine3
    [7, 10],
    [8, 11], // Ankles -> Feet
    [9, 12],
    [9, 13],
    [9, 14], // Spine3 -> Neck, L_Collar, R_Collar
    [12, 15], // Neck -> Head
    [13, 16],
    [14, 17], // Collars -> Shoulders
    [16, 18],
    [17, 19], // Shoulders -> Elbows
    [18, 20],
    [19, 21], // Elbows -> Wrists
    [20, 22],
    [21, 23], // Wrists -> Hands
  ];

  function drawSkeleton(ctx: CanvasRenderingContext2D, img?: HTMLImageElement) {
    ctx.clearRect(0, 0, width, height);

    let imgRect = {
      ox: 0,
      oy: 0,
      iw: width,
      ih: height,
      iwRaw: width,
      ihRaw: height,
    };

    // Draw background image if available
    if (img) {
      const scale = Math.min(width / img.width, height / img.height);
      const iw = img.width * scale;
      const ih = img.height * scale;
      const ox = (width - iw) / 2;
      const oy = (height - ih) / 2;
      ctx.drawImage(img, ox, oy, iw, ih);
      imgRect = { ox, oy, iw, ih, iwRaw: img.width, ihRaw: img.height };
    }

    // Styling: Cyan bones, White joints, thinner lines
    ctx.strokeStyle = "#00FFFF";
    ctx.lineWidth = 2;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.fillStyle = "#00FFFF";

    // Prioritize SMPL joints if available
    // We prioritize smpl_joints_2d because smpl_joints_2d_orig seems to be corrupted (white ball).
    // Also, PoseImageSkeletonOverlay uses smpl_joints_2d and works fine.
    let landmarks = null;
    let isGlobalCoords = false;

    if (keyFrame.smpl_joints_2d && keyFrame.smpl_joints_2d.length > 0) {
      landmarks = keyFrame.smpl_joints_2d;
    } else if (
      keyFrame.smpl_joints_2d_orig &&
      keyFrame.smpl_joints_2d_orig.length > 0
    ) {
      landmarks = keyFrame.smpl_joints_2d_orig;
      isGlobalCoords = true;
    }

    if (!landmarks || landmarks.length === 0) {
      if (!img) {
        ctx.fillStyle = "#999";
        ctx.font = "16px sans-serif";
        ctx.textAlign = "center";
        ctx.fillText("No pose data", width / 2, height / 2);
      }
      return;
    }

    // Helper to handle both object {x,y} and array [x,y] formats
    const getX = (lm: any) =>
      typeof lm?.x === "number" ? lm.x : Array.isArray(lm) ? lm[0] : 0;
    const getY = (lm: any) =>
      typeof lm?.y === "number" ? lm.y : Array.isArray(lm) ? lm[1] : 0;

    // Check if landmarks look like pixels (values > 1)
    const isPixelCoords = landmarks.some(
      (lm: any) => Math.abs(getX(lm)) > 1.5 || Math.abs(getY(lm)) > 1.5,
    );

    const imgW = imgRect.iwRaw || imgRect.iw;
    const imgH = imgRect.ihRaw || imgRect.ih;

    let transform = (x: number, y: number) => {
      // Default: map 0..1 to image rect
      return {
        x: imgRect.ox + x * imgRect.iw,
        y: imgRect.oy + y * imgRect.ih,
      };
    };

    // If we have global coordinates (from smpl_joints_2d_orig), use them directly
    if (isGlobalCoords) {
      transform = (x: number, y: number) => {
        const normX = x / imgW;
        const normY = y / imgH;
        return {
          x: imgRect.ox + normX * imgRect.iw,
          y: imgRect.oy + normY * imgRect.ih,
        };
      };
    } else if (keyFrame.smpl_bbox && keyFrame.smpl_bbox.length >= 4) {
      const bboxX = keyFrame.smpl_bbox[0];
      const bboxY = keyFrame.smpl_bbox[1];
      const bboxW = keyFrame.smpl_bbox[2] - bboxX;
      const bboxH = keyFrame.smpl_bbox[3] - bboxY;
      const bboxCX = bboxX + bboxW / 2;
      const bboxCY = bboxY + bboxH / 2;

      const xs = landmarks.map(getX);
      const ys = landmarks.map(getY);
      const minX = Math.min(...xs);
      const maxX = Math.max(...xs);
      const minY = Math.min(...ys);
      const maxY = Math.max(...ys);
      const rangeX = maxX - minX;
      const rangeY = maxY - minY;

      if (rangeX < 2.0 && rangeY < 2.0) {
        // Normalized coordinates
        const isCentered = minX < -0.1 || minY < -0.1;

        if (isCentered) {
          // Centered coordinates [-0.5, 0.5] relative to bbox center
          // Scale based on height
          const scale = bboxH / Math.max(rangeY, 0.1);

          transform = (x: number, y: number) => {
            const pixelX = bboxCX + x * scale;
            const pixelY = bboxCY + y * scale;
            // Map pixel to canvas
            const normX = pixelX / imgW;
            const normY = pixelY / imgH;
            return {
              x: imgRect.ox + normX * imgRect.iw,
              y: imgRect.oy + normY * imgRect.ih,
            };
          };
        } else {
          // Assumed [0, 1] mapped to bbox
          transform = (x: number, y: number) => {
            const pixelX = bboxX + x * bboxW;
            const pixelY = bboxY + y * bboxH;
            const normX = pixelX / imgW;
            const normY = pixelY / imgH;
            return {
              x: imgRect.ox + normX * imgRect.iw,
              y: imgRect.oy + normY * imgRect.ih,
            };
          };
        }
      } else {
        // Assumed pixels in HybrIK input space (typically 192x256)
        const inputW = 192;
        const inputH = 256;
        transform = (x: number, y: number) => {
          const pixelX = bboxX + (x / inputW) * bboxW;
          const pixelY = bboxY + (y / inputH) * bboxH;
          const normX = pixelX / imgW;
          const normY = pixelY / imgH;
          return {
            x: imgRect.ox + normX * imgRect.iw,
            y: imgRect.oy + normY * imgRect.ih,
          };
        };
      }
    } else if (isPixelCoords) {
      // Pixel coords relative to full image
      transform = (x: number, y: number) => {
        const normX = x / imgW;
        const normY = y / imgH;
        return {
          x: imgRect.ox + normX * imgRect.iw,
          y: imgRect.oy + normY * imgRect.ih,
        };
      };
    }

    // Draw connections (bones)
    // Always use SMPL connections as we prioritize SMPL data and even if it has extra joints (29 vs 24),
    // the first 24 are standard SMPL.
    let drawnConnections = 0;
    SMPL_CONNECTIONS.forEach(([start, end]) => {
      if (start < landmarks.length && end < landmarks.length) {
        const startLandmark = landmarks[start] as any;
        const endLandmark = landmarks[end] as any;

        const visA =
          typeof startLandmark?.visibility === "number"
            ? startLandmark.visibility
            : 1.0;
        const visB =
          typeof endLandmark?.visibility === "number"
            ? endLandmark.visibility
            : 1.0;

        if (visA > 0.3 && visB > 0.3) {
          const startPt = transform(getX(startLandmark), getY(startLandmark));
          const endPt = transform(getX(endLandmark), getY(endLandmark));
          ctx.beginPath();
          ctx.moveTo(startPt.x, startPt.y);
          ctx.lineTo(endPt.x, endPt.y);
          ctx.stroke();
          drawnConnections++;
        }
      }
    });

    // Draw joints
    ctx.fillStyle = "#FFFFFF"; // White joints
    landmarks.forEach((landmark, idx) => {
      const lm = landmark as any;
      const vis = typeof lm?.visibility === "number" ? lm.visibility : 1.0;

      if (vis > 0.3) {
        // Highlight key joints
        // SMPL has 24 joints, but sometimes we get 29 (with feet/hands).
        // Treat anything with >= 24 joints as SMPL.
        const isSMPL = landmarks.length >= 24;
        let isImportant = false;

        if (isSMPL) {
          // SMPL: L/R Shoulders(16,17), Elbows(18,19), Hips(1,2), Knees(4,5), Ankles(7,8), Head(15)
          isImportant = [16, 17, 18, 19, 1, 2, 4, 5, 7, 8, 15].includes(idx);
        } else {
          // MediaPipe
          isImportant = [
            11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28,
          ].includes(idx);
        }

        const radius = isImportant ? 4 : 2;
        const point = transform(getX(landmark), getY(landmark));

        ctx.beginPath();
        ctx.arc(point.x, point.y, radius, 0, 2 * Math.PI);
        ctx.fill();
      }
    });
  }

  let canvas: HTMLCanvasElement;
  let ctx: CanvasRenderingContext2D | null = null;
  let imageObj: HTMLImageElement | null = null;

  // React to changes
  $: if (canvas && keyFrame) {
    ctx = canvas.getContext("2d");
    if (ctx) {
      if (imageUrl) {
        // Load image if provided
        const img = new Image();
        img.crossOrigin = "anonymous";
        img.onload = () => {
          imageObj = img;
          if (ctx) drawSkeleton(ctx, img);
        };
        img.src = imageUrl;
      } else {
        imageObj = null;
        drawSkeleton(ctx);
      }
    }
  }
</script>

<div class="skeleton-container">
  <h4 class="phase-label">
    {keyFrame.phase.charAt(0).toUpperCase() + keyFrame.phase.slice(1)}
  </h4>
  <canvas bind:this={canvas} {width} {height} class="skeleton-canvas"></canvas>
  <p class="frame-info">
    Frame {keyFrame.frame_index} ({keyFrame.timestamp_sec.toFixed(2)}s)
  </p>
</div>

<style>
  .skeleton-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.5rem;
    padding: 1rem;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    background: #fff;
  }

  .phase-label {
    margin: 0;
    font-size: 1rem;
    font-weight: 600;
    color: #333;
    text-transform: capitalize;
  }

  .skeleton-canvas {
    border: 1px solid #ddd;
    border-radius: 4px;
    background: #f9f9f9;
  }

  .frame-info {
    margin: 0;
    font-size: 0.85rem;
    color: #666;
  }
</style>

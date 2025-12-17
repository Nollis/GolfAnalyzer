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
    mhr_joints_2d?: number[][]; // MHR-70 2D joints from SAM-3D
    mhr_joints_3d?: number[][]; // MHR-70 3D joints from SAM-3D
  }

  export let keyFrame: KeyFrame;
  export let width: number = 400;
  export let height: number = 600;
  export let imageUrl: string | null = null;

  // MHR-70 connections (from overlay_mhr_skeleton.py - verified working)
  // MHR indices: 0-4=face, 5=L_shoulder, 6=R_shoulder, 7=L_elbow, 8=R_elbow,
  // 9=L_hip, 10=R_hip, 11=L_knee, 12=R_knee, 13=L_ankle, 14=R_ankle,
  // 41=R_wrist, 62=L_wrist
  const MHR_CONNECTIONS = [
    // Left leg
    [13, 11],
    [11, 9],
    // Right leg
    [14, 12],
    [12, 10],
    // Hip line
    [9, 10],
    // Torso
    [5, 9],
    [6, 10],
    // Shoulder line
    [5, 6],
    // Left arm
    [5, 7],
    [7, 62],
    // Right arm
    [6, 8],
    [8, 41],
    // Face/head
    [1, 2],
    [0, 1],
    [0, 2],
    [1, 3],
    [2, 4],
    // Head to shoulders
    [3, 5],
    [4, 6],
  ];

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

  // MediaPipe Pose connections (33 landmarks)
  const MEDIAPIPE_CONNECTIONS = [
    [11, 13],
    [13, 15],
    [12, 14],
    [14, 16],
    [11, 12],
    [23, 24],
    [11, 23],
    [12, 24],
    [23, 25],
    [24, 26],
    [25, 27],
    [26, 28],
    [27, 29],
    [28, 30],
    [5, 6],
    [6, 8],
    [5, 7],
  ];

  // COCO/YOLOv8 connections (17 keypoints)
  const COCO_CONNECTIONS = [
    [0, 1],
    [0, 2],
    [1, 3],
    [2, 4],
    [5, 6],
    [5, 7],
    [7, 9],
    [6, 8],
    [8, 10],
    [5, 11],
    [6, 12],
    [11, 12],
    [11, 13],
    [13, 15],
    [12, 14],
    [14, 16],
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

    // Prioritize data sources: MHR > SMPL > MediaPipe
    let landmarks = null;
    let isGlobalCoords = false;
    let isMHR = false;
    let connections = SMPL_CONNECTIONS;

    // First try MHR joints (most accurate from SAM-3D)
    if (keyFrame.mhr_joints_2d && keyFrame.mhr_joints_2d.length > 0) {
      landmarks = keyFrame.mhr_joints_2d;
      isGlobalCoords = true; // MHR outputs pixel coordinates
      isMHR = true;
      connections = MHR_CONNECTIONS;
    } else if (keyFrame.smpl_joints_2d && keyFrame.smpl_joints_2d.length > 0) {
      landmarks = keyFrame.smpl_joints_2d;
    } else if (
      keyFrame.smpl_joints_2d_orig &&
      keyFrame.smpl_joints_2d_orig.length > 0
    ) {
      landmarks = keyFrame.smpl_joints_2d_orig;
      isGlobalCoords = true;
    } else if (keyFrame.landmarks && keyFrame.landmarks.length > 0) {
      // Fallback to normalized/body landmarks (YOLO/MediaPipe)
      landmarks = keyFrame.landmarks;
      // Choose sensible connections based on landmark count
      if (landmarks.length >= 33) {
        connections = MEDIAPIPE_CONNECTIONS;
      } else if (landmarks.length >= 17) {
        connections = COCO_CONNECTIONS;
      } else {
        connections = MEDIAPIPE_CONNECTIONS;
      }
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
    // Use dynamic connections based on data source (MHR or SMPL)
    let drawnConnections = 0;
    connections.forEach(([start, end]) => {
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
    gap: 0.4rem;
    padding: 0.5rem 0;
  }

  .phase-label {
    margin: 0;
    font-size: 0.95rem;
    font-weight: 600;
    color: #475569; /* slate-600 */
    text-transform: capitalize;
  }
  :global(.dark) .phase-label {
    color: #e2e8f0; /* slate-200 */
  }

  .skeleton-canvas {
    border: 1px solid #e2e8f0; /* slate-200 */
    border-radius: 16px;
    background: #f8fafc; /* slate-50 */
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    overflow: hidden;
  }
  :global(.dark) .skeleton-canvas {
    border: none;
    background: #0f172a; /* slate-950 */
    box-shadow: 0 12px 30px rgba(0, 0, 0, 0.4);
  }

  .frame-info {
    margin: 0;
    font-size: 0.82rem;
    color: #64748b; /* slate-500 */
  }
  :global(.dark) .frame-info {
    color: #94a3b8; /* slate-400 */
  }
</style>

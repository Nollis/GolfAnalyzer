<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import * as THREE from "three";

  export let pose: any = null;
  export let imageUrl: string = "";

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

  let container: HTMLDivElement;
  let canvas: HTMLCanvasElement;
  let ctx: CanvasRenderingContext2D | null = null;
  let img: HTMLImageElement | null = null;

  onMount(() => {
    ctx = canvas.getContext("2d");
    draw();
  });

  onDestroy(() => {
    ctx = null;
    img = null;
  });

  $: if (pose || imageUrl) draw();

  function draw() {
    if (!ctx || !canvas) return;

    const w = container?.clientWidth || 400;
    const h = container?.clientHeight || 300;
    canvas.width = w;
    canvas.height = h;
    ctx.clearRect(0, 0, w, h);

    const render = () => {
      ctx!.clearRect(0, 0, w, h);

      let imgRect = { ox: 0, oy: 0, iw: w, ih: h, iwRaw: w, ihRaw: h };
      if (img && img.complete) {
        const scale = Math.min(w / img.width, h / img.height);
        const iw = img.width * scale;
        const ih = img.height * scale;
        const ox = (w - iw) / 2;
        const oy = (h - ih) / 2;
        ctx!.drawImage(img, ox, oy, iw, ih);
        imgRect = { ox, oy, iw, ih, iwRaw: img.width, ihRaw: img.height };
      }

      // Prioritize SMPL joints for consistency with the editor
      let landmarks = pose?.smpl_joints_2d || pose?.smpl_joints_2d_orig;

      // Fallback to MediaPipe landmarks if SMPL not available
      if (!landmarks || !landmarks.length) {
        landmarks = pose?.landmarks;
      }

      if (!landmarks || !landmarks.length) return;

      // Normalize landmarks to maintain aspect ratio
      // Logic adapted from SkeletonViewer
      const smplBbox = pose?.smpl_bbox;

      // Check if landmarks look like pixels (values > 1)
      // Handle both object {x,y} and array [x,y] formats
      const getX = (lm: any) =>
        typeof lm?.x === "number" ? lm.x : Array.isArray(lm) ? lm[0] : 0;
      const getY = (lm: any) =>
        typeof lm?.y === "number" ? lm.y : Array.isArray(lm) ? lm[1] : 0;

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

      if (smplBbox && smplBbox.length >= 4) {
        const bboxX = smplBbox[0];
        const bboxY = smplBbox[1];
        const bboxW = smplBbox[2] - bboxX;
        const bboxH = smplBbox[3] - bboxY;
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

      ctx!.strokeStyle = "#00FFFF"; // Cyan
      ctx!.lineWidth = 2;
      ctx!.lineCap = "round";
      ctx!.lineJoin = "round";
      ctx!.fillStyle = "#00FFFF";

      // Draw bones
      // Draw bones
      SMPL_CONNECTIONS.forEach(([a, b]) => {
        if (a < landmarks.length && b < landmarks.length) {
          const lmA = landmarks[a];
          const lmB = landmarks[b];
          // Check visibility if available
          const visA =
            typeof lmA?.visibility === "number" ? lmA.visibility : 1.0;
          const visB =
            typeof lmB?.visibility === "number" ? lmB.visibility : 1.0;

          if (visA > 0.3 && visB > 0.3) {
            const pa = transform(getX(lmA), getY(lmA));
            const pb = transform(getX(lmB), getY(lmB));
            ctx!.beginPath();
            ctx!.moveTo(pa.x, pa.y);
            ctx!.lineTo(pb.x, pb.y);
            ctx!.stroke();
          }
        }
      });

      // Draw joints
      ctx!.fillStyle = "#FFFFFF"; // White joints
      landmarks.forEach((lm: any, idx: number) => {
        const vis = typeof lm?.visibility === "number" ? lm.visibility : 1.0;
        if (vis > 0.3) {
          // Highlight key joints (SMPL indices for golf)
          // L/R Shoulders(16,17), Elbows(18,19), Hips(1,2), Knees(4,5), Ankles(7,8), Head(15)
          const isImportant = [16, 17, 18, 19, 1, 2, 4, 5, 7, 8, 15].includes(
            idx,
          );
          const radius = isImportant ? 4 : 2;
          const p = transform(getX(lm), getY(lm));
          ctx!.beginPath();
          ctx!.arc(p.x, p.y, radius, 0, Math.PI * 2);
          ctx!.fill();
        }
      });
    };

    if (imageUrl) {
      img = new Image();
      img.crossOrigin = "anonymous";
      img.onload = render;
      img.onerror = render;
      img.src = imageUrl;
    } else {
      render();
    }
  }
</script>

<div
  bind:this={container}
  class="relative w-full h-full bg-gray-900 border border-gray-700 rounded"
>
  <canvas bind:this={canvas} class="absolute inset-0"></canvas>
</div>

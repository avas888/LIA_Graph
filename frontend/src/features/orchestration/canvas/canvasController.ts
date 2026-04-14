import type { LayoutResult, LaneId } from "../graph/types";
import { palette } from "@/shared/ui/colors";

interface MinimapElements {
  viewport: HTMLElement;
  canvas: HTMLElement;
  minimapCanvas: HTMLCanvasElement;
  lens: HTMLElement;
}

/**
 * Initializes minimap rendering and sync with viewport scroll.
 */
export function initMinimap(els: MinimapElements, layout: LayoutResult): () => void {
  const { viewport, minimapCanvas, lens } = els;
  const ctx = minimapCanvas.getContext("2d");
  if (!ctx) return () => {};

  const mmW = minimapCanvas.width;
  const mmH = minimapCanvas.height;
  const scaleX = mmW / layout.canvasWidth;
  const scaleY = mmH / layout.canvasHeight;
  const scale = Math.min(scaleX, scaleY);

  function drawMinimap(): void {
    if (!ctx) return;
    ctx.clearRect(0, 0, mmW, mmH);

    // Background
    ctx.fillStyle = palette.neutral[50];
    ctx.fillRect(0, 0, mmW, mmH);

    // Lane backgrounds
    for (const [, rect] of layout.laneRects) {
      ctx.fillStyle = `${palette.green[100]}80`; // 50% opacity
      ctx.fillRect(rect.x * scale, rect.y * scale, rect.w * scale, rect.h * scale);
      ctx.strokeStyle = palette.neutral[300];
      ctx.lineWidth = 0.5;
      ctx.strokeRect(rect.x * scale, rect.y * scale, rect.w * scale, rect.h * scale);
    }

    // Nodes as small rects
    for (const [, rect] of layout.nodePositions) {
      ctx.fillStyle = palette.white;
      ctx.fillRect(rect.x * scale, rect.y * scale, rect.w * scale, rect.h * scale);
      ctx.strokeStyle = palette.neutral[400];
      ctx.lineWidth = 0.5;
      ctx.strokeRect(rect.x * scale, rect.y * scale, rect.w * scale, rect.h * scale);
    }
  }

  function updateLens(): void {
    const lensW = (viewport.clientWidth / layout.canvasWidth) * mmW;
    const lensH = (viewport.clientHeight / layout.canvasHeight) * mmH;
    const lensX = (viewport.scrollLeft / layout.canvasWidth) * mmW;
    const lensY = (viewport.scrollTop / layout.canvasHeight) * mmH;

    lens.style.width = `${Math.min(lensW, mmW)}px`;
    lens.style.height = `${Math.min(lensH, mmH)}px`;
    lens.style.left = `${lensX}px`;
    lens.style.top = `${lensY}px`;
  }

  drawMinimap();
  updateLens();

  // Scroll sync
  const onScroll = () => updateLens();
  viewport.addEventListener("scroll", onScroll, { passive: true });

  // Click minimap to scroll
  const onMinimapClick = (e: MouseEvent) => {
    const rect = minimapCanvas.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;

    const targetScrollLeft = (clickX / mmW) * layout.canvasWidth - viewport.clientWidth / 2;
    const targetScrollTop = (clickY / mmH) * layout.canvasHeight - viewport.clientHeight / 2;

    viewport.scrollTo({
      left: Math.max(0, targetScrollLeft),
      top: Math.max(0, targetScrollTop),
      behavior: "smooth",
    });
  };
  minimapCanvas.addEventListener("click", onMinimapClick);

  return () => {
    viewport.removeEventListener("scroll", onScroll);
    minimapCanvas.removeEventListener("click", onMinimapClick);
  };
}

/**
 * Smooth-scroll the viewport so the given lane is visible.
 */
export function scrollToLane(
  viewport: HTMLElement,
  layout: LayoutResult,
  laneId: LaneId,
): void {
  const rect = layout.laneRects.get(laneId);
  if (!rect) return;

  viewport.scrollTo({
    left: Math.max(0, rect.x - 40),
    top: Math.max(0, rect.y - 20),
    behavior: "smooth",
  });
}

/**
 * Keyboard navigation: arrow keys scroll the viewport.
 */
export function initKeyboardNav(viewport: HTMLElement): () => void {
  const STEP = 120;
  const onKeyDown = (e: KeyboardEvent) => {
    switch (e.key) {
      case "ArrowLeft":
        viewport.scrollBy({ left: -STEP, behavior: "smooth" });
        e.preventDefault();
        break;
      case "ArrowRight":
        viewport.scrollBy({ left: STEP, behavior: "smooth" });
        e.preventDefault();
        break;
      case "ArrowUp":
        viewport.scrollBy({ top: -STEP, behavior: "smooth" });
        e.preventDefault();
        break;
      case "ArrowDown":
        viewport.scrollBy({ top: STEP, behavior: "smooth" });
        e.preventDefault();
        break;
    }
  };
  document.addEventListener("keydown", onKeyDown);
  return () => document.removeEventListener("keydown", onKeyDown);
}

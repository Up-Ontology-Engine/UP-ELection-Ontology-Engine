"use client";

import { useEffect, useRef, useCallback } from "react";
import { hexToRgba } from "@/lib/colors";
import type { GraphNode, GraphEdge } from "@/lib/api";

interface Props {
  nodes: GraphNode[];
  edges: GraphEdge[];
  nodeColors: Record<string, string>;
  selectedId?: string;
  theme?: "dark" | "light";
  onSelect: (node: GraphNode) => void;
}

interface SimNode extends GraphNode {
  x: number; y: number; vx: number; vy: number;
}

interface State {
  nodes: SimNode[];
  edges: GraphEdge[];
  dragging: SimNode | null;
  draggingMoved: boolean;
  hoveredId: string | null;
  frame: number;
  // Simulation convergence — physics only runs while ticksLeft > 0
  ticksLeft: number;
  scale: number;
  panX: number;
  panY: number;
  isPanning: boolean;
  panStartX: number;
  panStartY: number;
}

const NODE_RADII: Record<string, number> = {
  AssemblyConstituency: 22,
  Booth:                14,
  Issue:                13,
  Candidate:            16,
  Party:                18,
  Scheme:               13,
  Narrative:            12,
  PulseEvent:           10,
  DataQuality:          10,
  SchemeGap:            11,
  ContradictionFlag:    12,
  TwinScenario:         12,
};

function getRadius(type: string): number {
  return NODE_RADII[type] ?? 13;
}

export default function GraphCanvas({ nodes, edges, nodeColors, selectedId, theme = "dark", onSelect }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const stateRef = useRef<State>({
    nodes: [], edges: [], dragging: null, draggingMoved: false,
    hoveredId: null, frame: 0, ticksLeft: 0,
    scale: 1, panX: 0, panY: 0,
    isPanning: false, panStartX: 0, panStartY: 0,
  });

  const getColor = useCallback((type: string) => nodeColors[type] ?? "#94a3b8", [nodeColors]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const state = stateRef.current;

    let w = canvas.width = canvas.offsetWidth;
    let h = canvas.height = canvas.offsetHeight;

    // Theme-aware colors (use rgba for reliable alpha handling)
    const isDark = theme === "dark";
    const bgColor      = isDark ? hexToRgba("#060b14", 1) : hexToRgba("#faf8f5", 1);
    const edgeColor    = isDark ? hexToRgba("#1e3050", 1) : hexToRgba("#dccfbb", 1);
    const edgeLabelBg  = isDark ? hexToRgba("#060b14", "d0") : hexToRgba("#faf8f5", "d0");
    const edgeLabelFg  = isDark ? hexToRgba("#3d5570", 1) : hexToRgba("#aa9f8d", 1);
    const nodeLabelFg  = isDark ? hexToRgba("#f0f4fa", 1) : hexToRgba("#1f1a14", 1);
    const typeTagFg    = isDark ? hexToRgba("#5a7899", 1) : hexToRgba("#7c7264", 1);
    const gridLine     = isDark ? "rgba(26,43,68,0.4)" : "rgba(180,140,90,0.10)";

    // Initialize sim nodes with random positions near center
    const simNodes: SimNode[] = nodes.map((n) => ({
      ...n,
      x: w / 2 + (Math.random() - 0.5) * Math.min(w, 400),
      y: h / 2 + (Math.random() - 0.5) * Math.min(h, 400),
      vx: 0, vy: 0,
    }));
    stateRef.current.nodes = simNodes;
    stateRef.current.edges = edges;
    stateRef.current.scale = 1;
    stateRef.current.panX = 0;
    stateRef.current.panY = 0;
    // Short live-tick budget; the bulk of layout is pre-settled before first paint (below).
    stateRef.current.ticksLeft = Math.min(160, 60 + nodes.length);

    const idxMap = new Map(simNodes.map((n, i) => [n.id, i]));

    // ── Simulation ─────────────────────────────────────────────
    const springLen = 100;
    const repulsionK = 4000;
    const springK = 0.04;
    const gravityK = 0.018;
    const damping = 0.86;

    function tick() {
      const ns = stateRef.current.nodes;
      const es = stateRef.current.edges;

      // Repulsion between all node pairs
      for (let i = 0; i < ns.length; i++) {
        for (let j = i + 1; j < ns.length; j++) {
          const dx = ns[j].x - ns[i].x;
          const dy = ns[j].y - ns[i].y;
          const dist2 = dx * dx + dy * dy || 1;
          const dist = Math.sqrt(dist2);
          const force = repulsionK / dist2;
          const fx = force * dx / dist;
          const fy = force * dy / dist;
          ns[i].vx -= fx; ns[i].vy -= fy;
          ns[j].vx += fx; ns[j].vy += fy;
        }
      }

      // Spring forces along edges
      for (const e of es) {
        const si = idxMap.get(e.source);
        const ti = idxMap.get(e.target);
        if (si == null || ti == null) continue;
        const dx = ns[ti].x - ns[si].x;
        const dy = ns[ti].y - ns[si].y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const stretch = dist - springLen;
        const fx = springK * stretch * dx / dist;
        const fy = springK * stretch * dy / dist;
        ns[si].vx += fx; ns[si].vy += fy;
        ns[ti].vx -= fx; ns[ti].vy -= fy;
      }

      // Gravity toward center + damping + integrate
      for (const n of ns) {
        if (n === stateRef.current.dragging) { n.vx = 0; n.vy = 0; continue; }
        n.vx += (w / 2 - n.x) * gravityK;
        n.vy += (h / 2 - n.y) * gravityK;
        n.vx *= damping; n.vy *= damping;
        n.x += n.vx; n.y += n.vy;
        n.x = Math.max(30, Math.min(w - 30, n.x));
        n.y = Math.max(30, Math.min(h - 30, n.y));
      }
    }

    // ── Helpers ────────────────────────────────────────────────
    function screenToWorld(sx: number, sy: number) {
      const { scale, panX, panY } = stateRef.current;
      return { x: (sx - panX) / scale, y: (sy - panY) / scale };
    }

    function findNode(wx: number, wy: number): SimNode | null {
      for (const n of [...stateRef.current.nodes].reverse()) {
        const dx = n.x - wx, dy = n.y - wy;
        if (Math.sqrt(dx * dx + dy * dy) < getRadius(n.type) + 4) return n;
      }
      return null;
    }

    // ── Draw ───────────────────────────────────────────────────
    function drawGrid(ctx: CanvasRenderingContext2D) {
      const { scale, panX, panY } = stateRef.current;
      const gridSize = 32 * scale;
      const startX = panX % gridSize;
      const startY = panY % gridSize;
      ctx.strokeStyle = gridLine;
      ctx.lineWidth = 0.5;
      ctx.beginPath();
      for (let x = startX; x < w; x += gridSize) {
        ctx.moveTo(x, 0); ctx.lineTo(x, h);
      }
      for (let y = startY; y < h; y += gridSize) {
        ctx.moveTo(0, y); ctx.lineTo(w, y);
      }
      ctx.stroke();
    }

    function drawEdge(
      ctx: CanvasRenderingContext2D,
      s: SimNode, t: SimNode,
      edgeType: string,
      isHighlighted: boolean,
      scale: number
    ) {
      const dx = t.x - s.x, dy = t.y - s.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 1;
      const ux = dx / dist, uy = dy / dist;
      const sr = getRadius(s.type), tr = getRadius(t.type);
      if (dist < sr + tr + 2) return;

      const x1 = s.x + ux * sr, y1 = s.y + uy * sr;
      const x2 = t.x - ux * tr, y2 = t.y - uy * tr;

      const color = isHighlighted ? hexToRgba("#f97316", "80") : edgeColor;
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.strokeStyle = color;
      ctx.lineWidth = (isHighlighted ? 1.5 : 1) / scale;
      ctx.stroke();

      // Arrowhead
      const headLen = 7 / scale;
      const angle = Math.atan2(dy, dx);
      ctx.beginPath();
      ctx.moveTo(x2, y2);
      ctx.lineTo(x2 - headLen * Math.cos(angle - Math.PI / 6), y2 - headLen * Math.sin(angle - Math.PI / 6));
      ctx.lineTo(x2 - headLen * Math.cos(angle + Math.PI / 6), y2 - headLen * Math.sin(angle + Math.PI / 6));
      ctx.closePath();
      ctx.fillStyle = color;
      ctx.fill();

      // Edge label (only when zoomed in enough)
      if (scale > 0.65 && edgeType) {
        const mx = (x1 + x2) / 2, my = (y1 + y2) / 2;
        const fontSize = Math.max(7, 8 / scale);
          ctx.font = `${fontSize}px monospace`;
          const tw = ctx.measureText(edgeType).width;
          ctx.fillStyle = edgeLabelBg;
          ctx.fillRect(mx - tw / 2 - 2, my - fontSize, tw + 4, fontSize + 2);
          ctx.fillStyle = edgeLabelFg;
          ctx.textAlign = "center";
          ctx.fillText(edgeType, mx, my);
      }
    }

    function draw() {
      const ctx = canvas!.getContext("2d")!;
      const { nodes: ns, edges: es, hoveredId, scale, panX, panY } = stateRef.current;

      ctx.clearRect(0, 0, w, h);
      ctx.fillStyle = bgColor;
      ctx.fillRect(0, 0, w, h);
      drawGrid(ctx);

      ctx.save();
      ctx.translate(panX, panY);
      ctx.scale(scale, scale);

      // Edges
      for (const e of es) {
        const si = idxMap.get(e.source), ti = idxMap.get(e.target);
        if (si == null || ti == null) continue;
        const s = ns[si], t = ns[ti];
        const isHighlighted = s.id === hoveredId || t.id === hoveredId || s.id === selectedId || t.id === selectedId;
        drawEdge(ctx, s, t, e.type, isHighlighted, scale);
      }

      // Nodes
      for (const n of ns) {
        const r = getRadius(n.type);
        const color = getColor(n.type);
        const isHovered = n.id === hoveredId;
        const isSel = n.id === selectedId;

        // Outer glow ring for selected
        if (isSel) {
          ctx.beginPath();
          ctx.arc(n.x, n.y, r + 7, 0, Math.PI * 2);
          ctx.fillStyle = hexToRgba(color, "25");
          ctx.fill();
          ctx.beginPath();
          ctx.arc(n.x, n.y, r + 4, 0, Math.PI * 2);
          ctx.strokeStyle = hexToRgba(color, "70");
          ctx.lineWidth = 1.5 / scale;
          ctx.stroke();
        }

        // Node fill
        ctx.beginPath();
        ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
        ctx.fillStyle = isHovered ? hexToRgba(color, "50") : hexToRgba(color, "28");
        ctx.fill();

        // Node border
        ctx.strokeStyle = isHovered ? hexToRgba(color, 1) : (isSel ? hexToRgba(color, 1) : hexToRgba(color, "cc"));
        ctx.lineWidth = (isSel ? 2.5 : isHovered ? 2 : 1.5) / scale;
        ctx.stroke();

        // Node label
        const labelSize = Math.max(8, Math.min(11, 10 / scale));
        ctx.font = `bold ${labelSize}px sans-serif`;
        ctx.fillStyle = nodeLabelFg;
        ctx.textAlign = "center";
        const maxChars = Math.max(6, Math.floor(r * 1.4));
        const lbl = n.label.length > maxChars ? n.label.slice(0, maxChars - 1) + "…" : n.label;
        ctx.fillText(lbl, n.x, n.y + labelSize * 0.35);

        // Type tag below node (only when not too zoomed out)
        if (scale > 0.4) {
          const typeSize = Math.max(7, Math.min(9, 8 / scale));
          ctx.font = `${typeSize}px sans-serif`;
          ctx.fillStyle = typeTagFg;
          ctx.fillText(n.type, n.x, n.y + r + typeSize + 2);
        }
      }

      ctx.restore();
    }

    function loop() {
      const s = stateRef.current;
      if (s.ticksLeft > 0 || s.dragging) {
        tick();
        if (s.ticksLeft > 0) s.ticksLeft--;
        // Freeze once the layout is essentially at rest — kills lingering drift/jitter.
        if (!s.dragging) {
          let ke = 0;
          for (const n of s.nodes) ke += n.vx * n.vx + n.vy * n.vy;
          if (ke / (s.nodes.length || 1) < 0.05) s.ticksLeft = 0;
        }
      }
      draw();
      s.frame = requestAnimationFrame(loop);
    }

    // Pre-settle the layout off-screen so nodes appear already placed
    // instead of visibly flying in and oscillating.
    for (let i = 0; i < 150; i++) tick();
    for (const n of stateRef.current.nodes) { n.vx = 0; n.vy = 0; }

    stateRef.current.frame = requestAnimationFrame(loop);

    // ── Event handlers ─────────────────────────────────────────
    function onMouseDown(e: MouseEvent) {
      const rect = canvas!.getBoundingClientRect();
      const sx = e.clientX - rect.left, sy = e.clientY - rect.top;
      const wp = screenToWorld(sx, sy);
      const hit = findNode(wp.x, wp.y);

      if (hit) {
        stateRef.current.dragging = hit;
        stateRef.current.draggingMoved = false;
        // Re-heat the simulation briefly so neighbors react to the drag
        stateRef.current.ticksLeft = Math.max(stateRef.current.ticksLeft, 80);
        canvas!.style.cursor = "grabbing";
      } else {
        stateRef.current.isPanning = true;
        stateRef.current.panStartX = sx - stateRef.current.panX;
        stateRef.current.panStartY = sy - stateRef.current.panY;
        canvas!.style.cursor = "grabbing";
      }
    }

    function onMouseMove(e: MouseEvent) {
      const rect = canvas!.getBoundingClientRect();
      const sx = e.clientX - rect.left, sy = e.clientY - rect.top;

      if (stateRef.current.dragging) {
        const wp = screenToWorld(sx, sy);
        stateRef.current.dragging.x = wp.x;
        stateRef.current.dragging.y = wp.y;
        stateRef.current.dragging.vx = 0;
        stateRef.current.dragging.vy = 0;
        stateRef.current.draggingMoved = true;
        return;
      }
      if (stateRef.current.isPanning) {
        stateRef.current.panX = sx - stateRef.current.panStartX;
        stateRef.current.panY = sy - stateRef.current.panStartY;
        return;
      }

      // Hover detection
      const wp = screenToWorld(sx, sy);
      const hit = findNode(wp.x, wp.y);
      stateRef.current.hoveredId = hit?.id ?? null;
      canvas!.style.cursor = hit ? "pointer" : "grab";
    }

    function onMouseUp(e: MouseEvent) {
      const rect = canvas!.getBoundingClientRect();
      const sx = e.clientX - rect.left, sy = e.clientY - rect.top;
      const wp = screenToWorld(sx, sy);

      if (stateRef.current.dragging) {
        const n = stateRef.current.dragging;
        stateRef.current.dragging = null;
        if (!stateRef.current.draggingMoved) {
          // It was a click, not a drag
          onSelect(n);
        }
      } else if (stateRef.current.isPanning) {
        stateRef.current.isPanning = false;
        const hit = findNode(wp.x, wp.y);
        canvas!.style.cursor = hit ? "pointer" : "grab";
      }
      stateRef.current.draggingMoved = false;
    }

    function onMouseLeave() {
      stateRef.current.hoveredId = null;
      stateRef.current.dragging = null;
      stateRef.current.isPanning = false;
      canvas!.style.cursor = "grab";
    }

    function onWheel(e: WheelEvent) {
      e.preventDefault();
      const rect = canvas!.getBoundingClientRect();
      const sx = e.clientX - rect.left, sy = e.clientY - rect.top;
      const delta = e.deltaY < 0 ? 1.1 : 0.91;
      const newScale = Math.max(0.2, Math.min(4, stateRef.current.scale * delta));

      // Zoom toward cursor position
      const worldX = (sx - stateRef.current.panX) / stateRef.current.scale;
      const worldY = (sy - stateRef.current.panY) / stateRef.current.scale;
      stateRef.current.panX = sx - worldX * newScale;
      stateRef.current.panY = sy - worldY * newScale;
      stateRef.current.scale = newScale;
    }

    canvas.addEventListener("mousedown", onMouseDown);
    canvas.addEventListener("mousemove", onMouseMove);
    canvas.addEventListener("mouseup", onMouseUp);
    canvas.addEventListener("mouseleave", onMouseLeave);
    canvas.addEventListener("wheel", onWheel, { passive: false });

    const ro = new ResizeObserver(() => {
      w = canvas.width = canvas.offsetWidth;
      h = canvas.height = canvas.offsetHeight;
    });
    ro.observe(canvas);

    return () => {
      cancelAnimationFrame(state.frame);
      canvas.removeEventListener("mousedown", onMouseDown);
      canvas.removeEventListener("mousemove", onMouseMove);
      canvas.removeEventListener("mouseup", onMouseUp);
      canvas.removeEventListener("mouseleave", onMouseLeave);
      canvas.removeEventListener("wheel", onWheel);
      ro.disconnect();
    };
  }, [nodes, edges, getColor, onSelect, theme, selectedId]);

  return (
    <canvas
      ref={canvasRef}
      className="w-full h-full"
      style={{ display: "block", cursor: "grab" }}
    />
  );
}

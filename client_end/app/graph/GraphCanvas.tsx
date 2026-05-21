"use client";

import { useEffect, useRef, useCallback } from "react";
import type { GraphNode, GraphEdge } from "@/lib/api";

interface Props {
  nodes: GraphNode[];
  edges: GraphEdge[];
  nodeColors: Record<string, string>;
  onSelect: (node: GraphNode) => void;
}

interface SimNode extends GraphNode {
  x: number; y: number; vx: number; vy: number;
}

export default function GraphCanvas({ nodes, edges, nodeColors, onSelect }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const stateRef = useRef<{ nodes: SimNode[]; edges: GraphEdge[]; dragging: SimNode | null; frame: number }>({
    nodes: [], edges: [], dragging: null, frame: 0
  });

  const getColor = useCallback((type: string) => nodeColors[type] ?? "#94a3b8", [nodeColors]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const w = canvas.width = canvas.offsetWidth;
    const h = canvas.height = canvas.offsetHeight;

    // Initialize sim nodes
    const simNodes: SimNode[] = nodes.map((n, i) => ({
      ...n,
      x: w / 2 + (Math.random() - 0.5) * 300,
      y: h / 2 + (Math.random() - 0.5) * 300,
      vx: 0, vy: 0,
    }));
    stateRef.current.nodes = simNodes;
    stateRef.current.edges = edges;

    const idxMap = new Map(simNodes.map((n, i) => [n.id, i]));

    function tick() {
      const ns = stateRef.current.nodes;
      const es = stateRef.current.edges;
      const k = 80; // spring length
      const repulsion = 3000;
      const damping = 0.85;
      const gravity = 0.02;

      // Repulsion
      for (let i = 0; i < ns.length; i++) {
        for (let j = i + 1; j < ns.length; j++) {
          const dx = ns[j].x - ns[i].x;
          const dy = ns[j].y - ns[i].y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const force = repulsion / (dist * dist);
          ns[i].vx -= force * dx / dist;
          ns[i].vy -= force * dy / dist;
          ns[j].vx += force * dx / dist;
          ns[j].vy += force * dy / dist;
        }
      }

      // Spring (edges)
      for (const e of es) {
        const si = idxMap.get(e.source);
        const ti = idxMap.get(e.target);
        if (si == null || ti == null) continue;
        const dx = ns[ti].x - ns[si].x;
        const dy = ns[ti].y - ns[si].y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = (dist - k) * 0.05;
        const fx = force * dx / dist;
        const fy = force * dy / dist;
        ns[si].vx += fx; ns[si].vy += fy;
        ns[ti].vx -= fx; ns[ti].vy -= fy;
      }

      // Gravity to center
      for (const n of ns) {
        if (n === stateRef.current.dragging) { n.vx = 0; n.vy = 0; continue; }
        n.vx += (w / 2 - n.x) * gravity;
        n.vy += (h / 2 - n.y) * gravity;
        n.vx *= damping; n.vy *= damping;
        n.x += n.vx; n.y += n.vy;
        // Boundary
        n.x = Math.max(20, Math.min(w - 20, n.x));
        n.y = Math.max(20, Math.min(h - 20, n.y));
      }
    }

    function draw() {
      const ctx = canvas!.getContext("2d")!;
      ctx.clearRect(0, 0, w, h);
      ctx.fillStyle = "#0a0e1a";
      ctx.fillRect(0, 0, w, h);

      const ns = stateRef.current.nodes;
      const es = stateRef.current.edges;

      // Edges
      for (const e of es) {
        const si = idxMap.get(e.source);
        const ti = idxMap.get(e.target);
        if (si == null || ti == null) continue;
        const s = ns[si]; const t = ns[ti];
        ctx.beginPath();
        ctx.moveTo(s.x, s.y); ctx.lineTo(t.x, t.y);
        ctx.strokeStyle = "#1e2d45";
        ctx.lineWidth = 1;
        ctx.stroke();

        // Edge label
        const mx = (s.x + t.x) / 2; const my = (s.y + t.y) / 2;
        ctx.fillStyle = "#475569";
        ctx.font = "9px monospace";
        ctx.textAlign = "center";
        ctx.fillText(e.type, mx, my - 3);
      }

      // Nodes
      for (const n of ns) {
        const color = getColor(n.type);
        const r = 14;
        ctx.beginPath();
        ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
        ctx.fillStyle = color + "33";
        ctx.fill();
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.stroke();

        ctx.fillStyle = "#f1f5f9";
        ctx.font = "bold 10px sans-serif";
        ctx.textAlign = "center";
        const label = n.label.length > 12 ? n.label.slice(0, 10) + "…" : n.label;
        ctx.fillText(label, n.x, n.y + 3);

        ctx.fillStyle = "#94a3b8";
        ctx.font = "8px sans-serif";
        ctx.fillText(n.type, n.x, n.y + r + 10);
      }
    }

    function loop() {
      tick(); draw();
      stateRef.current.frame = requestAnimationFrame(loop);
    }
    stateRef.current.frame = requestAnimationFrame(loop);

    // Mouse handlers
    let mx = 0, my = 0;
    function mousedown(e: MouseEvent) {
      const rect = canvas!.getBoundingClientRect();
      mx = e.clientX - rect.left; my = e.clientY - rect.top;
      for (const n of stateRef.current.nodes) {
        const dx = n.x - mx; const dy = n.y - my;
        if (Math.sqrt(dx * dx + dy * dy) < 16) { stateRef.current.dragging = n; return; }
      }
    }
    function mousemove(e: MouseEvent) {
      if (!stateRef.current.dragging) return;
      const rect = canvas!.getBoundingClientRect();
      stateRef.current.dragging.x = e.clientX - rect.left;
      stateRef.current.dragging.y = e.clientY - rect.top;
    }
    function mouseup(e: MouseEvent) {
      const rect = canvas!.getBoundingClientRect();
      const cx = e.clientX - rect.left; const cy = e.clientY - rect.top;
      const wasDragging = stateRef.current.dragging;
      stateRef.current.dragging = null;
      if (wasDragging) {
        const dx = wasDragging.x - cx; const dy = wasDragging.y - cy;
        if (Math.sqrt(dx * dx + dy * dy) < 5) onSelect(wasDragging);
        return;
      }
      // Click without drag
      for (const n of stateRef.current.nodes) {
        const dx = n.x - cx; const dy = n.y - cy;
        if (Math.sqrt(dx * dx + dy * dy) < 16) { onSelect(n); return; }
      }
    }

    canvas.addEventListener("mousedown", mousedown);
    canvas.addEventListener("mousemove", mousemove);
    canvas.addEventListener("mouseup", mouseup);

    const ro = new ResizeObserver(() => {
      canvas.width = canvas.offsetWidth;
      canvas.height = canvas.offsetHeight;
    });
    ro.observe(canvas);

    return () => {
      cancelAnimationFrame(stateRef.current.frame);
      canvas.removeEventListener("mousedown", mousedown);
      canvas.removeEventListener("mousemove", mousemove);
      canvas.removeEventListener("mouseup", mouseup);
      ro.disconnect();
    };
  }, [nodes, edges, getColor, onSelect]);

  return (
    <canvas
      ref={canvasRef}
      className="w-full h-full cursor-grab active:cursor-grabbing"
      style={{ display: "block" }}
    />
  );
}

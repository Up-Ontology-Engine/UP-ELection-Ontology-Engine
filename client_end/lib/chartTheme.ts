"use client";

import { useTheme } from "@/components/ThemeProvider";

export function useChartColors() {
  const { theme } = useTheme();
  const d = theme !== "light";
  return {
    // SVG attributes (can't use CSS custom properties here)
    t1:     d ? "#f0f4fa" : "#0f1f35",
    t2:     d ? "#8ba0bc" : "#2d4a6a",
    t3:     d ? "#4d6480" : "#5a7899",
    t4:     d ? "#2e4260" : "#8aabcc",
    border: d ? "#1a2b44" : "#cbd8ea",
    bgCard: d ? "#0f1929" : "#ffffff",
    bgSurf: d ? "#0b1220" : "#edf1f7",
    cursor: d ? "rgba(255,255,255,0.03)" : "rgba(0,0,0,0.04)",
  };
}

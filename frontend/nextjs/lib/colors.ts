export function hexToRgba(hex: string, alpha: number | string) {
  // Normalize hex
  let h = String(hex || "#000").trim();
  if (!h.startsWith("#")) h = "#" + h;
  if (h.length === 4) {
    // expand short form #rgb
    h = "#" + h[1] + h[1] + h[2] + h[2] + h[3] + h[3];
  }

  // alpha may be a number 0-1, or a 2-digit hex string like '18'
  let a = 1;
  if (typeof alpha === "number") {
    a = Math.max(0, Math.min(1, alpha));
  } else if (typeof alpha === "string") {
    const s = alpha.trim();
    if (/^[0-9a-fA-F]{2}$/.test(s)) {
      a = parseInt(s, 16) / 255;
    } else {
      const n = parseFloat(s);
      if (!Number.isNaN(n)) a = Math.max(0, Math.min(1, n));
    }
  }

  const r = parseInt(h.slice(1, 3), 16);
  const g = parseInt(h.slice(3, 5), 16);
  const b = parseInt(h.slice(5, 7), 16);
  return `rgba(${r}, ${g}, ${b}, ${a})`;
}

export default hexToRgba;

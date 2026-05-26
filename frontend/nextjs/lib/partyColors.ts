/**
 * Political party brand colors — authoritative map for all frontend components.
 *
 * Prefer CSS variable references (`var(--color-bjp-saffron)`) in Tailwind /
 * inline styles; use this map when you need to compute JS-side colors
 * (e.g., Recharts / Canvas / SVG fills).
 *
 * Keep in sync with globals.css :root custom properties.
 */

export const PARTY_COLORS: Record<string, string> = {
  BJP:     "#FF9933",   // --color-bjp-saffron
  SP:      "#228B22",   // --color-sp-green
  BSP:     "#1A6FD8",   // --color-bsp-blue
  INC:     "#1351A8",   // --color-inc-blue
  AAP:     "#0066CC",   // --color-aap-blue
  RLD:     "#2E8B57",   // --color-rld-green
  NISHAD:  "#9333ea",   // purple
  SBSP:    "#ea580c",   // dark orange
  AIMIM:   "#16a34a",   // forest green
  IND:     "#6B7280",   // --color-ind-gray
  OTHER:   "#6B7280",
};

/** Returns the brand color for a party abbreviation, falling back to neutral gray. */
export function partyColor(partyId: string | null | undefined): string {
  if (!partyId) return PARTY_COLORS.OTHER;
  const key = partyId.trim().toUpperCase();
  return PARTY_COLORS[key] ?? PARTY_COLORS.OTHER;
}

/** Party display names for UI labels. */
export const PARTY_NAMES: Record<string, string> = {
  BJP:    "Bharatiya Janata Party",
  SP:     "Samajwadi Party",
  BSP:    "Bahujan Samaj Party",
  INC:    "Indian National Congress",
  AAP:    "Aam Aadmi Party",
  RLD:    "Rashtriya Lok Dal",
  NISHAD: "Nishad Party",
  SBSP:   "Suheldev Bharatiya Samaj Party",
  AIMIM:  "All India Majlis-e-Ittehadul Muslimeen",
  IND:    "Independent",
};

/** Confidence label → CSS variable token. */
export const CONFIDENCE_COLORS = {
  HIGH:   "var(--color-high-conf)",
  MEDIUM: "var(--color-med-conf)",
  LOW:    "var(--color-low-conf)",
} as const;

/** Polarity value → CSS variable token. */
export function polarityColor(polarity: number | null | undefined): string {
  if (polarity == null) return "var(--color-neutral)";
  if (polarity > 0)     return "var(--color-positive)";
  if (polarity < 0)     return "var(--color-negative)";
  return "var(--color-neutral)";
}

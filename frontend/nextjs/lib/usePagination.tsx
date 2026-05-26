"use client";

/**
 * usePagination — generic server-side pagination hook.
 *
 * Handles page state, API fetching with page/limit params,
 * loading states, and error handling.
 *
 * Usage:
 *   const { data, page, totalPages, goTo, next, prev, isLoading, error } =
 *     usePagination<Booth>("/api/ac/GKP_322/booths", { pageSize: 50 });
 */

import { useState, useEffect, useCallback, useRef } from "react";

interface PaginationOptions {
  pageSize?:      number;   // rows per page (default: 50)
  initialPage?:  number;   // 1-indexed (default: 1)
  params?:       Record<string, string | number | boolean>;  // extra query params
}

interface PaginatedResult<T> {
  data:        T[];
  page:        number;
  totalPages:  number;
  totalItems:  number;
  pageSize:    number;
  isLoading:   boolean;
  error:       string | null;
  goTo:        (p: number) => void;
  next:        () => void;
  prev:        () => void;
  refresh:     () => void;
  hasNext:     boolean;
  hasPrev:     boolean;
}

export function usePagination<T>(
  endpoint: string,
  options: PaginationOptions = {},
): PaginatedResult<T> {
  const { pageSize = 50, initialPage = 1, params = {} } = options;

  const [page,       setPage]       = useState(initialPage);
  const [data,       setData]       = useState<T[]>([]);
  const [totalItems, setTotalItems] = useState(0);
  const [isLoading,  setIsLoading]  = useState(false);
  const [error,      setError]      = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const fetch_ = useCallback(
    async (targetPage: number) => {
      // Cancel previous in-flight request
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      setIsLoading(true);
      setError(null);

      const qs = new URLSearchParams({
        page:  String(targetPage),
        limit: String(pageSize),
        ...Object.fromEntries(
          Object.entries(params).map(([k, v]) => [k, String(v)])
        ),
      });

      try {
        const res = await globalThis.fetch(`${endpoint}?${qs}`, {
          signal: controller.signal,
        });

        if (!res.ok) {
          throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        }

        const json = await res.json();

        // Support two common API response shapes:
        //   { items: T[], total: number }   ← preferred
        //   T[]  (array + X-Total-Count header)
        if (Array.isArray(json)) {
          setData(json as T[]);
          const total = Number(res.headers.get("X-Total-Count") ?? json.length);
          setTotalItems(total);
        } else {
          setData((json.items ?? json.data ?? json.results ?? []) as T[]);
          setTotalItems(json.total ?? json.count ?? json.total_count ?? 0);
        }
      } catch (err: unknown) {
        if ((err as Error).name === "AbortError") return;   // unmounted / cancelled
        setError((err as Error).message ?? "Failed to load data");
        setData([]);
      } finally {
        setIsLoading(false);
      }
    },
    [endpoint, pageSize, params],
  );

  // Fetch when page or fetch_ changes
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetch_(page);
    return () => abortRef.current?.abort();
  }, [fetch_, page]);

  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));

  const goTo    = useCallback((p: number) => setPage(Math.max(1, Math.min(p, totalPages))), [totalPages]);
  const next    = useCallback(() => setPage((p) => Math.min(p + 1, totalPages)), [totalPages]);
  const prev    = useCallback(() => setPage((p) => Math.max(p - 1, 1)), []);
  const refresh = useCallback(() => fetch_(page), [fetch_, page]);

  return {
    data,
    page,
    totalPages,
    totalItems,
    pageSize,
    isLoading,
    error,
    goTo,
    next,
    prev,
    refresh,
    hasNext: page < totalPages,
    hasPrev: page > 1,
  };
}


/**
 * PaginationControls — ready-to-use pagination UI component.
 *
 * Usage:
 *   <PaginationControls page={page} totalPages={totalPages}
 *     onGoTo={goTo} onNext={next} onPrev={prev} />
 */

interface ControlProps {
  page:       number;
  totalPages: number;
  totalItems?: number;
  pageSize?:  number;
  onGoTo:     (p: number) => void;
  onNext:     () => void;
  onPrev:     () => void;
  isLoading?: boolean;
}

export function PaginationControls({
  page, totalPages, totalItems, pageSize,
  onGoTo, onNext, onPrev, isLoading,
}: ControlProps) {
  const btnStyle = (disabled: boolean): React.CSSProperties => ({
    padding:       "4px 12px",
    fontSize:      "11px",
    fontWeight:    600,
    background:    disabled ? "transparent" : "var(--bg-surface, #1e293b)",
    border:        "1px solid var(--border, #334155)",
    borderRadius:  "2px",
    color:         disabled ? "var(--text-4, #475569)" : "var(--text-2, #cbd5e1)",
    cursor:        disabled ? "not-allowed" : "pointer",
    letterSpacing: "0.04em",
    opacity:       disabled ? 0.4 : 1,
  });

  if (totalPages <= 1) return null;

  const start = totalItems && pageSize ? (page - 1) * pageSize + 1 : null;
  const end   = totalItems && pageSize ? Math.min(page * pageSize, totalItems) : null;

  return (
    <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
      <button style={btnStyle(page <= 1)} onClick={onPrev} disabled={page <= 1 || isLoading}>
        ← PREV
      </button>

      {/* Page number pills — show ±2 pages around current */}
      {Array.from({ length: totalPages }, (_, i) => i + 1)
        .filter((p) => Math.abs(p - page) <= 2 || p === 1 || p === totalPages)
        .map((p, idx, arr) => {
          const gap = idx > 0 && p - arr[idx - 1] > 1;
          return (
            <span key={p} style={{ display: "flex", alignItems: "center", gap: "4px" }}>
              {gap && <span style={{ color: "var(--text-4)", fontSize: "11px" }}>…</span>}
              <button
                style={{
                  ...btnStyle(false),
                  background:  p === page ? "var(--saffron-subtle, rgba(249,115,22,0.1))" : "transparent",
                  color:       p === page ? "var(--saffron, #f97316)" : "var(--text-3, #94a3b8)",
                  borderColor: p === page ? "var(--saffron, #f97316)" : "var(--border)",
                }}
                onClick={() => onGoTo(p)}
                disabled={isLoading}
              >
                {p}
              </button>
            </span>
          );
        })}

      <button style={btnStyle(page >= totalPages)} onClick={onNext} disabled={page >= totalPages || isLoading}>
        NEXT →
      </button>

      {start && end && totalItems && (
        <span style={{ fontSize: "11px", color: "var(--text-4)", marginLeft: "4px" }}>
          {start}–{end} of {totalItems.toLocaleString("en-IN")}
        </span>
      )}
    </div>
  );
}

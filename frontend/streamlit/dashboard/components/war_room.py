"""
Shared war-room theme helpers: CSS injection, HTML card builders, plotly defaults.
"""
from __future__ import annotations
import streamlit as st


# ── CSS ───────────────────────────────────────────────────────────────────────

_CSS = """
<style>
/* ── App shell ────────────────────────────────────────── */
.stApp { background-color: #0a0e1a; }
[data-testid="stSidebar"] { background-color: #070b14; border-right: 1px solid #1e2d4a; }

/* ── Sidebar logo strip ───────────────────────────────── */
.wr-sidebar-brand {
  background: linear-gradient(90deg,#FF6B35 0%,#c0390a 100%);
  color: #fff; font-family: monospace; font-weight: 700;
  letter-spacing: .12em; text-transform: uppercase;
  padding: 10px 14px; border-radius: 6px; margin-bottom: 8px;
  font-size: .85em;
}

/* ── Section headers ──────────────────────────────────── */
.wr-section {
  border-left: 3px solid #FF6B35; padding-left: 12px;
  font-family: monospace; font-size: .82em; font-weight: 700;
  text-transform: uppercase; letter-spacing: .12em;
  color: #FF6B35; margin: 18px 0 10px;
}

/* ── Intel card ───────────────────────────────────────── */
.wr-card {
  background: #0f1729; border: 1px solid #1e2d4a;
  border-radius: 8px; padding: 14px 16px; margin-bottom: 10px;
}
.wr-card-accent { border-left: 4px solid var(--ac,#FF6B35); }

/* ── Status badges ────────────────────────────────────── */
.badge {
  display:inline-block; padding:2px 9px; border-radius:12px;
  font-size:.78em; font-weight:700; letter-spacing:.06em; margin-right:4px;
}
.badge-high    { background:#e74c3c33; color:#e74c3c; border:1px solid #e74c3c; }
.badge-medium  { background:#f39c1233; color:#f39c12; border:1px solid #f39c12; }
.badge-low     { background:#2ecc7133; color:#2ecc71; border:1px solid #2ecc71; }
.badge-unknown { background:#95a5a633; color:#95a5a6; border:1px solid #95a5a6; }

/* ── Trend arrows ─────────────────────────────────────── */
.trend-up   { color:#e74c3c; font-weight:700; }
.trend-down { color:#2ecc71; font-weight:700; }

/* ── War-room metric ──────────────────────────────────── */
.wr-metric-label { font-size:.72em; text-transform:uppercase; letter-spacing:.1em; color:#8b949e; }
.wr-metric-value { font-size:1.9em; font-weight:700; line-height:1.1; color:#e6edf3; }
.wr-metric-delta { font-size:.8em; margin-top:2px; }

/* ── Risk row ─────────────────────────────────────────── */
.risk-row {
  background:#0f1729; border:1px solid #1e2d4a; border-radius:6px;
  padding:10px 14px; margin-bottom:8px;
  display:flex; align-items:center; gap:12px;
}

/* ── Horizontal separator ─────────────────────────────── */
.wr-sep { border:none; border-top:1px solid #1e2d4a; margin:16px 0; }

/* ── Timeline node ────────────────────────────────────── */
.tl-node {
  background:#0f1729; border-left:3px solid #FF6B35;
  border-radius:0 8px 8px 0; padding:10px 14px; margin-bottom:10px;
}

/* ── Scrollable evidence box ──────────────────────────── */
.ev-box {
  background:#050810; border:1px solid #1e2d4a; border-radius:6px;
  padding:10px 14px; margin-bottom:8px; font-size:.9em;
}
</style>
"""


def inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


# ── HTML helpers ──────────────────────────────────────────────────────────────

def section(title: str, icon: str = "") -> None:
    prefix = f"{icon}&nbsp;" if icon else ""
    st.markdown(f'<div class="wr-section">{prefix}{title}</div>', unsafe_allow_html=True)


def card(body: str, accent: str = "#FF6B35") -> None:
    st.markdown(
        f'<div class="wr-card wr-card-accent" style="--ac:{accent}">{body}</div>',
        unsafe_allow_html=True,
    )


def badge(text: str, level: str = "medium") -> str:
    """Return HTML badge span. level: high / medium / low / unknown"""
    return f'<span class="badge badge-{level.lower()}">{text}</span>'


def metric_html(label: str, value: str, delta: str = "", delta_color: str = "#8b949e") -> str:
    delta_html = (
        f'<div class="wr-metric-delta" style="color:{delta_color}">{delta}</div>'
        if delta else ""
    )
    return f"""
    <div>
      <div class="wr-metric-label">{label}</div>
      <div class="wr-metric-value">{value}</div>
      {delta_html}
    </div>"""


def risk_row(icon: str, title: str, body: str, level: str = "high") -> None:
    colors = {"high": "#e74c3c", "medium": "#f39c12", "low": "#2ecc71"}
    c = colors.get(level, "#8b949e")
    st.markdown(
        f"""<div class="risk-row" style="border-left:4px solid {c}">
        <span style="font-size:1.4em">{icon}</span>
        <div><b style="color:{c}">{title}</b><br>
        <span style="font-size:.85em;color:#8b949e">{body}</span></div>
        </div>""",
        unsafe_allow_html=True,
    )


def info_bar(text: str, color: str = "#FF6B35") -> None:
    st.markdown(
        f"""<div style="background:{color}22;border-left:4px solid {color};
        border-radius:0 6px 6px 0;padding:10px 14px;margin-bottom:12px;
        font-family:monospace;font-size:.92em">{text}</div>""",
        unsafe_allow_html=True,
    )


# ── Plotly defaults ───────────────────────────────────────────────────────────

PLOTLY_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=0, r=0, t=30, b=20),
    font=dict(family="monospace", color="#e6edf3"),
)

PALETTE = {
    "bjp":        "#FF6B35",
    "sp":         "#3498db",
    "bsp":        "#9b59b6",
    "inc":        "#2ecc71",
    "others":     "#95a5a6",
    "high_risk":  "#e74c3c",
    "medium_risk":"#f39c12",
    "low_risk":   "#2ecc71",
    "neutral":    "#8b949e",
}

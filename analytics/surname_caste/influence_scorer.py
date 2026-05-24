"""
influence_scorer.py
====================
Computes electoral influence scores for each caste group per constituency.

Metrics produced
----------------
1. population_share      : % of voters belonging to this caste group in the AC
2. pearson_r_{party}     : Pearson correlation between caste_share and party_vote_share
3. p_value_{party}       : p-value for the correlation
4. dominant_party        : party with highest mean vote share when caste is dominant (>30%)
5. dominant_party_win_pct: % of booths where winner == dominant_party (when caste >30%)
6. swing_potential       : LOW | MEDIUM | HIGH — based on winner variance in dominant booths
7. n_booths_dominant     : number of booths where caste share > DOMINANCE_THRESHOLD
8. candidate_caste_match : True if winning candidate's surname maps to this caste group

Output
------
data/transformed/caste_influence_scores.json
{
  "ac_322": {
    "Yadav": {
      "population_share": 0.18,
      "pearson_r_BJP": -0.32,
      "pearson_r_SP": 0.71,
      "p_value_SP": 0.002,
      "dominant_party": "SP",
      "dominant_party_win_pct": 0.72,
      "swing_potential": "LOW",
      "n_booths_dominant": 34,
      "candidate_caste_match": false,
      "n_voters": 8420
    },
    ...
  }
}
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from scipy.stats import pearsonr
except ImportError:
    pearsonr = None  # will gracefully degrade

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
TRANSFORMED = ROOT / "data" / "transformed"

DOMINANCE_THRESHOLD = 0.25   # caste_share > 25% → booth is "dominated" by this caste
MIN_BOOTHS_FOR_CORR = 8      # minimum booths needed to compute Pearson r

OUT_SCORES = TRANSFORMED / "caste_influence_scores.json"


def _pearson(x: pd.Series, y: pd.Series) -> tuple[float, float]:
    """Safe Pearson correlation. Returns (r, p_value) or (nan, nan)."""
    valid = x.notna() & y.notna()
    x_v, y_v = x[valid], y[valid]
    if len(x_v) < MIN_BOOTHS_FOR_CORR:
        return (float("nan"), float("nan"))
    if x_v.std() == 0 or y_v.std() == 0:
        return (float("nan"), float("nan"))
    if pearsonr is not None:
        r, p = pearsonr(x_v.values, y_v.values)
        return (round(float(r), 4), round(float(p), 6))
    # Manual fallback if scipy not available
    r = float(np.corrcoef(x_v.values, y_v.values)[0, 1])
    return (round(r, 4), float("nan"))


def _swing_potential(winner_series: pd.Series) -> str:
    """
    Compute swing potential from winner diversity in dominant booths.
    HIGH = multiple parties win → caste is not locked in
    """
    n = len(winner_series)
    if n < 3:
        return "INSUFFICIENT_DATA"
    n_parties = winner_series.nunique()
    top_party_pct = winner_series.value_counts().iloc[0] / n
    if top_party_pct >= 0.85:
        return "LOW"
    elif top_party_pct >= 0.65:
        return "MEDIUM"
    else:
        return "HIGH"


def compute_influence_scores(
    analysis_df: pd.DataFrame,
    candidates_df: pd.DataFrame | None = None,
    *,
    ac_number: int = 322,
    output_path: Path = OUT_SCORES,
    force: bool = False,
) -> dict:
    """
    Compute caste influence scores for the given AC.

    Parameters
    ----------
    analysis_df   : output of aggregator.build_caste_booth_analysis()
    candidates_df : output of parse_candidates (optional, for candidate caste match)
    ac_number     : AC being analysed
    """
    if output_path.exists() and not force:
        with open(output_path, encoding="utf-8") as fh:
            return json.load(fh)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df = analysis_df.copy()

    caste_cols = [c for c in df.columns if c.startswith("caste_share_")]
    party_cols = [c for c in df.columns if c.startswith("party_share_")]

    caste_names = [c.replace("caste_share_", "") for c in caste_cols]
    party_names = [c.replace("party_share_", "") for c in party_cols]

    n_booths = len(df)
    log.info(
        "Computing influence scores: %d castes × %d parties across %d booths",
        len(caste_names), len(party_names), n_booths,
    )

    # ── Candidate caste lookup ──────────────────────────────────────────────
    winner_caste_groups: set[str] = set()
    if candidates_df is not None:
        winners = candidates_df[
            (candidates_df["constituency_no"] == str(ac_number)) &
            (candidates_df["winner"] == True)
        ]
        # Load caste mapper to check winner caste
        try:
            from analytics.surname_caste.caste_mapper import CasteMapper
            mapper = CasteMapper(use_llm=False)
            for _, row in winners.iterrows():
                info = mapper.lookup(row.get("candidate_surname", ""))
                cg = info.get("caste_group", "Unknown")
                if cg != "Unknown":
                    winner_caste_groups.add(cg)
                    log.info(
                        "Winner %s → surname %s → caste %s",
                        row["candidate_name"], row["candidate_surname"], cg,
                    )
        except Exception as exc:
            log.warning("Could not resolve winner caste: %s", exc)

    # ── Per-caste metrics ──────────────────────────────────────────────────
    scores: dict[str, dict] = {}

    for caste, col in zip(caste_names, caste_cols):
        caste_x = df[col].fillna(0)
        n_voters_total = (caste_x * df.get("voter_roll_count", pd.Series([0] * n_booths))).sum()
        pop_share = round(float(caste_x.mean()), 4)

        # Pearson r vs each party
        party_corr: dict[str, float] = {}
        p_values: dict[str, float] = {}
        for party, pcol in zip(party_names, party_cols):
            r, p = _pearson(caste_x, df[pcol].fillna(0))
            party_corr[party] = r
            p_values[party] = p

        # Dominant party (highest mean vote share in dominant booths)
        dominant_mask = caste_x >= DOMINANCE_THRESHOLD
        n_dominant = int(dominant_mask.sum())
        dominant_party = None
        dominant_win_pct = None
        swing = "INSUFFICIENT_DATA"

        if n_dominant >= 3:
            dom_df = df[dominant_mask]
            mean_shares = {
                party: dom_df[pcol].mean()
                for party, pcol in zip(party_names, party_cols)
            }
            dominant_party = max(mean_shares, key=mean_shares.get)
            if "winner_party" in dom_df.columns:
                wins = (dom_df["winner_party"] == dominant_party).sum()
                dominant_win_pct = round(float(wins / n_dominant), 4)
                swing = _swing_potential(dom_df["winner_party"])

        # Best correlated party
        valid_corrs = {p: r for p, r in party_corr.items() if not np.isnan(r)}
        best_corr_party = max(valid_corrs, key=lambda p: abs(valid_corrs[p])) if valid_corrs else None
        best_corr_r = round(float(valid_corrs[best_corr_party]), 4) if best_corr_party else None

        scores[caste] = {
            "population_share": pop_share,
            "n_booths_dominant": n_dominant,
            "dominant_party": dominant_party,
            "dominant_party_win_pct": dominant_win_pct,
            "swing_potential": swing,
            "best_corr_party": best_corr_party,
            "best_corr_r": best_corr_r,
            "candidate_caste_match": caste in winner_caste_groups,
            **{f"pearson_r_{p}": v for p, v in party_corr.items()},
            **{f"p_value_{p}": v for p, v in p_values.items()},
        }

    # Sort by population share desc
    scores = dict(sorted(scores.items(), key=lambda kv: kv[1]["population_share"], reverse=True))

    output_data = {f"ac_{ac_number}": scores}

    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(output_data, fh, ensure_ascii=False, indent=2, default=_json_serialise)
    log.info("Influence scores saved → %s  (%d caste groups)", output_path, len(scores))

    return output_data


def _json_serialise(obj):
    """JSON serialiser that handles numpy/nan/inf."""
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        v = float(obj)
        if np.isnan(v) or np.isinf(v):
            return None
        return round(v, 6)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    raise TypeError(f"Object of type {type(obj)} is not JSON serialisable")


def load_influence_scores(path: Path = OUT_SCORES) -> dict:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def top_influential_castes(
    scores: dict,
    ac_key: str = "ac_322",
    n: int = 10,
    sort_by: str = "population_share",
) -> list[dict]:
    """Return top N castes sorted by a metric, as a list of dicts."""
    ac_data = scores.get(ac_key, {})
    rows = [{"caste": k, **v} for k, v in ac_data.items()]
    rows.sort(key=lambda r: (r.get(sort_by) or 0), reverse=True)
    return rows[:n]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
    from analytics.surname_caste.aggregator import build_caste_booth_analysis
    df = build_caste_booth_analysis()
    scores = compute_influence_scores(df, force=True)
    top = top_influential_castes(scores, n=15)
    for row in top:
        print(
            f"{row['caste']:20s} | pop={row['population_share']:.1%} "
            f"| dom={row.get('dominant_party','?'):6s} "
            f"| best_r={row.get('best_corr_r') or 'N/A'}"
        )

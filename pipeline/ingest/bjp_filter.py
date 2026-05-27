# -*- coding: utf-8 -*-
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

"""
BJP Sentiment Filter
====================
Loads any scraped JSON file and classifies each article as:
  PRO-BJP  / ANTI-BJP / NEUTRAL

Usage:
  python bjp_filter.py                          # uses latest result file
  python bjp_filter.py results/myfile.json      # specific file
"""

import glob
import json
import os
from datetime import datetime

from colorama import Fore, Style, init

init(autoreset=True)

# ══════════════════════════════════════════════════════════════════
#  BJP SENTIMENT LEXICON
# ══════════════════════════════════════════════════════════════════

PRO_BJP_KEYWORDS = [
    # Development / Governance praise
    "development",
    "vikas",
    "inaugurates",
    "inaugurated",
    "launches",
    "launched",
    "growth",
    "progress",
    "infrastructure",
    "smart city",
    "investment",
    "improved",
    "achievement",
    "success",
    "felicitated",
    "awarded",
    "double engine",
    "double-engine",
    "sabka saath",
    "amrit kaal",
    # BJP leaders praised
    "yogi praised",
    "pm modi inaugurates",
    "modi launches",
    "bjp government",
    "yogi government",
    "cm yogi inaugurates",
    "cm yogi launches",
    "bjp wins",
    "bjp victory",
    "bjp leads",
    "saffron wave",
    # Hindi pro
    "विकास",
    "उपलब्धि",
    "सफलता",
    "भाजपा सरकार",
    "योगी सरकार",
    "प्रगति",
    "नई परियोजना",
    "उद्घाटन",
    "डबल इंजन",
    # Law & Order credited to BJP
    "law and order improved",
    "crime reduced",
    "mafia eliminated",
    "encounter mafia",
    "goonda raj ended",
    "safe uttar pradesh",
    # Welfare schemes
    "free ration",
    "ujjwala",
    "pm awas",
    "ayushman bharat",
    "jan dhan",
    "swachh bharat",
    "toilet built",
    "bijli ghar ghar",
]

ANTI_BJP_KEYWORDS = [
    # Corruption / Failure
    "corruption",
    "scam",
    "scandal",
    "bribe",
    "fraud",
    "mismanagement",
    "bhrashtachar",
    "घोटाला",
    "भ्रष्टाचार",
    "रिश्वत",
    # Unemployment
    "unemployment",
    "berozgari",
    "job loss",
    "jobs gone",
    "no jobs",
    "बेरोजगारी",
    "रोजगार नहीं",
    "नौकरी नहीं",
    # Inflation / hardship
    "inflation",
    "price rise",
    "mahangai",
    "महंगाई",
    "petrol price",
    "lpg price",
    "costly",
    "poor",
    "poverty",
    # Law & Order failures
    "rape",
    "murder",
    "mob lynching",
    "riots",
    "communal violence",
    "crime rise",
    "unsafe",
    "criminals",
    "gangster",
    "दंगा",
    "बलात्कार",
    "हत्या",
    "अपराध बढ़ा",
    # Protests / Opposition
    "protest against",
    "opposition slams",
    "yogi criticized",
    "bjp criticized",
    "yogi fails",
    "bjp failure",
    "bjp government fails",
    "bjp anti farmer",
    "bjp anti poor",
    "akhilesh attacks",
    "sp slams bjp",
    "bsp slams",
    "demonstration against",
    "agitation against",
    "योगी की आलोचना",
    "भाजपा विरोध",
    "सरकार विफल",
    # Farmers anger
    "farmer suicide",
    "kisan aatmhatya",
    "sugarcane dues",
    "ganna bakaya",
    "किसान आत्महत्या",
    "गन्ना बकाया",
    # BRD hospital tragedy
    "brd deaths",
    "oxygen deaths",
    "hospital deaths",
    "encephalitis deaths",
    # Flood blame
    "flood mismanagement",
    "flood victims ignored",
    "flood relief delayed",
    # Anti-BJP electoral signals
    "bjp loses",
    "bjp defeated",
    "bjp setback",
    "anti-incumbency",
    "people angry",
    "public anger",
    "jan virodh",
]

NEUTRAL_OVERRIDE_KEYWORDS = [
    # Pure news without bias
    "election schedule",
    "election commission",
    "voting date",
    "candidate list",
    "nomination filed",
    "seat sharing",
    "चुनाव आयोग",
    "मतदान",
    "प्रत्याशी",
]


# ══════════════════════════════════════════════════════════════════
#  CLASSIFIER
# ══════════════════════════════════════════════════════════════════


def classify_bjp(text: str) -> dict:
    """Return BJP sentiment label + scores."""
    t = text.lower()

    pro_score = sum(1 for kw in PRO_BJP_KEYWORDS if kw.lower() in t)
    anti_score = sum(1 for kw in ANTI_BJP_KEYWORDS if kw.lower() in t)
    neutral_hit = any(kw.lower() in t for kw in NEUTRAL_OVERRIDE_KEYWORDS)

    matched_pro = [kw for kw in PRO_BJP_KEYWORDS if kw.lower() in t][:5]
    matched_anti = [kw for kw in ANTI_BJP_KEYWORDS if kw.lower() in t][:5]

    # Decide label
    if neutral_hit and pro_score == 0 and anti_score == 0:
        label = "NEUTRAL"
    elif pro_score == 0 and anti_score == 0:
        label = "NEUTRAL"
    elif pro_score > anti_score * 1.2:
        label = "PRO-BJP"
    elif anti_score > pro_score * 1.2:
        label = "ANTI-BJP"
    elif pro_score == anti_score:
        label = "NEUTRAL"
    elif pro_score > anti_score:
        label = "LEAN-PRO-BJP"
    else:
        label = "LEAN-ANTI-BJP"

    # Net score: positive = pro, negative = anti
    net = pro_score - anti_score
    total = pro_score + anti_score or 1
    confidence = round(abs(net) / total, 3)

    return {
        "label": label,
        "pro_score": pro_score,
        "anti_score": anti_score,
        "net_score": net,
        "confidence": confidence,
        "matched_pro": matched_pro,
        "matched_anti": matched_anti,
    }


def classify_articles(articles: list) -> list:
    """Add bjp_sentiment field to each article."""
    for art in articles:
        text = f"{art.get('title','')} {art.get('summary','')} {art.get('content','')}"
        art["bjp_sentiment"] = classify_bjp(text)
    return articles


# ══════════════════════════════════════════════════════════════════
#  LOAD / SAVE
# ══════════════════════════════════════════════════════════════════


def find_latest_result() -> str:
    files = sorted(glob.glob("results/gorakhpur_election_*.json"))
    if not files:
        raise FileNotFoundError("No result files found in results/")
    return files[-1]


def save_filtered(articles: list, label_prefix: str, out_dir: str = "results") -> str:
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{out_dir}/{label_prefix}_{ts}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "generated_at": datetime.now().isoformat(),
                "total": len(articles),
                "articles": articles,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    return path


# ══════════════════════════════════════════════════════════════════
#  REPORT
# ══════════════════════════════════════════════════════════════════

LABEL_COLORS = {
    "PRO-BJP": Fore.GREEN,
    "LEAN-PRO-BJP": Fore.LIGHTGREEN_EX,
    "NEUTRAL": Fore.YELLOW,
    "LEAN-ANTI-BJP": Fore.LIGHTRED_EX,
    "ANTI-BJP": Fore.RED,
}


def print_report(articles: list):
    if not articles:
        print(f"{Fore.RED}No articles.{Style.RESET_ALL}")
        return

    # Group by label
    groups: dict = {}
    for a in articles:
        lbl = a["bjp_sentiment"]["label"]
        groups.setdefault(lbl, []).append(a)

    total = len(articles)
    print(f"\n{Fore.CYAN}" + "-" * 64)
    print("  BJP SENTIMENT FILTER -- GORAKHPUR ELECTION ARTICLES")
    print("-" * 64 + Style.RESET_ALL)
    print(f"  Total articles classified : {Fore.WHITE}{total}{Style.RESET_ALL}\n")

    order = ["PRO-BJP", "LEAN-PRO-BJP", "NEUTRAL", "LEAN-ANTI-BJP", "ANTI-BJP"]
    for lbl in order:
        arts = groups.get(lbl, [])
        if not arts:
            continue
        pct = round(len(arts) * 100 / total)
        bar = "#" * min(len(arts), 40)
        clr = LABEL_COLORS.get(lbl, Fore.WHITE)
        print(f"  {clr}{lbl:<18}{Style.RESET_ALL}  {bar}  {len(arts):>3} ({pct}%)")

    # Sample headlines per group
    for lbl in ["PRO-BJP", "ANTI-BJP"]:
        arts = groups.get(lbl, [])
        if not arts:
            continue
        clr = LABEL_COLORS[lbl]
        print(f"\n  {clr}-- Top {lbl} Headlines --{Style.RESET_ALL}")
        for a in arts[:6]:
            s = a["bjp_sentiment"]
            print(f"    pro={s['pro_score']} anti={s['anti_score']}  {a['title'][:65]}")
            if s["matched_pro"]:
                print(
                    f"      {Fore.GREEN}Pro signals : {', '.join(s['matched_pro'][:3])}{Style.RESET_ALL}"
                )
            if s["matched_anti"]:
                print(
                    f"      {Fore.RED}Anti signals: {', '.join(s['matched_anti'][:3])}{Style.RESET_ALL}"
                )

    # Topic breakdown within pro vs anti
    print(f"\n  {Fore.CYAN}-- Topic Breakdown --{Style.RESET_ALL}")
    for lbl in ["PRO-BJP", "ANTI-BJP"]:
        arts = groups.get(lbl, [])
        if not arts:
            continue
        topic_cnt: dict = {}
        for a in arts:
            for t in a.get("topics", []):
                topic_cnt[t] = topic_cnt.get(t, 0) + 1
        clr = LABEL_COLORS[lbl]
        print(f"  {clr}{lbl}{Style.RESET_ALL}")
        for t, c in sorted(topic_cnt.items(), key=lambda x: -x[1])[:6]:
            print(f"    {t:<28} {c}")

    return groups


# ══════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Load file
    if len(sys.argv) > 1 and sys.argv[1].endswith(".json"):
        src_file = sys.argv[1]
    else:
        src_file = find_latest_result()

    print(f"\n{Fore.CYAN}Loading: {src_file}{Style.RESET_ALL}")
    with open(src_file, encoding="utf-8") as f:
        data = json.load(f)

    articles = data.get("articles", [])
    print(f"  {len(articles)} articles loaded.")

    # Classify
    classify_articles(articles)

    # Print report
    groups = print_report(articles)

    # Save split files
    pro_arts = groups.get("PRO-BJP", []) + groups.get("LEAN-PRO-BJP", [])
    anti_arts = groups.get("ANTI-BJP", []) + groups.get("LEAN-ANTI-BJP", [])
    neu_arts = groups.get("NEUTRAL", [])

    p1 = save_filtered(pro_arts, "pro_bjp")
    p2 = save_filtered(anti_arts, "anti_bjp")
    p3 = save_filtered(neu_arts, "neutral")

    # Also save fully classified master file
    master_path = src_file.replace(".json", "_classified.json")
    data["articles"] = articles
    data["bjp_classification"] = {
        "pro_bjp": len(pro_arts),
        "anti_bjp": len(anti_arts),
        "neutral": len(neu_arts),
        "classified_at": datetime.now().isoformat(),
    }
    with open(master_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n  {Fore.GREEN}Saved:{Style.RESET_ALL}")
    print(f"    PRO-BJP  ({len(pro_arts):>3}) -> {p1}")
    print(f"    ANTI-BJP ({len(anti_arts):>3}) -> {p2}")
    print(f"    NEUTRAL  ({len(neu_arts):>3}) -> {p3}")
    print(f"    MASTER             -> {master_path}\n")

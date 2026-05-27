# ruff: noqa: E402, F401, F404, F405, F841, F811
# -*- coding: utf-8 -*-
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

"""
Gorakhpur Election Pipeline
============================
One command: scrape + classify Pro/Anti-BJP + save reports

Usage:
  python pipeline.py            # scrape fresh + classify
  python pipeline.py --file results/gorakhpur_election_XYZ.json  # classify existing file
  python pipeline.py --full     # scrape with full article text
"""

import json
import os
import re
import sys
import time
from datetime import datetime

import feedparser
import requests
from bs4 import BeautifulSoup
from colorama import Fore, Style, init
from dateutil import parser as dateparser

init(autoreset=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
}
TIMEOUT = 12
DELAY = 0.5

# ══════════════════════════════════════════════════════
#  SCRAPER CONFIG
# ══════════════════════════════════════════════════════

GORAKHPUR_ANCHORS = [
    "gorakhpur",
    "gorakhnath",
    "brd medical",
    "ddu gorakhpur",
    "gida gorakhpur",
    "rapti gorakhpur",
    "गोरखपुर",
    "गोरखनाथ",
]

ELECTION_TOPICS = {
    "Yogi Adityanath": {
        "kw": ["yogi adityanath", "yogi", "cm yogi", "mahant yogi", "योगी आदित्यनाथ", "योगी"]
    },
    "Development": {
        "kw": [
            "development",
            "vikas",
            "highway",
            "airport",
            "smart city",
            "inaugurat",
            "विकास",
            "सड़क",
            "बिजली",
        ]
    },
    "Unemployment": {
        "kw": [
            "unemployment",
            "berozgari",
            "jobs",
            "rozgar",
            "youth employment",
            "बेरोजगारी",
            "रोजगार",
            "नौकरी",
        ]
    },
    "Law and Order": {
        "kw": [
            "crime",
            "police",
            "gangster",
            "mafia",
            "murder",
            "robbery",
            "encounter",
            "अपराध",
            "पुलिस",
            "माफिया",
            "हत्या",
        ]
    },
    "Farmers": {
        "kw": [
            "farmer",
            "kisan",
            "sugarcane",
            "crop",
            "msp",
            "irrigation",
            "fertilizer",
            "किसान",
            "गन्ना",
            "फसल",
            "सिंचाई",
        ]
    },
    "Healthcare": {
        "kw": [
            "hospital",
            "health",
            "brd medical",
            "doctor",
            "medicine",
            "encephalitis",
            "अस्पताल",
            "स्वास्थ्य",
            "डॉक्टर",
        ]
    },
    "Education": {
        "kw": [
            "school",
            "college",
            "university",
            "ddu",
            "student",
            "teacher",
            "स्कूल",
            "शिक्षा",
            "छात्र",
        ]
    },
    "Corruption": {
        "kw": ["corruption", "scam", "bribe", "fraud", "scandal", "भ्रष्टाचार", "घोटाला", "रिश्वत"]
    },
    "Communal": {
        "kw": ["communal", "riot", "hindu", "muslim", "temple", "mosque", "दंगा", "सांप्रदायिक"]
    },
    "Flood": {"kw": ["flood", "rapti", "rohini", "inundation", "बाढ़", "राप्ती"]},
    "Party Politics": {
        "kw": [
            "bjp",
            "samajwadi",
            "bsp",
            "congress",
            "nda",
            "election",
            "vote",
            "rally",
            "भाजपा",
            "सपा",
            "चुनाव",
            "वोट",
        ]
    },
    "Local Leaders": {
        "kw": [
            "ravi kishan",
            "gorakhpur mp",
            "gorakhpur mla",
            "akhilesh",
            "mayawati",
            "रवि किशन",
            "अखिलेश",
        ]
    },
}

RSS_SOURCES = [
    {
        "name": "TOI UP",
        "url": "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms",
        "lang": "en",
    },
    {
        "name": "Hindustan Times",
        "url": "https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml",
        "lang": "en",
    },
    {"name": "NDTV UP", "url": "https://feeds.feedburner.com/ndtvnews-uttar-pradesh", "lang": "en"},
    {"name": "India Today", "url": "https://www.indiatoday.in/rss/1206514", "lang": "en"},
    {
        "name": "The Hindu",
        "url": "https://www.thehindu.com/news/national/feeder/default.rss",
        "lang": "en",
    },
    {"name": "News18 Politics", "url": "https://www.news18.com/rss/politics.xml", "lang": "en"},
    {
        "name": "Indian Express",
        "url": "https://indianexpress.com/section/india/feed/",
        "lang": "en",
    },
    {"name": "The Print", "url": "https://theprint.in/category/politics/feed/", "lang": "en"},
    {
        "name": "Jagran UP",
        "url": "https://www.jagran.com/rss/news-national-uttar-pradesh.xml",
        "lang": "hi",
    },
    {
        "name": "Amar Ujala UP",
        "url": "https://www.amarujala.com/rss/uttar-pradesh.xml",
        "lang": "hi",
    },
    {
        "name": "Navbharat Times",
        "url": "https://navbharattimes.indiatimes.com/rssfeedsdefault.cms",
        "lang": "hi",
    },
    {
        "name": "Live Hindustan UP",
        "url": "https://www.livehindustan.com/rss/up-uttarakhand.xml",
        "lang": "hi",
    },
    {"name": "Dainik Bhaskar UP", "url": "https://www.bhaskar.com/rss-feed/1061/", "lang": "hi"},
]

GOOGLE_QUERIES = [
    ("gorakhpur development bjp yogi", "en"),
    ("gorakhpur unemployment jobs youth", "en"),
    ("gorakhpur crime law order police", "en"),
    ("gorakhpur farmers sugarcane msp", "en"),
    ("gorakhpur election 2027 bjp sp bsp", "en"),
    ("yogi adityanath gorakhpur visit", "en"),
    ("gorakhpur flood rapti disaster", "en"),
    ("gorakhpur hospital healthcare brd", "en"),
    ("gorakhpur corruption scam fraud", "en"),
    ("gorakhpur communal riot temple", "en"),
    ("gorakhpur bjp anti incumbency voters", "en"),
    ("gorakhpur ravi kishan mp development", "en"),
    ("गोरखपुर विकास योजना चुनाव", "hi"),
    ("गोरखपुर बेरोजगारी किसान समस्या", "hi"),
    ("गोरखपुर भ्रष्टाचार अपराध पुलिस", "hi"),
    ("गोरखपुर योगी आदित्यनाथ सरकार", "hi"),
    ("गोरखपुर सपा भाजपा 2027 चुनाव", "hi"),
    ("गोरखपुर बाढ़ राप्ती नदी", "hi"),
    ("गोरखपुर स्वास्थ्य अस्पताल", "hi"),
]

# ══════════════════════════════════════════════════════
#  PRO / ANTI BJP LEXICON  (expanded)
# ══════════════════════════════════════════════════════

PRO_SIGNALS = [
    # Development / inauguration
    "inaugurates",
    "inaugurated",
    "launches",
    "launched",
    "dedicate",
    "dedicates",
    "foundation stone",
    "lays foundation",
    "development project",
    "infrastructure project",
    "smart city",
    "metro gorakhpur",
    "gorakhpur airport",
    "gorakhpur link expressway",
    "fertilizer plant",
    "double engine",
    "double-engine government",
    "sabka saath",
    "amrit kaal",
    "viksit bharat",
    "new project",
    "sets up",
    # Law & order wins
    "encounter",
    "mafia eliminated",
    "gangster arrested",
    "crime down",
    "crime reduced",
    "law and order improved",
    "safe uttar pradesh",
    "bulldozer action",
    "anti-mafia",
    "goonda raj ended",
    "crime control",
    # Welfare credited to BJP
    "free ration",
    "pm awas",
    "ujjwala",
    "ayushman",
    "jan dhan",
    "bijli",
    "swachh bharat",
    "toilet",
    "house built",
    "scheme beneficiary",
    "pm kisan",
    "kisan samman",
    # Positive words about BJP/Yogi
    "yogi praised",
    "modi praised",
    "bjp achievement",
    "bjp government delivers",
    "cm yogi inaugurates",
    "cm yogi launches",
    "pm modi inaugurates",
    "bjp wins",
    "bjp victory",
    "saffron wave",
    "bjp leads",
    # Hindi pro signals
    "विकास कार्य",
    "उद्घाटन",
    "शिलान्यास",
    "लोकार्पण",
    "नई परियोजना",
    "मुफ्त राशन",
    "आयुष्मान",
    "उपलब्धि",
    "सफलता",
    "विकसित",
    "कानून व्यवस्था",
    "माफिया मुक्त",
    "अपराध मुक्त",
    "डबल इंजन",
    "योगी की सराहना",
    "भाजपा की जीत",
    "भाजपा सरकार का विकास",
]

ANTI_SIGNALS = [
    # Corruption / scandal
    "corruption",
    "scam",
    "bribe",
    "fraud",
    "misappropriation",
    "embezzle",
    "scandal",
    "land grab",
    "illegal",
    "irregularities",
    "paper leak",
    "भ्रष्टाचार",
    "घोटाला",
    "रिश्वत",
    "घपला",
    "धोखाधड़ी",
    # Unemployment
    "unemployment",
    "no jobs",
    "job loss",
    "youth unemployed",
    "berozgari",
    "बेरोजगारी",
    "नौकरी नहीं",
    "रोजगार नहीं",
    "पलायन",
    "migration crisis",
    # Inflation / poverty
    "inflation",
    "price rise",
    "costly",
    "petrol price hike",
    "lpg costly",
    "महंगाई",
    "मूल्य वृद्धि",
    "महंगा",
    "पेट्रोल",
    "गैस महंगी",
    # Law & order failures
    "rape",
    "murder",
    "kidnapping",
    "lynching",
    "mob violence",
    "communal riot",
    "criminals roam",
    "goonda",
    "extortion",
    "drugs",
    "organised crime",
    "बलात्कार",
    "हत्या",
    "अपहरण",
    "दंगा",
    "अपराधी",
    "वसूली",
    # Farmer distress
    "farmer suicide",
    "kisan aatmhatya",
    "sugarcane dues unpaid",
    "ganna bhugtan",
    "किसान आत्महत्या",
    "गन्ना बकाया",
    "किसान परेशान",
    "कृषि संकट",
    # BRD / healthcare failures
    "brd deaths",
    "oxygen deaths",
    "encephalitis deaths",
    "hospital neglect",
    "अस्पताल में मौत",
    "ऑक्सीजन",
    "इलाज न मिलना",
    # Flood / disaster mismanagement
    "flood victims ignored",
    "flood relief delayed",
    "flood mismanagement",
    "बाढ़ पीड़ित",
    "राहत नहीं",
    "बाढ़ में मौत",
    # Anti-BJP political signals
    "anti-incumbency",
    "voters angry",
    "public anger",
    "bjp loses",
    "bjp setback",
    "bjp defeat",
    "opposition wins",
    "bjp criticized",
    "yogi criticized",
    "bjp fails",
    "government failure",
    "failed government",
    "akhilesh slams",
    "sp attacks bjp",
    "bsp slams yogi",
    "congress slams",
    "protest against bjp",
    "dharna against",
    "demonstration against yogi",
    "जनता नाराज",
    "सरकार विफल",
    "योगी की आलोचना",
    "भाजपा विरोध",
    "हार",
    "भाजपा की हार",
    "विरोध प्रदर्शन",
    "सरकार पर निशाना",
]

# ══════════════════════════════════════════════════════
#  TOPIC DEFAULT SENTIMENT
#  When keywords are absent, topic itself implies lean
# ══════════════════════════════════════════════════════

# Topics that inherently carry a political lean (based on how coverage works)
TOPIC_DEFAULT_BIAS = {
    "Corruption": -2,  # almost always anti-government (anti-BJP in UP)
    "Unemployment": -1,  # negative for ruling party
    "Flood": -1,  # govt blamed for poor relief
    "Farmers": -1,  # sugarcane dues, MSP anger = anti-BJP lean
    "Law and Order": -1,  # crime stories = negative for ruling party
    "Communal": -1,  # riots = failure of governance
    "Development": +2,  # projects/inauguration = pro-BJP in UP
    "Yogi Adityanath": +1,  # coverage of CM's visits/actions = mild pro
    "Healthcare": -1,  # BRD deaths, doctor strikes = negative
    "Education": 0,
    "Party Politics": 0,
    "Local Leaders": 0,
}

# Google News query → implicit lean of articles it surfaces
SOURCE_QUERY_BIAS = {
    "corruption": -3,
    "scam": -3,
    "fraud": -3,
    "crime": -2,
    "law order police": -1,
    "flood": -2,
    "unemployment": -2,
    "anti incumbency": -3,
    "development bjp": +2,
    "yogi adityanath": +1,
    "inaugurat": +2,
    "healthcare brd": -1,
    "farmers sugarcane": -1,
    "communal riot": -2,
    "विकास": +2,
    "भ्रष्टाचार": -3,
    "अपराध": -2,
    "बाढ़": -2,
    "बेरोजगारी": -2,
}


# ══════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════


def clean_html(html):
    return re.sub(r"\s+", " ", BeautifulSoup(html, "lxml").get_text(" ")).strip()


def safe_date(raw):
    try:
        return dateparser.parse(str(raw), ignoretz=True).isoformat()
    except Exception:
        return datetime.now().isoformat()


def is_gorakhpur(text):
    t = text.lower()
    return any(a.lower() in t for a in GORAKHPUR_ANCHORS)


def detect_topics(text):
    t = text.lower()
    return [name for name, cfg in ELECTION_TOPICS.items() if any(kw in t for kw in cfg["kw"])]


def get_topic_bias(topics: list) -> int:
    """Sum bias scores for detected topics."""
    return sum(TOPIC_DEFAULT_BIAS.get(t, 0) for t in topics)


def get_source_bias(source: str) -> int:
    """Infer bias from the Google News query that found the article."""
    s = source.lower()
    score = 0
    for kw, bias in SOURCE_QUERY_BIAS.items():
        if kw.lower() in s:
            score += bias
    return score


def classify_bjp(text: str, topics: list = None, source: str = "") -> dict:
    """
    Classify article as PRO-BJP / ANTI-BJP / NEUTRAL.
    Uses 3 layers (in priority order):
      1. Explicit keyword matches in title+summary  (strongest)
      2. Topic-based default bias                  (medium)
      3. Source/query context bias                 (weakest tiebreaker)
    """
    t = text.lower()
    pro_matched = [s for s in PRO_SIGNALS if s.lower() in t]
    anti_matched = [s for s in ANTI_SIGNALS if s.lower() in t]
    kw_pro = len(pro_matched)
    kw_anti = len(anti_matched)
    kw_pro - kw_anti

    # Layer 2: topic bias
    topic_bias = get_topic_bias(topics or [])

    # Layer 3: source/query bias (only acts as tiebreaker)
    src_bias = get_source_bias(source)

    # Convert to comparable units (keywords count more)
    # Each keyword match = 2 pts; each topic bias unit = 1 pt; source = 0.5 pt
    total_pro = kw_pro * 2 + max(topic_bias, 0) + max(src_bias, 0) * 0.5
    total_anti = kw_anti * 2 + max(-topic_bias, 0) + max(-src_bias, 0) * 0.5
    net = total_pro - total_anti
    confidence = round(abs(net) / max(total_pro + total_anti, 1), 3)

    if total_pro == 0 and total_anti == 0:
        label = "NEUTRAL"
    elif total_pro >= total_anti * 1.2:
        label = "PRO-BJP"
    elif total_anti >= total_pro * 1.2:
        label = "ANTI-BJP"
    elif total_pro > total_anti:
        label = "LEAN-PRO"
    elif total_anti > total_pro:
        label = "LEAN-ANTI"
    else:
        label = "NEUTRAL"

    return {
        "label": label,
        "pro": kw_pro,
        "anti": kw_anti,
        "net": round(net, 2),
        "confidence": confidence,
        "topic_bias": topic_bias,
        "source_bias": src_bias,
        "pro_matched": pro_matched[:4],
        "anti_matched": anti_matched[:4],
    }


# ══════════════════════════════════════════════════════
#  SCRAPER
# ══════════════════════════════════════════════════════


class Scraper:
    def __init__(self, fetch_full=False):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.seen = set()
        self.fetch_full = fetch_full

    def _parse_feed(self, src):
        out = []
        try:
            feed = feedparser.parse(src["url"])
            for e in feed.entries[:30]:
                title = getattr(e, "title", "")
                summary = getattr(e, "summary", "")
                link = getattr(e, "link", "")
                pub = getattr(e, "published", getattr(e, "updated", None))
                if link in self.seen:
                    continue
                text = f"{title} {clean_html(summary)}"
                if not is_gorakhpur(text):
                    continue
                topics = detect_topics(text)
                if not topics:
                    continue
                self.seen.add(link)
                out.append(
                    {
                        "title": title,
                        "summary": clean_html(summary)[:500],
                        "url": link,
                        "source": src["name"],
                        "language": src["lang"],
                        "published": safe_date(pub),
                        "topics": topics,
                        "content": "",
                        "scraped_at": datetime.now().isoformat(),
                    }
                )
        except Exception as e:
            print(f"  {Fore.RED}! {src['name']}: {e}{Style.RESET_ALL}")
        return out

    def _full_text(self, url):
        try:
            r = self.session.get(url, timeout=TIMEOUT)
            soup = BeautifulSoup(r.text, "lxml")
            for sel in ["article", ".article-body", "[itemprop='articleBody']", ".content-body"]:
                node = soup.select_one(sel)
                if node:
                    txt = " ".join(p.get_text() for p in node.find_all("p"))
                    if len(txt) > 150:
                        return re.sub(r"\s+", " ", txt)[:3000]
            return re.sub(
                r"\s+",
                " ",
                " ".join(p.get_text() for p in soup.find_all("p") if len(p.get_text()) > 40),
            )[:3000]
        except Exception:
            return ""

    def run(self):
        arts = []
        print(f"\n{Fore.CYAN}[1/2] RSS Feeds{Style.RESET_ALL}")
        for src in RSS_SOURCES:
            batch = self._parse_feed(src)
            arts.extend(batch)
            c = Fore.GREEN + f"+{len(batch)}" if batch else Fore.RED + "0"
            print(f"  {src['name']:<28} {c}{Style.RESET_ALL}")
            time.sleep(DELAY)

        print(f"\n{Fore.CYAN}[2/2] Google News Queries{Style.RESET_ALL}")
        for q, lang in GOOGLE_QUERIES:
            enc = requests.utils.quote(q)
            hl = "hi" if lang == "hi" else "en-IN"
            ceid = "IN:hi" if lang == "hi" else "IN:en"
            url = f"https://news.google.com/rss/search?q={enc}&hl={hl}&gl=IN&ceid={ceid}"
            batch = self._parse_feed({"name": f"GNews:{q[:30]}", "url": url, "lang": lang})
            arts.extend(batch)
            c = Fore.GREEN + f"+{len(batch)}" if batch else Fore.RED + "0"
            print(f"  [{lang}] {q[:42]:<44} {c}{Style.RESET_ALL}")
            time.sleep(DELAY)

        if self.fetch_full:
            print(f"\n{Fore.YELLOW}Fetching full text...{Style.RESET_ALL}")
            for i, a in enumerate(arts, 1):
                print(f"  [{i}/{len(arts)}] {a['title'][:55]}", end="\r")
                a["content"] = self._full_text(a["url"])
                time.sleep(0.8)

        return arts


# ══════════════════════════════════════════════════════
#  CLASSIFIER + REPORT
# ══════════════════════════════════════════════════════

COLORS = {
    "PRO-BJP": Fore.GREEN,
    "LEAN-PRO": Fore.LIGHTGREEN_EX,
    "NEUTRAL": Fore.YELLOW,
    "LEAN-ANTI": Fore.LIGHTRED_EX,
    "ANTI-BJP": Fore.RED,
}


def run_classification(articles):
    for a in articles:
        text = f"{a.get('title','')} {a.get('summary','')} {a.get('content','')}"
        topics = a.get("topics", [])
        source = a.get("source", "")
        a["bjp_sentiment"] = classify_bjp(text, topics=topics, source=source)
    return articles


def print_report(articles):
    groups = {}
    for a in articles:
        lbl = a["bjp_sentiment"]["label"]
        groups.setdefault(lbl, []).append(a)

    total = len(articles)
    print(f"\n{Fore.CYAN}" + "=" * 64)
    print("  BJP SENTIMENT REPORT -- GORAKHPUR ELECTION")
    print("=" * 64 + Style.RESET_ALL)
    print(f"  Total articles : {total}\n")

    for lbl in ["PRO-BJP", "LEAN-PRO", "NEUTRAL", "LEAN-ANTI", "ANTI-BJP"]:
        grp = groups.get(lbl, [])
        if not grp:
            continue
        pct = round(len(grp) * 100 / total)
        bar = "#" * min(len(grp), 45)
        clr = COLORS.get(lbl, Fore.WHITE)
        print(f"  {clr}{lbl:<14}{Style.RESET_ALL} {bar} {len(grp):>3} ({pct}%)")

    # Top 6 headlines per category
    for lbl in ["PRO-BJP", "ANTI-BJP"]:
        grp = groups.get(lbl, [])
        if not grp:
            continue
        clr = COLORS[lbl]
        print(f"\n  {clr}--- {lbl} Top Articles ---{Style.RESET_ALL}")
        for a in grp[:6]:
            s = a["bjp_sentiment"]
            print(f"    [pro={s['pro']} anti={s['anti']}] {a['title'][:68]}")
            if s["pro_matched"]:
                print(f"      {Fore.GREEN}+ {', '.join(s['pro_matched'][:3])}{Style.RESET_ALL}")
            if s["anti_matched"]:
                print(f"      {Fore.RED}- {', '.join(s['anti_matched'][:3])}{Style.RESET_ALL}")

    # Topic breakdown
    print(f"\n  {Fore.CYAN}--- Topic Breakdown by BJP Stance ---{Style.RESET_ALL}")
    print(f"  {'Topic':<28} {'PRO':>5} {'ANTI':>5} {'NEUTRAL':>8}")
    print("  " + "-" * 50)
    all_topics = sorted({t for a in articles for t in a.get("topics", [])})
    for topic in all_topics:
        p = sum(
            1
            for a in articles
            if topic in a.get("topics", [])
            and a["bjp_sentiment"]["label"] in ("PRO-BJP", "LEAN-PRO")
        )
        n = sum(
            1
            for a in articles
            if topic in a.get("topics", [])
            and a["bjp_sentiment"]["label"] in ("ANTI-BJP", "LEAN-ANTI")
        )
        u = sum(
            1
            for a in articles
            if topic in a.get("topics", []) and a["bjp_sentiment"]["label"] == "NEUTRAL"
        )
        print(
            f"  {topic:<28} {Fore.GREEN}{p:>5}{Style.RESET_ALL} {Fore.RED}{n:>5}{Style.RESET_ALL} {Fore.YELLOW}{u:>8}{Style.RESET_ALL}"
        )

    return groups


def save_all(articles, groups):
    os.makedirs("results", exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Master
    master = f"results/gorakhpur_election_{ts}.json"
    with open(master, "w", encoding="utf-8") as f:
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

    # Split files
    saved = {"master": master}
    for lbl, arts in groups.items():
        slug = lbl.lower().replace("-", "_").replace(" ", "_")
        path = f"results/{slug}_{ts}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                {"label": lbl, "total": len(arts), "articles": arts},
                f,
                ensure_ascii=False,
                indent=2,
            )
        saved[lbl] = path

    return saved


# ══════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════

if __name__ == "__main__":
    args = sys.argv[1:]
    fetch_full = "--full" in args

    # Load existing file or scrape fresh
    src_file = next((a for a in args if a.endswith(".json")), None)
    file_flag = next((i for i, a in enumerate(args) if a == "--file"), None)
    if file_flag is not None and file_flag + 1 < len(args):
        src_file = args[file_flag + 1]

    if src_file:
        print(f"\n{Fore.CYAN}Loading: {src_file}{Style.RESET_ALL}")
        with open(src_file, encoding="utf-8") as f:
            data = json.load(f)
        articles = data.get("articles", [])
        print(f"  {len(articles)} articles loaded.")
    else:
        print(f"\n{Fore.CYAN}Scraping fresh articles...{Style.RESET_ALL}")
        scraper = Scraper(fetch_full=fetch_full)
        articles = scraper.run()
        print(f"\n  Total scraped: {Fore.WHITE}{len(articles)}{Style.RESET_ALL}")

    # Classify
    print(f"\n{Fore.YELLOW}Classifying BJP sentiment...{Style.RESET_ALL}")
    run_classification(articles)

    # Report
    groups = print_report(articles)

    # Save
    saved = save_all(articles, groups)
    print(f"\n{Fore.GREEN}Files saved:{Style.RESET_ALL}")
    for lbl, path in saved.items():
        count = len(groups.get(lbl, articles))
        print(f"  {lbl:<20} ({count:>3} articles)  ->  {path}")
    print()

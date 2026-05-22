# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

"""
Gorakhpur Election Sentiment Scraper
=====================================
Scrapes articles from 15+ Indian newspapers covering ALL key
election-influencing topics in Gorakhpur and stores them in JSON.

Topics covered:
  Development, Unemployment, Law & Order, Farmers, Healthcare,
  Education, Corruption, Communal Relations, Flood/Environment,
  Party Politics (BJP/SP/BSP/INC), Yogi Adityanath, Local Leaders

Run:
  python gorakhpur_scraper.py              # scrape all topics
  python gorakhpur_scraper.py --full       # also fetch full article body

Output: results/gorakhpur_articles_<timestamp>.json
"""

import os, re, json, time, sys
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from dateutil import parser as dateparser
from colorama import Fore, Style, init

init(autoreset=True)

# ── Request config ─────────────────────────────────────────────────
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
}
TIMEOUT = 12
DELAY   = 0.6   # seconds between requests


# ══════════════════════════════════════════════════════════════════
#  ELECTION TOPIC DEFINITIONS
#  Each topic has English + Hindi keywords for relevance detection
# ══════════════════════════════════════════════════════════════════

ELECTION_TOPICS = {
    "Yogi Adityanath": {
        "en": ["yogi adityanath", "yogi", "cm yogi", "chief minister yogi",
               "mahant yogi", "ajay bisht"],
        "hi": ["योगी आदित्यनाथ", "योगी", "मुख्यमंत्री योगी"],
    },
    "Development": {
        "en": ["development", "infrastructure", "highway", "metro", "airport",
               "smart city", "gorakhpur development", "industrial"],
        "hi": ["विकास", "सड़क", "बिजली", "पानी", "गोरखपुर विकास"],
    },
    "Unemployment": {
        "en": ["unemployment", "jobs", "youth", "employment", "rozgar",
               "berozgari", "job crisis"],
        "hi": ["बेरोजगारी", "रोजगार", "नौकरी", "युवा"],
    },
    "Law and Order": {
        "en": ["crime", "police", "gangster", "mafia", "murder", "robbery",
               "safety", "law order", "encounter"],
        "hi": ["अपराध", "पुलिस", "माफिया", "हत्या", "गुंडा", "एनकाउंटर"],
    },
    "Farmers": {
        "en": ["farmer", "kisan", "agriculture", "sugarcane", "crop",
               "msp", "irrigation", "fertilizer", "farm"],
        "hi": ["किसान", "खेती", "गन्ना", "फसल", "सिंचाई", "खाद"],
    },
    "Healthcare": {
        "en": ["hospital", "health", "brd medical", "doctor", "medicine",
               "encephalitis", "health scheme"],
        "hi": ["अस्पताल", "स्वास्थ्य", "डॉक्टर", "बीआरडी", "दवाई"],
    },
    "Education": {
        "en": ["school", "college", "university", "ddu", "education",
               "student", "teacher", "exam"],
        "hi": ["स्कूल", "कॉलेज", "शिक्षा", "छात्र", "विश्वविद्यालय"],
    },
    "Corruption": {
        "en": ["corruption", "scam", "bribe", "scandal", "fraud",
               "misappropriation"],
        "hi": ["भ्रष्टाचार", "घोटाला", "रिश्वत", "घपला", "धोखाधड़ी"],
    },
    "Communal": {
        "en": ["communal", "hindu", "muslim", "riot", "religion",
               "temple", "mosque", "minority"],
        "hi": ["सांप्रदायिक", "दंगा", "हिंदू", "मुस्लिम", "धर्म"],
    },
    "Flood and Environment": {
        "en": ["flood", "rapti", "rohini", "river", "inundation",
               "pollution", "environment", "climate"],
        "hi": ["बाढ़", "राप्ती", "नदी", "प्रदूषण", "पर्यावरण"],
    },
    "Party Politics": {
        "en": ["bjp", "samajwadi", "bsp", "congress", "nda",
               "india alliance", "election", "vote", "rally", "campaign"],
        "hi": ["भाजपा", "सपा", "बसपा", "कांग्रेस", "चुनाव", "वोट", "रैली"],
    },
    "Local Leaders": {
        "en": ["ravi kishan", "gorakhpur mp", "gorakhpur mla",
               "akhilesh yadav", "mayawati"],
        "hi": ["रवि किशन", "अखिलेश यादव", "मायावती", "स्थानीय नेता"],
    },
}

# Gorakhpur relevance anchors — article must match at least one
GORAKHPUR_ANCHORS = [
    "gorakhpur", "गोरखपुर", "gorakhnath", "गोरखनाथ",
    "brd medical", "ddu gorakhpur", "gida gorakhpur",
    "rapti gorakhpur", "rohini gorakhpur",
]


# ══════════════════════════════════════════════════════════════════
#  RSS SOURCES
# ══════════════════════════════════════════════════════════════════

RSS_SOURCES = [
    # English
    {"name": "Times of India – UP",
     "url":  "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms", "lang": "en"},
    {"name": "Hindustan Times – India",
     "url":  "https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml", "lang": "en"},
    {"name": "NDTV – UP/Uttarakhand",
     "url":  "https://feeds.feedburner.com/ndtvnews-uttar-pradesh", "lang": "en"},
    {"name": "India Today – Politics",
     "url":  "https://www.indiatoday.in/rss/1206514", "lang": "en"},
    {"name": "The Hindu – National",
     "url":  "https://www.thehindu.com/news/national/feeder/default.rss", "lang": "en"},
    {"name": "News18 – Politics",
     "url":  "https://www.news18.com/rss/politics.xml", "lang": "en"},
    {"name": "Firstpost – Politics",
     "url":  "https://www.firstpost.com/rss/politics.xml", "lang": "en"},
    {"name": "Indian Express – India",
     "url":  "https://indianexpress.com/section/india/feed/", "lang": "en"},
    {"name": "The Print – Politics",
     "url":  "https://theprint.in/category/politics/feed/", "lang": "en"},
    {"name": "Scroll – India",
     "url":  "https://scroll.in/feed", "lang": "en"},
    # Hindi
    {"name": "Jagran – UP",
     "url":  "https://www.jagran.com/rss/news-national-uttar-pradesh.xml", "lang": "hi"},
    {"name": "Amar Ujala – UP",
     "url":  "https://www.amarujala.com/rss/uttar-pradesh.xml", "lang": "hi"},
    {"name": "Navbharat Times",
     "url":  "https://navbharattimes.indiatimes.com/rssfeedsdefault.cms", "lang": "hi"},
    {"name": "Live Hindustan – UP",
     "url":  "https://www.livehindustan.com/rss/up-uttarakhand.xml", "lang": "hi"},
    {"name": "Dainik Bhaskar – UP",
     "url":  "https://www.bhaskar.com/rss-feed/1061/", "lang": "hi"},
    {"name": "Patrika – UP",
     "url":  "https://api.patrika.com/rss/uttar-pradesh", "lang": "hi"},
]

# Google News topic queries (dynamic - covers latest)
GOOGLE_NEWS_QUERIES = [
    ("gorakhpur development bjp",                "en"),
    ("gorakhpur unemployment jobs",              "en"),
    ("gorakhpur crime law order",                "en"),
    ("gorakhpur farmers sugarcane",              "en"),
    ("gorakhpur election 2024 2027",             "en"),
    ("yogi adityanath gorakhpur",                "en"),
    ("gorakhpur flood rapti",                    "en"),
    ("gorakhpur hospital healthcare",            "en"),
    ("गोरखपुर विकास चुनाव",                      "hi"),
    ("गोरखपुर बेरोजगारी किसान",                  "hi"),
    ("गोरखपुर भ्रष्टाचार अपराध",                "hi"),
    ("गोरखपुर योगी आदित्यनाथ",                  "hi"),
    ("गोरखपुर सपा भाजपा चुनाव",                 "hi"),
]


# ══════════════════════════════════════════════════════════════════
#  HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════════

def clean_html(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    return re.sub(r"\s+", " ", soup.get_text(separator=" ")).strip()

def safe_date(raw) -> str:
    if not raw:
        return datetime.now().isoformat()
    try:
        return dateparser.parse(str(raw), ignoretz=True).isoformat()
    except Exception:
        return datetime.now().isoformat()

def is_gorakhpur(text: str) -> bool:
    t = text.lower()
    return any(kw.lower() in t for kw in GORAKHPUR_ANCHORS)

def detect_topics(text: str) -> list:
    """Return list of matching election topics."""
    t = text.lower()
    matched = []
    for topic, kws in ELECTION_TOPICS.items():
        all_kws = kws.get("en", []) + kws.get("hi", [])
        if any(kw.lower() in t for kw in all_kws):
            matched.append(topic)
    return matched

def fetch_full_text(url: str, session: requests.Session) -> str:
    """Pull readable article body from a URL."""
    try:
        r = session.get(url, timeout=TIMEOUT)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        for sel in [
            "article", ".article-body", ".story-content",
            ".content-body", "[itemprop='articleBody']",
            ".storyContent", ".field-items", "#article-body",
        ]:
            node = soup.select_one(sel)
            if node:
                txt = " ".join(p.get_text() for p in node.find_all("p"))
                if len(txt) > 150:
                    return re.sub(r"\s+", " ", txt).strip()[:3000]
        # Fallback
        txt = " ".join(p.get_text() for p in soup.find_all("p") if len(p.get_text()) > 40)
        return re.sub(r"\s+", " ", txt).strip()[:3000]
    except Exception:
        return ""


# ══════════════════════════════════════════════════════════════════
#  SCRAPER CLASS
# ══════════════════════════════════════════════════════════════════

class GorakhpurElectionScraper:

    def __init__(self, fetch_full: bool = False):
        self.fetch_full = fetch_full
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.articles: list = []
        self.seen_urls: set = set()

    # ── Scrape one RSS source ───────────────────────────────────────
    def _scrape_rss(self, src: dict) -> list:
        results = []
        try:
            feed = feedparser.parse(src["url"])
            for entry in feed.entries[:30]:
                title   = getattr(entry, "title",   "")
                summary = getattr(entry, "summary", "")
                link    = getattr(entry, "link",    "")
                pub     = getattr(entry, "published",
                          getattr(entry, "updated", None))

                if link in self.seen_urls:
                    continue

                text = f"{title} {clean_html(summary)}"

                # Must mention Gorakhpur + at least one election topic
                if not is_gorakhpur(text):
                    continue
                topics = detect_topics(text)
                if not topics:
                    continue

                self.seen_urls.add(link)
                results.append({
                    "title":     title,
                    "summary":   clean_html(summary)[:500],
                    "url":       link,
                    "source":    src["name"],
                    "language":  src["lang"],
                    "published": safe_date(pub),
                    "topics":    topics,
                    "content":   "",
                    "scraped_at": datetime.now().isoformat(),
                })
        except Exception as e:
            print(f"  {Fore.RED}✗ {src['name']}: {e}{Style.RESET_ALL}")
        return results

    # ── Scrape Google News for a query ─────────────────────────────
    def _scrape_google(self, query: str, lang: str) -> list:
        q_enc = requests.utils.quote(query)
        url = (
            f"https://news.google.com/rss/search"
            f"?q={q_enc}&hl={'hi' if lang=='hi' else 'en-IN'}"
            f"&gl=IN&ceid={'IN:hi' if lang=='hi' else 'IN:en'}"
        )
        src = {"name": f"Google News: {query[:35]}", "url": url, "lang": lang}
        return self._scrape_rss(src)

    # ── Enrich with full body text ──────────────────────────────────
    def _enrich(self, art: dict) -> dict:
        if art["url"] and not art["content"]:
            art["content"] = fetch_full_text(art["url"], self.session)
            # Re-detect topics including full content
            full_text = f"{art['title']} {art['summary']} {art['content']}"
            art["topics"] = detect_topics(full_text) or art["topics"]
        return art

    # ── Main run ───────────────────────────────────────────────────
    def run(self) -> list:
        print(f"\n{Fore.CYAN}" + "-"*62)
        print("   Gorakhpur Election Scraper -- All Key Topics")
        print("-"*62 + f"{Style.RESET_ALL}\n")

        # 1. RSS feeds
        print(f"{Fore.YELLOW}[1/2] Scraping RSS feeds…{Style.RESET_ALL}")
        for src in RSS_SOURCES:
            arts = self._scrape_rss(src)
            self.articles.extend(arts)
            status = f"{Fore.GREEN}+{len(arts)}{Style.RESET_ALL}" if arts else f"{Fore.RED}0{Style.RESET_ALL}"
            print(f"      {src['name']:<38} {status}")
            time.sleep(DELAY)

        # 2. Google News queries
        print(f"\n{Fore.YELLOW}[2/2] Scraping Google News topic queries…{Style.RESET_ALL}")
        for query, lang in GOOGLE_NEWS_QUERIES:
            arts = self._scrape_google(query, lang)
            self.articles.extend(arts)
            status = f"{Fore.GREEN}+{len(arts)}{Style.RESET_ALL}" if arts else f"{Fore.RED}0{Style.RESET_ALL}"
            print(f"      [{lang}] {query:<42} {status}")
            time.sleep(DELAY)

        # 3. Optionally enrich
        if self.fetch_full and self.articles:
            total = len(self.articles)
            print(f"\n{Fore.YELLOW}Fetching full article text ({total} articles)…{Style.RESET_ALL}")
            for i, art in enumerate(self.articles, 1):
                print(f"  [{i:>3}/{total}] {art['title'][:58]}…", end="\r")
                self._enrich(art)
                time.sleep(0.8)
            print()

        return self.articles

    # ── Save to JSON ───────────────────────────────────────────────
    def save(self) -> str:
        os.makedirs("results", exist_ok=True)
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = f"results/gorakhpur_election_{ts}.json"
        payload = {
            "generated_at": datetime.now().isoformat(),
            "total_articles": len(self.articles),
            "topics_covered": list(ELECTION_TOPICS.keys()),
            "articles": self.articles,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return path

    # ── Console summary ────────────────────────────────────────────
    def print_summary(self):
        arts = self.articles
        if not arts:
            print(f"\n{Fore.RED}No articles scraped.{Style.RESET_ALL}")
            return

        # Count per topic
        topic_counts: dict = {}
        for a in arts:
            for t in a.get("topics", []):
                topic_counts[t] = topic_counts.get(t, 0) + 1

        # Count per source
        src_counts: dict = {}
        for a in arts:
            s = a["source"]
            src_counts[s] = src_counts.get(s, 0) + 1

        # Language split
        en = sum(1 for a in arts if a["language"] == "en")
        hi = sum(1 for a in arts if a["language"] == "hi")

        print(f"\n{Fore.CYAN}" + "-"*62)
        print("  SCRAPE COMPLETE -- SUMMARY")
        print("-"*62 + f"{Style.RESET_ALL}")
        print(f"  Total articles : {Fore.WHITE}{len(arts)}{Style.RESET_ALL}")
        print(f"  English        : {Fore.GREEN}{en}{Style.RESET_ALL}")
        print(f"  Hindi          : {Fore.YELLOW}{hi}{Style.RESET_ALL}")

        print(f"\n  {Fore.CYAN}Articles by Election Topic:{Style.RESET_ALL}")
        for topic, cnt in sorted(topic_counts.items(), key=lambda x: -x[1]):
            bar = "█" * min(cnt, 30)
            print(f"    {topic:<28} {Fore.GREEN}{bar} {cnt}{Style.RESET_ALL}")

        print(f"\n  {Fore.CYAN}Articles by Source:{Style.RESET_ALL}")
        for src, cnt in sorted(src_counts.items(), key=lambda x: -x[1]):
            print(f"    {src:<40} {Fore.WHITE}{cnt}{Style.RESET_ALL}")

        print(f"\n  {Fore.CYAN}Sample Headlines:{Style.RESET_ALL}")
        for a in arts[:8]:
            tlist = ", ".join(a["topics"][:2])
            print(f"    [{Fore.YELLOW}{tlist}{Style.RESET_ALL}] {a['title'][:65]}")
            print(f"       {Fore.CYAN}{a['source']}{Style.RESET_ALL} | {a['published'][:10]}")


# ══════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    fetch_full = "--full" in sys.argv

    scraper = GorakhpurElectionScraper(fetch_full=fetch_full)
    scraper.run()
    scraper.print_summary()
    path = scraper.save()
    print(f"\n  {Fore.GREEN}✔  Saved → {path}{Style.RESET_ALL}\n")

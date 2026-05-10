"""
Lightweight Article Scraper for Gorakhpur with Pro/Anti-BJP Sentiment
Focus: Scrape Gorakhpur articles and classify sentiment
"""

import feedparser
import requests
from datetime import datetime
from typing import List, Dict, Tuple
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
#  GORAKHPUR & SENTIMENT KEYWORDS
# ─────────────────────────────────────────────

GORAKHPUR_KEYWORDS = [
    # Exact matches
    "gorakhpur", "गोरखपुर", "gorkhapur",
    # Regional context (Uttar Pradesh, Eastern UP)
    "uttar pradesh", "उत्तर प्रदेश", "eastern up", "eastern uttar",
    # Key politicians
    "yogi", "योगी", "adityanath", "ravi kishan", "राविकिशन",
    # Election related
    "lok sabha", "assembly", "विधानसभा", "लोकसभा", "election", "चुनाव",
    # BJP-related (since most Gorakhpur sentiment is BJP-related)
    "bjp", "भाजपा", "saffron", "प्रधानमंत्री", "prime minister",
    # Regions near Gorakhpur
    "banaras", "varanasi", "काशी", "देवरिया", "पूर्वांचल"
]

PRO_BJP_KEYWORDS = [
    # English - BJP achievements/positive
    "bjp victory", "bjp wins", "bjp success", "bjp achievement", "bjp growth",
    "development under bjp", "bjp government strong", "bjp performance good", 
    "bjp government formation", "bjp elected", "bjp chosen", "yogi success",
    "yogi government", "yogi achievement", "yogi performance", "bjp stability",
    "bjp positive", "bjp support", "bjp expands", "bjp grows", "bjp dominates",
    # CM/Leader achievements
    "cm sworn in", "cm elected", "cm takes oath", "first bjp cm", "bjp cm",
    "leader elected", "government formation", "power", "victory", "won",
    # Hindi
    "भाजपा जीत", "भाजपा विजय", "भाजपा सफलता", "भाजपा विकास", "भाजपा शक्ति",
    "योगी जी", "योगी शक्ति", "योगी सफलता", "भाजपा अच्छा", "भाजपा बेहतर",
    "भाजपा चुना", "सरकार बनी", "शपथ ग्रहण"
]

ANTI_BJP_KEYWORDS = [
    # English - BJP challenges/negative
    "bjp failure", "bjp crisis", "bjp problem", "bjp controversy", "bjp corruption",
    "bjp criticism", "bjp attack", "anti-bjp", "against bjp", "bjp negative", 
    "bjp poor", "bjp weak", "yogi criticism", "yogi failure", "bjp faces crisis",
    "bjp loses", "bjp defeated", "bjp challenge", "bjp opposition",
    # Challenges/defeats
    "defeat", "loss", "opposition", "challenge", "crisis", "controversy", "corruption",
    "unseated", "dissolved", "resigned", "failed", "dropped",
    # Hindi
    "भाजपा असफल", "भाजपा संकट", "भाजपा विरोध", "भाजपा समस्या", "भाजपा भ्रष्टाचार",
    "योगी आलोचना", "योगी असफल", "भाजपा आलोचना", "भाजपा कमजोर", "भाजपा गलत",
    "हार", "संकट", "विरोध", "समस्या"
]

# ─────────────────────────────────────────────
#  RSS FEED SOURCES (25+ sources)
# ─────────────────────────────────────────────

RSS_FEEDS = [
    {"name": "TOI UP", "url": "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms"},
    {"name": "HT India", "url": "https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml"},
    {"name": "NDTV UP", "url": "https://feeds.feedburner.com/ndtvnews-uttar-pradesh"},
    {"name": "News18 Politics", "url": "https://www.news18.com/rss/politics.xml"},
    {"name": "India Today", "url": "https://www.indiatoday.in/rss/1206514"},
    {"name": "The Hindu", "url": "https://www.thehindu.com/news/national/feeder/default.rss"},
    {"name": "Indian Express", "url": "https://indianexpress.com/feed/"},
    {"name": "Deccan Chronicle", "url": "https://www.deccanchronicle.com/feed/"},
    {"name": "Business Standard", "url": "https://www.business-standard.com/feed/"},
    {"name": "Mint", "url": "https://www.livemint.com/feed/"},
    {"name": "Jagran UP", "url": "https://www.jagran.com/rss/news-national-uttar-pradesh.xml"},
    {"name": "Amar Ujala", "url": "https://www.amarujala.com/rss/uttar-pradesh.xml"},
    {"name": "NavBharat Times", "url": "https://navbharattimes.indiatimes.com/rssfeedsdefault.cms"},
    {"name": "LiveHindustan", "url": "https://www.livehindustan.com/rss/up-uttarakhand.xml"},
    {"name": "Dainik Bhaskar", "url": "https://www.bhaskar.com/feed/"},
    {"name": "Nai Duniya", "url": "https://www.naiduniya.com/rss/"},
    {"name": "UP Politics", "url": "https://www.thehindu.com/politics/feeder/default.rss"},
    {"name": "Elections India", "url": "https://www.deccanchronicle.com/elections/"},
    {"name": "Governance", "url": "https://indianexpress.com/section/india/"},
    {"name": "Economy & Jobs", "url": "https://www.thehindu.com/business/"},
    {"name": "Health", "url": "https://indianexpress.com/section/health/"},
    {"name": "Education", "url": "https://www.business-standard.com/category/current-affairs"},
    {"name": "Social News", "url": "https://www.livemint.com/news"},
    {"name": "Crime & Law", "url": "https://www.hindustantimes.com/feeds/rss/india-crime/rssfeed.xml"},
    {"name": "Farmer Issues", "url": "https://www.deccanchronicle.com/farming/"},
]

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


class ArticleCollector:
    """Lightweight scraper - collect Gorakhpur articles with Pro/Anti-BJP sentiment."""

    def __init__(self):
        self.articles = []
        self.total_fetched = 0
        self.scrape_time = None

    def is_gorakhpur_related(self, title: str, summary: str = "") -> bool:
        """Check if article is Gorakhpur-related (strict filter)."""
        text = (title + " " + summary).lower()
        return any(kw in text for kw in GORAKHPUR_KEYWORDS)

    def classify_sentiment(self, title: str, summary: str = "") -> str:
        """Classify article sentiment as Pro-BJP or Anti-BJP."""
        text = (title + " " + summary).lower()
        
        # Count keyword matches
        pro_count = sum(1 for kw in PRO_BJP_KEYWORDS if kw.lower() in text)
        anti_count = sum(1 for kw in ANTI_BJP_KEYWORDS if kw.lower() in text)
        
        # Additional pattern matching for sentiment indicators
        # Pro-BJP patterns: victory, wins, success, elected, govt formation, etc.
        pro_patterns = ["victory", "wins", "success", "elected", "sworn in", 
                       "takes oath", "forms government", "first cm", "chosen",
                       "dominat", "expand", "growth"]
        anti_patterns = ["defeat", "loss", "crisis", "resign", "dissolved", 
                        "opposition", "fail", "challenges", "controversies",
                        "unseated", "dropped", "unseat"]
        
        # Add pattern matches (case-insensitive)
        text_lower = text.lower()
        pro_count += sum(1 for pattern in pro_patterns if pattern in text_lower)
        anti_count += sum(1 for pattern in anti_patterns if pattern in text_lower)
        
        # If it mentions BJP government/CM formation - likely Pro-BJP
        if "bjp" in text_lower and ("government" in text_lower or "cm" in text_lower):
            if "crisis" not in text_lower and "resign" not in text_lower:
                pro_count += 2
        
        # Decision logic
        if pro_count > anti_count:
            return "Pro-BJP"
        elif anti_count > pro_count:
            return "Anti-BJP"
        else:
            return "Neutral"

    def scrape_feed(self, feed_url: str, source_name: str, articles_per_feed: int = 100) -> int:
        """Scrape single RSS feed and return article count."""
        count = 0
        try:
            logger.info(f"  Fetching from {source_name}…")
            feed = feedparser.parse(feed_url)
            
            for entry in feed.entries[:articles_per_feed]:
                title = entry.get("title", "")
                summary = entry.get("summary", "")
                
                # STRICT FILTER: Only include Gorakhpur-related articles
                if not self.is_gorakhpur_related(title, summary):
                    continue
                
                # Classify sentiment
                sentiment = self.classify_sentiment(title, summary)
                
                article = {
                    "source": source_name,
                    "title": title,
                    "url": entry.get("link", ""),
                    "summary": summary,
                    "published": entry.get("published", datetime.now().isoformat()),
                    "sentiment": sentiment,
                }
                
                # Skip if duplicate URL exists
                if not any(a["url"] == article["url"] for a in self.articles):
                    self.articles.append(article)
                    count += 1
                
        except Exception as e:
            logger.warning(f"    ⚠️  Error: {str(e)[:50]}")
        
        if count > 0:
            logger.info(f"    ✅ Added {count} articles from {source_name}")
        return count

    def scrape_all(self, articles_per_feed: int = 100, target: int = 500) -> List[Dict]:
        """Scrape all RSS feeds."""
        start_time = datetime.now()
        logger.info(f"\n🔄 SCRAPING STARTED")
        logger.info(f"📰 Target: {target}+ articles from {len(RSS_FEEDS)} sources")
        logger.info(f"📊 Fetching ~{articles_per_feed} articles per feed\n")
        
        total_added = 0
        for i, feed in enumerate(RSS_FEEDS, 1):
            added = self.scrape_feed(feed["url"], feed["name"], articles_per_feed)
            total_added += added
            logger.info(f"  Progress: {len(self.articles)} articles collected")
            
            if len(self.articles) >= target:
                logger.info(f"  ✅ Reached target! Stopping…")
                break
        
        self.scrape_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"\n{'='*80}")
        logger.info(f"✅ SCRAPING COMPLETE")
        logger.info(f"{'='*80}")
        logger.info(f"Total articles collected: {len(self.articles)}")
        logger.info(f"Time taken: {self.scrape_time:.1f} seconds")
        logger.info(f"Average: {len(self.articles)/self.scrape_time:.1f} articles/sec")
        
        return self.articles

    def print_summary(self):
        """Print collected articles summary."""
        if not self.articles:
            print("No articles collected yet.")
            return
        
        print(f"\n{'='*80}")
        print(f"ARTICLES COLLECTION SUMMARY")
        print(f"{'='*80}")
        print(f"\nTotal articles: {len(self.articles)}")
        
        # Group by source
        sources_dict = {}
        for article in self.articles:
            source = article["source"]
            sources_dict[source] = sources_dict.get(source, 0) + 1
        
        print(f"\nArticles by source ({len(sources_dict)} sources):")
        for source in sorted(sources_dict.keys(), key=lambda x: sources_dict[x], reverse=True):
            print(f"  {source:<20} : {sources_dict[source]:>3} articles")
        
        # Sample articles
        print(f"\n\nSample Articles (first 5):")
        print("-" * 80)
        for i, article in enumerate(self.articles[:5], 1):
            print(f"\n{i}. {article['title'][:70]}")
            print(f"   Source: {article['source']}")
            print(f"   URL: {article['url'][:60]}...")
            print(f"   Date: {article['published'][:10]}")

    def export_to_json(self, filename: str = "articles_collection.json"):
        """Export articles to JSON file."""
        import json
        data = {
            "collected_at": datetime.now().isoformat(),
            "total_articles": len(self.articles),
            "scrape_time_seconds": self.scrape_time,
            "articles": self.articles
        }
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"✅ Exported {len(self.articles)} articles to {filename}")
        return filename

    def export_to_csv(self, filename: str = "articles_collection.csv"):
        """Export articles to CSV file with sentiment."""
        import csv
        if not self.articles:
            print("No articles to export.")
            return
        
        fieldnames = ["source", "title", "sentiment", "url", "published"]
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(self.articles)
        
        logger.info(f"✅ Exported {len(self.articles)} articles to {filename}")
        return filename

    def search_articles(self, keyword: str) -> List[Dict]:
        """Search articles by keyword."""
        keyword_lower = keyword.lower()
        results = [
            a for a in self.articles
            if keyword_lower in a["title"].lower() or keyword_lower in a["summary"].lower()
        ]
        return results

    def filter_by_source(self, source_name: str) -> List[Dict]:
        """Get articles from specific source."""
        return [a for a in self.articles if a["source"].lower() == source_name.lower()]

    def get_latest(self, limit: int = 10) -> List[Dict]:
        """Get latest articles."""
        return self.articles[-limit:]

    def get_topics_coverage(self) -> Dict:
        """Show sentiment breakdown and topics."""
        topics = {
            "Pro-BJP": len([a for a in self.articles if a.get("sentiment") == "Pro-BJP"]),
            "Anti-BJP": len([a for a in self.articles if a.get("sentiment") == "Anti-BJP"]),
            "Neutral": len([a for a in self.articles if a.get("sentiment") == "Neutral"]),
        }
        return topics


def main():
    """Main execution."""
    print("\n" + "="*80)
    print("LIGHTWEIGHT ARTICLE COLLECTOR - Gorakhpur News")
    print("="*80)
    print("\nMode: Scraping articles only (no sentiment analysis)")
    print("Focus: Collect maximum articles and store in memory\n")
    
    collector = ArticleCollector()
    
    # Ask user for target
    try:
        target = int(input("How many articles to collect? (default: 500): ").strip() or "500")
    except:
        target = 500
    
    try:
        per_feed = int(input("Articles per feed? (default: 100): ").strip() or "100")
    except:
        per_feed = 100
    
    # Scrape
    articles = collector.scrape_all(articles_per_feed=per_feed, target=target)
    
    # Show summary
    collector.print_summary()
    
    # Show topic coverage
    print(f"\n\nTopic Coverage:")
    print("-" * 80)
    coverage = collector.get_topics_coverage()
    for topic, count in sorted(coverage.items(), key=lambda x: x[1], reverse=True):
        print(f"  {topic:<20}: {count:>3} articles")
    
    # Export options
    print(f"\n\nExport Options:")
    print("-" * 80)
    print("1. Export to JSON (for analysis)")
    print("2. Export to CSV (for Excel)")
    print("3. Both")
    print("4. Skip export")
    
    choice = input("\nChoice (1-4): ").strip()
    
    if choice in ["1", "3"]:
        collector.export_to_json()
    if choice in ["2", "3"]:
        collector.export_to_csv()
    
    print(f"\n✅ Done! {len(collector.articles)} articles ready in memory")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")

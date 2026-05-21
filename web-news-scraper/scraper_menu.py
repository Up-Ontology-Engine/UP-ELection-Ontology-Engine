"""
Interactive Menu for Simple Article Scraper
No sentiment analysis - just collect & store articles
"""

import sys
from simple_scraper import ArticleCollector


def print_banner():
    print("""
╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║    📰 GORAKHPUR ARTICLE SCRAPER - Pro/Anti-BJP SENTIMENT ANALYSIS 📰        ║
║                                                                            ║
║           Gorakhpur-Related Articles · Pro-BJP vs Anti-BJP Sentiment       ║
║                    Collect → Analyze → Export → Filter                    ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
    """)


def show_menu():
    print("\n" + "="*80)
    print("MAIN MENU")
    print("="*80)
    print("""
    1. 📥 Quick Scrape (500 articles, ~2 min)
    2. 📥 Custom Scrape (user-defined count)
    3. 🔍 Search & Filter Articles
    4. 📊 Show Sentiment Statistics
    5. 💾 Export Articles
    6. ℹ️  Show Current Collection
    7. ❌ Exit
    """)


def scrape_articles(collector, count=500, per_feed=100):
    """Execute scraping."""
    print(f"\n⏳ Scraping {count}+ articles…")
    collector.scrape_all(articles_per_feed=per_feed, target=count)
    return collector


def search_menu(collector):
    """Search interface."""
    if not collector.articles:
        print("\n⚠️  No articles collected. Scrape first!")
        return
    
    print("\n" + "="*80)
    print("SEARCH & FILTER")
    print("="*80)
    
    while True:
        print("""
Search options:
  1. Search by keyword
  2. Filter by Pro-BJP sentiment
  3. Filter by Anti-BJP sentiment
  4. Filter by Neutral sentiment
  5. View all articles
  6. Back to menu
        """)
        
        choice = input("Choice (1-6): ").strip()
        
        if choice == '1':
            keyword = input("Enter search keyword: ").strip()
            results = collector.search_articles(keyword)
            
        elif choice == '2':
            results = [a for a in collector.articles if a.get("sentiment") == "Pro-BJP"]
            
        elif choice == '3':
            results = [a for a in collector.articles if a.get("sentiment") == "Anti-BJP"]
            
        elif choice == '4':
            results = [a for a in collector.articles if a.get("sentiment") == "Neutral"]
            
        elif choice == '5':
            results = collector.articles
            
        elif choice == '6':
            break
        else:
            print("Invalid choice")
            continue
        
        if not results:
            print(f"\n❌ No articles found")
            continue
        
        print(f"\n📰 Found {len(results)} articles:")
        print("-"*80)
        
        for i, article in enumerate(results[:15], 1):
            sentiment_emoji = "✅" if article.get("sentiment") == "Pro-BJP" else "❌" if article.get("sentiment") == "Anti-BJP" else "➖"
            print(f"\n{i}. [{sentiment_emoji}] {article['title'][:70]}")
            print(f"   Sentiment: {article.get('sentiment')}")
            print(f"   Source: {article['source']}")
            print(f"   URL: {article['url'][:60]}...")
        
        if len(results) > 15:
            print(f"\n... and {len(results)-15} more articles")


def statistics_menu(collector):
    """Show statistics."""
    if not collector.articles:
        print("\n⚠️  No articles collected yet.")
        return
    
    print("\n" + "="*80)
    print("SENTIMENT STATISTICS - Gorakhpur")
    print("="*80)
    
    print(f"\nTotal articles: {len(collector.articles)}")
    
    # Sentiment breakdown
    sentiments = {}
    for article in collector.articles:
        sentiment = article.get("sentiment", "Unknown")
        sentiments[sentiment] = sentiments.get(sentiment, 0) + 1
    
    print(f"\n📊 Sentiment Breakdown:")
    pro_count = sentiments.get("Pro-BJP", 0)
    anti_count = sentiments.get("Anti-BJP", 0)
    neutral_count = sentiments.get("Neutral", 0)
    
    print(f"  ✅ Pro-BJP       : {pro_count:>4} articles ({pro_count*100//len(collector.articles):>2}%)")
    print(f"  ❌ Anti-BJP      : {anti_count:>4} articles ({anti_count*100//len(collector.articles):>2}%)")
    print(f"  ➖ Neutral       : {neutral_count:>4} articles ({neutral_count*100//len(collector.articles):>2}%)")
    
    # By source
    sources = {}
    for article in collector.articles:
        source = article["source"]
        sources[source] = sources.get(source, 0) + 1
    
    print(f"\nArticles by source ({len(sources)} sources):")
    for source in sorted(sources.keys(), key=lambda x: sources[x], reverse=True)[:15]:
        print(f"  {source:<25}: {sources[source]:>4} articles")


def export_menu(collector):
    """Export interface."""
    if not collector.articles:
        print("\n⚠️  No articles to export.")
        return
    
    print("\n" + "="*80)
    print("EXPORT OPTIONS")
    print("="*80)
    print(f"""
    1. Export to JSON (articles_collection.json)
    2. Export to CSV (articles_collection.csv)
    3. Export both
    4. Cancel
    """)
    
    choice = input("Choice (1-4): ").strip()
    
    if choice == '1':
        collector.export_to_json()
    elif choice == '2':
        collector.export_to_csv()
    elif choice == '3':
        collector.export_to_json()
        collector.export_to_csv()
    else:
        print("Cancelled.")


def show_collection(collector):
    """Display current collection."""
    if not collector.articles:
        print("\n⚠️  No articles collected yet.")
        return
    
    print("\n" + "="*80)
    print("CURRENT COLLECTION")
    print("="*80)
    
    collector.print_summary()
    
    # Ask to show more
    if len(collector.articles) > 5:
        try:
            show_count = int(input(f"\nShow how many articles? (max {len(collector.articles)}): ").strip() or "10")
            show_count = min(show_count, len(collector.articles))
            
            print("\n" + "-"*80)
            for i, article in enumerate(collector.articles[:show_count], 1):
                sentiment_emoji = "✅" if article.get("sentiment") == "Pro-BJP" else "❌" if article.get("sentiment") == "Anti-BJP" else "➖"
                print(f"\n{i}. [{sentiment_emoji}] {article['title']}")
                print(f"   Sentiment: {article.get('sentiment')}")
                print(f"   Source: {article['source']}")
                print(f"   Published: {article['published'][:10]}")
                print(f"   URL: {article['url'][:70]}")
        except:
            pass


def main():
    """Main menu loop."""
    print_banner()
    collector = ArticleCollector()
    
    while True:
        show_menu()
        choice = input("Choice (1-7): ").strip()
        
        if choice == '1':
            collector = scrape_articles(collector, count=500, per_feed=100)
        
        elif choice == '2':
            try:
                count = int(input("How many articles? (default: 500): ").strip() or "500")
                per_feed = int(input("Articles per feed? (default: 100): ").strip() or "100")
                collector = scrape_articles(collector, count=count, per_feed=per_feed)
            except ValueError:
                print("❌ Invalid input")
        
        elif choice == '3':
            search_menu(collector)
        
        elif choice == '4':
            statistics_menu(collector)
        
        elif choice == '5':
            export_menu(collector)
        
        elif choice == '6':
            show_collection(collector)
        
        elif choice == '7':
            print("\n👋 Goodbye!\n")
            sys.exit(0)
        
        else:
            print("\n❌ Invalid choice")
        
        input("\nPress Enter to continue…")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

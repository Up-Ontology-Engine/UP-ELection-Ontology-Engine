"""
Indian Newspaper Data Scraper
Scrapes news articles from major Indian news sources about elections
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import List, Dict
import logging
import re

try:
    import requests
    from bs4 import BeautifulSoup
    WEB_AVAILABLE = True
except ImportError:
    WEB_AVAILABLE = False

try:
    import feedparser
    FEED_AVAILABLE = True
except ImportError:
    FEED_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NewspaperScraper:
    """Scrape news from Indian news websites"""
    
    def __init__(self):
        self.output_dir = 'data/newspapers'
        os.makedirs(self.output_dir, exist_ok=True)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # Major Indian news sources
        self.sources = {
            'theprint': 'https://theprint.in',
            'indianexpress': 'https://indianexpress.com',
            'thehindu': 'https://thehindu.com',
            'deccan': 'https://www.deccanherald.com',
            'outlookindia': 'https://www.outlookindia.com',
            'aajtak': 'https://aajtak.intoday.in',
            'bhaskar': 'https://www.bhaskar.com',
        }
    
    def scrape_theprint(self, query: str = 'election uttar pradesh') -> List[Dict]:
        """Scrape The Print using RSS feed"""
        if not FEED_AVAILABLE:
            logger.warning("feedparser not installed. Run: pip install feedparser")
            return []
        
        articles = []
        urls = [
            'https://theprint.in/india/feed/',
            'https://theprint.in/politics/feed/',
        ]
        
        for url in urls:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:50]:
                    if 'election' in entry.title.lower() or 'up' in entry.title.lower():
                        articles.append({
                            'source': 'The Print',
                            'title': entry.title,
                            'link': entry.link,
                            'published': entry.get('published', ''),
                            'summary': entry.get('summary', '')[:500],
                        })
            except Exception as e:
                logger.error(f"Error scraping The Print: {e}")
        
        return articles
    
    def scrape_indianexpress(self, keyword: str = 'election') -> List[Dict]:
        """Scrape Indian Express"""
        articles = []
        
        try:
            url = f'https://indianexpress.com/search/{keyword}/'
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find article containers (adjust selector based on actual HTML structure)
            for article in soup.find_all('div', class_='articles')[0:50]:
                try:
                    title = article.find('h2')
                    link = article.find('a')
                    date = article.find('span', class_='date')
                    
                    if title and link:
                        articles.append({
                            'source': 'Indian Express',
                            'title': title.text.strip(),
                            'link': link.get('href', ''),
                            'published': date.text.strip() if date else '',
                        })
                except Exception as e:
                    logger.debug(f"Error parsing article: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error scraping Indian Express: {e}")
        
        return articles
    
    def scrape_thehindu(self, query: str = 'election') -> List[Dict]:
        """Scrape The Hindu"""
        articles = []
        
        try:
            # The Hindu uses RSS feeds
            if FEED_AVAILABLE:
                feed_url = f'https://www.thehindu.com/search/?q={query}&sort=recent'
                feed = feedparser.parse(feed_url)
                
                for entry in feed.entries[:50]:
                    articles.append({
                        'source': 'The Hindu',
                        'title': entry.title,
                        'link': entry.link,
                        'published': entry.get('published', ''),
                        'summary': entry.get('summary', '')[:500],
                    })
        except Exception as e:
            logger.error(f"Error scraping The Hindu: {e}")
        
        return articles
    
    def scrape_bhaskar_election_news(self) -> List[Dict]:
        """Scrape Dainik Bhaskar election news"""
        articles = []
        
        try:
            url = 'https://www.bhaskar.com/elections/'
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find news items
            for item in soup.find_all('div', class_='news-item')[0:50]:
                try:
                    link = item.find('a')
                    title = item.find('h2') or item.find('h3')
                    
                    if link and title:
                        articles.append({
                            'source': 'Dainik Bhaskar',
                            'title': title.text.strip(),
                            'link': link.get('href', ''),
                            'published': datetime.now().isoformat(),
                        })
                except Exception as e:
                    logger.debug(f"Error parsing Bhaskar article: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error scraping Dainik Bhaskar: {e}")
        
        return articles
    
    def scrape_aajtak_elections(self) -> List[Dict]:
        """Scrape Aaj Tak election coverage"""
        articles = []
        
        try:
            url = 'https://aajtak.intoday.in/elections/'
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find stories
            for story in soup.find_all('div', class_='story')[0:50]:
                try:
                    link = story.find('a')
                    headline = story.find('h3')
                    
                    if link and headline:
                        articles.append({
                            'source': 'Aaj Tak',
                            'title': headline.text.strip(),
                            'link': link.get('href', ''),
                            'published': datetime.now().isoformat(),
                        })
                except Exception as e:
                    logger.debug(f"Error parsing Aaj Tak article: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error scraping Aaj Tak: {e}")
        
        return articles
    
    def extract_article_content(self, article_url: str) -> Dict:
        """Extract full article content"""
        try:
            response = requests.get(article_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(['script', 'style']):
                script.decompose()
            
            # Extract text
            paragraphs = soup.find_all('p')
            content = '\n'.join([p.text.strip() for p in paragraphs])
            
            return {
                'url': article_url,
                'content': content[:2000],  # First 2000 chars
                'scraped_at': datetime.now().isoformat(),
            }
        
        except Exception as e:
            logger.error(f"Error extracting content from {article_url}: {e}")
            return None
    
    def scrape_all_sources(self) -> List[Dict]:
        """Scrape all configured news sources"""
        all_articles = []
        
        logger.info("Scraping The Print...")
        all_articles.extend(self.scrape_theprint())
        time.sleep(2)
        
        logger.info("Scraping Indian Express...")
        all_articles.extend(self.scrape_indianexpress())
        time.sleep(2)
        
        logger.info("Scraping The Hindu...")
        all_articles.extend(self.scrape_thehindu())
        time.sleep(2)
        
        logger.info("Scraping Dainik Bhaskar...")
        all_articles.extend(self.scrape_bhaskar_election_news())
        time.sleep(2)
        
        logger.info("Scraping Aaj Tak...")
        all_articles.extend(self.scrape_aajtak_elections())
        
        # Remove duplicates based on title
        unique_articles = {}
        for article in all_articles:
            key = article['title'].lower()
            if key not in unique_articles:
                unique_articles[key] = article
        
        all_articles = list(unique_articles.values())
        
        # Save to file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"{self.output_dir}/election_news_{timestamp}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_articles, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved {len(all_articles)} articles to {output_file}")
        return all_articles
    
    def scrape_uttar_pradesh_news(self) -> List[Dict]:
        """Scrape UP-specific news"""
        queries = [
            'uttar pradesh election',
            'gorakhpur election',
            'up election 2024',
            'उत्तर प्रदेश चुनाव',
            'गोरखपुर चुनाव',
        ]
        
        all_articles = []
        for query in queries:
            logger.info(f"Searching for: {query}")
            articles = self.scrape_indianexpress(keyword=query)
            all_articles.extend(articles)
            time.sleep(1)
        
        return all_articles


class NewsAggregator:
    """Aggregate and analyze news from multiple sources"""
    
    def __init__(self):
        self.output_dir = 'data/newspapers'
        os.makedirs(self.output_dir, exist_ok=True)
    
    def analyze_coverage(self, articles: List[Dict]) -> Dict:
        """Analyze news coverage patterns"""
        analysis = {
            'total_articles': len(articles),
            'sources': {},
            'topics': {},
            'timeline': {},
        }
        
        for article in articles:
            source = article.get('source', 'Unknown')
            analysis['sources'][source] = analysis['sources'].get(source, 0) + 1
        
        return analysis
    
    def save_analysis(self, articles: List[Dict]):
        """Save analysis report"""
        analysis = self.analyze_coverage(articles)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"{self.output_dir}/news_analysis_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'analysis': analysis,
                'total_articles': len(articles),
                'sources_breakdown': analysis['sources'],
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Analysis saved to {output_file}")


def scrape_all_news_sources():
    """Main function to scrape all news sources"""
    scraper = NewspaperScraper()
    articles = scraper.scrape_all_sources()
    
    aggregator = NewsAggregator()
    aggregator.save_analysis(articles)
    
    logger.info(f"Total articles scraped: {len(articles)}")
    return articles


if __name__ == '__main__':
    if not WEB_AVAILABLE:
        print("Error: requests and beautifulsoup4 required")
        print("Install with: pip install requests beautifulsoup4 feedparser")
    else:
        scrape_all_news_sources()

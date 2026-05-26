# Election Data Scrapers

Complete scraping suite for YouTube videos, comments, and Indian newspapers for election data.

## Setup

### 1. Install Dependencies

```bash
pip install google-api-python-client
pip install yt-dlp
pip install requests beautifulsoup4
pip install feedparser
```

Or install from requirements:
```bash
pip install -r scraper_requirements.txt
```

### 2. Set Up YouTube API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable YouTube Data API v3
4. Create an API key (restricted to YouTube API)
5. Set environment variable:
   ```bash
   export YOUTUBE_API_KEY="your_api_key_here"
   ```

Or add to `.env`:
```
YOUTUBE_API_KEY=your_api_key_here
```

## Scripts Overview

### 1. YouTube Videos Scraper
Scrapes video metadata and statistics for election-related content.

**File:** `youtube_videos_scraper.py`

**Features:**
- Search videos by keywords
- Extract video statistics (views, likes, comments)
- Support for multiple queries
- Bilingual search (English + Hindi)
- Rate limiting to respect API quotas

**Usage:**
```bash
python scripts/youtube_videos_scraper.py
```

**Output:** `data/yt_cache/youtube_videos_YYYYMMDD_HHMMSS.json`

### 2. YouTube Comments Scraper
Extracts comments and replies from videos.

**File:** `youtube_comments_scraper.py`

**Features:**
- Fetch top-level comments and replies
- Extract comment metadata (likes, timestamps, author)
- Sentiment analysis
- Entity extraction (mentions, hashtags, parties)

**Usage:**
```python
from scripts.youtube_comments_scraper import YouTubeCommentsScraper

scraper = YouTubeCommentsScraper()
comments = scraper.scrape_multiple_videos(['video_id_1', 'video_id_2'])

# Analyze sentiment
sentiment = scraper.analyze_sentiment(comments)

# Extract mentions
mentions = scraper.extract_mentions(comments)
```

**Output:** `data/yt_cache/youtube_comments_YYYYMMDD_HHMMSS.json`

### 3. Newspaper Scraper
Collects news articles from major Indian news sources.

**File:** `newspaper_scraper.py`

**Supported Sources:**
- The Print
- Indian Express
- The Hindu
- Dainik Bhaskar
- Aaj Tak
- Deccan Herald
- Outlook India

**Features:**
- Multi-source scraping
- RSS feed parsing
- Full article content extraction
- Duplicate removal
- Coverage analysis

**Usage:**
```python
from scripts.newspaper_scraper import NewspaperScraper, NewsAggregator

scraper = NewspaperScraper()
articles = scraper.scrape_all_sources()

# Or scrape UP-specific news
up_articles = scraper.scrape_uttar_pradesh_news()

# Analyze coverage
aggregator = NewsAggregator()
aggregator.save_analysis(articles)
```

**Output:** `data/newspapers/election_news_YYYYMMDD_HHMMSS.json`

### 4. Master Orchestrator
Coordinates all scrapers in a single workflow.

**File:** `master_scraper_orchestrator.py`

**Usage:**
```bash
# Run all scrapers
python scripts/master_scraper_orchestrator.py

# Run with config file
python scripts/master_scraper_orchestrator.py --config scripts/scraper_config.json

# Skip specific scrapers
python scripts/master_scraper_orchestrator.py --skip-videos --skip-comments

# Run only newspaper scraper
python scripts/master_scraper_orchestrator.py --newspaper-only

# Run only YouTube scrapers
python scripts/master_scraper_orchestrator.py --youtube-only
```

**Output:** `data/scraping_logs/scraping_log_YYYYMMDD_HHMMSS.json`

## Configuration

Edit `scripts/scraper_config.json` to customize:

```json
{
  "youtube_api_key": "your_api_key",
  "max_videos": 100,
  "max_comments_per_video": 200,
  "max_articles": 300,
  "queries": {
    "youtube": ["query1", "query2"],
    "news": ["query1", "query2"]
  },
  "news_sources": ["theprint", "indianexpress", "thehindu"]
}
```

## Output Formats

### YouTube Videos
```json
{
  "video_id": "dQw4w9WgXcQ",
  "title": "Video Title",
  "description": "...",
  "channel": "Channel Name",
  "published_at": "2024-01-15T10:30:00Z",
  "thumbnail": "https://...",
  "views": 150000,
  "likes": 5000,
  "comments_count": 320,
  "duration": "PT10M30S"
}
```

### YouTube Comments
```json
{
  "video_id": "dQw4w9WgXcQ",
  "comment_id": "UgxL...",
  "author": "User Name",
  "text": "Comment text",
  "likes": 45,
  "published_at": "2024-01-15T15:30:00Z",
  "is_reply": false,
  "reply_count": 3
}
```

### News Articles
```json
{
  "source": "The Print",
  "title": "Article Title",
  "link": "https://...",
  "published": "2024-01-15",
  "summary": "Article summary..."
}
```

## API Rate Limits

YouTube API quotas:
- Free tier: 10,000 units/day
- Each search: ~100 units
- Each video statistics: ~1 unit
- Each comment thread: ~1 unit

The scrapers include rate limiting. Adjust delays in `scraper_config.json`:
```json
"rate_limiting": {
  "youtube_api_delay_seconds": 1,
  "web_scrape_delay_seconds": 2
}
```

## Troubleshooting

### YouTube API Key Issues
```bash
# Verify API key
export YOUTUBE_API_KEY="your_key"
python -c "from googleapiclient.discovery import build; print('API OK')"
```

### Web Scraping Issues
- Add User-Agent headers (already done)
- Increase delays between requests
- Check if websites block scraping
- Use VPN if rate limited

### Large Dataset Handling
- Use pagination (already implemented)
- Filter by date range
- Split queries
- Process in batches

## Data Storage

Scraped data is stored in:
- `data/yt_cache/` - YouTube data
- `data/newspapers/` - News articles
- `data/scraping_logs/` - Execution logs

## Integration with Ontology Engine

To integrate with the election ontology:

```python
from scripts.youtube_videos_scraper import YouTubeVideoScraper
from etl.data_ingestion import SourceIngester

# Scrape data
scraper = YouTubeVideoScraper()
videos = scraper.scrape_search_results(queries=['election'])

# Ingest into knowledge graph
ingester = SourceIngester()
ingester.process_youtube_videos(videos)
```

## Advanced Usage

### Custom Queries
```python
from scripts.newspaper_scraper import NewspaperScraper

scraper = NewspaperScraper()
articles = scraper.scrape_indianexpress('custom-query')
```

### Sentiment Analysis
```python
from scripts.youtube_comments_scraper import YouTubeCommentsScraper

scraper = YouTubeCommentsScraper()
comments = scraper.scrape_multiple_videos(['video_id'])

# Analyze
sentiment = scraper.analyze_sentiment(comments)
print(f"Positive: {sentiment['positive_ratio']:.1%}")
```

### Entity Extraction
```python
mentions = scraper.extract_mentions(comments)
print(f"Party mentions: {mentions['parties']}")
print(f"Popular hashtags: {mentions['hashtags']}")
```

## Scheduling

Schedule daily scraping using cron:

```bash
# Run daily at 6 AM
0 6 * * * cd /path/to/project && python scripts/master_scraper_orchestrator.py >> logs/scraper.log 2>&1
```

Or use APScheduler:
```python
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()
scheduler.add_job(scrape_all_news_sources, 'cron', hour=6)
scheduler.start()
```

## Performance Tips

1. **Batch Processing**: Scrape multiple videos in one session
2. **Caching**: Check if data already exists before scraping
3. **Parallel Requests**: Use threading for I/O-bound web scraping
4. **Database**: Store in MongoDB for fast querying
5. **Indexing**: Create indexes on source and date fields

## License

Election data scrapers for UP-ELection-Ontology-Engine

## Support

For issues:
1. Check rate limits
2. Verify API keys
3. Test with sample queries
4. Check logs in `data/scraping_logs/`

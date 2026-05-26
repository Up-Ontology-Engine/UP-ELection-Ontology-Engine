# Complete Scraping Guide for UP Election Ontology

## Overview

This guide provides complete instructions for scraping YouTube videos, comments, and newspaper articles for the UP Election Ontology project.

## Quick Start (5 minutes)

### 1. Setup Environment

```bash
cd /Users/aryansingh/Documents/UP-ELection-Ontology-Engine
bash scripts/setup_scrapers.sh
```

### 2. Configure YouTube API

```bash
# Get your API key from https://console.cloud.google.com/
export YOUTUBE_API_KEY="your_key_here"
```

### 3. Run All Scrapers

```bash
python scripts/master_scraper_orchestrator.py
```

## Detailed Components

### 1. YouTube Videos Scraper
**Purpose:** Collect video metadata and engagement metrics

**What it does:**
- Searches YouTube for election-related videos
- Extracts: title, description, channel, views, likes, comments
- Supports bilingual queries (English + Hindi)
- Respects API rate limits

**Example:**
```python
from scripts.youtube_videos_scraper import YouTubeVideoScraper

scraper = YouTubeVideoScraper(api_key="YOUR_API_KEY")
videos = scraper.scrape_search_results(
    queries=['उत्तर प्रदेश चुनाव', 'Gorakhpur election'],
    max_results=50
)

# Videos saved to: data/yt_cache/youtube_videos_*.json
```

**Sample Output:**
```json
[
  {
    "video_id": "abc123xyz",
    "title": "UP Election 2024 Coverage",
    "channel": "News Channel",
    "published_at": "2024-01-15T10:30:00Z",
    "views": 150000,
    "likes": 5000,
    "comments_count": 320
  }
]
```

---

### 2. YouTube Comments Scraper
**Purpose:** Extract public opinions from video comments

**What it does:**
- Fetches top-level comments and replies
- Extracts sentiment (basic analysis)
- Identifies entities: parties, locations, politicians
- Extracts hashtags and mentions

**Example:**
```python
from scripts.youtube_comments_scraper import YouTubeCommentsScraper

scraper = YouTubeCommentsScraper(api_key="YOUR_API_KEY")

# Get comments from multiple videos
video_ids = ['abc123', 'def456']
comments = scraper.scrape_multiple_videos(video_ids)

# Analyze sentiment
sentiment = scraper.analyze_sentiment(comments)
# Output: {'total_comments': 500, 'positive': 0.65, 'negative': 0.20}

# Extract mentions
mentions = scraper.extract_mentions(comments)
# Output: {'parties': {'BJP': 120, 'SP': 85}, 'hashtags': ['#election', ...]}
```

**Sample Output:**
```json
[
  {
    "video_id": "abc123",
    "comment_id": "Ugx...",
    "author": "User Name",
    "text": "Great election coverage!",
    "likes": 45,
    "published_at": "2024-01-15T15:30:00Z",
    "is_reply": false
  }
]
```

---

### 3. Newspaper Scraper
**Purpose:** Aggregate election news from Indian sources

**Supported Sources:**
1. **The Print** - Independent journalism
2. **Indian Express** - National daily
3. **The Hindu** - South Indian perspective
4. **Dainik Bhaskar** - Hindi coverage
5. **Aaj Tak** - Broadcast news archive
6. **Deccan Herald** - Business & politics
7. **Outlook India** - News & analysis

**Example:**
```python
from scripts.newspaper_scraper import NewspaperScraper, NewsAggregator

scraper = NewspaperScraper()

# Scrape all sources
articles = scraper.scrape_all_sources()

# Or scrape UP-specific news
up_articles = scraper.scrape_uttar_pradesh_news()

# Analyze coverage
aggregator = NewsAggregator()
aggregator.save_analysis(articles)
```

**Sample Output:**
```json
[
  {
    "source": "The Print",
    "title": "UP Election: Gorakhpur Seat Analysis",
    "link": "https://...",
    "published": "2024-01-15",
    "summary": "Gorakhpur constituency analysis..."
  }
]
```

---

### 4. Master Orchestrator
**Purpose:** Coordinate all scrapers in one workflow

**Usage:**
```bash
# Run all scrapers
python scripts/master_scraper_orchestrator.py

# Run with custom config
python scripts/master_scraper_orchestrator.py --config scripts/scraper_config.json

# Skip specific scrapers
python scripts/master_scraper_orchestrator.py --skip-videos --skip-comments

# Newspaper only
python scripts/master_scraper_orchestrator.py --newspaper-only

# YouTube only
python scripts/master_scraper_orchestrator.py --youtube-only
```

**Output Log:**
```json
{
  "start_time": "2024-01-15T10:00:00Z",
  "end_time": "2024-01-15T10:45:00Z",
  "duration_seconds": 2700,
  "results": {
    "youtube_videos": {"status": "success", "videos_scraped": 150},
    "youtube_comments": {"status": "success", "comments_scraped": 5000},
    "newspaper": {"status": "success", "articles_scraped": 320}
  }
}
```

---

### 5. Data Processor
**Purpose:** Clean and normalize scraped data for ontology ingestion

**What it does:**
- Normalizes data structure across sources
- Extracts entities (politicians, parties, locations)
- Identifies language
- Adds ingestion metadata

**Example:**
```python
from scripts.scraped_data_processor import ScrapedDataProcessor

processor = ScrapedDataProcessor()

# Process all scraped data
report = processor.process_all()

# Results saved to: data/processed/
# Generated report: data/processed/ingestion_report.json
```

**Normalized Format:**
```json
{
  "source": "youtube_video",
  "external_id": "abc123",
  "title": "Election Coverage",
  "published_date": "2024-01-15T10:30:00Z",
  "entities": {
    "locations": ["Uttar Pradesh", "Gorakhpur"],
    "parties": ["BJP", "SP"],
    "hashtags": ["#election", "#UP2024"]
  },
  "language": "en",
  "ingestion_date": "2024-01-15T12:00:00Z"
}
```

---

## Configuration

Edit `scripts/scraper_config.json`:

```json
{
  "youtube_api_key": "YOUR_API_KEY",
  "max_videos": 100,
  "max_comments_per_video": 200,
  "max_articles": 300,
  "queries": {
    "youtube": [
      "उत्तर प्रदेश चुनाव 2024",
      "Uttar Pradesh election 2024",
      "गोरखपुर चुनाव"
    ],
    "news": [
      "election uttar pradesh",
      "gorakhpur election",
      "up election 2024"
    ]
  },
  "rate_limiting": {
    "youtube_api_delay_seconds": 1,
    "web_scrape_delay_seconds": 2
  }
}
```

---

## Complete Workflow

### Step 1: Setup (One-time)
```bash
# Run setup script
bash scripts/setup_scrapers.sh

# Set YouTube API key
export YOUTUBE_API_KEY="your_key"
```

### Step 2: Scrape Data
```bash
# Option A: Run all scrapers
python scripts/master_scraper_orchestrator.py

# Option B: Run individual scrapers
python scripts/youtube_videos_scraper.py      # ~5 min
python scripts/youtube_comments_scraper.py    # ~10 min (requires video IDs)
python scripts/newspaper_scraper.py           # ~5 min
```

### Step 3: Check Results
```bash
# View scraped videos
ls -lh data/yt_cache/youtube_videos_*.json

# View scraped comments
ls -lh data/yt_cache/youtube_comments_*.json

# View news articles
ls -lh data/newspapers/election_news_*.json

# View logs
cat data/scraping_logs/scraping_log_*.json
```

### Step 4: Process Data
```bash
# Clean and normalize scraped data
python scripts/scraped_data_processor.py

# Check processed data
ls -lh data/processed/
cat data/processed/ingestion_report.json
```

### Step 5: Integrate with Ontology
```python
# In your ETL pipeline
from scripts.scraped_data_processor import ScrapedDataProcessor
from etl.data_ingestion import SourceIngester

processor = ScrapedDataProcessor()
processor.process_all()

# Load processed data
ingester = SourceIngester()
ingester.ingest_from_directory('data/processed')
```

---

## Data Output Locations

```
data/
├── yt_cache/
│   ├── youtube_videos_20240115_100000.json
│   ├── youtube_comments_20240115_105000.json
│   └── ...
├── newspapers/
│   ├── election_news_20240115_100000.json
│   ├── news_analysis_20240115_100000.json
│   └── ...
├── scraping_logs/
│   ├── scraping_log_20240115_100000.json
│   └── ...
└── processed/
    ├── processed_videos_20240115_100000.json
    ├── processed_comments_20240115_100000.json
    ├── processed_articles_20240115_100000.json
    ├── ingestion_report.json
    └── ...
```

---

## API Quotas & Limits

**YouTube API:**
- Free tier: 10,000 units/day
- Search query: ~100 units
- Get statistics: ~1 unit per video
- Each comment thread: ~1 unit

**Typical Usage:**
- 50 videos: ~150 units
- 200 comments: ~5 units
- **Total: ~155 units/day (well within free tier)**

**Web Scraping:**
- No official limits
- Scrapers include rate limiting
- Respectful delays: 2-3 seconds between requests

---

## Troubleshooting

### Issue: "YouTube API key not available"
```bash
# Set environment variable
export YOUTUBE_API_KEY="your_key_here"

# Or add to .env file
echo "YOUTUBE_API_KEY=your_key_here" > .env
```

### Issue: No comments found
- Videos may have comments disabled
- API may be rate limited
- Check `data/scraping_logs/` for errors

### Issue: Web scraper returns empty results
- Website may block automated access
- HTML structure may have changed
- Check User-Agent headers (already included)
- Increase delays in config

### Issue: "Module not found" errors
```bash
# Reinstall dependencies
pip install -r scripts/scraper_requirements.txt
```

---

## Advanced Usage

### Scheduled Daily Scraping
```bash
# Add to crontab (6 AM daily)
0 6 * * * cd /path/to/project && python scripts/master_scraper_orchestrator.py >> logs/scraper.log 2>&1
```

### Parallel Processing
```python
from concurrent.futures import ThreadPoolExecutor
from scripts.youtube_videos_scraper import YouTubeVideoScraper

queries = ['query1', 'query2', 'query3']
scraper = YouTubeVideoScraper()

with ThreadPoolExecutor(max_workers=3) as executor:
    results = executor.map(scraper.search_videos, queries)
```

### Database Storage
```python
import pymongo
from scripts.scraped_data_processor import ScrapedDataProcessor

client = pymongo.MongoClient()
db = client['election_ontology']

processor = ScrapedDataProcessor()
processor.process_all()

# Insert into MongoDB
for file in Path('data/processed').glob('*.json'):
    with open(file) as f:
        data = json.load(f)
        db.sources.insert_many(data)
```

### Custom Entity Extraction
```python
from scripts.youtube_comments_scraper import YouTubeCommentsScraper

scraper = YouTubeCommentsScraper()
comments = scraper.scrape_multiple_videos(['video_id'])

# Your custom NLP
for comment in comments:
    entities = extract_custom_entities(comment['text'])
    # Process entities
```

---

## Performance Tips

1. **Batch Operations**: Process multiple videos in single session
2. **Caching**: Skip already-scraped videos
3. **Rate Limiting**: Configured automatically, adjust if needed
4. **Database**: Store results in MongoDB for fast queries
5. **Parallel**: Use ThreadPoolExecutor for web scraping

---

## Support & Documentation

- **Main README**: [SCRAPER_README.md](SCRAPER_README.md)
- **Configuration**: [scraper_config.json](scraper_config.json)
- **Logs**: [data/scraping_logs/](../data/scraping_logs/)
- **YouTube API**: https://developers.google.com/youtube/v3
- **Issues**: Check logs for detailed error messages

---

## Next Steps

1. ✅ Set up environment
2. ✅ Configure API keys
3. ✅ Run scrapers
4. ✅ Process data
5. ✅ Integrate with ontology
6. 🚀 Schedule regular scraping

**Ready to scrape!** 🎉

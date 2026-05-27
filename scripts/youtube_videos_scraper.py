"""
YouTube Videos Scraper
Scrapes video metadata, transcripts, and engagement metrics for election-related content
"""

import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List

# Try Google API, fallback to yt-dlp
try:
    from googleapiclient.discovery import build

    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False

try:
    import yt_dlp

    YTDLP_AVAILABLE = True
except ImportError:
    YTDLP_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class YouTubeVideoScraper:
    """Scrape YouTube videos using Google API or yt-dlp"""

    def __init__(self, api_key: str = None, use_api: bool = True):
        self.api_key = api_key or os.getenv("YOUTUBE_API_KEY")
        self.use_api = use_api and GOOGLE_API_AVAILABLE and self.api_key
        self.youtube = build("youtube", "v3", developerKey=self.api_key) if self.use_api else None
        self.output_dir = "data/yt_cache"
        os.makedirs(self.output_dir, exist_ok=True)

    def search_videos(
        self,
        query: str,
        max_results: int = 50,
        region_code: str = "IN",
        publish_date_after: str = None,
    ) -> List[Dict]:
        """Search for videos using YouTube API"""
        if not self.use_api:
            logger.warning(
                "YouTube API key not available. Install google-api-python-client and set YOUTUBE_API_KEY"
            )
            return []

        try:
            request = self.youtube.search().list(
                q=query,
                part="snippet",
                maxResults=min(max_results, 50),
                regionCode=region_code,
                type="video",
                order="relevance",
                publishedAfter=publish_date_after
                or (datetime.now() - timedelta(days=90)).isoformat() + "Z",
                relevanceLanguage="hi,en",
            )

            response = request.execute()
            videos = []

            for item in response.get("items", []):
                video_data = {
                    "video_id": item["id"]["videoId"],
                    "title": item["snippet"]["title"],
                    "description": item["snippet"]["description"],
                    "channel": item["snippet"]["channelTitle"],
                    "published_at": item["snippet"]["publishedAt"],
                    "thumbnail": item["snippet"]["thumbnails"]["high"]["url"],
                }
                videos.append(video_data)

            return videos
        except Exception as e:
            logger.error(f"Error searching videos: {e}")
            return []

    def get_video_stats(self, video_id: str) -> Dict:
        """Get video statistics (views, likes, comments count)"""
        if not self.use_api:
            return {}

        try:
            request = self.youtube.videos().list(part="statistics,contentDetails", id=video_id)
            response = request.execute()

            if response.get("items"):
                item = response["items"][0]
                stats = item["statistics"]
                content = item["contentDetails"]

                return {
                    "video_id": video_id,
                    "views": int(stats.get("viewCount", 0)),
                    "likes": int(stats.get("likeCount", 0)),
                    "comments_count": int(stats.get("commentCount", 0)),
                    "duration": content.get("duration", "PT0S"),
                }
            return {}
        except Exception as e:
            logger.error(f"Error getting video stats for {video_id}: {e}")
            return {}

    def scrape_search_results(self, queries: List[str], max_results: int = 100) -> List[Dict]:
        """Scrape multiple search queries"""
        all_videos = []

        for query in queries:
            logger.info(f"Searching for: {query}")
            videos = self.search_videos(query, max_results=max_results)

            for video in videos:
                stats = self.get_video_stats(video["video_id"])
                video.update(stats)
                all_videos.append(video)
                time.sleep(0.5)  # Rate limiting

        # Save to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"{self.output_dir}/youtube_videos_{timestamp}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(all_videos, f, ensure_ascii=False, indent=2)

        logger.info(f"Saved {len(all_videos)} videos to {output_file}")
        return all_videos


class YouTubeDLPScraper:
    """Fallback scraper using yt-dlp for metadata"""

    def __init__(self):
        self.output_dir = "data/yt_cache"
        os.makedirs(self.output_dir, exist_ok=True)

    def scrape_video_metadata(self, urls: List[str]) -> List[Dict]:
        """Extract metadata from YouTube URLs"""
        if not YTDLP_AVAILABLE:
            logger.error("yt-dlp not installed. Run: pip install yt-dlp")
            return []

        videos = []
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": "in_playlist",
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            for url in urls:
                try:
                    info = ydl.extract_info(url, download=False)
                    videos.append(
                        {
                            "url": url,
                            "title": info.get("title"),
                            "channel": info.get("uploader"),
                            "duration": info.get("duration"),
                            "views": info.get("view_count"),
                            "published": info.get("upload_date"),
                            "description": info.get("description"),
                        }
                    )
                except Exception as e:
                    logger.error(f"Error extracting {url}: {e}")

        return videos


def scrape_election_videos():
    """Main function to scrape election-related videos"""
    queries = [
        "उत्तर प्रदेश चुनाव 2024",
        "Uttar Pradesh election 2024",
        "UP election candidates",
        "गोरखपुर चुनाव 2024",
        "Gorakhpur election news",
        "भारत चुनाव समाचार",
        "Indian election coverage",
    ]

    scraper = YouTubeVideoScraper()
    videos = scraper.scrape_search_results(queries, max_results=50)

    logger.info(f"Total videos scraped: {len(videos)}")
    return videos


if __name__ == "__main__":
    scrape_election_videos()

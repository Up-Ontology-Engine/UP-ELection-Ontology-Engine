"""
YouTube Comments Scraper
Scrapes comments, replies, and sentiment from election-related videos
"""

import json
import logging
import os
import re
import time
from datetime import datetime
from typing import Dict, List

try:
    from googleapiclient.discovery import build

    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False

try:
    import requests
    from bs4 import BeautifulSoup

    WEB_SCRAPE_AVAILABLE = True
except ImportError:
    WEB_SCRAPE_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class YouTubeCommentsScraper:
    """Scrape YouTube comments using Google API"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("YOUTUBE_API_KEY")
        self.youtube = build("youtube", "v3", developerKey=self.api_key) if self.api_key else None
        self.output_dir = "data/yt_cache"
        os.makedirs(self.output_dir, exist_ok=True)

    def get_comments(self, video_id: str, max_results: int = 100) -> List[Dict]:
        """Fetch top-level comments for a video"""
        if not self.youtube:
            logger.error("YouTube API key not available")
            return []

        comments = []

        try:
            request = self.youtube.commentThreads().list(
                part="snippet,replies",
                videoId=video_id,
                textFormat="plainText",
                maxResults=min(max_results, 100),
                order="relevance",
            )

            while request and len(comments) < max_results:
                response = request.execute()

                for item in response.get("items", []):
                    thread = item["snippet"]
                    comment_data = {
                        "video_id": video_id,
                        "comment_id": item["id"],
                        "author": thread["authorDisplayName"],
                        "text": thread["textDisplay"],
                        "likes": thread["likeCount"],
                        "published_at": thread["publishedAt"],
                        "updated_at": thread["updatedAt"],
                        "reply_count": thread["replyCount"],
                        "is_reply": False,
                    }
                    comments.append(comment_data)

                    # Get replies
                    if item.get("replies"):
                        for reply in item["replies"]["comments"]:
                            reply_data = {
                                "video_id": video_id,
                                "comment_id": reply["id"],
                                "parent_id": item["id"],
                                "author": reply["snippet"]["authorDisplayName"],
                                "text": reply["snippet"]["textDisplay"],
                                "likes": reply["snippet"]["likeCount"],
                                "published_at": reply["snippet"]["publishedAt"],
                                "updated_at": reply["snippet"]["updatedAt"],
                                "is_reply": True,
                            }
                            comments.append(reply_data)

                # Get next page
                if "nextPageToken" in response and len(comments) < max_results:
                    request = self.youtube.commentThreads().list(
                        part="snippet,replies",
                        videoId=video_id,
                        textFormat="plainText",
                        maxResults=min(max_results - len(comments), 100),
                        pageToken=response["nextPageToken"],
                        order="relevance",
                    )
                else:
                    request = None

                time.sleep(1)  # Rate limiting

        except Exception as e:
            logger.error(f"Error fetching comments for {video_id}: {e}")

        return comments

    def scrape_multiple_videos(
        self, video_ids: List[str], max_comments_per_video: int = 200
    ) -> List[Dict]:
        """Scrape comments from multiple videos"""
        all_comments = []

        for video_id in video_ids:
            logger.info(f"Scraping comments for video: {video_id}")
            comments = self.get_comments(video_id, max_results=max_comments_per_video)
            all_comments.extend(comments)

        # Save to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"{self.output_dir}/youtube_comments_{timestamp}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(all_comments, f, ensure_ascii=False, indent=2)

        logger.info(f"Saved {len(all_comments)} comments to {output_file}")
        return all_comments

    def analyze_sentiment(self, comments: List[Dict]) -> Dict:
        """Basic sentiment analysis of comments"""
        positive_keywords = ["good", "great", "excellent", "बहुत अच्छा", "शानदार", "भारी", "वाह"]
        negative_keywords = ["bad", "worst", "terrible", "बुरा", "खराब", "भयानक", "निंदा"]

        sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}

        for comment in comments:
            text = comment["text"].lower()

            if any(keyword in text for keyword in positive_keywords):
                sentiment_counts["positive"] += 1
            elif any(keyword in text for keyword in negative_keywords):
                sentiment_counts["negative"] += 1
            else:
                sentiment_counts["neutral"] += 1

        return {
            "total_comments": len(comments),
            "sentiment": sentiment_counts,
            "positive_ratio": sentiment_counts["positive"] / len(comments) if comments else 0,
        }

    def extract_mentions(self, comments: List[Dict]) -> Dict:
        """Extract mentioned entities (politicians, parties, locations)"""
        entities = {
            "names": {},
            "parties": {},
            "hashtags": [],
        }

        party_keywords = ["भाजपा", "बीजेपी", "samajwadi", "sp", "कांग्रेस", "congress", "aadmi"]

        for comment in comments:
            text = comment["text"]

            # Extract hashtags
            hashtags = re.findall(r"#\w+", text)
            entities["hashtags"].extend(hashtags)

            # Count party mentions
            for party in party_keywords:
                if party.lower() in text.lower():
                    entities["parties"][party] = entities["parties"].get(party, 0) + 1

            # Extract words (basic NER)
            words = text.split()
            for word in words:
                if len(word) > 3 and word[0].isupper():
                    entities["names"][word] = entities["names"].get(word, 0) + 1

        # Sort by frequency
        entities["names"] = dict(
            sorted(entities["names"].items(), key=lambda x: x[1], reverse=True)[:20]
        )
        entities["parties"] = dict(
            sorted(entities["parties"].items(), key=lambda x: x[1], reverse=True)
        )
        entities["hashtags"] = list(set(entities["hashtags"]))

        return entities


def scrape_video_comments(video_ids: List[str]):
    """Main function to scrape comments"""
    scraper = YouTubeCommentsScraper()
    comments = scraper.scrape_multiple_videos(video_ids, max_comments_per_video=200)

    # Analyze sentiment
    sentiment = scraper.analyze_sentiment(comments)
    logger.info(f"Sentiment analysis: {sentiment}")

    # Extract mentions
    mentions = scraper.extract_mentions(comments)
    logger.info(f"Top mentions: {mentions}")

    return {
        "comments": comments,
        "sentiment": sentiment,
        "entities": mentions,
    }


if __name__ == "__main__":
    # Example video IDs
    video_ids = ["dQw4w9WgXcQ"]  # Replace with actual video IDs
    scrape_video_comments(video_ids)

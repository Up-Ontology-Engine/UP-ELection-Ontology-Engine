"""
Scraped Data Processor
Processes and integrates scraped data for the election ontology
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ScrapedDataProcessor:
    """Process and clean scraped data for ontology ingestion"""
    
    def __init__(self, data_dir: str = 'data'):
        self.data_dir = data_dir
        self.output_dir = f'{data_dir}/processed'
        os.makedirs(self.output_dir, exist_ok=True)
    
    def load_scraped_videos(self, file_path: str) -> List[Dict]:
        """Load YouTube videos from scraper output"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            return []
    
    def load_scraped_comments(self, file_path: str) -> List[Dict]:
        """Load YouTube comments from scraper output"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            return []
    
    def load_scraped_articles(self, file_path: str) -> List[Dict]:
        """Load news articles from scraper output"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            return []
    
    def extract_entities_from_text(self, text: str) -> Dict:
        """Extract potential entities from text"""
        entities = {
            'locations': [],
            'politicians': [],
            'parties': [],
            'hashtags': [],
            'emails': [],
            'urls': [],
        }
        
        # Extract hashtags
        hashtags = re.findall(r'#\w+', text)
        entities['hashtags'] = list(set(hashtags))
        
        # Extract URLs
        urls = re.findall(r'https?://\S+', text)
        entities['urls'] = list(set(urls))
        
        # Extract emails
        emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        entities['emails'] = list(set(emails))
        
        # Indian location names (basic)
        locations = ['uttar pradesh', 'up', 'gorakhpur', 'lucknow', 'kanpur', 'delhi']
        for loc in locations:
            if loc.lower() in text.lower():
                entities['locations'].append(loc.title())
        
        # Indian political parties (basic)
        parties = ['BJP', 'SP', 'Congress', 'AAP', 'DMK', 'AIADMK', 'BSP', 'TMC']
        for party in parties:
            if party.upper() in text.upper():
                entities['parties'].append(party)
        
        return entities
    
    def normalize_video_data(self, videos: List[Dict]) -> List[Dict]:
        """Normalize YouTube video data"""
        normalized = []
        
        for video in videos:
            norm_video = {
                'source': 'youtube_video',
                'external_id': video.get('video_id', ''),
                'title': video.get('title', ''),
                'description': video.get('description', ''),
                'channel': video.get('channel', ''),
                'published_date': video.get('published_at', ''),
                'thumbnail_url': video.get('thumbnail', ''),
                'metrics': {
                    'views': video.get('views', 0),
                    'likes': video.get('likes', 0),
                    'comments': video.get('comments_count', 0),
                },
                'entities': self.extract_entities_from_text(
                    f"{video.get('title', '')} {video.get('description', '')}"
                ),
                'language': 'en' if any(ord(c) < 128 for c in video.get('title', '')) else 'hi',
                'ingestion_date': datetime.now().isoformat(),
            }
            normalized.append(norm_video)
        
        return normalized
    
    def normalize_comments_data(self, comments: List[Dict]) -> List[Dict]:
        """Normalize YouTube comments data"""
        normalized = []
        
        for comment in comments:
            norm_comment = {
                'source': 'youtube_comment',
                'external_id': comment.get('comment_id', ''),
                'parent_id': comment.get('video_id', ''),
                'author': comment.get('author', 'Anonymous'),
                'text': comment.get('text', ''),
                'published_date': comment.get('published_at', ''),
                'updated_date': comment.get('updated_at', ''),
                'metrics': {
                    'likes': comment.get('likes', 0),
                    'reply_count': comment.get('reply_count', 0),
                },
                'entities': self.extract_entities_from_text(comment.get('text', '')),
                'is_reply': comment.get('is_reply', False),
                'language': 'en' if any(ord(c) < 128 for c in comment.get('text', '')) else 'hi',
                'ingestion_date': datetime.now().isoformat(),
            }
            normalized.append(norm_comment)
        
        return normalized
    
    def normalize_articles_data(self, articles: List[Dict]) -> List[Dict]:
        """Normalize news article data"""
        normalized = []
        
        for article in articles:
            # Create a unique ID from title and source
            article_id = f"{article.get('source', 'unknown').replace(' ', '_')}_{hash(article.get('title', '')) & 0xffffffff}"
            
            norm_article = {
                'source': 'news_article',
                'external_id': article_id,
                'source_name': article.get('source', ''),
                'title': article.get('title', ''),
                'url': article.get('link', ''),
                'published_date': article.get('published', ''),
                'summary': article.get('summary', ''),
                'entities': self.extract_entities_from_text(
                    f"{article.get('title', '')} {article.get('summary', '')}"
                ),
                'language': 'en',
                'ingestion_date': datetime.now().isoformat(),
            }
            normalized.append(norm_article)
        
        return normalized
    
    def save_processed_data(self, data: List[Dict], filename: str):
        """Save processed data to JSON file"""
        output_path = f"{self.output_dir}/{filename}"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(data)} records to {output_path}")
        return output_path
    
    def process_all_youtube_videos(self):
        """Process all YouTube video files"""
        video_dir = f'{self.data_dir}/yt_cache'
        if not os.path.exists(video_dir):
            logger.warning(f"No YouTube cache directory: {video_dir}")
            return
        
        for file in Path(video_dir).glob('youtube_videos_*.json'):
            logger.info(f"Processing {file.name}...")
            videos = self.load_scraped_videos(str(file))
            normalized = self.normalize_video_data(videos)
            self.save_processed_data(normalized, f"processed_videos_{file.stem}.json")
    
    def process_all_comments(self):
        """Process all YouTube comments files"""
        video_dir = f'{self.data_dir}/yt_cache'
        if not os.path.exists(video_dir):
            logger.warning(f"No YouTube cache directory: {video_dir}")
            return
        
        for file in Path(video_dir).glob('youtube_comments_*.json'):
            logger.info(f"Processing {file.name}...")
            comments = self.load_scraped_comments(str(file))
            normalized = self.normalize_comments_data(comments)
            self.save_processed_data(normalized, f"processed_comments_{file.stem}.json")
    
    def process_all_articles(self):
        """Process all news article files"""
        news_dir = f'{self.data_dir}/newspapers'
        if not os.path.exists(news_dir):
            logger.warning(f"No newspapers directory: {news_dir}")
            return
        
        for file in Path(news_dir).glob('election_news_*.json'):
            logger.info(f"Processing {file.name}...")
            articles = self.load_scraped_articles(str(file))
            normalized = self.normalize_articles_data(articles)
            self.save_processed_data(normalized, f"processed_articles_{file.stem}.json")
    
    def generate_ingestion_report(self) -> Dict:
        """Generate report of processed data"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'videos': 0,
            'comments': 0,
            'articles': 0,
            'entities_count': {
                'locations': 0,
                'parties': 0,
                'hashtags': 0,
                'urls': 0,
            }
        }
        
        # Count processed files
        for file in Path(self.output_dir).glob('processed_videos_*.json'):
            with open(file) as f:
                data = json.load(f)
                report['videos'] += len(data)
        
        for file in Path(self.output_dir).glob('processed_comments_*.json'):
            with open(file) as f:
                data = json.load(f)
                report['comments'] += len(data)
        
        for file in Path(self.output_dir).glob('processed_articles_*.json'):
            with open(file) as f:
                data = json.load(f)
                report['articles'] += len(data)
        
        # Save report
        report_file = f"{self.output_dir}/ingestion_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Report saved to {report_file}")
        return report
    
    def process_all(self):
        """Process all scraped data"""
        logger.info("Starting data processing...")
        self.process_all_youtube_videos()
        self.process_all_comments()
        self.process_all_articles()
        report = self.generate_ingestion_report()
        logger.info(f"Processing complete. Report: {report}")
        return report


if __name__ == '__main__':
    processor = ScrapedDataProcessor()
    processor.process_all()

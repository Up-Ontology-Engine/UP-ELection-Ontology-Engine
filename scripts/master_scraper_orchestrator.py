"""
Master Scraper Orchestrator
Runs all scrapers (YouTube videos, comments, newspapers) in coordinated fashion
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict
import argparse

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ScraperOrchestrator:
    """Orchestrate all data scrapers"""
    
    def __init__(self, config_file: str = None):
        self.config = self.load_config(config_file)
        self.output_dir = 'data/scraping_logs'
        os.makedirs(self.output_dir, exist_ok=True)
        self.results = {}
    
    def load_config(self, config_file: str = None) -> Dict:
        """Load scraper configuration"""
        if config_file and os.path.exists(config_file):
            with open(config_file, 'r') as f:
                return json.load(f)
        
        # Default configuration
        return {
            'youtube_api_key': os.getenv('YOUTUBE_API_KEY'),
            'max_videos': 100,
            'max_comments_per_video': 200,
            'max_articles': 300,
            'queries': {
                'youtube': [
                    'उत्तर प्रदेश चुनाव 2024',
                    'Uttar Pradesh election 2024',
                    'गोरखपुर चुनाव',
                    'Gorakhpur election',
                ],
                'news': [
                    'election uttar pradesh',
                    'up election candidates',
                    'gorakhpur election news',
                ]
            }
        }
    
    def run_youtube_video_scraper(self) -> Dict:
        """Run YouTube video scraper"""
        logger.info("Starting YouTube video scraper...")
        
        try:
            from scripts.youtube_videos_scraper import YouTubeVideoScraper
            
            scraper = YouTubeVideoScraper(api_key=self.config.get('youtube_api_key'))
            videos = scraper.scrape_search_results(
                self.config['queries']['youtube'],
                max_results=self.config['max_videos']
            )
            
            result = {
                'status': 'success',
                'videos_scraped': len(videos),
                'timestamp': datetime.now().isoformat(),
            }
            logger.info(f"YouTube videos scraped: {len(videos)}")
            return result
        
        except Exception as e:
            logger.error(f"YouTube video scraper failed: {e}")
            return {'status': 'failed', 'error': str(e)}
    
    def run_youtube_comments_scraper(self, video_ids: list = None) -> Dict:
        """Run YouTube comments scraper"""
        logger.info("Starting YouTube comments scraper...")
        
        try:
            from scripts.youtube_comments_scraper import YouTubeCommentsScraper
            
            scraper = YouTubeCommentsScraper(api_key=self.config.get('youtube_api_key'))
            
            if not video_ids:
                logger.warning("No video IDs provided for comments scraper")
                return {'status': 'skipped', 'reason': 'no_videos'}
            
            comments = scraper.scrape_multiple_videos(
                video_ids,
                max_comments_per_video=self.config['max_comments_per_video']
            )
            
            result = {
                'status': 'success',
                'comments_scraped': len(comments),
                'timestamp': datetime.now().isoformat(),
            }
            logger.info(f"YouTube comments scraped: {len(comments)}")
            return result
        
        except Exception as e:
            logger.error(f"YouTube comments scraper failed: {e}")
            return {'status': 'failed', 'error': str(e)}
    
    def run_newspaper_scraper(self) -> Dict:
        """Run newspaper scraper"""
        logger.info("Starting newspaper scraper...")
        
        try:
            from scripts.newspaper_scraper import NewspaperScraper, NewsAggregator
            
            scraper = NewspaperScraper()
            articles = scraper.scrape_all_sources()
            
            aggregator = NewsAggregator()
            aggregator.save_analysis(articles)
            
            result = {
                'status': 'success',
                'articles_scraped': len(articles),
                'timestamp': datetime.now().isoformat(),
            }
            logger.info(f"News articles scraped: {len(articles)}")
            return result
        
        except Exception as e:
            logger.error(f"Newspaper scraper failed: {e}")
            return {'status': 'failed', 'error': str(e)}
    
    def run_all_scrapers(self, skip_videos: bool = False, 
                        skip_comments: bool = False, 
                        skip_news: bool = False) -> Dict:
        """Run all scrapers in sequence"""
        logger.info("=" * 50)
        logger.info("MASTER SCRAPER ORCHESTRATOR STARTING")
        logger.info("=" * 50)
        
        start_time = datetime.now()
        
        # Run newspaper scraper (independent)
        if not skip_news:
            self.results['newspaper'] = self.run_newspaper_scraper()
        
        # Run YouTube video scraper
        video_ids = []
        if not skip_videos:
            self.results['youtube_videos'] = self.run_youtube_video_scraper()
            # In production, extract video IDs from results for comments scraper
        
        # Run YouTube comments scraper
        if not skip_comments and video_ids:
            self.results['youtube_comments'] = self.run_youtube_comments_scraper(video_ids)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Save orchestration log
        log_data = {
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'duration_seconds': duration,
            'results': self.results,
            'config': {k: v for k, v in self.config.items() if k != 'youtube_api_key'}
        }
        
        log_file = f"{self.output_dir}/scraping_log_{start_time.strftime('%Y%m%d_%H%M%S')}.json"
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)
        
        logger.info("=" * 50)
        logger.info(f"SCRAPING COMPLETED IN {duration:.1f} seconds")
        logger.info(f"Log saved to: {log_file}")
        logger.info("=" * 50)
        
        return log_data
    
    def print_summary(self):
        """Print summary of results"""
        print("\n" + "=" * 50)
        print("SCRAPING SUMMARY")
        print("=" * 50)
        
        for scraper_name, result in self.results.items():
            status = result.get('status', 'unknown')
            print(f"\n{scraper_name.upper()}: {status}")
            
            if status == 'success':
                if 'videos_scraped' in result:
                    print(f"  Videos: {result['videos_scraped']}")
                if 'comments_scraped' in result:
                    print(f"  Comments: {result['comments_scraped']}")
                if 'articles_scraped' in result:
                    print(f"  Articles: {result['articles_scraped']}")
            elif status == 'failed':
                print(f"  Error: {result.get('error', 'Unknown error')}")


def main():
    parser = argparse.ArgumentParser(description='Master Scraper Orchestrator')
    parser.add_argument('--config', type=str, help='Config file path')
    parser.add_argument('--skip-videos', action='store_true', help='Skip YouTube video scraper')
    parser.add_argument('--skip-comments', action='store_true', help='Skip YouTube comments scraper')
    parser.add_argument('--skip-news', action='store_true', help='Skip newspaper scraper')
    parser.add_argument('--newspaper-only', action='store_true', help='Run only newspaper scraper')
    parser.add_argument('--youtube-only', action='store_true', help='Run only YouTube scrapers')
    
    args = parser.parse_args()
    
    orchestrator = ScraperOrchestrator(config_file=args.config)
    
    if args.newspaper_only:
        orchestrator.results['newspaper'] = orchestrator.run_newspaper_scraper()
    elif args.youtube_only:
        orchestrator.results['youtube_videos'] = orchestrator.run_youtube_video_scraper()
    else:
        orchestrator.run_all_scrapers(
            skip_videos=args.skip_videos,
            skip_comments=args.skip_comments,
            skip_news=args.skip_news,
        )
    
    orchestrator.print_summary()


if __name__ == '__main__':
    main()

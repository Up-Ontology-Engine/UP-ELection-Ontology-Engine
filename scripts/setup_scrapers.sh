#!/bin/bash
# Quick Start Setup for Election Data Scrapers

set -e

echo "=================================="
echo "Election Data Scraper Setup"
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python version
echo -e "${YELLOW}Checking Python version...${NC}"
python3 --version

# Create virtual environment if not exists
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv .venv
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source .venv/bin/activate

# Upgrade pip
echo -e "${YELLOW}Upgrading pip...${NC}"
pip install --upgrade pip

# Install scraper dependencies
echo -e "${YELLOW}Installing scraper dependencies...${NC}"
pip install -r scripts/scraper_requirements.txt

# Create necessary directories
echo -e "${YELLOW}Creating data directories...${NC}"
mkdir -p data/yt_cache
mkdir -p data/newspapers
mkdir -p data/scraping_logs
mkdir -p data/processed

# Check for YouTube API key
echo -e "${YELLOW}Checking YouTube API configuration...${NC}"
if [ -z "$YOUTUBE_API_KEY" ]; then
    echo -e "${RED}⚠️  YOUTUBE_API_KEY not set${NC}"
    echo "To set it, run:"
    echo "  export YOUTUBE_API_KEY='your_api_key_here'"
    echo "Or add to .env file"
else
    echo -e "${GREEN}✓ YOUTUBE_API_KEY is set${NC}"
fi

echo ""
echo -e "${GREEN}=================================="
echo "Setup Complete!"
echo "==================================${NC}"
echo ""
echo "Next steps:"
echo "1. Set YouTube API key:"
echo "   export YOUTUBE_API_KEY='your_key'"
echo ""
echo "2. Run scrapers:"
echo "   - All: python scripts/master_scraper_orchestrator.py"
echo "   - YouTube videos: python scripts/youtube_videos_scraper.py"
echo "   - YouTube comments: python scripts/youtube_comments_scraper.py"
echo "   - Newspapers: python scripts/newspaper_scraper.py"
echo ""
echo "3. Process scraped data:"
echo "   python scripts/scraped_data_processor.py"
echo ""
echo "4. View results:"
echo "   ls data/yt_cache/"
echo "   ls data/newspapers/"
echo "   ls data/scraping_logs/"
echo ""

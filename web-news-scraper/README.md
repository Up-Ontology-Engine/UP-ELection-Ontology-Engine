# Gorakhpur Political Sentiment & Election Ontology Engine

This repository contains a comprehensive **Political Ontology and Sentiment Analysis Engine** specifically designed to track and analyze the electorate's pulse in Gorakhpur, Uttar Pradesh. 

It scrapes regional bilingual news, classifies articles across key election topics, and provides insights on political sentiment (Pro/Anti-BJP).

## Key Features

* ** Multi-Source News Scraper Pipeline:**
  * Integrates with 15+ Indian newspaper RSS feeds (Times of India, Hindustan Times, Jagran, Amar Ujala, etc.) and dynamic Google News queries.
  * Supports both English and Hindi article scraping.
  * Automatically deduplicates articles and can optionally fetch full article body text for deeper analysis.
* ** Political Ontology & Topic Inference:**
  * Maps articles to 12 key election-influencing topics: Development, Law & Order, Unemployment, Corruption, Communal Relations, Farmers, Healthcare, Education, and more.
* ** Multilingual Sentiment Engine:**
  * Analyzes sentiment using a custom 80+ keyword Hindi/English political lexicon.
  * Employs a **3-Layer Classification Architecture** (Explicit Keywords, Topic-Based Default Bias, Source-Query Context) to accurately classify articles as `PRO-BJP`, `ANTI-BJP`, or `NEUTRAL`.
* ** Real-time Flask Dashboard:**
  * Flask REST API serving JSON payloads to the frontend.
  * Beautiful, responsive Dark Mode UI featuring KPI cards and Chart.js visualizations (Topic breakdowns, Source tracking, Sentiment timelines).
  * Auto-refreshing data mechanism.

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Scraping & Classification Pipeline
To scrape the latest news, classify the political sentiment, and save the reports:
```bash
python pipeline.py
```

*Optional Flags:*
* `python pipeline.py --full` : Scrapes with the full article text (slower, but yields richer data).
* `python pipeline.py --file results/YOUR_FILE.json` : Re-classifies an existing JSON file without re-scraping.

### 3. Start the Web Dashboard (Optional)
To view the data on the local web dashboard:
```bash
python app.py
```
Then, open your browser and navigate to: `http://localhost:5000`

## Project Structure & Data Outputs

All scraped and classified data is automatically partitioned and saved locally into the `/results` directory as structured JSON datasets:
* `master_*.json`: All scraped articles with their respective classifications.
* `pro_bjp_*.json`: Articles heavily leaning towards the ruling party.
* `anti_bjp_*.json`: Articles heavily critical or negative regarding the ruling party.
* `neutral_*.json`: Purely factual or balanced articles.

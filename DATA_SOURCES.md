# Data Sources and Storage Locations

This document lists the project's data sources and where each type of data is stored in the repository.

**Raw / Ingested Sources**

- **Electoral rolls & Form 20:** stored under `data/Form 20 Gorakhpur Data/` (raw Excel/CSV inputs). See ingestion scripts in `ingestion/` that parse these files.
- **ECI booth results:** collected by `ingestion/eci_results_scraper.py` / `ingestion/eci_booth_results.py`. Raw results and booth-level files are often placed in `data/PoolBoothData/` and `data/PoolBoothData_JSON/`.
- **YouTube videos & comments:** collected by `ingestion/ingest_youtube_videos.py` and `ingestion/youtube_comments.py`. Cached/raw YouTube data lives in `data/yt_cache/`.
- **News & multi-source scrapes:** collected by `ingestion/news_scraper.py` and `ingestion/multi_news_scraper.py`. Raw news dumps live under `data/Digital_Dataset/` and other `data/` subfolders (e.g., `data/gorakhpur 10 years data/`).
- **Grievances / portal scrapes:** `ingestion/grievance_scraper.py` and archived HTTP captures like `stategisportal.nic.in.har` in repo root.
- **Candidate & affidavit data:** scripts include `ingestion/myneta_candidates.py` and `ingestion/ddp_affidavits.py`. Raw outputs may be placed in `data/` or `data/transformed/` depending on pipeline.
- **Government schemes data:** `ingestion/egramswaraj_schemes.py`, `ingestion/electoral_demographics.py`, and related loaders — raw sources often stored in `data/UP_Gov_schemes_Data/`.
- **Census / demographic transforms:** see `etl/transform_census.py` and outputs in `data/transformed/`.

**Transformed / Processed Data**

- **Transformed datasets:** consolidated and cleaned datasets are saved to `data/transformed/`.
- **Analytics outputs:** analytics and metric results produced by `analytics/` scripts (e.g., `analytics/booth_metrics.py`) are stored either in `data/transformed/` or in the `logs/` folder depending on the script.
- **Neo4j / Graph loaders:** graph import files and cypher constraints are in `graph/` (e.g., `graph/constraints.cypher`), with graph loader scripts under `graph/loaders/` and `graph/queries/`.

**Database / Seeds**

- **DB seeds and migrations:** `db/seeds/` contains seed data used to populate the database; `db/migrations/` contains migration definitions.

**Configuration & Pipeline Metadata**

- **Ingestion configuration:** `ingestion_config.json` holds configuration for ingestion sources and mappings.
- **HAR and captures:** `stategisportal.nic.in.har` stores an HTTP Archive capture used for debugging/scraping.

**Where ingestion code lives (sources)**

- The main ingestion and scrapers are in `ingestion/` — look at these files for exact source endpoints and output paths (e.g., `ingestion/eci_results_scraper.py`, `ingestion/ingest_youtube_videos.py`, `ingestion/grievance_scraper.py`, etc.).

**Quick pointers**

- Raw inputs: [data/](data/)
- Transformed outputs: [data/transformed/](data/transformed/)
- DB seeds: [db/seeds/](db/seeds/)
- Graph assets: [graph/](graph/)
- Ingestion scripts: [ingestion/](ingestion/)
- Ingestion config: [ingestion_config.json](ingestion_config.json)
- HAR capture: [stategisportal.nic.in.har](stategisportal.nic.in.har)

If you want, I can expand each bullet into per-script exact output paths, or scan each ingestion script and list the file paths they write to automatically. 

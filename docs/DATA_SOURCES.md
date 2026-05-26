# Data Sources and Storage Locations

This document lists the project's data sources and where each type of data is stored in the repository.

**Raw / Ingested Sources**

- **Electoral rolls & Form 20:** stored under `data/Form 20 Gorakhpur Data/` (raw Excel inputs) and `data/PoolBoothData_JSON/`. See ingestion scripts in `pipeline/ingest/` that parse these files.
- **ECI booth results:** collected by `pipeline/ingest/eci_results_scraper.py` / `pipeline/ingest/eci_booth_results.py`. Raw results and booth-level files are placed in `data/PoolBoothData_JSON/`.
- **YouTube videos & comments:** collected by `pipeline/ingest/ingest_youtube_videos.py` and `pipeline/ingest/youtube_comments.py`. Cached/raw YouTube data lives in `data/Digital_Dataset/`.
- **News & multi-source scrapes:** collected by `pipeline/ingest/news_scraper.py` and `pipeline/ingest/multi_news_scraper.py`. Raw news dumps live under `data/Digital_Dataset/` and `data/gorakhpur_grievance_only/`.
- **Grievances / portal scrapes:** `pipeline/ingest/grievance_scraper.py` and raw dumps in `data/gorakhpur_grievance_only/`.
- **Candidate & affidavit data:** scripts include `pipeline/ingest/myneta_candidates.py` and related loaders. Raw outputs are placed in `data/Myneta/` and `data/candidates/`.
- **Government schemes data:** `pipeline/ingest/egramswaraj_schemes.py`, `pipeline/ingest/electoral_demographics.py`, and related loaders — raw sources stored in `data/UP_Gov_schemes_Data/` and `data/Benficiary/`.
- **Census / demographic transforms:** see `pipeline/etl/transform_census.py` and outputs in `data/transformed/`.

**Transformed / Processed Data**

- **Transformed datasets:** consolidated and cleaned datasets are saved to `data/processed/`.
- **Analytics outputs:** analytics and metric results produced by `pipeline/analytics/` scripts (e.g., `pipeline/analytics/booth_metrics.py`) are stored either in `data/processed/` or in the `logs/` folder depending on the script.
- **Neo4j / Graph loaders:** graph import files and cypher constraints are in `pipeline/graph/` (e.g., `pipeline/graph/constraints.cypher`), with graph loader scripts under `pipeline/graph/loaders/` and `pipeline/graph/queries/`.

**Database / Seeds**

- **DB seeds and migrations:** `data/seeds/` contains seed data used to populate the database; `pipeline/db/migrations/` contains migration definitions.

**Configuration & Pipeline Metadata**

- **Ingestion configuration:** canonical file is `pipeline/config/ingestion_config.json`; root `ingestion_config.json` is retained only as a compatibility copy.
- **HAR and captures:** `stategisportal.nic.in.har` stores an HTTP Archive capture used for debugging/scraping.

**Where ingestion code lives (sources)**

- The main ingestion and scrapers are in `pipeline/ingest/` — look at these files for exact source endpoints and output paths (e.g., `pipeline/ingest/eci_results_scraper.py`, `pipeline/ingest/ingest_youtube_videos.py`, `pipeline/ingest/grievance_scraper.py`, etc.).

**Quick pointers**

- Raw inputs: [data/](../data/)
- Transformed outputs: [data/transformed/](../data/transformed/)
- DB seeds: [data/seeds/](../data/seeds/)
- Graph assets: [graph/](../pipeline/graph/)
- Ingestion scripts: [ingestion/](../pipeline/ingest/)
- Ingestion config: [config/ingestion_config.json](../pipeline/config/ingestion_config.json)

If you want, I can expand each bullet into per-script exact output paths, or scan each ingestion script and list the file paths they write to automatically. 

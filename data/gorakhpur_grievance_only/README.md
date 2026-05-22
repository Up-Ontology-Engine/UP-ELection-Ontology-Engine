# Gorakhpur Grievance Only JSON

This folder contains only grievance-style Gorakhpur records.

## Start here

- `json/manifest.json`: master index with counts and file paths.
- `json/grievance_records.json`: all grievance records in one JSON array.
- `json/myneta_grievance_records.json`: MyNeta grievance check result.

## Categorized JSON folders

- `json/by_archive_year/`: split by GDELT archive year or latest article seen year.
- `json/by_event_year/`: split by event/article year.
- `json/by_source_type/`: split by `government`, `news_media`, `other_web`, `unknown`.
- `json/by_category/`: split by inferred grievance category.

## Counts

- Total grievance records: 10,422
- GDELT historical event records: 10,340
- Newer GDELT DOC article records from latest live check: 82
- MyNeta published grievance records: 0

MyNeta note: the supplied page contains a discrepancy submission form, but it
does not publicly list submitted grievances. Candidate affidavit details are not
included here because this folder is grievance-only.

## Latest Live Check

The latest check queried the GDELT DOC API with a `1week` window. All six live
DOC API category searches completed successfully and added 82 newer article
records.

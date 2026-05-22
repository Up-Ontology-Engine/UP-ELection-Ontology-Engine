#!/usr/bin/env python3
"""
UP-EOM Management CLI — Ontology Engine + Data Pipeline Manager

Usage:
  python manage.py status
  python manage.py graph apply-constraints [--v2]
  python manage.py graph load [--stage all|etl|neo4j] [--dry-run]
  python manage.py graph stats
  python manage.py graph validate
  python manage.py ingest form20 [--year 2022]
  python manage.py ingest youtube
  python manage.py ingest political
  python manage.py ingest metrics
  python manage.py ingest all
  python manage.py ontology validate
  python manage.py ontology export [--out schema.json]
  python manage.py api start [--port 8000] [--reload]
  python manage.py etl list
  python manage.py etl run <script>
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

# ── Bootstrap: load .env before any project imports ──────────────────────────
_REPO_ROOT = Path(__file__).parent
sys.path.insert(0, str(_REPO_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(_REPO_ROOT / ".env")
except ImportError:
    pass  # python-dotenv not installed; env must be set externally

# ── ANSI colour helpers ───────────────────────────────────────────────────────
_NO_COLOR = not sys.stdout.isatty() or os.environ.get("NO_COLOR")

def _c(code: str, text: str) -> str:
    if _NO_COLOR:
        return text
    return f"\033[{code}m{text}\033[0m"

def green(s: str)  -> str: return _c("32", s)
def red(s: str)    -> str: return _c("31", s)
def yellow(s: str) -> str: return _c("33", s)
def blue(s: str)   -> str: return _c("34", s)
def cyan(s: str)   -> str: return _c("36", s)
def bold(s: str)   -> str: return _c("1",  s)
def dim(s: str)    -> str: return _c("2",  s)
def ok(s: str)     -> str: return f"  {green('✓')} {s}"
def fail(s: str)   -> str: return f"  {red('✗')} {s}"
def warn(s: str)   -> str: return f"  {yellow('!')} {s}"
def info(s: str)   -> str: return f"  {blue('·')} {s}"

def _hr(char: str = "─", width: int = 60) -> str:
    return dim(char * width)

def _section(title: str) -> None:
    print()
    print(bold(cyan(f"▸ {title}")))
    print(_hr())

def _table(rows: list[tuple[str, str]], width: int = 32) -> None:
    for key, val in rows:
        print(f"  {dim(key.ljust(width))} {val}")


# ── Shared DB helpers (lazy imports so CLI loads fast) ───────────────────────

def _pg_engine():
    from api.db import get_pg_engine
    return get_pg_engine()

def _neo4j_session():
    from api.db import get_neo4j_session
    return get_neo4j_session()


# ═══════════════════════════════════════════════════════════════════════════════
# COMMANDS
# ═══════════════════════════════════════════════════════════════════════════════


# ── status ────────────────────────────────────────────────────────────────────

def cmd_status(args: argparse.Namespace) -> None:
    """Health check: PostgreSQL + Neo4j connectivity and row/node counts."""
    print(bold("\n  UP-EOM System Status"))
    print(dim("  Election Ontology Engine — Gorakhpur Urban AC-322"))

    _section("PostgreSQL")
    pg_tables = [
        ("ac_master",             "Assembly Constituencies"),
        ("booth_master",          "Polling Booths"),
        ("booth_metrics",         "Booth Pulse Metrics"),
        ("booth_results",         "Booth Election Results"),
        ("turnout_stats",         "Turnout Stats"),
        ("candidate_master",      "Candidates"),
        ("ac_demographics",       "AC Demographics"),
        ("pulse_events_raw",      "Pulse Events (raw)"),
        ("yt_videos",             "YouTube Videos"),
    ]
    try:
        from sqlalchemy import text
        engine = _pg_engine()
        with engine.connect() as conn:
            print(ok(f"Connected  {dim(os.environ.get('POSTGRES_URL', '').split('@')[-1])}"))
            for tbl, label in pg_tables:
                try:
                    n = conn.execute(text(f"SELECT COUNT(*) FROM {tbl}")).scalar()
                    flag = green(f"{n:>7,}") if (n or 0) > 0 else yellow(f"{n:>7,}")
                    print(f"    {flag}  {dim(label)} ({tbl})")
                except Exception as e:
                    print(f"    {red('ERROR'):>7}  {dim(label)} ({tbl}) — {e}")
    except Exception as e:
        print(fail(f"Cannot connect: {e}"))

    _section("Neo4j Graph")
    try:
        with _neo4j_session() as s:
            uri = os.environ.get("NEO4J_URI", "")
            print(ok(f"Connected  {dim(uri)}"))
            # Node counts
            for rec in s.run(
                "MATCH (n) WITH labels(n)[0] AS lbl, count(n) AS cnt "
                "WHERE lbl IS NOT NULL RETURN lbl, cnt ORDER BY cnt DESC"
            ):
                flag = green(f"{rec['cnt']:>7,}")
                print(f"    {flag}  {dim('nodes')}  :{rec['lbl']}")
            # Rel counts
            total_rels = s.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"]
            print(f"    {green(f'{total_rels:>7,}')}  {dim('total relationships')}")
            # Constraints
            constr = list(s.run("SHOW CONSTRAINTS YIELD name"))
            print(f"    {green(f'{len(constr):>7}'):>7}  {dim('active constraints')}")
    except Exception as e:
        print(fail(f"Cannot connect: {e}"))

    _section("Environment")
    env_vars = [
        "POSTGRES_URL", "NEO4J_URI", "NEO4J_USER",
        "SARVAM_API_KEY", "GOOGLE_API_KEY", "PILOT_AC_ID",
    ]
    for var in env_vars:
        val = os.environ.get(var)
        if val:
            masked = val[:6] + "…" if len(val) > 6 and "KEY" in var else val
            print(ok(f"{var} = {dim(masked)}"))
        else:
            print(warn(f"{var} not set"))
    print()


# ── graph apply-constraints ──────────────────────────────────────────────────

def cmd_graph_apply_constraints(args: argparse.Namespace) -> None:
    """Apply Neo4j schema constraints and indexes from constraints.cypher."""
    cypher_files = [_REPO_ROOT / "graph" / "constraints.cypher"]
    if args.v2:
        cypher_files.append(_REPO_ROOT / "graph" / "constraints_v2.cypher")

    print(bold(f"\n  Applying Neo4j constraints ({len(cypher_files)} file(s))"))

    try:
        with _neo4j_session() as session:
            for cypher_file in cypher_files:
                if not cypher_file.exists():
                    print(warn(f"File not found: {cypher_file}"))
                    continue
                print(info(f"Reading {cypher_file.name}"))
                statements = _parse_cypher_file(cypher_file)
                applied, skipped, errors = 0, 0, 0
                for stmt in statements:
                    stmt = stmt.strip()
                    if not stmt:
                        skipped += 1
                        continue
                    try:
                        session.run(stmt)
                        applied += 1
                    except Exception as e:
                        # IF NOT EXISTS means duplicates are safe — only report real errors
                        if "already exists" not in str(e).lower():
                            print(fail(f"  {stmt[:80]}… → {e}"))
                            errors += 1
                        else:
                            skipped += 1
                status = green("OK") if errors == 0 else red(f"{errors} ERRORS")
                print(ok(f"{cypher_file.name}: {applied} applied · {skipped} skipped · {status}"))
    except Exception as e:
        print(fail(f"Neo4j connection failed: {e}"))
        sys.exit(1)
    print()


def _parse_cypher_file(path: Path) -> list[str]:
    """Split a .cypher file on semicolons, stripping // comments."""
    text = path.read_text()
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("//") or stripped.startswith("//"):
            continue
        lines.append(line)
    return [s.strip() for s in "\n".join(lines).split(";") if s.strip()]


# ── graph load ───────────────────────────────────────────────────────────────

def cmd_graph_load(args: argparse.Namespace) -> None:
    """Run the full ETL → PostgreSQL → Neo4j pipeline."""
    stage = args.stage
    if args.dry_run:
        print(yellow(f"\n  [DRY RUN] Would run: flows.graph.flow_load_graph --stage {stage}"))
        print(info("Remove --dry-run to execute."))
        return

    print(bold(f"\n  Graph Load Pipeline — stage: {stage}"))
    t0 = time.monotonic()
    try:
        from flows.graph.flow_load_graph import run
        run(stage=stage)
        elapsed = time.monotonic() - t0
        print(ok(f"Pipeline complete in {elapsed:.1f}s"))
    except Exception as e:
        print(fail(f"Pipeline failed: {e}"))
        import traceback; traceback.print_exc()
        sys.exit(1)
    print()


# ── graph stats ──────────────────────────────────────────────────────────────

def cmd_graph_stats(args: argparse.Namespace) -> None:
    """Show Neo4j node and relationship counts."""
    print(bold("\n  Neo4j Graph Statistics"))
    try:
        with _neo4j_session() as s:
            _section("Nodes by Label")
            rows = list(s.run(
                "MATCH (n) WITH labels(n)[0] AS lbl, count(n) AS cnt "
                "WHERE lbl IS NOT NULL RETURN lbl, cnt ORDER BY cnt DESC"
            ))
            if not rows:
                print(warn("No nodes found — is the graph loaded?"))
            for rec in rows:
                bar = "█" * min(30, rec["cnt"] // max(1, max(r["cnt"] for r in rows) // 30))
                print(f"    {green(str(rec['cnt']).rjust(6))}  {dim(bar)}  {rec['lbl']}")

            _section("Relationships by Type")
            for rec in s.run(
                "MATCH ()-[r]->() RETURN type(r) AS rel_type, count(r) AS cnt ORDER BY cnt DESC"
            ):
                print(f"    {cyan(str(rec['cnt']).rjust(6))}  [:{rec['rel_type']}]")

            _section("Summary")
            total_n = sum(r["cnt"] for r in rows)
            total_e = s.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"]
            constr  = len(list(s.run("SHOW CONSTRAINTS YIELD name")))
            _table([
                ("Total nodes",       green(f"{total_n:,}")),
                ("Total edges",       cyan(f"{total_e:,}")),
                ("Active constraints", green(str(constr))),
            ])
    except Exception as e:
        print(fail(f"Neo4j connection failed: {e}"))
        sys.exit(1)
    print()


# ── graph validate ───────────────────────────────────────────────────────────

def cmd_graph_validate(args: argparse.Namespace) -> None:
    """Run graph integrity validation checks."""
    print(bold("\n  Graph Validation"))
    try:
        from graph.validators.validate_graph import run as validate
        validate()
    except ImportError:
        print(warn("graph.validators.validate_graph not found — running built-in checks"))
        _builtin_graph_validate()
    print()


def _builtin_graph_validate() -> None:
    """Minimal built-in validation if the validator module is missing."""
    checks: list[tuple[str, str, str]] = []
    try:
        with _neo4j_session() as s:
            # Orphan booths (no AC link)
            n = s.run(
                "MATCH (b:Booth) WHERE NOT ()-[:HAS_BOOTH]->(b) RETURN count(b) AS c"
            ).single()["c"]
            checks.append(("Orphan Booth nodes", str(n), "fail" if n > 0 else "ok"))

            # PulseEvents without Booth
            n = s.run(
                "MATCH (p:PulseEvent) WHERE p.mapped_booth_id IS NULL RETURN count(p) AS c"
            ).single()["c"]
            checks.append(("PulseEvents without booth", str(n), "warn" if n > 0 else "ok"))

            # Candidates without Party link
            n = s.run(
                "MATCH (c:Candidate) WHERE NOT (c)-[:REPRESENTS]->() RETURN count(c) AS c"
            ).single()["c"]
            checks.append(("Candidates missing party", str(n), "warn" if n > 0 else "ok"))

            # Duplicate booth_ids
            n = s.run(
                "MATCH (b:Booth) WITH b.booth_id AS id, count(b) AS c "
                "WHERE c > 1 RETURN count(*) AS dupes"
            ).single()["dupes"]
            checks.append(("Duplicate booth_ids", str(n), "fail" if n > 0 else "ok"))

        for label, count, status in checks:
            marker = ok if status == "ok" else (fail if status == "fail" else warn)
            print(marker(f"{label}: {count}"))
    except Exception as e:
        print(fail(f"Validation failed: {e}"))


# ── ingest ───────────────────────────────────────────────────────────────────

def cmd_ingest(args: argparse.Namespace) -> None:
    """Run data ingestion pipelines."""
    target = args.target
    tasks: list[tuple[str, callable]] = []

    if target in ("form20", "all"):
        tasks.append(("Form-20 Election Data", _ingest_form20))
    if target in ("youtube", "all"):
        tasks.append(("YouTube Videos", _ingest_youtube))
    if target in ("political", "all"):
        tasks.append(("Political Data (booth metrics)", _ingest_political))
    if target in ("metrics", "all"):
        tasks.append(("Booth Metrics Compute", _ingest_metrics))

    if not tasks:
        print(fail(f"Unknown ingest target: {target}"))
        print(info("Available: form20 | youtube | political | metrics | all"))
        sys.exit(1)

    print(bold(f"\n  Data Ingestion — {target}"))
    for label, fn in tasks:
        _section(label)
        t0 = time.monotonic()
        try:
            fn(args)
            elapsed = time.monotonic() - t0
            print(ok(f"Done in {elapsed:.1f}s"))
        except Exception as e:
            print(fail(f"Failed: {e}"))
            import traceback; traceback.print_exc()
    print()


def _ingest_form20(args: argparse.Namespace) -> None:
    from etl.ingest_political_data import run
    run()


def _ingest_youtube(args: argparse.Namespace) -> None:
    from etl.ingest_youtube_videos import run
    run()
    try:
        from etl.stage_youtube_to_pulse import run as stage_run
        stage_run()
        print(info("YouTube → Pulse events staged"))
    except Exception as e:
        print(warn(f"Pulse staging skipped: {e}"))


def _ingest_political(args: argparse.Namespace) -> None:
    from etl.ingest_political_data import run
    run()


def _ingest_metrics(args: argparse.Namespace) -> None:
    from etl.compute_booth_metrics import compute_metrics
    compute_metrics()


# ── ontology validate ────────────────────────────────────────────────────────

def cmd_ontology_validate(args: argparse.Namespace) -> None:
    """Validate ontology: check IDs, constraints, and schema consistency."""
    print(bold("\n  Ontology Validation"))

    from sqlalchemy import text

    checks_passed = 0
    checks_failed = 0

    def chk(label: str, passed: bool, detail: str = "") -> None:
        nonlocal checks_passed, checks_failed
        if passed:
            checks_passed += 1
            print(ok(f"{label}" + (f"  {dim(detail)}" if detail else "")))
        else:
            checks_failed += 1
            print(fail(f"{label}" + (f"  {yellow(detail)}" if detail else "")))

    _section("PostgreSQL ID Format")
    try:
        engine = _pg_engine()
        with engine.connect() as conn:
            # Booth ID format: GKP_322_NNN
            bad_booths = conn.execute(text(
                "SELECT COUNT(*) FROM booth_master WHERE booth_id NOT SIMILAR TO 'GKP_[0-9]+_[0-9]+'"
            )).scalar()
            chk("Booth IDs match GKP_<ac>_<num> pattern", bad_booths == 0,
                f"{bad_booths} non-conforming" if bad_booths else "all match")

            # AC ID format
            bad_acs = conn.execute(text(
                "SELECT COUNT(*) FROM ac_master WHERE ac_id NOT SIMILAR TO 'GKP_[0-9]+'"
            )).scalar()
            chk("AC IDs match GKP_<num> pattern", bad_acs == 0,
                f"{bad_acs} non-conforming" if bad_acs else "all match")

            # Candidate ID
            bad_cands = conn.execute(text(
                "SELECT COUNT(*) FROM candidate_master "
                "WHERE candidate_id NOT SIMILAR TO 'GKP_CAN_[0-9]+_[0-9]+'"
            )).scalar()
            chk("Candidate IDs match GKP_CAN_<year>_<seq>", bad_cands == 0,
                f"{bad_cands} non-conforming" if bad_cands else "all match")

            # Orphan booth_metrics (no matching booth_master)
            orphans = conn.execute(text(
                "SELECT COUNT(*) FROM booth_metrics bm "
                "WHERE NOT EXISTS (SELECT 1 FROM booth_master WHERE booth_id = bm.booth_id)"
            )).scalar()
            chk("booth_metrics has no orphan records", orphans == 0,
                f"{orphans} orphan records" if orphans else "clean")
    except Exception as e:
        print(fail(f"PostgreSQL check failed: {e}"))

    _section("Neo4j Ontology Constraints")
    try:
        with _neo4j_session() as s:
            constr_rows = list(s.run("SHOW CONSTRAINTS YIELD name, labelsOrTypes, properties"))
            constr_set = {
                (r["labelsOrTypes"][0] if r["labelsOrTypes"] else "", r["properties"][0] if r["properties"] else "")
                for r in constr_rows
            }
            required = [
                ("AssemblyConstituency", "ac_id"),
                ("Booth",               "booth_id"),
                ("Candidate",           "candidate_id"),
                ("Party",               "party_id"),
                ("Issue",               "code"),
            ]
            for label, prop in required:
                found = (label, prop) in constr_set
                chk(f"UNIQUE {label}({prop})", found,
                    "active" if found else "MISSING — run: manage.py graph apply-constraints")

            # Orphan detection
            orphan_pe = s.run(
                "MATCH (pe:PulseEvent) WHERE pe.mapped_booth_id IS NOT NULL "
                "AND NOT EXISTS { MATCH (b:Booth {booth_id: pe.mapped_booth_id}) } "
                "RETURN count(pe) AS c"
            ).single()["c"]
            chk("PulseEvents reference valid booths", orphan_pe == 0,
                f"{orphan_pe} dangling" if orphan_pe else "all valid")
    except Exception as e:
        print(fail(f"Neo4j check failed: {e}"))

    _section("Summary")
    total = checks_passed + checks_failed
    color = green if checks_failed == 0 else red
    print(f"  {color(f'{checks_passed}/{total} checks passed')}")
    if checks_failed > 0:
        print(warn("Run 'python manage.py graph apply-constraints' to fix constraint issues."))
    print()


# ── ontology export ──────────────────────────────────────────────────────────

def cmd_ontology_export(args: argparse.Namespace) -> None:
    """Export live ontology schema (entities, relationships, counts) as JSON."""
    print(bold("\n  Ontology Export"))

    schema: dict = {
        "version": "1.0.0-ontology-phase",
        "ac": "GKP_322 — Gorakhpur Urban",
        "entities": [],
        "relationships": [],
        "constraints": [],
        "postgresql_tables": {},
        "neo4j_counts": {},
    }

    try:
        with _neo4j_session() as s:
            for rec in s.run(
                "MATCH (n) WITH labels(n)[0] AS lbl, count(n) AS cnt "
                "WHERE lbl IS NOT NULL RETURN lbl, cnt ORDER BY lbl"
            ):
                schema["neo4j_counts"][rec["lbl"]] = rec["cnt"]
            for rec in s.run("SHOW CONSTRAINTS YIELD name, type, labelsOrTypes, properties"):
                schema["constraints"].append({
                    "name": rec["name"],
                    "type": rec["type"],
                    "labels": list(rec["labelsOrTypes"]),
                    "properties": list(rec["properties"]),
                    "active": True,
                })
        print(ok("Neo4j data collected"))
    except Exception as e:
        print(warn(f"Neo4j unavailable: {e}"))

    try:
        from sqlalchemy import text
        engine = _pg_engine()
        with engine.connect() as conn:
            for tbl in ["ac_master","booth_master","booth_metrics","booth_results",
                        "turnout_stats","candidate_master","ac_demographics",
                        "pulse_events_raw","yt_videos"]:
                try:
                    n = conn.execute(text(f"SELECT COUNT(*) FROM {tbl}")).scalar()
                    schema["postgresql_tables"][tbl] = n
                except Exception:
                    schema["postgresql_tables"][tbl] = None
        print(ok("PostgreSQL counts collected"))
    except Exception as e:
        print(warn(f"PostgreSQL unavailable: {e}"))

    # Static ontology definitions
    schema["entities"] = [
        {"name": "State",              "id_field": "state_id",   "example": "UP"},
        {"name": "District",           "id_field": "district_id","example": "GKP"},
        {"name": "AssemblyConstituency","id_field": "ac_id",     "example": "GKP_322"},
        {"name": "Booth",              "id_field": "booth_id",   "example": "GKP_322_001"},
        {"name": "Candidate",          "id_field": "candidate_id","example": "GKP_CAN_2022_001"},
        {"name": "Party",              "id_field": "party_id",   "example": "BJP"},
        {"name": "Issue",              "id_field": "code",       "example": "water"},
        {"name": "Scheme",             "id_field": "name",       "example": "PM_UJJWALA"},
        {"name": "PulseEvent",         "id_field": "event_id",   "example": "PE_YT_abc123"},
        {"name": "YouTubeVideo",       "id_field": "video_id",   "example": "dQw4w9WgXcQ"},
        {"name": "Channel",            "id_field": "channel_id", "example": "UCxxx"},
    ]
    schema["relationships"] = [
        {"from": "State",             "to": "District",              "type": "HAS_DISTRICT"},
        {"from": "District",          "to": "AssemblyConstituency",  "type": "HAS_AC"},
        {"from": "AssemblyConstituency","to": "Booth",               "type": "HAS_BOOTH"},
        {"from": "Candidate",         "to": "Party",                 "type": "REPRESENTS"},
        {"from": "Candidate",         "to": "AssemblyConstituency",  "type": "CONTESTED_IN"},
        {"from": "PulseEvent",        "to": "Issue",                 "type": "ABOUT_ISSUE"},
        {"from": "YouTubeVideo",      "to": "AssemblyConstituency",  "type": "ABOUT_AC"},
        {"from": "YouTubeVideo",      "to": "Channel",               "type": "FROM_CHANNEL"},
    ]

    out_path = Path(args.out) if args.out else _REPO_ROOT / "ontology_export.json"
    out_path.write_text(json.dumps(schema, indent=2, default=str))
    print(ok(f"Exported to {out_path}"))
    print()


# ── api start ────────────────────────────────────────────────────────────────

def cmd_api_start(args: argparse.Namespace) -> None:
    """Start the FastAPI backend server with uvicorn."""
    port = args.port
    reload_flag = ["--reload"] if args.reload else []
    cmd = [
        sys.executable, "-m", "uvicorn",
        "api.main:app",
        "--host", "0.0.0.0",
        "--port", str(port),
        *reload_flag,
    ]
    print(bold(f"\n  Starting API server on http://0.0.0.0:{port}"))
    if args.reload:
        print(info("Hot-reload enabled"))
    print(dim(f"  $ {' '.join(cmd)}"))
    print()
    try:
        subprocess.run(cmd, cwd=_REPO_ROOT, check=True)
    except KeyboardInterrupt:
        print(f"\n{info('Server stopped')}")
    except subprocess.CalledProcessError as e:
        print(fail(f"Server exited with code {e.returncode}"))
        sys.exit(e.returncode)


# ── etl list / run ───────────────────────────────────────────────────────────

_ETL_SCRIPTS = {
    "form20":         ("etl.ingest_political_data",  "run"),
    "youtube":        ("etl.ingest_youtube_videos",  "run"),
    "metrics":        ("etl.compute_booth_metrics",  "compute_metrics"),
    "youtube-pulse":  ("etl.stage_youtube_to_pulse", "run"),
    "news-pulse":     ("etl.stage_news_to_pulse",    "run"),
    "geography":      ("etl.transform_geography",    "run"),
    "candidates":     ("etl.transform_candidates",   "run"),
    "schemes":        ("etl.transform_schemes",      "run"),
    "panchayats":     ("etl.transform_panchayats",   "run"),
    "census":         ("etl.transform_census",       "run"),
    "seed-cands":     ("etl.seed_known_candidates",  "run"),
    "ls2024":         ("etl.seed_ls2024_results",    "run"),
    "expand-aliases": ("etl.expand_aliases",         "run"),
}

def cmd_etl_list(args: argparse.Namespace) -> None:
    """List all available ETL scripts."""
    print(bold("\n  Available ETL Scripts"))
    _section("Run with: python manage.py etl run <name>")
    for name, (module, fn) in _ETL_SCRIPTS.items():
        print(f"  {cyan(name.ljust(20))}  {dim(module + '.' + fn + '()')}")
    print()


def cmd_etl_run(args: argparse.Namespace) -> None:
    """Run a named ETL script."""
    name = args.script
    if name not in _ETL_SCRIPTS:
        print(fail(f"Unknown ETL script: {name!r}"))
        print(info(f"Run 'python manage.py etl list' to see available scripts."))
        sys.exit(1)

    module_name, fn_name = _ETL_SCRIPTS[name]
    print(bold(f"\n  ETL: {name}  →  {module_name}.{fn_name}()"))
    t0 = time.monotonic()
    try:
        import importlib
        mod = importlib.import_module(module_name)
        fn  = getattr(mod, fn_name)
        fn()
        elapsed = time.monotonic() - t0
        print(ok(f"Completed in {elapsed:.1f}s"))
    except ImportError as e:
        print(fail(f"Module import failed: {e}"))
        sys.exit(1)
    except AttributeError:
        print(fail(f"Function '{fn_name}' not found in {module_name}"))
        sys.exit(1)
    except Exception as e:
        print(fail(f"ETL failed: {e}"))
        import traceback; traceback.print_exc()
        sys.exit(1)
    print()


# ═══════════════════════════════════════════════════════════════════════════════
# ARGUMENT PARSER
# ═══════════════════════════════════════════════════════════════════════════════

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="manage.py",
        description=bold("UP-EOM Management CLI — Election Ontology Engine"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=dim(
            "Examples:\n"
            "  python manage.py status\n"
            "  python manage.py graph apply-constraints\n"
            "  python manage.py graph load --stage neo4j\n"
            "  python manage.py ingest all\n"
            "  python manage.py api start --reload\n"
            "  python manage.py ontology validate\n"
        ),
    )
    sub = p.add_subparsers(dest="command", metavar="<command>")
    sub.required = True

    # status
    sub.add_parser("status", help="Check DB/Neo4j health and row/node counts")

    # graph
    g = sub.add_parser("graph", help="Neo4j graph operations")
    gsub = g.add_subparsers(dest="graph_cmd", metavar="<subcommand>")
    gsub.required = True

    gc = gsub.add_parser("apply-constraints", help="Apply schema constraints from .cypher files")
    gc.add_argument("--v2", action="store_true", help="Also apply constraints_v2.cypher")

    gl = gsub.add_parser("load", help="Run ETL → Postgres → Neo4j pipeline")
    gl.add_argument("--stage", choices=["all", "etl", "neo4j"], default="all")
    gl.add_argument("--dry-run", action="store_true", help="Show what would run, don't execute")

    gsub.add_parser("stats",    help="Show node/relationship counts")
    gsub.add_parser("validate", help="Run graph integrity checks")

    # ingest
    ing = sub.add_parser("ingest", help="Run data ingestion pipelines")
    ing.add_argument(
        "target",
        choices=["form20", "youtube", "political", "metrics", "all"],
        help="What to ingest",
    )
    ing.add_argument("--year", type=int, default=2022, help="Election year (for form20)")

    # ontology
    ont = sub.add_parser("ontology", help="Ontology validation and export")
    osub = ont.add_subparsers(dest="ont_cmd", metavar="<subcommand>")
    osub.required = True
    osub.add_parser("validate", help="Validate IDs and constraints")
    oe = osub.add_parser("export", help="Export ontology schema as JSON")
    oe.add_argument("--out", default=None, metavar="FILE", help="Output file (default: ontology_export.json)")

    # api
    api_p = sub.add_parser("api", help="Start the FastAPI backend")
    asub = api_p.add_subparsers(dest="api_cmd", metavar="<subcommand>")
    asub.required = True
    astart = asub.add_parser("start", help="Start uvicorn server")
    astart.add_argument("--port", type=int, default=8000)
    astart.add_argument("--reload", action="store_true", help="Enable hot-reload")

    # conversion
    conv = sub.add_parser("conversion", help="Voter Conversion Engine operations")
    csub = conv.add_subparsers(dest="conv_cmd", metavar="<subcommand>")
    csub.required = True
    cs = csub.add_parser("seed", help="Seed demo beneficiary data for testing")
    cs.add_argument("--ac", default="GKP_URBAN", metavar="AC_ID", help="AC ID (default: GKP_URBAN)")
    cs.add_argument("--per-booth", type=int, default=18, metavar="N", help="Beneficiaries per booth (default: 18)")
    csub.add_parser("stats", help="Show beneficiary + conversion stats")

    # etl
    etl_p = sub.add_parser("etl", help="Run individual ETL scripts")
    esub = etl_p.add_subparsers(dest="etl_cmd", metavar="<subcommand>")
    esub.required = True
    esub.add_parser("list", help="List all available ETL scripts")
    er = esub.add_parser("run", help="Run a named ETL script")
    er.add_argument("script", metavar="<script>", help="Script name (see: etl list)")

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    dispatch = {
        "status":     cmd_status,
        "graph":      _dispatch_graph,
        "ingest":     cmd_ingest,
        "ontology":   _dispatch_ontology,
        "api":        _dispatch_api,
        "etl":        _dispatch_etl,
        "conversion": _dispatch_conversion,
    }

    handler = dispatch.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()


def _dispatch_graph(args: argparse.Namespace) -> None:
    {
        "apply-constraints": cmd_graph_apply_constraints,
        "load":              cmd_graph_load,
        "stats":             cmd_graph_stats,
        "validate":          cmd_graph_validate,
    }[args.graph_cmd](args)


def _dispatch_ontology(args: argparse.Namespace) -> None:
    {
        "validate": cmd_ontology_validate,
        "export":   cmd_ontology_export,
    }[args.ont_cmd](args)


def _dispatch_api(args: argparse.Namespace) -> None:
    {"start": cmd_api_start}[args.api_cmd](args)


def _dispatch_etl(args: argparse.Namespace) -> None:
    {"list": cmd_etl_list, "run": cmd_etl_run}[args.etl_cmd](args)


def _dispatch_conversion(args: argparse.Namespace) -> None:
    {"seed": cmd_conversion_seed, "stats": cmd_conversion_stats}[args.conv_cmd](args)


def cmd_conversion_seed(args: argparse.Namespace) -> None:
    from api.queries import init_beneficiary_tables, seed_demo_beneficiaries, _rac
    print(info(f"Initialising beneficiary tables…"))
    init_beneficiary_tables()
    ac = args.ac
    n = args.per_booth
    print(info(f"Seeding demo data for {bold(ac)} ({n} beneficiaries/booth)…"))
    count = seed_demo_beneficiaries(_rac(ac), per_booth=n)
    print(ok(f"Seeded {bold(str(count))} beneficiary records."))


def cmd_conversion_stats(args: argparse.Namespace) -> None:
    from api.queries import get_conversion_stats, get_conversion_overview, _rac
    ac = getattr(args, "ac", "GKP_URBAN")
    stats = get_conversion_stats(_rac(ac))
    if not stats["total_beneficiaries"]:
        print(warn("No beneficiary data found. Run: python manage.py conversion seed"))
        return
    print(bold(f"\n=== Conversion Stats: {ac} ==="))
    print(f"  Total Beneficiaries : {green(str(stats['total_beneficiaries']))}")
    print(f"  Conversion Targets  : {yellow(str(stats['total_targets']))} (non-BJP)")
    print(f"  Confirmed Supporters: {cyan(str(stats['total_supporters']))}")
    print(f"  Contacted           : {green(str(stats['total_contacted']))} ({stats['contact_rate_pct']}%)")
    print(f"  Target Contact Rate : {green(str(stats['target_contact_pct']) + '%')}")
    print(f"  Booths With Data    : {stats['booths_with_data']}")
    if stats["top_schemes"]:
        print(bold("\n  Top Schemes:"))
        for s in stats["top_schemes"][:5]:
            print(f"    {s['scheme']:<35} {cyan(str(s['count']))}")
    print()


if __name__ == "__main__":
    main()

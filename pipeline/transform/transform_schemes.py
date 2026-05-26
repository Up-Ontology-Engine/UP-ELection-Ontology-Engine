"""
ETL: eGramSwaraj Scheme Data → scheme_activity + panchayat_master enrichment

Sources:
  data/processed/gov_schemes/BlockWiseSummaryReport_2022-2023.xls  → block-wise panchayat financial summary
  data/processed/gov_schemes/BlockWiseSummaryReport_2024-2025.xls  → same, FY 2024-25
  data/processed/gov_schemes/DistrictWiseExpenditureReport.xls     → district-level receipts/payments

What these files contain:
  - eGramSwaraj panchayat accounting data (Block + Village Panchayat receipts/payments)
  - NOT election Form-20 data
  - Voucher counts (RV=Receipt Voucher, PV=Payment Voucher) per block
  - Used to assess panchayat governance activity level

IMPORTANT: pip install xlrd==1.2.0 required for .xls format

Run: python -m etl.transform_schemes
"""
from __future__ import annotations

import logging
import os
import re
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy import text

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parents[1] / "data" / "data"


def _parse_voucher_count(cell: str) -> dict[str, int]:
    """Parse '89/(RV-1179)/(PV-3421)/(CV-0)/(JV-0)' → {rv: 1179, pv: 3421}"""
    result = {"gp_count": 0, "rv_count": 0, "pv_count": 0}
    if not isinstance(cell, str):
        return result
    m = re.match(r"(\d+)", cell)
    if m:
        result["gp_count"] = int(m.group(1))
    rv = re.search(r"RV-(\d+)", cell)
    pv = re.search(r"PV-(\d+)", cell)
    if rv: result["rv_count"] = int(rv.group(1))
    if pv: result["pv_count"] = int(pv.group(1))
    return result


def load_block_wise_summary(engine: sa.Engine) -> int:
    try:
        import xlrd
    except ImportError:
        raise ImportError("Run: python -m pip install xlrd==1.2.0")

    files = [
        (DATA_DIR / "BlockWiseSummaryReport_2022-2023.xls", "2022-2023"),
        (DATA_DIR / "BlockWiseSummaryReport_2024-2025.xls", "2024-2025"),
    ]

    total = 0
    with engine.connect() as conn:
        for fpath, fy in files:
            if not fpath.exists():
                logger.warning("Not found: %s", fpath)
                continue

            wb = xlrd.open_workbook(str(fpath))
            sh = wb.sheet_by_index(0)

            for row_idx in range(sh.nrows):
                district = str(sh.cell_value(row_idx, 0)).strip()
                if "gorakhpur" not in district.lower():
                    continue

                block_name  = str(sh.cell_value(row_idx, 1)).strip()
                voucher_raw = str(sh.cell_value(row_idx, 3)).strip()

                parsed       = _parse_voucher_count(voucher_raw)
                panchayat_id = f"{block_name.upper().replace(' ', '_')}_BLOCK_AGGREGATE"

                # Ensure FK target exists before inserting scheme_activity
                conn.execute(
                    text("""
                        INSERT INTO panchayat_master (panchayat_id, gp_name, block_name, district_id)
                        VALUES (:pid, :gp, :block, 'GKP')
                        ON CONFLICT (panchayat_id) DO NOTHING
                    """),
                    {"pid": panchayat_id, "gp": f"{block_name} Block", "block": block_name},
                )

                # Store as scheme_activity row representing governance activity
                conn.execute(
                    text("""
                        INSERT INTO scheme_activity
                            (panchayat_id, scheme_name, issue_tag,
                             activity_desc, beneficiary_count, status, financial_year)
                        VALUES
                            (:panchayat_id, :scheme_name, :issue_tag,
                             :activity_desc, :beneficiary_count, :status, :financial_year)
                    """),
                    {
                        "panchayat_id":    panchayat_id,
                        "scheme_name":     "eGramSwaraj Panchayat Activity",
                        "issue_tag":       "governance",
                        "activity_desc":   (
                            f"Block {block_name}: {parsed['gp_count']} GPs, "
                            f"RV={parsed['rv_count']}, PV={parsed['pv_count']}"
                        ),
                        "beneficiary_count": parsed["gp_count"],
                        "status":          "completed",
                        "financial_year":  fy,
                    },
                )
                total += 1

        conn.commit()

    logger.info("Loaded %d block-wise scheme rows for Gorakhpur", total)
    return total


def load_district_expenditure(engine: sa.Engine) -> int:
    """Load district-level panchayat financial data from eGramSwaraj."""
    try:
        import xlrd
    except ImportError:
        raise ImportError("Run: python -m pip install xlrd==1.2.0")

    fpath = DATA_DIR / "DistrictWiseExpenditureReport.xls"
    if not fpath.exists():
        logger.warning("Not found: %s", fpath)
        return 0

    wb = xlrd.open_workbook(str(fpath))
    total = 0

    with engine.connect() as conn:
        for sheet_name in wb.sheet_names():
            sh = wb.sheet_by_name(sheet_name)
            fy = sheet_name  # e.g. "2022-2023"

            for row_idx in range(sh.nrows):
                district = str(sh.cell_value(row_idx, 0)).strip()
                if "gorakhpur" not in district.lower():
                    continue

                try:
                    bp_receipts = float(sh.cell_value(row_idx, 1) or 0)
                    vp_payments = float(sh.cell_value(row_idx, 4) or 0)
                except (ValueError, IndexError):
                    continue

                conn.execute(
                    text("""
                        INSERT INTO panchayat_master (panchayat_id, gp_name, block_name, district_id)
                        VALUES ('GKP_DISTRICT_AGGREGATE', 'Gorakhpur District', 'District', 'GKP')
                        ON CONFLICT (panchayat_id) DO NOTHING
                    """),
                )
                conn.execute(
                    text("""
                        INSERT INTO scheme_activity
                            (panchayat_id, scheme_name, issue_tag,
                             activity_desc, beneficiary_count, status, financial_year)
                        VALUES
                            (:panchayat_id, :scheme_name, :issue_tag,
                             :activity_desc, :beneficiary_count, :status, :financial_year)
                    """),
                    {
                        "panchayat_id":    "GKP_DISTRICT_AGGREGATE",
                        "scheme_name":     "District Panchayat Expenditure",
                        "issue_tag":       "governance",
                        "activity_desc":   (
                            f"Gorakhpur FY{fy}: "
                            f"BP Receipts=₹{bp_receipts/1e7:.1f}Cr, "
                            f"VP Payments=₹{vp_payments/1e7:.1f}Cr"
                        ),
                        "beneficiary_count": 0,
                        "status":          "completed",
                        "financial_year":  fy,
                    },
                )
                total += 1
        conn.commit()

    logger.info("Loaded %d district expenditure rows", total)
    return total


def run():
    engine = sa.create_engine(os.environ["POSTGRES_URL"])
    n1 = load_block_wise_summary(engine)
    n2 = load_district_expenditure(engine)
    logger.info("Total scheme rows loaded: %d", n1 + n2)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    run()

"""
Parse downloaded MyNeta affidavit HTML files for GKP_322 (Gorakhpur Urban 2022)
and emit a structured JSON profile per candidate.

Output: data/raw/candidates/GKP_322_candidate_profiles.json
"""

import json
import re
from pathlib import Path

from bs4 import BeautifulSoup

HTML_DIR = Path("data/raw/myneta_html/uttarpradesh2022")
OUT_FILE = Path("data/raw/candidates/GKP_322_candidate_profiles.json")
BASE_URL  = "https://www.myneta.info/uttarpradesh2022/candidate.php?candidate_id="
ELECTION  = "UP Assembly 2022"
AC_ID     = "GKP_322"


# ── helpers ──────────────────────────────────────────────────────────────────

def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

def _parse_amount(text: str) -> int | None:
    """'1,54,94,054' or 'Rs 1,54,94,054' → 15494054; 'Nil'/'' → None"""
    clean = text.replace("\xa0", " ").strip()
    if not clean or "nil" in clean.lower():
        return None
    # Prefer the number immediately after Rs prefix
    m = re.search(r"Rs\s*([\d,]+)", clean, re.IGNORECASE)
    if m:
        return int(m.group(1).replace(",", ""))
    # Fallback: first multi-digit number (e.g. gross-total row has no Rs prefix)
    m2 = re.search(r"(\d[\d,]*\d)", clean)
    if m2:
        return int(m2.group(1).replace(",", ""))
    return None

def _parse_itr_cell(td_html: str) -> list[dict]:
    """Parse multi-year ITR cell like '2020-2021 ** Rs\xa013,20,653 ...' """
    entries = []
    # bs4 converts &nbsp; to \xa0 in the tag repr
    for match in re.finditer(
        r"(\d{4}\s*-\s*\d{4})\s*\*\*\s*<b>\s*Rs\xa0([\d,]+)", td_html
    ):
        fy  = match.group(1).replace(" ", "")
        amt = int(match.group(2).replace(",", ""))
        if amt > 0:
            entries.append({"fy": fy, "amount_rs": amt})
    return entries


# ── section parsers ───────────────────────────────────────────────────────────

def parse_header(soup: BeautifulSoup) -> dict:
    panel = soup.find("div", class_="w3-sand")
    out = {
        "name": None, "result": None, "party": None,
        "constituency": None, "relation": None, "age": None,
        "voter_enrollment": None, "self_profession": None, "spouse_profession": None,
    }
    if not panel:
        return out

    h2 = panel.find("h2")
    if h2:
        winner = h2.find("font")
        out["result"] = _clean(winner.get_text()).strip("()") if winner else "Lost"
        out["name"] = _clean(h2.get_text().replace(winner.get_text() if winner else "", ""))

    for div in panel.find_all("div"):
        t = _clean(div.get_text())
        if t.startswith("Party:"):
            out["party"] = t.replace("Party:", "").strip()
        elif t.startswith("S/o") or t.startswith("D/o") or t.startswith("W/o"):
            out["relation"] = t
        elif t.startswith("Age:"):
            m = re.search(r"\d+", t)
            out["age"] = int(m.group()) if m else None
        elif "Name Enrolled as Voter in:" in t:
            out["voter_enrollment"] = t.replace("Name Enrolled as Voter in:", "").strip()

    h5 = panel.find("h5")
    if h5:
        out["constituency"] = _clean(h5.get_text())

    prof_p = panel.find("p")
    if prof_p:
        lines = [_clean(l) for l in prof_p.get_text("\n").split("\n") if l.strip()]
        for line in lines:
            if line.startswith("Self Profession:"):
                out["self_profession"] = line.replace("Self Profession:", "").strip()
            elif line.startswith("Spouse Profession:"):
                out["spouse_profession"] = line.replace("Spouse Profession:", "").strip()

    return out


def parse_criminal_cases(soup: BeautifulSoup) -> dict:
    section = soup.find("div", string=re.compile(r"Details of Criminal Cases"))
    criminal_text = ""
    cases_count = 0

    # Extract count from Google Charts data in the gauage script
    scripts = soup.find_all("script")
    for s in scripts:
        sc = s.get_text()
        m = re.search(r"\['Cases',\s*(\d+)\]", sc)
        if m:
            cases_count = int(m.group(1))
            break

    if section:
        # Walk siblings until next section
        details = []
        for sib in section.find_next_siblings():
            if sib.name and "w3-panel" in sib.get("class", []) and sib != section:
                break
            t = _clean(sib.get_text())
            if t and t not in ("", "No criminal cases"):
                details.append(t)
        criminal_text = " ".join(details)

    return {
        "count": cases_count,
        "details": criminal_text if criminal_text else None,
    }


def parse_education(soup: BeautifulSoup) -> dict:
    panel = soup.find("h3", string=re.compile(r"Educational Details"))
    if not panel:
        return {"category": None, "degree": None, "institution": None, "year": None}
    container = panel.find_parent("div")
    text = _clean(container.get_text(" ")) if container else ""
    category = None
    m = re.search(r"Category:\s*(\S+)", text)
    if m:
        category = m.group(1)
    degree = institution = year = None
    # Strip header and category lines before matching degree
    text_for_degree = re.sub(r"Educational Details\s*", "", text, flags=re.IGNORECASE)
    text_for_degree = re.sub(r"Category:\s*\S+\s*", "", text_for_degree)
    # Pattern: "B.Sc. from H. N. Bahuguna University, ... in 1992"
    m2 = re.search(r"([\w\.\s]+?)\s+from\s+(.+?)\s+in\s+(\d{4})", text_for_degree)
    if m2:
        degree      = _clean(m2.group(1))
        institution = _clean(m2.group(2))
        year        = int(m2.group(3))
    return {"category": category, "degree": degree, "institution": institution, "year": year}


def parse_itr(soup: BeautifulSoup) -> dict:
    table = soup.find("table", id="income_tax")
    if not table:
        return {"self": [], "spouse": [], "huf": []}
    result = {"self": [], "spouse": [], "huf": []}
    for row in table.find_all("tr")[1:]:
        cells = row.find_all("td")
        if len(cells) < 4:
            continue
        relation = _clean(cells[0].get_text()).lower()
        itr_cell_html = str(cells[3])
        entries = _parse_itr_cell(itr_cell_html)
        if relation in result:
            result[relation] = entries
        elif entries:
            result[relation] = entries
    return result


def parse_movable_assets(soup: BeautifulSoup) -> dict:
    table = soup.find("table", id="movable_assets")
    if not table:
        return {}
    labels = {
        "i":   "cash",
        "ii":  "bank_deposits",
        "iii": "bonds_debentures_shares",
        "iv":  "postal_savings_lic",
        "v":   "personal_loans_given",
        "vi":  "motor_vehicles",
        "vii": "jewellery",
        "viii":"other_assets",
    }
    assets: dict = {}
    total_movable = None
    rows = table.find_all("tr")
    for row in rows:
        cells = row.find_all("td")
        if not cells:
            continue
        # Total rows
        first = _clean(cells[0].get_text())
        if "Gross Total" in first or "Totals (Calculated" in first:
            # last td is the combined total
            last_td = cells[-1]
            total_movable = _parse_amount(last_td.get_text())
            continue
        sr = _clean(cells[0].get_text()).lower().rstrip(".")
        if sr not in labels:
            continue
        key = labels[sr]
        # Table layout: [0]=SrNo [1]=Description [2]=self [3..7]=spouse..dep3 [-1]=total
        # Data rows have 9 cells (extra total col); header/total rows have 8
        self_td  = cells[2] if len(cells) >= 9 else None
        total_td = cells[-1] if len(cells) >= 9 else None

        self_amount  = _parse_amount(self_td.get_text())  if self_td  else None
        total_amount = _parse_amount(total_td.get_text()) if total_td else None

        # Descriptions (e.g. bank names) are <span class="desc"> inside the self column
        descs = []
        if self_td:
            for span in self_td.find_all("span", class_="desc"):
                descs.append(_clean(span.get_text()))

        assets[key] = {
            "self_amount_rs": self_amount,
            "total_amount_rs": total_amount,
            "descriptions": descs if descs else None,
        }

    assets["total_movable_rs"] = total_movable
    return assets


def parse_immovable_assets(soup: BeautifulSoup) -> dict:
    table = soup.find("table", id="immovable_assets")
    if not table:
        return {}
    labels = {
        "i":   "agricultural_land",
        "ii":  "non_agricultural_land",
        "iii": "commercial_buildings",
        "iv":  "residential_buildings",
        "v":   "others",
    }
    assets: dict = {}
    total_immovable = None
    for row in table.find_all("tr"):
        cells = row.find_all("td")
        if not cells:
            continue
        first = _clean(cells[0].get_text())
        if "Total Current Market Value" in first or "Totals Calculated" in first:
            total_immovable = _parse_amount(cells[-1].get_text())
            continue
        sr = _clean(cells[0].get_text()).lower().rstrip(".")
        if sr not in labels:
            continue
        key = labels[sr]
        self_td  = cells[1] if len(cells) > 1 else None
        total_td = cells[-1]
        assets[key] = {
            "self_amount_rs": _parse_amount(self_td.get_text()) if self_td else None,
            "total_amount_rs": _parse_amount(total_td.get_text()),
        }
    assets["total_immovable_rs"] = total_immovable
    return assets


def parse_liabilities(soup: BeautifulSoup) -> dict:
    table = soup.find("table", id="liabilities")
    if not table:
        return {}
    rows = table.find_all("tr")
    result: dict = {"total_liabilities_rs": None, "govt_dues_total_rs": None, "items": []}
    for row in rows:
        cells = row.find_all("td")
        if not cells:
            continue
        desc = _clean(cells[1].get_text()) if len(cells) > 1 else ""
        total_td = cells[-1]
        amt = _parse_amount(total_td.get_text())
        if "Grand Total of Liabilities" in desc:
            result["total_liabilities_rs"] = amt
        elif "Grand Total of all Govt Dues" in desc:
            result["govt_dues_total_rs"] = amt
        elif amt and amt > 0:
            result["items"].append({"description": desc, "total_rs": amt})
    return result


def parse_profession(soup: BeautifulSoup) -> dict:
    table = soup.find("table", id="profession")
    if not table:
        return {"self": None, "spouse": None}
    rows = table.find_all("tr")
    out: dict = {}
    for row in rows:
        cells = row.find_all("td")
        if len(cells) >= 2:
            key = _clean(cells[0].get_text()).lower()
            val = _clean(cells[1].get_text())
            out[key] = val if val not in ("NA", "N/A", "") else None
    return out


def parse_other_elections(soup: BeautifulSoup) -> list[dict]:
    rows = soup.select("table.w3-striped.w3-centered tr")
    results = []
    for row in rows:
        cells = row.find_all("td")
        if len(cells) >= 3:
            election = _clean(cells[0].get_text())
            assets   = _parse_amount(cells[1].get_text())
            cases    = _clean(cells[2].get_text())
            if election and not election.startswith("Declaration"):
                results.append({
                    "election": election,
                    "declared_assets_rs": assets,
                    "declared_cases": int(cases) if cases.isdigit() else None,
                })
    return results


# ── main parser ───────────────────────────────────────────────────────────────

def parse_file(html_path: Path) -> dict:
    myneta_id = int(html_path.stem.replace("_affidavit", ""))
    soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser")

    header      = parse_header(soup)
    criminal    = parse_criminal_cases(soup)
    education   = parse_education(soup)
    itr         = parse_itr(soup)
    movable     = parse_movable_assets(soup)
    immovable   = parse_immovable_assets(soup)
    liabilities = parse_liabilities(soup)
    profession  = parse_profession(soup)
    other_elec  = parse_other_elections(soup)

    # Summary totals from the small card (more reliable for nil cases)
    assets_card = soup.find("a", attrs={"href": "#movable_assets"})
    net_worth_rs = total_assets_rs = total_liab_rs = None
    if assets_card:
        _card_parent = assets_card.find_parent("div")
        card_table = _card_parent.find("table") if _card_parent else None
        if card_table:
            for row in card_table.find_all("tr"):
                cells = row.find_all("td")
                if len(cells) >= 2:
                    label = _clean(cells[0].get_text()).lower()
                    val   = _parse_amount(cells[1].get_text())
                    if "assets" in label:
                        total_assets_rs = val
                    elif "liabilities" in label:
                        total_liab_rs = val
            if total_assets_rs is not None and total_liab_rs is not None:
                net_worth_rs = total_assets_rs - total_liab_rs
            elif total_assets_rs is not None:
                net_worth_rs = total_assets_rs

    return {
        "myneta_id": myneta_id,
        "source_url": f"{BASE_URL}{myneta_id}",
        "election": ELECTION,
        "ac_id": AC_ID,
        "personal": {
            "name": header["name"],
            "result": header["result"],
            "party": header["party"],
            "constituency": header["constituency"],
            "relation": header["relation"],
            "age": header["age"],
            "voter_enrollment": header["voter_enrollment"],
        },
        "profession": {
            "self": header.get("self_profession") or profession.get("self"),
            "spouse": header.get("spouse_profession") or profession.get("spouse"),
        },
        "education": education,
        "criminal_cases": criminal,
        "income": {
            "itr": itr,
        },
        "assets": {
            "summary": {
                "total_assets_rs": total_assets_rs,
                "total_liabilities_rs": total_liab_rs,
                "net_worth_rs": net_worth_rs,
            },
            "movable": movable,
            "immovable": immovable,
            "liabilities": liabilities,
        },
        "electoral_history": other_elec,
    }


def main():
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    profiles = []
    html_files = sorted(HTML_DIR.glob("*_affidavit.html"))
    print(f"Parsing {len(html_files)} HTML files...")
    for f in html_files:
        try:
            profile = parse_file(f)
            profiles.append(profile)
            print(f"  {f.name} | {profile['personal']['name']} ({profile['personal']['party']}) "
                  f"assets={profile['assets']['summary']['total_assets_rs']}")
        except Exception as e:
            print(f"  ERROR {f.name}: {e}")

    OUT_FILE.write_text(json.dumps(profiles, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {len(profiles)} profiles to {OUT_FILE}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Generate weekly KV milestone report snapshots with LLM narrative."""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
from dotenv import load_dotenv

from gus_client import GUSClient

load_dotenv()

DATA_DIR = Path(__file__).parent / "data"
WEEKLY_DIR = DATA_DIR / "weekly_reports"
XLSX_BASE_DIR = DATA_DIR / "xlsx"
REPORTS = {
    "SCRT2 milestones": "00OEE000002tild2AA",
    "VegamDB milestones": "00OEE000002tu8T2AQ",
}


def normalize_text(value: object) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):  # Handles NaN/NaT from Excel imports
            return ""
    except Exception:
        pass
    return str(value).strip()


def pick_column(columns: List[str], candidates: List[str]) -> Optional[str]:
    lowered = {c.lower().replace("_", " ").replace(".", " "): c for c in columns}
    for candidate in candidates:
        for lower_name, original in lowered.items():
            if candidate in lower_name:
                return original
    return None


def parse_percent(value: object) -> float:
    text = normalize_text(value).replace("%", "")
    if text == "":
        return 0.0
    try:
        parsed = float(text)
        if 0.0 <= parsed <= 1.0:
            parsed *= 100.0
        return max(0.0, min(100.0, parsed))
    except ValueError:
        return 0.0


def parse_remaining(value: object) -> float:
    text = normalize_text(value)
    if text == "":
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def build_gus_epic_url(epic_id: str, explicit_url: str = "") -> str:
    explicit = normalize_text(explicit_url)
    if explicit.startswith("http://") or explicit.startswith("https://"):
        return explicit
    record_id = normalize_text(epic_id)
    if len(record_id) >= 15:
        return f"https://gus.lightning.force.com/lightning/r/ADM_Theme__c/{record_id}/view"
    return ""


def build_milestone_rows(report_json: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows, detail_columns = GUSClient.flatten_rows(report_json)
    if not rows:
        return []

    columns = detail_columns or list(rows[0].keys())
    milestone_col = pick_column(columns, ["milestone", "theme"])
    team_col = pick_column(columns, ["team", "owner", "assignee", "scrumteam", "scrum team"])
    owner_col = pick_column(columns, ["owner full name", "owner", "product owner"])
    epic_name_col = pick_column(columns, ["epic name", "work", "epic", "subject", "title", "summary"])
    epic_id_col = pick_column(columns, ["epic id", "work id", "work item id", "id"])
    epic_url_col = pick_column(columns, ["epic url", "url", "link"])
    status_col = pick_column(columns, ["health", "status", "state"])
    comment_col = pick_column(columns, ["epic health comment", "health comment", "latest update", "comment", "notes"])
    percent_col = pick_column(columns, ["% complete", "percent complete", "completion", "progress"])
    remaining_col = pick_column(columns, ["remaining work items", "remaining items", "remaining", "work items"])

    output: List[Dict[str, Any]] = []
    last_milestone = ""
    last_team = ""
    last_owner = ""
    for row in rows:
        milestone = normalize_text(row.get(milestone_col, "")) if milestone_col else ""
        team = normalize_text(row.get(team_col, "")) if team_col else ""
        owner = normalize_text(row.get(owner_col, "")) if owner_col else ""

        if milestone:
            last_milestone = milestone
        if team:
            last_team = team
        if owner:
            last_owner = owner

        epic_name = normalize_text(row.get(epic_name_col, "")) if epic_name_col else ""
        if not epic_name or epic_name.isdigit():
            continue
        output.append(
            {
                "Milestone": milestone or last_milestone,
                "Team": team or last_team,
                "Owner": owner or last_owner,
                "Epic Name": epic_name,
                "Epic ID": normalize_text(row.get(epic_id_col, "")) if epic_id_col else "",
                "Status": normalize_text(row.get(status_col, "")) if status_col else "",
                "Epic Health Comment": normalize_text(row.get(comment_col, "")) if comment_col else "",
                "% Complete": parse_percent(row.get(percent_col, 0.0)) if percent_col else 0.0,
                "Remaining Work Items": parse_remaining(row.get(remaining_col, 0.0)) if remaining_col else 0.0,
                "GUS Epic": build_gus_epic_url(
                    normalize_text(row.get(epic_id_col, "")) if epic_id_col else "",
                    normalize_text(row.get(epic_url_col, "")) if epic_url_col else "",
                ),
            }
        )
    return output


def build_milestone_rows_from_table(raw_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not raw_rows:
        return []
    columns = list(raw_rows[0].keys())
    milestone_col = pick_column(columns, ["theme", "milestone"])
    team_col = pick_column(columns, ["team", "owner", "assignee"])
    owner_col = pick_column(columns, ["owner full name", "owner", "product owner"])
    epic_name_col = pick_column(columns, ["epic name", "work", "epic", "subject", "title", "summary"])
    epic_id_col = pick_column(columns, ["epic id", "work id", "work item id", "id"])
    epic_url_col = pick_column(columns, ["epic url", "url", "link"])
    status_col = pick_column(columns, ["health", "status", "state"])
    comment_col = pick_column(columns, ["epic health comment", "health comment", "latest update", "comment", "notes"])
    percent_col = pick_column(columns, ["% of work items complete", "% complete", "percent complete", "completion", "progress"])
    remaining_col = pick_column(columns, ["remaining work items", "remaining items", "remaining"])
    subtotal_col = pick_column(columns, ["subtotal", "count"])

    output: List[Dict[str, Any]] = []
    last_milestone = ""
    last_team = ""
    last_owner = ""
    for row in raw_rows:
        milestone = normalize_text(row.get(milestone_col, "")) if milestone_col else ""
        team = normalize_text(row.get(team_col, "")) if team_col else ""
        owner = normalize_text(row.get(owner_col, "")) if owner_col else ""

        # Carry forward grouping context across rows, including non-epic group header rows.
        if milestone:
            last_milestone = milestone
        if team:
            last_team = team
        if owner:
            last_owner = owner

        epic_name = normalize_text(row.get(epic_name_col, "")) if epic_name_col else ""
        if not epic_name or epic_name.lower() in {"subtotal", "count"} or epic_name.isdigit():
            continue
        if subtotal_col:
            subtotal_value = normalize_text(row.get(subtotal_col, ""))
            if subtotal_value.lower() in {"subtotal", "count"}:
                continue

        output.append(
            {
                "Milestone": milestone or last_milestone,
                "Team": team or last_team,
                "Owner": owner or last_owner,
                "Epic Name": epic_name,
                "Epic ID": normalize_text(row.get(epic_id_col, "")) if epic_id_col else "",
                "Status": normalize_text(row.get(status_col, "")) if status_col else "",
                "Epic Health Comment": normalize_text(row.get(comment_col, "")) if comment_col else "",
                "% Complete": parse_percent(row.get(percent_col, 0.0)) if percent_col else 0.0,
                "Remaining Work Items": parse_remaining(row.get(remaining_col, 0.0)) if remaining_col else 0.0,
                "GUS Epic": build_gus_epic_url(
                    normalize_text(row.get(epic_id_col, "")) if epic_id_col else "",
                    normalize_text(row.get(epic_url_col, "")) if epic_url_col else "",
                ),
            }
        )
    return output


def read_rows_from_xlsx(xlsx_path: str) -> List[Dict[str, Any]]:
    sheet = pd.read_excel(xlsx_path, sheet_name=0, header=None)
    header_idx = None
    for idx, row in sheet.iterrows():
        values = [normalize_text(v).lower() for v in row.tolist()]
        if any("epic name" in v for v in values) and any("health" in v or "status" in v for v in values):
            header_idx = idx
            break
    if header_idx is None:
        raise ValueError(f"Could not detect header row in Excel file: {xlsx_path}")

    headers = [normalize_text(v) for v in sheet.iloc[header_idx].tolist()]
    data = sheet.iloc[header_idx + 1 :].copy()
    data.columns = headers
    data = data.dropna(how="all")

    normalized_rows: List[Dict[str, Any]] = []
    for _, row in data.iterrows():
        item = {str(k): row[k] for k in data.columns if str(k).strip() and not str(k).startswith("Unnamed")}
        normalized_rows.append(item)
    return build_milestone_rows_from_table(normalized_rows)


def current_week_key(now: datetime) -> str:
    iso = now.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def current_cw_label(now: datetime) -> str:
    return f"cw{now.isocalendar().week:02d}"


def detect_week_excel_files(week_label: str, xlsx_base_dir: Path) -> Dict[str, Optional[str]]:
    week_dir = xlsx_base_dir / week_label
    discovered: Dict[str, Optional[str]] = {
        "SCRT2 milestones": None,
        "VegamDB milestones": None,
    }
    if not week_dir.exists():
        return discovered

    for path in sorted(week_dir.glob("*.xlsx")):
        name = path.name.lower()
        if "scrt2" in name and discovered["SCRT2 milestones"] is None:
            discovered["SCRT2 milestones"] = str(path)
        if ("vegamdb" in name or "vega" in name) and discovered["VegamDB milestones"] is None:
            discovered["VegamDB milestones"] = str(path)
    return discovered


def summarize_tab(rows: List[Dict[str, Any]], label: str) -> Dict[str, Any]:
    total = len(rows)
    teams = len({r["Team"] for r in rows if r.get("Team")})
    statuses = len({r["Status"] for r in rows if r.get("Status")})
    avg_complete = round(sum(float(r.get("% Complete", 0.0)) for r in rows) / total, 1) if total else 0.0
    remaining = round(sum(float(r.get("Remaining Work Items", 0.0)) for r in rows), 1)
    return {
        "label": label,
        "total_epics": total,
        "teams": teams,
        "status_buckets": statuses,
        "avg_complete": avg_complete,
        "remaining_work_items": remaining,
    }


def parse_milestone_date(value: str) -> Optional[str]:
    text = normalize_text(value)
    match = re.search(r"(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?", text)
    if not match:
        return None
    month = int(match.group(1))
    day = int(match.group(2))
    year_text = match.group(3)
    year = datetime.now().year if not year_text else int(year_text)
    if year < 100:
        year += 2000
    try:
        return datetime(year, month, day).strftime("%Y-%m-%d")
    except ValueError:
        return None


def build_milestone_groups(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        milestone = normalize_text(row.get("Milestone", "")) or "Unspecified"
        grouped.setdefault(milestone, []).append(row)

    groups: List[Dict[str, Any]] = []
    for milestone, items in grouped.items():
        groups.append(
            {
                "milestone": milestone,
                "milestone_date": parse_milestone_date(milestone),
                "epic_count": len(items),
                "epics": [
                    {
                        "Epic Name": normalize_text(i.get("Epic Name", "")),
                        "Status": normalize_text(i.get("Status", "")),
                        "Epic Health Comment": normalize_text(i.get("Epic Health Comment", "")),
                        "Team": normalize_text(i.get("Team", "")),
                        "Owner": normalize_text(i.get("Owner", "")),
                        "% Complete": float(i.get("% Complete", 0.0) or 0.0),
                        "Remaining Work Items": float(i.get("Remaining Work Items", 0.0) or 0.0),
                        "GUS Epic": normalize_text(i.get("GUS Epic", "")),
                    }
                    for i in items
                ],
            }
        )

    # Sort by parsed date when available, then by milestone name
    groups.sort(key=lambda g: (g["milestone_date"] is None, g["milestone_date"] or "9999-12-31", g["milestone"]))
    return groups


class KVNarrativeGenerator:
    """Generate weekly summary text using LLM gateway with safe fallback."""

    def __init__(self) -> None:
        self.api_key = os.getenv("LLM_GW_EXPRESS_KEY", "").strip()
        self.openai_user_id = os.getenv("OPENAI_USER_ID", "").strip()
        self.model = os.getenv("KV_LLM_MODEL", "claude-sonnet-4-20250514")
        self.api_url = "https://eng-ai-model-gateway.sfproxy.devx-preprod.aws-esvc1-useast2.aws.sfdc.cl/chat/completions"

    def generate(self, week_key: str, tab_summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not self.api_key:
            return self._fallback(tab_summaries)
        try:
            return self._call_llm(week_key, tab_summaries)
        except Exception:
            return self._fallback(tab_summaries)

    def _fallback(self, tab_summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
        headline = "Weekly milestone snapshot"
        overall = "Auto-generated summary (LLM unavailable): "
        parts: List[str] = []
        per_tab: Dict[str, str] = {}
        for summary in tab_summaries:
            sentence = (
                f"{summary['label']}: {summary['total_epics']} epics, "
                f"{summary['avg_complete']}% avg completion, "
                f"{summary['remaining_work_items']} remaining work items."
            )
            parts.append(sentence)
            per_tab[summary["label"]] = sentence
        overall += " ".join(parts)
        return {"headline": headline, "overall_summary": overall, "tab_narratives": per_tab}

    def _call_llm(self, week_key: str, tab_summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
        prompt = (
            "You are a program operations analyst. Write concise executive narrative for weekly epic milestone status. "
            "Return strict JSON with keys: headline, overall_summary, tab_narratives. "
            "tab_narratives must be an object keyed by tab label, each value 2-3 sentences.\n\n"
            f"Week: {week_key}\n"
            f"Tab summaries:\n{json.dumps(tab_summaries, indent=2)}"
        )
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Return valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        if self.openai_user_id:
            payload["user"] = self.openai_user_id

        response = requests.post(self.api_url, headers=headers, json=payload, timeout=90)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            raise ValueError("LLM response is not an object")
        return parsed


def save_weekly_bundle(bundle: Dict[str, Any]) -> Path:
    WEEKLY_DIR.mkdir(parents=True, exist_ok=True)
    week_key = bundle["week_key"]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = WEEKLY_DIR / f"weekly_report_{week_key}_{timestamp}.json"
    latest = WEEKLY_DIR / "latest.json"
    path.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    latest.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    return path


def generate_weekly_report(
    scrt2_xlsx: Optional[str] = None,
    vegamdb_xlsx: Optional[str] = None,
    week_label: Optional[str] = None,
    xlsx_base_dir: Optional[str] = None,
) -> Path:
    now = datetime.now()
    resolved_week_label = week_label or current_cw_label(now)
    resolved_xlsx_base = Path(xlsx_base_dir) if xlsx_base_dir else XLSX_BASE_DIR
    auto_xlsx = detect_week_excel_files(resolved_week_label, resolved_xlsx_base)
    scrt2_xlsx = scrt2_xlsx or auto_xlsx["SCRT2 milestones"]
    vegamdb_xlsx = vegamdb_xlsx or auto_xlsx["VegamDB milestones"]

    session = GUSClient().get_session()
    if not session and not (scrt2_xlsx and vegamdb_xlsx):
        raise RuntimeError(
            "Missing SF auth. Set SF_INSTANCE_URL/SF_ACCESS_TOKEN (or SALESFORCE_*), "
            "or provide both --scrt2-xlsx and --vegamdb-xlsx."
        )

    tabs_payload: Dict[str, Any] = {}
    tab_summaries: List[Dict[str, Any]] = []
    for label, report_id in REPORTS.items():
        xlsx_source = scrt2_xlsx if label == "SCRT2 milestones" else vegamdb_xlsx
        if xlsx_source:
            rows = read_rows_from_xlsx(xlsx_source)
            source = f"Excel ({Path(xlsx_source).name})"
        else:
            if not session:
                raise RuntimeError(f"Missing Salesforce session for report {label}.")
            raw = GUSClient(report_id=report_id).fetch_report(session)
            rows = build_milestone_rows(raw)
            source = "GUS Reports API"
        summary = summarize_tab(rows, label)
        milestone_groups = build_milestone_groups(rows)
        tab_summaries.append(summary)
        tabs_payload[label] = {
            "report_id": report_id,
            "rows": rows,
            "metadata": {
                **summary,
                "grouped_by_milestone": milestone_groups,
                "milestones": [g["milestone"] for g in milestone_groups],
            },
            "source": source,
        }

    week_key = current_week_key(now)
    narrative = KVNarrativeGenerator().generate(week_key, tab_summaries)
    for label in REPORTS:
        tabs_payload[label]["narrative"] = narrative.get("tab_narratives", {}).get(label, "")

    bundle = {
        "week_key": week_key,
        "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "metadata": {
            "report_type": "kv_milestone_weekly",
            "source": "Mixed" if (scrt2_xlsx or vegamdb_xlsx) else "GUS Reports API",
            "reports": REPORTS,
            "week_label": resolved_week_label,
            "inputs": {
                "scrt2_xlsx": scrt2_xlsx or "",
                "vegamdb_xlsx": vegamdb_xlsx or "",
                "xlsx_base_dir": str(resolved_xlsx_base),
            },
            "tab_summaries": tab_summaries,
        },
        "narrative": {
            "headline": narrative.get("headline", ""),
            "overall_summary": narrative.get("overall_summary", ""),
        },
        "tabs": tabs_payload,
    }
    return save_weekly_bundle(bundle)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate KV weekly milestone report")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and build without saving report")
    parser.add_argument("--scrt2-xlsx", type=str, default="", help="Path to SCRT2 milestones Excel file")
    parser.add_argument("--vegamdb-xlsx", type=str, default="", help="Path to VegamDB milestones Excel file")
    parser.add_argument("--week", type=str, default="", help="Calendar week label like cw14")
    parser.add_argument("--xlsx-base-dir", type=str, default="", help="Base directory for weekly xlsx folders")
    args = parser.parse_args()
    week_label = args.week.strip() or current_cw_label(datetime.now())
    if not re.match(r"^cw\d{2}$", week_label, re.IGNORECASE):
        raise RuntimeError("Invalid --week format. Use values like cw14.")
    week_label = week_label.lower()
    xlsx_base_dir = args.xlsx_base_dir.strip() or str(XLSX_BASE_DIR)

    if args.dry_run:
        discovered = detect_week_excel_files(week_label, Path(xlsx_base_dir))
        if not args.scrt2_xlsx and discovered["SCRT2 milestones"]:
            print(f"Auto-detected SCRT2 file: {discovered['SCRT2 milestones']}")
        if not args.vegamdb_xlsx and discovered["VegamDB milestones"]:
            print(f"Auto-detected VegamDB file: {discovered['VegamDB milestones']}")
        if args.scrt2_xlsx:
            print(f"Dry-run Excel parse: {args.scrt2_xlsx}")
            print(f"Rows parsed: {len(read_rows_from_xlsx(args.scrt2_xlsx))}")
            return 0
        if args.vegamdb_xlsx:
            print(f"Dry-run Excel parse: {args.vegamdb_xlsx}")
            print(f"Rows parsed: {len(read_rows_from_xlsx(args.vegamdb_xlsx))}")
            return 0
        session = GUSClient().get_session()
        if not session:
            raise RuntimeError("Missing SF auth. Set SF_INSTANCE_URL/SF_ACCESS_TOKEN (or SALESFORCE_*).")
        print("Dry-run auth check passed.")
        return 0

    path = generate_weekly_report(
        scrt2_xlsx=args.scrt2_xlsx or None,
        vegamdb_xlsx=args.vegamdb_xlsx or None,
        week_label=week_label,
        xlsx_base_dir=xlsx_base_dir,
    )
    print(f"Saved weekly report: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

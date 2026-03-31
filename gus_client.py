#!/usr/bin/env python3
"""
GUS report client for Salesforce Analytics API.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv

load_dotenv()

DEFAULT_REPORT_ID = "00OEE000002tild2AA"
DEFAULT_API_VERSION = "v62.0"


class GUSClient:
    """Fetches Salesforce report data and flattens detail rows."""

    def __init__(self, report_id: str = DEFAULT_REPORT_ID, api_version: str = DEFAULT_API_VERSION):
        self.report_id = report_id
        self.api_version = api_version

    def get_session(self) -> Optional[Dict[str, str]]:
        """Resolve Salesforce session from environment variables."""
        instance_url = os.getenv("SF_INSTANCE_URL", "").strip()
        access_token = os.getenv("SF_ACCESS_TOKEN", "").strip()
        if instance_url and access_token:
            return {"instance_url": instance_url, "access_token": access_token}

        # QC-style fallback vars
        session_id = os.getenv("SALESFORCE_SESSION_ID", "").strip()
        instance_host = os.getenv("SALESFORCE_INSTANCE", "").strip()
        if session_id and instance_host:
            if instance_host.startswith("http://") or instance_host.startswith("https://"):
                resolved_instance = instance_host
            else:
                resolved_instance = f"https://{instance_host}"
            return {"instance_url": resolved_instance, "access_token": session_id}
        return None

    def fetch_report(self, session: Dict[str, str]) -> Dict[str, Any]:
        """Fetch report JSON from Salesforce Analytics API."""
        base_url = session["instance_url"].rstrip("/")
        url = f"{base_url}/services/data/{self.api_version}/analytics/reports/{self.report_id}"
        response = requests.get(
            url,
            headers={
                "Authorization": f"Bearer {session['access_token']}",
                "Accept": "application/json",
            },
            params={"includeDetails": "true"},
            timeout=90,
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def flatten_rows(report_json: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Convert `factMap` rows into list[dict] using detail column positions."""
        metadata = report_json.get("reportMetadata", {})
        detail_columns = metadata.get("detailColumns", []) or []
        fact_map = report_json.get("factMap", {}) or {}
        rows: List[Dict[str, Any]] = []

        for _, fact in fact_map.items():
            for detail_row in fact.get("rows", []) or []:
                cells = detail_row.get("dataCells", []) or []
                out: Dict[str, Any] = {}
                for idx, cell in enumerate(cells):
                    column = detail_columns[idx] if idx < len(detail_columns) else f"column_{idx}"
                    value = cell.get("value")
                    label = cell.get("label")
                    out[column] = value if value is not None else label
                    out[f"{column}__label"] = label
                    out[f"{column}__value"] = value
                rows.append(out)

        return rows, detail_columns


def save_snapshot(report_json: Dict[str, Any], output_dir: Path, report_id: str) -> Path:
    """Save timestamped and latest snapshots for fast reload."""
    output_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    dated = output_dir / f"report_{report_id}_{now}.json"
    latest = output_dir / f"report_{report_id}_latest.json"

    dated.write_text(json.dumps(report_json, indent=2), encoding="utf-8")
    latest.write_text(json.dumps(report_json, indent=2), encoding="utf-8")
    return dated


def load_latest_snapshot(output_dir: Path, report_id: str) -> Optional[Dict[str, Any]]:
    """Load most recent cached report payload if available."""
    latest = output_dir / f"report_{report_id}_latest.json"
    if not latest.exists():
        return None
    try:
        return json.loads(latest.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None

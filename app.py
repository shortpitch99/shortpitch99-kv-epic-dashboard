#!/usr/bin/env python3
"""KV milestone dashboard renderer for saved weekly reports."""

from __future__ import annotations

import json
import re
import base64
import html
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="KV Epic Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_DIR = Path(__file__).parent / "data"
WEEKLY_DIR = DATA_DIR / "weekly_reports"
CLOUD_WEEKLY_DIR = Path(__file__).parent / "cloud_reports"
HEADER_IMAGE_PATHS = [
    Path(__file__).parent / "assets" / "scrt2.png",
    Path("/users/rchowdhuri/Downloads/scrt2.png"),
    Path("/Users/rchowdhuri/Downloads/scrt2.png"),
]
REPORTS = {
    "SCRT2 milestones": "00OEE000002tild2AA",
    "VegamDB milestones": "00OEE000002tu8T2AQ",
}


def get_banner_image_src() -> str:
    local_path = next((p for p in HEADER_IMAGE_PATHS if p.exists()), None)
    if not local_path:
        return ""
    try:
        image_data = base64.b64encode(local_path.read_bytes()).decode("utf-8")
        return f"data:image/png;base64,{image_data}"
    except Exception:
        return ""


def inject_styles() -> None:
    css = """
        <style>
        .main > div {
            padding-top: 1.0rem;
        }
        .kv-banner {
            background: linear-gradient(135deg, #111827, #1f2937);
            color: #f9fafb;
            border-radius: 10px;
            padding: 18px 20px;
            margin: 0 0 18px 0;
            box-shadow: 0 6px 18px rgba(0,0,0,0.18);
            width: 100%;
            position: relative;
            overflow: hidden;
        }
        .kv-banner h1 {
            margin: 0;
            font-size: 2.1rem;
            font-weight: 800;
            text-align: center;
            position: relative;
            z-index: 2;
        }
        .kv-banner p {
            margin: 6px 0 0 0;
            color: #d1d5db;
            font-size: 0.95rem;
            text-align: center;
            position: relative;
            z-index: 2;
        }
        .kv-banner-bg {
            position: absolute;
            inset: 0;
            width: 100%;
            height: 100%;
            object-fit: cover;
            opacity: 0.55;
            z-index: 1;
        }
        </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def current_week_key(now: datetime) -> str:
    iso = now.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def list_weekly_reports() -> List[Path]:
    WEEKLY_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(WEEKLY_DIR.glob("weekly_report_*.json"), reverse=True)
    if CLOUD_WEEKLY_DIR.exists():
        files.extend(sorted(CLOUD_WEEKLY_DIR.glob("weekly_report_*.json"), reverse=True))
    # Deduplicate by filename, prefer local WEEKLY_DIR if both exist.
    dedup: Dict[str, Path] = {}
    for path in files:
        if path.name not in dedup:
            dedup[path.name] = path
    return sorted(dedup.values(), key=lambda p: p.name, reverse=True)


def load_report(path: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def load_latest_report() -> Optional[Dict[str, Any]]:
    for latest in [WEEKLY_DIR / "latest.json", CLOUD_WEEKLY_DIR / "latest.json"]:
        if latest.exists():
            loaded = load_report(latest)
            if loaded:
                return loaded
    return None


def render_header(snapshot: Dict[str, Any]) -> None:
    image_src = get_banner_image_src()
    if image_src:
        components.html(
            f"""
            <div style="position:relative;width:100%;height:120px;border-radius:10px;overflow:hidden;margin:0 0 12px 0;">
              <img src="{image_src}" alt="KV Banner"
                   style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;filter:brightness(0.72);" />
              <div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;
                          color:#ffffff;font-size:2rem;font-weight:800;letter-spacing:0.01em;text-shadow:0 2px 8px rgba(0,0,0,0.6);">
                KV Epic Dashboard
              </div>
            </div>
            """,
            height=130,
        )
    else:
        st.markdown(
            """
            <div style="background:linear-gradient(135deg,#111827,#1f2937);color:#fff;border-radius:10px;padding:14px 18px;margin-bottom:12px;text-align:center;font-size:1.8rem;font-weight:800;">
              KV Epic Dashboard
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_narrative(snapshot: Dict[str, Any]) -> None:
    # Intentionally suppress top-level weekly narrative section.
    return


def render_weekly_status(snapshot: Dict[str, Any]) -> None:
    ws = snapshot.get("weekly_status", {}) or {}
    headline = str(ws.get("headline", "")).strip() or "Executive Weekly Status"
    summary = str(ws.get("summary", "")).strip()
    if summary:
        goal_label = "<span style='color:#1e3a8a; font-weight:700;'>Goal:</span>"
        status_label = "<span style='color:#1e3a8a; font-weight:700;'>Status:</span>"
        progress_label = "<span style='color:#1e3a8a; font-weight:700;'>Progress:</span>"
        next_label = "<span style='color:#1e3a8a; font-weight:700;'>Next:</span>"
        summary = re.sub(r"(?im)^(\s*-\s*)?goal\s*:\s*", rf"- {goal_label} ", summary)
        summary = re.sub(r"(?im)^(\s*-\s*)?status\s*:\s*", rf"- {status_label} ", summary)
        summary = re.sub(r"(?im)^(\s*-\s*)?progress\s*:\s*", rf"- {progress_label} ", summary)
        summary = re.sub(r"(?im)^(\s*-\s*)?next\s*:\s*", rf"- {next_label} ", summary)
    st.markdown(f"### {headline}")
    if summary:
        st.markdown(summary, unsafe_allow_html=True)
    else:
        st.info("Weekly status is not available for this snapshot yet. Re-run `run_report.sh`.")


def parse_milestone_date(value: str) -> Optional[datetime]:
    text = str(value or "")
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
        return datetime(year, month, day)
    except ValueError:
        return None


def select_most_imminent_milestone(df: pd.DataFrame) -> Optional[str]:
    if "Milestone" not in df.columns:
        return None
    milestones = [m for m in df["Milestone"].dropna().astype(str).unique().tolist() if m.strip()]
    if not milestones:
        return None

    today = datetime.now().date()
    future: List[tuple[int, str]] = []
    past: List[tuple[int, str]] = []
    without_date: List[str] = []
    for milestone in milestones:
        parsed = parse_milestone_date(milestone)
        if not parsed:
            without_date.append(milestone)
            continue
        delta_days = (parsed.date() - today).days
        if delta_days >= 0:
            future.append((delta_days, milestone))
        else:
            past.append((abs(delta_days), milestone))

    if future:
        return sorted(future, key=lambda x: x[0])[0][1]
    if past:
        return sorted(past, key=lambda x: x[0])[0][1]
    return sorted(without_date)[0]


def select_imminent_and_previous_milestones(df: pd.DataFrame) -> List[str]:
    if "Milestone" not in df.columns:
        return []
    milestones = [m for m in df["Milestone"].dropna().astype(str).unique().tolist() if m.strip()]
    if not milestones:
        return []

    dated: List[tuple[datetime, str]] = []
    undated: List[str] = []
    for milestone in milestones:
        parsed = parse_milestone_date(milestone)
        if parsed:
            dated.append((parsed, milestone))
        else:
            undated.append(milestone)

    if not dated:
        return sorted(undated)[:2]

    dated.sort(key=lambda x: x[0])
    today = datetime.now()

    # Most imminent: nearest upcoming, else nearest recent past
    upcoming_idx = None
    for i, (d, _) in enumerate(dated):
        if d.date() >= today.date():
            upcoming_idx = i
            break
    if upcoming_idx is not None:
        imminent_idx = upcoming_idx
    else:
        imminent_idx = len(dated) - 1

    selected = [dated[imminent_idx][1]]
    if imminent_idx - 1 >= 0:
        selected.append(dated[imminent_idx - 1][1])
    elif imminent_idx + 1 < len(dated):
        selected.append(dated[imminent_idx + 1][1])

    if len(selected) < 2 and undated:
        for m in sorted(undated):
            if m not in selected:
                selected.append(m)
                if len(selected) == 2:
                    break
    return selected[:2]


def render_imminent_milestone(df: pd.DataFrame, tab_key: str) -> None:
    milestone_list = select_imminent_and_previous_milestones(df)
    if not milestone_list:
        st.warning("No milestone value found in this tab.")
        return

    for idx, milestone in enumerate(milestone_list):
        header = "Most Imminent Milestone" if idx == 0 else "Previous Milestone"
        st.markdown(
            f'<div style="font-size:1.5rem;font-weight:800;color:#1e3a8a;margin:10px 0 8px 0;">{header}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div style="font-size:1.1rem;font-weight:600;color:#0f766e;margin:0 0 10px 0;">{milestone}</div>',
            unsafe_allow_html=True,
        )

        subset = df[df["Milestone"].astype(str) == milestone].copy()
        render_milestone_epics_table(subset, f"{tab_key}_imminent_{idx}")

    render_all_milestones_from_df(df, tab_key)


def select_imminent_group(groups: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not groups:
        return None
    today = datetime.now().date()
    ranked: List[tuple[int, int, Dict[str, Any]]] = []
    for idx, group in enumerate(groups):
        milestone_date = group.get("milestone_date")
        if milestone_date:
            try:
                d = datetime.strptime(str(milestone_date), "%Y-%m-%d").date()
                delta = (d - today).days
                # Upcoming first (bucket 0), then most recent past (bucket 1)
                bucket = 0 if delta >= 0 else 1
                distance = abs(delta)
                ranked.append((bucket, distance, group))
                continue
            except ValueError:
                pass
        # No date: push after dated milestones
        ranked.append((2, idx, group))
    ranked.sort(key=lambda x: (x[0], x[1]))
    return ranked[0][2] if ranked else None


def select_imminent_and_previous_groups(groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not groups:
        return []
    dated: List[tuple[datetime, Dict[str, Any]]] = []
    undated: List[Dict[str, Any]] = []
    for g in groups:
        milestone_date = g.get("milestone_date")
        if milestone_date:
            try:
                d = datetime.strptime(str(milestone_date), "%Y-%m-%d")
                dated.append((d, g))
                continue
            except ValueError:
                pass
        undated.append(g)

    if not dated:
        return undated[:2]

    dated.sort(key=lambda x: x[0])
    today = datetime.now()
    upcoming_idx = None
    for i, (d, _) in enumerate(dated):
        if d.date() >= today.date():
            upcoming_idx = i
            break
    imminent_idx = upcoming_idx if upcoming_idx is not None else len(dated) - 1
    selected = [dated[imminent_idx][1]]
    if imminent_idx - 1 >= 0:
        selected.append(dated[imminent_idx - 1][1])
    elif imminent_idx + 1 < len(dated):
        selected.append(dated[imminent_idx + 1][1])
    return selected[:2]


def render_imminent_from_groups(groups: List[Dict[str, Any]], tab_key: str) -> None:
    selected_groups = select_imminent_and_previous_groups(groups)
    if not selected_groups:
        st.warning("No milestone groups available in metadata.")
        return

    for idx, group in enumerate(selected_groups):
        milestone = str(group.get("milestone", "")).strip() or "Unspecified"
        header = "Most Imminent Milestone" if idx == 0 else "Previous Milestone"
        st.markdown(
            f'<div style="font-size:1.5rem;font-weight:800;color:#1e3a8a;margin:10px 0 8px 0;">{header}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div style="font-size:1.1rem;font-weight:600;color:#0f766e;margin:0 0 10px 0;">{milestone}</div>',
            unsafe_allow_html=True,
        )
        epics = group.get("epics", []) or []
        subset = pd.DataFrame(epics)
        if subset.empty:
            st.caption("No epics found for this milestone group.")
            continue
        render_milestone_epics_table(subset, f"{tab_key}_imminent_{idx}")

    render_all_milestones_from_groups(groups, tab_key)


def render_status_colored_table(table: pd.DataFrame) -> None:
    color_map = {
        "on track": "#e8f5e9",
        "completed": "#e3f2fd",
        "blocked": "#ffebee",
        "watch": "#fffde7",
    }

    def status_color(status: str) -> str:
        s = str(status or "").strip().lower()
        for key, color in color_map.items():
            if key in s:
                return color
        return "#ffffff"

    cols = table.columns.tolist()
    header = "".join(
        f'<th style="text-align:left;padding:8px;border-bottom:1px solid #ddd;">{html.escape(str(c))}</th>'
        for c in cols
    )
    rows: List[str] = []
    for _, row in table.iterrows():
        bg = status_color(row.get("Health Status", ""))
        cells: List[str] = []
        for c in cols:
            value = row.get(c, "")
            text = "" if pd.isna(value) else str(value)
            if c in {"Epic Name", "Last Comment"}:
                cell = text
            else:
                cell = html.escape(text)
            cells.append(f'<td style="padding:8px;vertical-align:top;">{cell}</td>')
        rows.append(f'<tr style="background:{bg};">{"".join(cells)}</tr>')

    html_table = f"""
    <div style="overflow-x:auto;">
      <table style="width:100%;border-collapse:collapse;font-size:0.92rem;">
        <thead><tr style="background:#f8fafc;">{header}</tr></thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
    </div>
    """
    st.markdown(html_table, unsafe_allow_html=True)


def render_notes_section(payload: Dict[str, Any], tab_key: str) -> None:
    notes = payload.get("notes", {}) or {}
    risks = notes.get("risks", []) or []
    actions = notes.get("action_items", []) or []

    st.markdown("---")
    st.markdown(
        '<div style="font-size:1.4rem;font-weight:800;color:#1e3a8a;margin:8px 0 8px 0;">Risks and Action Items</div>',
        unsafe_allow_html=True,
    )

    if not risks and not actions:
        st.info("No risks or action items for this week.")
        return

    if risks:
        st.markdown(
            '<div style="font-size:1.05rem;font-weight:700;color:#0f766e;margin:6px 0;">Risks</div>',
            unsafe_allow_html=True,
        )
        rdf = pd.DataFrame(risks).rename(
            columns={
                "priority_or_severity": "Severity",
                "owner": "Owner",
                "due": "Due",
                "status": "Status",
                "summary": "Summary",
            }
        )
        st.dataframe(rdf, use_container_width=True, hide_index=True, key=f"risks_{tab_key}")
    else:
        st.caption("No risks recorded.")

    if actions:
        st.markdown(
            '<div style="font-size:1.05rem;font-weight:700;color:#0f766e;margin:10px 0 6px 0;">Action Items</div>',
            unsafe_allow_html=True,
        )
        adf = pd.DataFrame(actions).rename(
            columns={
                "priority_or_severity": "Priority",
                "owner": "Owner",
                "due": "Due",
                "status": "Status",
                "summary": "Summary",
            }
        )
        st.dataframe(adf, use_container_width=True, hide_index=True, key=f"actions_{tab_key}")
    else:
        st.caption("No action items recorded.")


def render_milestone_epics_table(subset: pd.DataFrame, tab_key: str) -> None:
    required_cols = ["Epic Name", "Status", "Epic Health Comment"]
    keep_cols = [c for c in required_cols if c in subset.columns]
    if len(keep_cols) < 3:
        st.warning("Required columns are missing for epic list display.")
        return

    status_options = sorted(
        [s for s in subset["Status"].dropna().unique().tolist() if str(s).strip() != ""]
    ) if "Status" in subset.columns else []
    selected_status = st.multiselect(
        "Filter Status",
        status_options,
        default=status_options,
        key=f"status_{tab_key}",
    ) if status_options else []
    if selected_status and "Status" in subset.columns:
        subset = subset[subset["Status"].isin(selected_status)]

    extra_cols = [c for c in ["Team", "Owner", "% Complete"] if c in subset.columns]
    table = subset[keep_cols + extra_cols].copy().rename(
        columns={
            "Status": "Health Status",
            "Epic Health Comment": "Last Comment",
            "% Complete": "% of Work Items Complete",
        }
    )
    if "GUS Epic" in subset.columns and "Epic Name" in table.columns:
        links = subset["GUS Epic"].fillna("").astype(str).tolist()
        names = table["Epic Name"].fillna("").astype(str).tolist()
        linked_names = []
        for name, link in zip(names, links):
            if link.strip():
                linked_names.append(f'<a href="{link.strip()}" target="_blank">{name}</a>')
            else:
                linked_names.append(name)
        table["Epic Name"] = linked_names
    if "Last Comment" in table.columns:
        table["Last Comment"] = (
            table["Last Comment"]
            .fillna("")
            .astype(str)
            .str.replace("\\\\r\\\\n", "<br>", regex=False)
            .str.replace("\\\\n", "<br>", regex=False)
            .str.replace("\r\n", "<br>", regex=False)
            .str.replace("\n", "<br>", regex=False)
        )
    render_status_colored_table(table)
    st.caption(f"Showing {len(subset)} epics for milestone")


def render_all_milestones_from_groups(groups: List[Dict[str, Any]], tab_key: str) -> None:
    st.markdown("---")
    st.markdown(
        '<div style="font-size:1.5rem;font-weight:800;color:#1e3a8a;margin:10px 0 8px 0;">Epics for All Milestones</div>',
        unsafe_allow_html=True,
    )
    for idx, group in enumerate(groups):
        milestone = str(group.get("milestone", "")).strip() or "Unspecified"
        subset = pd.DataFrame(group.get("epics", []) or [])
        if subset.empty:
            continue
        st.markdown(
            f'<div style="font-size:1.1rem;font-weight:600;color:#0f766e;margin:8px 0 8px 0;">{milestone}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div style="font-size:1.1rem;font-weight:600;color:#0f766e;margin:0 0 10px 0;">Epics for this milestone</div>',
            unsafe_allow_html=True,
        )
        render_milestone_epics_table(subset, f"{tab_key}_all_{idx}")


def render_all_milestones_from_df(df: pd.DataFrame, tab_key: str) -> None:
    if "Milestone" not in df.columns:
        return
    st.markdown("---")
    st.markdown(
        '<div style="font-size:1.5rem;font-weight:800;color:#1e3a8a;margin:10px 0 8px 0;">Epics for All Milestones</div>',
        unsafe_allow_html=True,
    )
    milestone_list = [m for m in df["Milestone"].dropna().astype(str).unique().tolist() if m.strip()]
    for idx, milestone in enumerate(milestone_list):
        subset = df[df["Milestone"].astype(str) == milestone].copy()
        if subset.empty:
            continue
        st.markdown(
            f'<div style="font-size:1.1rem;font-weight:600;color:#0f766e;margin:8px 0 8px 0;">{milestone}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div style="font-size:1.1rem;font-weight:600;color:#0f766e;margin:0 0 10px 0;">Epics for this milestone</div>',
            unsafe_allow_html=True,
        )
        render_milestone_epics_table(subset, f"{tab_key}_all_{idx}")


def main() -> None:
    inject_styles()
    st.sidebar.title("KV Weekly Reports")

    snapshot: Optional[Dict[str, Any]] = None

    history = list_weekly_reports()
    labels = [p.stem.replace("weekly_report_", "") for p in history]
    selected_path = None
    if labels:
        selected_label = st.sidebar.selectbox("Saved reports", labels, index=0)
        selected_path = history[labels.index(selected_label)]
    else:
        st.sidebar.info("No saved weekly reports yet.")

    if snapshot is None and selected_path is not None:
        snapshot = load_report(selected_path)
    if snapshot is None:
        snapshot = load_latest_report()

    if not snapshot:
        render_header({"week_key": current_week_key(datetime.now()), "generated_at": "not available"})
        st.warning("No saved data found yet. Run `./run_report.sh` to generate this week's report.")
        return

    render_header(snapshot)
    render_narrative(snapshot)

    tabs_data = snapshot.get("tabs", {})
    tab_names = ["SCRT2", "VegamDB", "Weekly Status"]
    tab_to_key = {"SCRT2": "SCRT2 milestones", "VegamDB": "VegamDB milestones"}
    tabs = st.tabs(tab_names)
    for tab, tab_name in zip(tabs, tab_names):
        with tab:
            if tab_name == "Weekly Status":
                render_weekly_status(snapshot)
                continue
            payload = tabs_data.get(tab_to_key[tab_name], {})
            metadata = payload.get("metadata", {}) or {}
            groups = metadata.get("grouped_by_milestone", []) or []
            df = pd.DataFrame(payload.get("rows", []))
            if df.empty:
                st.warning("No rows found for this report in selected snapshot.")
                continue
            tab_narrative = payload.get("narrative", "")
            if tab_narrative:
                st.markdown("#### Weekly Summary")
                st.write(tab_narrative)
            render_notes_section(payload, tab_key=tab_name.lower())
            if groups:
                render_imminent_from_groups(groups, tab_key=tab_name.lower())
            else:
                render_imminent_milestone(df, tab_key=tab_name.lower())


if __name__ == "__main__":
    main()

"""
Kiểm tra freshness từ manifest pipeline (SLA đơn giản theo giờ).

Sinh viên mở rộng: đọc watermark DB, so sánh với clock batch, v.v.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Tuple


def parse_iso(ts: str) -> datetime | None:
    if not ts:
        return None
    try:
        # Cho phép "2026-04-10T08:00:00" không có timezone
        if ts.endswith("Z"):
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def check_manifest_freshness(
    manifest_path: Path,
    *,
    sla_hours: float = 24.0,
    now: datetime | None = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    Trả về ("PASS" | "WARN" | "FAIL", detail dict).

    Đọc trường `latest_exported_at` hoặc max exported_at trong cleaned summary.
    """
    now = now or datetime.now(timezone.utc)
    if not manifest_path.is_file():
        return "FAIL", {"reason": "manifest_missing", "path": str(manifest_path)}

    data: Dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    ts_raw = data.get("latest_exported_at") or data.get("run_timestamp")
    dt = parse_iso(str(ts_raw)) if ts_raw else None
    if dt is None:
        return "WARN", {"reason": "no_timestamp_in_manifest", "manifest": data}

    age_hours = (now - dt).total_seconds() / 3600.0
    detail = {
        "latest_exported_at": ts_raw,
        "age_hours": round(age_hours, 3),
        "sla_hours": sla_hours,
    }
    if age_hours <= sla_hours:
        return "PASS", detail
    return "FAIL", {**detail, "reason": "freshness_sla_exceeded"}


def check_timestamp_freshness(
    timestamp: str,
    *,
    boundary: str,
    sla_hours: float = 24.0,
    now: datetime | None = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    Kiểm tra freshness cho một boundary cụ thể.

    - ingest: watermark của dữ liệu nguồn/export (`latest_exported_at`)
    - publish: thời điểm pipeline publish manifest/vector snapshot (`publish_timestamp`)
    """
    now = now or datetime.now(timezone.utc)
    dt = parse_iso(timestamp)
    if dt is None:
        return "WARN", {"boundary": boundary, "timestamp": timestamp, "reason": "invalid_or_missing_timestamp"}

    age_hours = (now - dt).total_seconds() / 3600.0
    detail = {
        "boundary": boundary,
        "timestamp": timestamp,
        "age_hours": round(age_hours, 3),
        "sla_hours": sla_hours,
    }
    if age_hours <= sla_hours:
        return "PASS", detail
    return "FAIL", {**detail, "reason": "freshness_sla_exceeded"}


def check_manifest_boundary_freshness(
    manifest_path: Path,
    *,
    sla_hours: float = 24.0,
    now: datetime | None = None,
) -> Dict[str, Tuple[str, Dict[str, Any]]]:
    """
    Đo freshness ở 2 boundary để có bằng chứng bonus:
    ingest dùng `ingest_watermark/latest_exported_at`, publish dùng `publish_timestamp/run_timestamp`.
    """
    now = now or datetime.now(timezone.utc)
    if not manifest_path.is_file():
        detail = {"reason": "manifest_missing", "path": str(manifest_path)}
        return {"ingest": ("FAIL", {**detail, "boundary": "ingest"}), "publish": ("FAIL", {**detail, "boundary": "publish"})}

    data: Dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    ingest_ts = str(data.get("ingest_watermark") or data.get("latest_exported_at") or "")
    publish_ts = str(data.get("publish_timestamp") or data.get("run_timestamp") or "")

    return {
        "ingest": check_timestamp_freshness(ingest_ts, boundary="ingest", sla_hours=sla_hours, now=now),
        "publish": check_timestamp_freshness(publish_ts, boundary="publish", sla_hours=sla_hours, now=now),
    }

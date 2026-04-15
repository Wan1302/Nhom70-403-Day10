"""
Expectation suite đơn giản (không bắt buộc Great Expectations).

Sinh viên có thể thay bằng GE / pydantic / custom — miễn là có halt có kiểm soát.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass
class ExpectationResult:
    name: str
    passed: bool
    severity: str  # "warn" | "halt"
    detail: str


def run_expectations(cleaned_rows: List[Dict[str, Any]]) -> Tuple[List[ExpectationResult], bool]:
    """
    Trả về (results, should_halt).

    should_halt = True nếu có bất kỳ expectation severity halt nào fail.
    """
    results: List[ExpectationResult] = []

    # E1: có ít nhất 1 dòng sau clean
    ok = len(cleaned_rows) >= 1
    results.append(
        ExpectationResult(
            "min_one_row",
            ok,
            "halt",
            f"cleaned_rows={len(cleaned_rows)}",
        )
    )

    # E2: không doc_id rỗng
    bad_doc = [r for r in cleaned_rows if not (r.get("doc_id") or "").strip()]
    ok2 = len(bad_doc) == 0
    results.append(
        ExpectationResult(
            "no_empty_doc_id",
            ok2,
            "halt",
            f"empty_doc_id_count={len(bad_doc)}",
        )
    )

    # E3: policy refund không được chứa cửa sổ sai 14 ngày (sau khi đã fix)
    bad_refund = [
        r
        for r in cleaned_rows
        if r.get("doc_id") == "policy_refund_v4"
        and "14 ngày làm việc" in (r.get("chunk_text") or "")
    ]
    ok3 = len(bad_refund) == 0
    results.append(
        ExpectationResult(
            "refund_no_stale_14d_window",
            ok3,
            "halt",
            f"violations={len(bad_refund)}",
        )
    )

    # E4: chunk_text đủ dài
    short = [r for r in cleaned_rows if len((r.get("chunk_text") or "")) < 8]
    ok4 = len(short) == 0
    results.append(
        ExpectationResult(
            "chunk_min_length_8",
            ok4,
            "warn",
            f"short_chunks={len(short)}",
        )
    )

    # E5: effective_date đúng định dạng ISO sau clean (phát hiện parser lỏng)
    iso_bad = [
        r
        for r in cleaned_rows
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", (r.get("effective_date") or "").strip())
    ]
    ok5 = len(iso_bad) == 0
    results.append(
        ExpectationResult(
            "effective_date_iso_yyyy_mm_dd",
            ok5,
            "halt",
            f"non_iso_rows={len(iso_bad)}",
        )
    )

    # E6: không còn marker phép năm cũ 10 ngày trên doc HR (conflict version sau clean)
    bad_hr_annual = [
        r
        for r in cleaned_rows
        if r.get("doc_id") == "hr_leave_policy"
        and "10 ngày phép năm" in (r.get("chunk_text") or "")
    ]
    ok6 = len(bad_hr_annual) == 0
    results.append(
        ExpectationResult(
            "hr_leave_no_stale_10d_annual",
            ok6,
            "halt",
            f"violations={len(bad_hr_annual)}",
        )
    )

    # E7: Defense-in-depth — xác nhận không có ghi chú nội bộ/migration nào lọt qua cleaning.
    # metric_impact: FAIL nếu R7 bị vô hiệu hoá hoặc bỏ qua (vd chạy pipeline không có rule R7);
    # hiện tại PASS sau sprint2 vì R7 đã quarantine row 3.
    _INTERNAL_MARKERS = ("(ghi chú:", "lỗi migration", "bản sync cũ")
    bad_internal = [
        r for r in cleaned_rows
        if any(m in (r.get("chunk_text") or "").lower() for m in _INTERNAL_MARKERS)
    ]
    ok7 = len(bad_internal) == 0
    results.append(
        ExpectationResult(
            "no_internal_note_in_cleaned",
            ok7,
            "halt",
            f"violations={len(bad_internal)}",
        )
    )

    # E8: Completeness — tất cả 4 doc_id bắt buộc phải còn ít nhất 1 chunk sau clean.
    # metric_impact: WARN nếu inject xoá hết chunk của 1 doc (vd bỏ toàn bộ sla_p1_2026);
    # hiện tại PASS sau sprint2 vì đủ 4 doc_id.
    _REQUIRED_DOCS = frozenset({"policy_refund_v4", "sla_p1_2026", "it_helpdesk_faq", "hr_leave_policy"})
    present_docs = {r.get("doc_id") for r in cleaned_rows}
    missing_docs = sorted(_REQUIRED_DOCS - present_docs)
    ok8 = len(missing_docs) == 0
    results.append(
        ExpectationResult(
            "all_required_docs_present",
            ok8,
            "warn",
            f"missing_docs={missing_docs}",
        )
    )

    # E9: Không có chunk nào chứa placeholder chưa điền — phòng inject dữ liệu rỗng.
    # metric_impact: WARN nếu inject row với text "TODO", "N/A", "PLACEHOLDER", "[TBD]";
    # hiện tại PASS vì không có chunk nào chứa các marker này.
    _PLACEHOLDER_MARKERS = ("todo", "placeholder", "n/a", "[tbd]")
    bad_placeholder = [
        r for r in cleaned_rows
        if any(m in (r.get("chunk_text") or "").lower() for m in _PLACEHOLDER_MARKERS)
    ]
    ok9 = len(bad_placeholder) == 0
    results.append(
        ExpectationResult(
            "no_placeholder_in_chunk",
            ok9,
            "warn",
            f"placeholder_chunks={len(bad_placeholder)}",
        )
    )

    halt = any(not r.passed and r.severity == "halt" for r in results)
    return results, halt

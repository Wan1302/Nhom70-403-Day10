# Data contract — Lab Day 10

> Bắt đầu từ `contracts/data_contract.yaml` — mở rộng và đồng bộ file này.

---

## 1. Nguồn dữ liệu (source map)

| Nguồn | Phương thức ingest | Failure mode chính | Metric / alert |
|-------|--------------------|--------------------|----------------|
| Raw policy export: `data/raw/policy_export_dirty.csv` | `etl_pipeline.py run --raw ...` đọc CSV | duplicate row, thiếu ngày, doc_id lạ, HR 2025 stale, internal migration note policy-v3 | `raw_records`, `cleaned_records`, `quarantine_records`, `reason` trong quarantine CSV |
| Inject export: `data/raw/policy_export_inject.csv` | Sprint 3 chạy với `--no-refund-fix --skip-validate` | refund stale `14 ngày làm việc` được publish để demo eval fail | `hits_forbidden=yes` ở `artifacts/eval/after_inject_bad.csv` |
| Canonical docs: `data/docs/*.txt` | Nguồn chuẩn để đối chiếu policy/FAQ | nội dung retrieval lệch canonical, ví dụ refund 14 ngày thay vì 7 ngày | `contains_expected`, `hits_forbidden`, `top1_doc_expected` |

## 2. Schema cleaned

| Cột | Kiểu | Bắt buộc | Ghi chú |
|-----|------|----------|---------|
| `chunk_id` | string | Có | ID dùng để upsert/prune Chroma |
| `doc_id` | string | Có | Phải thuộc `allowed_doc_ids` |
| `chunk_text` | string | Có | Không rỗng; expectation tối thiểu 8 ký tự, cleaning rule loại dưới 20 ký tự |
| `effective_date` | date | Có | Chuẩn ISO `YYYY-MM-DD` |
| `exported_at` | datetime | Có | Dùng cho freshness monitor |

## 3. Quy tắc quarantine vs drop

Record bị flag sẽ được ghi vào `artifacts/quarantine/quarantine_<run_id>.csv` kèm `reason`, thay vì bị drop âm thầm.

| Reason | Ý nghĩa |
|--------|---------|
| `unknown_doc_id` | `doc_id` không thuộc allowlist |
| `missing_effective_date` | Thiếu ngày hiệu lực |
| `invalid_effective_date_format` | Ngày không parse được |
| `stale_hr_policy_effective_date` | HR policy trước `2026-01-01` |
| `missing_chunk_text` | Text rỗng |
| `chunk_text_too_short` | Text quá ngắn để embed có chất lượng |
| `internal_migration_note_in_text` | Ghi chú/migration note nội bộ không được publish |
| `duplicate_chunk_text` | Trùng nội dung sau normalize |
| `missing_exported_at` | Thiếu timestamp nguồn |

Chỉ merge lại sau khi Data Owner của `Nhom70 Data Pipeline` xác nhận nguồn đã được sửa và pipeline đã rerun sạch.

## 4. Phiên bản & canonical

| Tài liệu | Source of truth | Version hợp lệ |
|----------|-----------------|----------------|
| Refund policy | `data/docs/policy_refund_v4.txt` | v4, refund window 7 ngày làm việc |
| HR leave policy | `data/docs/hr_leave_policy.txt` | 2026, nhân viên dưới 3 năm có 12 ngày phép năm |
| P1 SLA | `data/docs/sla_p1_2026.txt` | P1 first response 15 phút, resolution 4 giờ |
| IT Helpdesk FAQ | `data/docs/it_helpdesk_faq.txt` | Lockout sau 5 lần đăng nhập sai |

Freshness alert đi tới `nhom70-data-alerts` theo contract YAML.

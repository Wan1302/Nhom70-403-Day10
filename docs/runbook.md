# Runbook — Lab Day 10

## Symptom

Agent hoặc user nhận được câu trả lời lệch policy:

- Refund window trả lời **14 ngày làm việc** thay vì **7 ngày làm việc**.
- HR leave trả lời **10 ngày phép năm** thay vì **12 ngày phép năm** cho chính sách 2026.
- Eval retrieval có `hits_forbidden=yes` hoặc `top1_doc_expected=no`.
- Freshness check trả `FAIL` vì `latest_exported_at` cũ hơn SLA 24 giờ.

## Detection

| Metric | Nguồn kiểm tra | Dấu hiệu |
|--------|----------------|----------|
| `hits_forbidden` | `artifacts/eval/after_inject_bad.csv`, `artifacts/eval/after_fix_eval.csv` | `yes` nghĩa là top-k còn dính nội dung cũ hoặc bị cấm |
| `contains_expected` | `artifacts/eval/*.csv` | `no` nghĩa là retrieval chưa tìm được nội dung đúng |
| Expectation halt | `quality/expectations.py` hoặc output pipeline khi chạy | `refund_no_stale_14d_window FAIL` phải dừng pipeline nếu không demo inject |
| Freshness | `python etl_pipeline.py freshness --manifest ...` | `FAIL` khi `age_hours > 24` |
| Quarantine reason | `artifacts/quarantine/quarantine_<run_id>.csv` | Cho biết dòng bị loại vì duplicate, stale HR, doc_id lạ, internal note, thiếu ngày |

## Diagnosis

| Bước | Việc làm | Kết quả mong đợi |
|------|----------|------------------|
| 1 | Mở `artifacts/manifests/manifest_<run_id>.json` | Xác nhận `run_id`, `raw_records`, `cleaned_records`, `quarantine_records`, `no_refund_fix`, `skipped_validate` |
| 2 | Nếu `run_id=inject-bad`, kiểm tra manifest | `no_refund_fix=true`, `skipped_validate=true`; đây là run demo dữ liệu xấu |
| 3 | Mở `artifacts/quarantine/quarantine_sprint2.csv` | Có 5 dòng: duplicate, internal migration note, missing date, stale HR 2025, unknown doc_id |
| 4 | So sánh eval before/after | `q_refund_window` đổi từ `hits_forbidden=yes` ở inject sang `no` ở after fix |
| 5 | Chạy freshness command | Snapshot hiện có `latest_exported_at=2026-04-10T08:00:00`, nên FAIL theo SLA 24h là hợp lý |

## Mitigation

Nếu phát hiện stale refund trong top-k:

```bash
python etl_pipeline.py run --run-id after-restore
python eval_retrieval.py --out artifacts/eval/after_fix_eval.csv
```

Khi phục hồi, không dùng `--no-refund-fix` hoặc `--skip-validate`. Hai flag này chỉ dành cho Sprint 3, lúc nhóm cố tình đưa dữ liệu xấu vào để chứng minh eval có thể bắt lỗi.

Nếu freshness FAIL, cần lấy export mới từ hệ nguồn rồi chạy lại pipeline. Với snapshot lab ngày `2026-04-10`, FAIL không phải lỗi code; nó chỉ nói rằng data đã quá SLA.

## Prevention

- Giữ expectation `refund_no_stale_14d_window` và `hr_leave_no_stale_10d_annual` ở severity `halt`.
- Giữ rule quarantine `internal_migration_note_in_text` để bản sync cũ policy-v3 không vào Chroma.
- Duy trì source map và owner trong `contracts/data_contract.yaml`.
- Tích hợp freshness check vào scheduler và gửi cảnh báo tới `nhom70-data-alerts`.
- Khi thêm rule mới, cập nhật `reports/group_report.md` bảng `metric_impact` bằng artifact thật.

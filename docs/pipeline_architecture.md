# Kiến trúc pipeline — Lab Day 10

**Nhóm:** Nhóm 70-403
**Cập nhật:** 2026-04-15

## 1. Sơ đồ luồng

```text
data/raw/policy_export_dirty.csv
        |
        v
+------------------+
| Ingest CSV       |  raw_records -> manifest
| etl_pipeline.py  |
+--------+---------+
         |
         v
+------------------+       bad rows
| Clean / Transform|--------------------+
| cleaning_rules.py|                    v
+--------+---------+       artifacts/quarantine/quarantine_<run_id>.csv
         |
         | cleaned rows
         v
+------------------+
| Expectations     |  halt/warn results
| expectations.py  |
+--------+---------+
         |
         v
+------------------+       upsert by chunk_id, prune old ids
| Embed Chroma     |---------------------> chroma collection: day10_kb
+--------+---------+
         |
         v
+------------------+
| Manifest/Freshness|
| freshness_check.py|
+--------+---------+
         |
         v
artifacts/manifests/manifest_<run_id>.json
artifacts/eval/*.csv
```

Freshness được đo sau publish bằng `latest_exported_at` trong manifest. `run_id` cũng được giữ trong manifest, tên file cleaned/quarantine và metadata của vector trong Chroma.

## 2. Ranh giới trách nhiệm

| Thành phần | Input | Output | File / Module | Owner nhóm |
|------------|-------|--------|---------------|------------|
| Ingest | `data/raw/*.csv` | Raw rows, `raw_records` | `etl_pipeline.py::cmd_run` | Nhóm / người chạy pipeline |
| Transform | Raw rows | Cleaned CSV, quarantine CSV | `transform/cleaning_rules.py` | Cleaning & Quality Owner |
| Quality | Cleaned rows | Expectation results, halt flag | `quality/expectations.py` | Cleaning & Quality Owner |
| Embed | Cleaned CSV + `run_id` | Chroma `day10_kb` | `etl_pipeline.py::cmd_embed_internal` | Embed & Idempotency Owner |
| Monitor / Docs | Manifest + eval CSV | Freshness status, reports, runbook | `monitoring/freshness_check.py`, `docs/*.md` | Monitoring / Docs Owner |

## 3. Idempotency & rerun

Embed dùng `chunk_id` làm key upsert. Mỗi run lấy danh sách id đang có trong collection, tính `prev_ids - current_ids`, rồi prune id không còn trong cleaned snapshot. Nhờ vậy, run phục hồi `after-restore` không giữ lại vector stale từ `inject-bad`. Điểm cần lưu ý là `chunk_id` vẫn phụ thuộc vào `seq`; nếu CSV bị reorder thì id có thể đổi dù nội dung giống nhau.

## 4. Liên hệ Day 09

Collection `day10_kb` được tách khỏi Day 09 để nhóm kiểm chứng pipeline trước khi cho agent dùng. Khi cần tích hợp, Day 09 chỉ cần trỏ `CHROMA_COLLECTION` sang `day10_kb` sau khi pipeline chuẩn pass expectation và eval sạch.

## 5. Rủi ro đã biết

- Snapshot hiện có freshness FAIL vì export ngày `2026-04-10`.
- Artifact log chưa được commit; bằng chứng hiện dựa vào manifest/CSV.
- Chưa có alert tự động khi freshness FAIL.
- Chưa có validation framework như Great Expectations hoặc pydantic.

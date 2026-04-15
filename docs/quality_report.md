# Quality report — Lab Day 10

**run_id chính:** `sprint2`, `inject-bad`, `after-restore`
**Ngày:** 2026-04-15

---

## 1. Tóm tắt số liệu

| Chỉ số | `sprint2` clean | `inject-bad` | `after-restore` | Ghi chú |
|--------|-----------------|--------------|-----------------|---------|
| raw_records | 10 | 5 | 5 | `inject-bad` và `after-restore` dùng `data/raw/policy_export_inject.csv` |
| cleaned_records | 5 | 5 | 5 | Khớp manifest và cleaned CSV |
| quarantine_records | 5 | 0 | 0 | Inject file chỉ chứa 5 row hợp lệ về schema |
| no_refund_fix | false | true | false | Inject cố ý bỏ fix refund |
| skipped_validate | false | true | false | Inject cố ý bypass halt để embed dữ liệu xấu |
| Expectation halt? | Không | Có nếu không skip | Không | `cleaned_inject-bad.csv` fail `refund_no_stale_14d_window` với `violations=1` |

Khi so sánh Sprint 1 với Sprint 2 trên `policy_export_dirty.csv`, số liệu đổi khá rõ: `sprint1` có `cleaned_records=6`, `quarantine_records=4`, còn `sprint2` có `cleaned_records=5`, `quarantine_records=5`. Dòng bị loại thêm nằm trong `artifacts/quarantine/quarantine_sprint2.csv` với reason `internal_migration_note_in_text`.

---

## 2. Before / after retrieval

Artifact dùng:

- Before bad: `artifacts/eval/after_inject_bad.csv`
- After fix: `artifacts/eval/after_fix_eval.csv`

### Câu hỏi then chốt: refund window (`q_refund_window`)

| Scenario | top1_doc_id | top1_preview | contains_expected | hits_forbidden |
|----------|-------------|--------------|-------------------|----------------|
| `inject-bad` | `policy_refund_v4` | Yêu cầu hoàn tiền được chấp nhận trong vòng 14 ngày làm việc kể từ thời điểm xác nhận đơn hàng. | yes | yes |
| `after-restore` | `policy_refund_v4` | Yêu cầu được gửi trong vòng 7 ngày làm việc kể từ thời điểm xác nhận đơn hàng. | yes | no |

Kết luận: trước khi fix, top-k vẫn còn cửa sổ refund stale `14 ngày làm việc`. Sau khi chạy lại pipeline chuẩn, top-k quay về nội dung đúng `7 ngày làm việc` và `hits_forbidden=no`.

### Merit: versioning HR — `q_leave_version`

| Scenario | top1_doc_id | contains_expected | hits_forbidden | top1_doc_expected |
|----------|-------------|-------------------|----------------|-------------------|
| `inject-bad` | `hr_leave_policy` | yes | no | yes |
| `after-restore` | `hr_leave_policy` | yes | no | yes |

Kết quả HR ổn định vì bản HR 2025 có `10 ngày phép năm` đã bị quarantine bởi rule `stale_hr_policy_effective_date` trong dirty export.

---

## 3. Freshness & monitor

Lệnh kiểm tra:

```bash
python etl_pipeline.py freshness --manifest artifacts/manifests/manifest_sprint2.json
```

Kết quả tại thời điểm kiểm tra ngày 2026-04-15:

```text
FAIL {"latest_exported_at": "2026-04-10T08:00:00", "age_hours": 118.964, "sla_hours": 24.0, "reason": "freshness_sla_exceeded"}
```

Giải thích: dữ liệu mẫu cố ý dùng snapshot cũ hơn 24 giờ. Pipeline vẫn sạch về schema và expectation, nhưng nếu đây là production thì cần re-ingest trước khi cho agent dùng.

---

## 4. Corruption inject

Sprint 3 dùng:

```bash
python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate
```

Hai flag này thể hiện rõ trong `manifest_inject-bad.json`: `no_refund_fix=true`, `skipped_validate=true`. Khi đó chunk refund chứa `14 ngày làm việc` được embed để chứng minh eval bắt được lỗi. Run phục hồi là `after-restore`, không dùng hai flag trên; eval sau fix nằm ở `artifacts/eval/after_fix_eval.csv`.

---

## 5. Hạn chế & việc chưa làm

- Bộ eval hiện có 4 câu hỏi, đủ cho evidence chính nhưng chưa bao phủ toàn corpus.
- Freshness mới đo boundary publish từ manifest, chưa đo riêng ingest watermark.
- Chưa có Great Expectations hoặc pydantic validation thật; expectation hiện là custom Python.
- R8 `missing_exported_at` và R9 `chunk_text_too_short` đã có trong code, nhưng artifact hiện có chưa kèm run inject riêng cho hai rule này.

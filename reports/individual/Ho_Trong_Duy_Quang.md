# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Hồ Trọng Duy Quang  - 2A202600081
<br>
**Vai trò:** Quality & Embed Owner — expectations, pydantic validation, inject eval, freshness evidence  
**Ngày nộp:** 15/04/2026  
**Độ dài yêu cầu:** 400–650 từ

---

## 1. Tôi phụ trách phần nào? (80–120 từ)

**File / module:**

- `quality/expectations.py`: thêm và kiểm chứng các expectation mới: `no_internal_note_in_cleaned` ở mức `halt`, `all_required_docs_present` ở mức `warn`, và `no_placeholder_in_chunk` ở mức `warn`.
- `quality/schema_validation.py`: bổ sung pydantic model validate schema cleaned thật cho `chunk_id`, `doc_id`, `chunk_text`, `effective_date`, `exported_at`.
- `artifacts/eval/after_inject_bad.csv`, `artifacts/eval/after_fix_eval.csv`: tạo bằng chứng inject và sau khi khôi phục.

Tôi kết nối phần của mình với pipeline chính trong `etl_pipeline.py`: sau khi clean xong, `validate_cleaned_rows(cleaned)` kiểm schema bằng pydantic, rồi `run_expectations(cleaned)` quyết định có halt hay tiếp tục embed. Bằng chứng run thật gồm `sprint2-exp`, `inject-bad`, `after-restore` và run bonus `bonus-final` trong logs.

## 2. Một quyết định kỹ thuật (100–150 từ)

Quyết định quan trọng nhất của tôi là tách schema validation khỏi business expectations. Pydantic trong `quality/schema_validation.py` kiểm kiểu dữ liệu và contract của cleaned rows trước khi embed; còn `quality/expectations.py` kiểm lỗi nghiệp vụ như refund stale, HR version cũ hoặc internal note. Với `refund_no_stale_14d_window`, `effective_date_iso_yyyy_mm_dd`, `hr_leave_no_stale_10d_annual` và `no_internal_note_in_cleaned`, tôi giữ mức `halt` vì đây là lỗi làm sai tri thức trong vector store. Ngược lại, `all_required_docs_present` và `no_placeholder_in_chunk` là `warn` để pipeline vẫn quan sát được dữ liệu thử nghiệm mà không quá giòn. Cách tách này giúp nhóm claim bonus pydantic nhưng không xóa solution expectation cũ.

## 3. Một lỗi hoặc anomaly đã xử lý (100–150 từ)

Anomaly chính là stale refund window: dữ liệu inject cố ý đưa lại chunk “14 ngày làm việc” cho `policy_refund_v4`, trong khi chính sách đúng sau clean phải là “7 ngày làm việc”. Khi chạy `python etl_pipeline.py run --run-id inject-bad --raw data/raw/policy_export_inject.csv --no-refund-fix --skip-validate`, expectation `refund_no_stale_14d_window` báo `FAIL (halt) :: violations=1`. Tôi dùng `--skip-validate` chỉ để demo Sprint 3, cho phép embed dữ liệu xấu và đo hậu quả retrieval. Sau đó chạy lại không dùng `--no-refund-fix` với `run_id=after-restore`; cùng raw inject nhưng rule fix được bật, log chuyển thành `expectation[refund_no_stale_14d_window] OK (halt) :: violations=0`. Đây là bằng chứng lỗi được phát hiện bằng expectation và được sửa bằng cleaning rule.

## 4. Bằng chứng trước / sau (80–120 từ)

Run sạch `sprint2-exp` cho thấy pipeline chuẩn hoạt động: `raw_records=10`, `cleaned_records=5`, `quarantine_records=5`, tất cả expectation đều `OK`, `embed_upsert count=5 collection=day10_kb`, và `PIPELINE_OK`. Với inject xấu, `inject-bad` có `refund_no_stale_14d_window FAIL` và `after_inject_bad.csv` cho `q_refund_window` chứa “14 ngày làm việc”, `hits_forbidden=yes`. Sau restore, `after_fix_eval.csv` trả “7 ngày làm việc”, `hits_forbidden=no`; `q_leave_version` vẫn `top1_doc_expected=yes`. Run bonus `bonus-final` thêm bằng chứng `schema_validation=OK :: framework=pydantic rows=5 errors=0`, `ingest_freshness_check=FAIL` vì snapshot nguồn cũ, và `publish_freshness_check=PASS` vì manifest/vector snapshot vừa publish.

## 5. Cải tiến tiếp theo (40–80 từ)

Nếu có thêm 2 giờ, tôi sẽ đưa cutoff versioning và danh sách marker nguy hiểm ra `contracts/data_contract.yaml` hoặc biến môi trường thay vì hard-code. Tôi cũng sẽ thêm một inject riêng cho placeholder và thiếu `exported_at` để chứng minh rõ hơn tác động của `no_placeholder_in_chunk` và rule `missing_exported_at`.

# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Hồ Trọng Duy Quang  - 2A202600081
<br>
**Vai trò:** Cleaning & Quality Owner — expectations, inject eval, bằng chứng before/after  
**Ngày nộp:** 15/04/2026  
**Độ dài yêu cầu:** 400–650 từ

---

## 1. Tôi phụ trách phần nào? (80–120 từ)

**File / module:**

- `quality/expectations.py`: thêm và kiểm chứng các expectation mới: `no_internal_note_in_cleaned` ở mức `halt`, `all_required_docs_present` ở mức `warn`, và `no_placeholder_in_chunk` ở mức `warn`.
- `artifacts/eval/after_inject_bad.csv`, `artifacts/eval/after_fix_eval.csv`: tạo bằng chứng inject và sau khi khôi phục.

Tôi kết nối phần của mình với pipeline chính trong `etl_pipeline.py`: sau khi clean xong, `run_expectations(cleaned)` quyết định có halt hay tiếp tục embed. Bằng chứng code nằm ở comment `metric_impact` trong các rule/expectation mới và các log run thật: `sprint2-exp`, `inject-bad`, `after-restore`.

## 2. Một quyết định kỹ thuật (100–150 từ)

Quyết định quan trọng nhất của tôi là phân biệt rõ expectation nào phải `halt` và expectation nào chỉ nên `warn`. Với `refund_no_stale_14d_window`, `effective_date_iso_yyyy_mm_dd`, `hr_leave_no_stale_10d_annual` và `no_internal_note_in_cleaned`, tôi giữ hoặc đặt mức `halt` vì đây là lỗi làm sai tri thức trong vector store: agent có thể trả lời sai chính sách hoàn tiền, version nghỉ phép hoặc vô tình lộ ghi chú migration. Ngược lại, `all_required_docs_present` và `no_placeholder_in_chunk` được đặt `warn` để pipeline vẫn chạy khi thiếu slice tài liệu hoặc có marker placeholder trong dữ liệu thử nghiệm, nhưng log vẫn đủ mạnh để nhóm điều tra. Cách này giúp pipeline vừa bảo vệ các lỗi nghiêm trọng, vừa không quá giòn khi Sprint 3 cần inject dữ liệu xấu để quan sát before/after.

## 3. Một lỗi hoặc anomaly đã xử lý (100–150 từ)

Anomaly chính là stale refund window: dữ liệu inject cố ý đưa lại chunk “14 ngày làm việc” cho `policy_refund_v4`, trong khi chính sách đúng sau clean phải là “7 ngày làm việc”. Khi chạy `python etl_pipeline.py run --run-id inject-bad --raw data/raw/policy_export_inject.csv --no-refund-fix --skip-validate`, expectation `refund_no_stale_14d_window` báo `FAIL (halt) :: violations=1`. Tôi dùng `--skip-validate` chỉ để demo Sprint 3, cho phép embed dữ liệu xấu và đo hậu quả retrieval. Sau đó chạy lại không dùng `--no-refund-fix` với `run_id=after-restore`; cùng raw inject nhưng rule fix được bật, log chuyển thành `expectation[refund_no_stale_14d_window] OK (halt) :: violations=0`. Đây là bằng chứng lỗi được phát hiện bằng expectation và được sửa bằng cleaning rule.

## 4. Bằng chứng trước / sau (80–120 từ)

Run sạch `sprint2-exp` cho thấy pipeline chuẩn hoạt động: `raw_records=10`, `cleaned_records=5`, `quarantine_records=5`, tất cả expectation đều `OK`, `embed_upsert count=5 collection=day10_kb`, và `PIPELINE_OK`. Với inject xấu, log có `run_id=inject-bad`, `refund_no_stale_14d_window FAIL`, nhưng vẫn embed để tạo CSV eval. Dòng then chốt trong `after_inject_bad.csv` là `q_refund_window`, `top1_preview` chứa “14 ngày làm việc”, `contains_expected=yes`, `hits_forbidden=yes`. Sau khi khôi phục, `after_fix_eval.csv` chuyển thành `q_refund_window`, `top1_preview` chứa “7 ngày làm việc”, `contains_expected=yes`, `hits_forbidden=no`. Câu `q_leave_version` vẫn ổn định ở cả hai file: `top1_doc_expected=yes`.

## 5. Cải tiến tiếp theo (40–80 từ)

Nếu có thêm 2 giờ, tôi sẽ đưa cutoff versioning và danh sách marker nguy hiểm ra `contracts/data_contract.yaml` hoặc biến môi trường thay vì hard-code trong `quality/expectations.py` và `transform/cleaning_rules.py`. Sau đó tôi sẽ thêm một inject nhỏ cho placeholder chưa điền để chứng minh `no_placeholder_in_chunk` có tác động đo được, tránh bị xem là expectation trivial.

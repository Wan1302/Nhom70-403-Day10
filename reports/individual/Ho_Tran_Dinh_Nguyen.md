# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Hồ Trần Đình Nguyên
**Vai trò:** Cleaning & Quality Owner
**Ngày nộp:** 2026-04-15

---

## 1. Tôi phụ trách phần nào?

**File / module:**

- `transform/cleaning_rules.py` — thêm 3 rule cleaning mới: R7 (`internal_migration_note_in_text`), R8 (`missing_exported_at`), R9 (`chunk_text_too_short`)
- `quality/expectations.py` — thêm 3 expectation mới: E7 (`no_internal_note_in_cleaned`), E8 (`all_required_docs_present`), E9 (`no_placeholder_in_chunk`)

**Kết nối với thành viên khác:**

Tôi nhận CSV raw từ Ingestion Owner và trả về `cleaned_sprint2.csv` + `quarantine_sprint2.csv` cho Embed Owner xử lý tiếp. Các rule tôi viết trực tiếp ảnh hưởng đến số lượng chunk được embed vào Chroma — nếu rule sai thì eval của Embed Owner cũng sai theo.

**Bằng chứng:**

Commit `sprint1-2: add cleaning rules R7/R8/R9` trên branch `feature/nguyen`, merge vào main qua PR #1.

---

## 2. Một quyết định kỹ thuật

Quyết định quan trọng nhất tôi thực hiện là chọn **severity `halt`** cho expectation E7 (`no_internal_note_in_cleaned`) thay vì `warn`.

Lý do: E7 là lớp defense-in-depth cho R7 — nếu R7 bị vô hiệu hoá hoặc bị bypass (ví dụ ai đó comment out rule trong quá trình debug), E7 sẽ là tuyến phòng thủ cuối cùng trước khi chunk nhiễm thông tin nội bộ được embed vào vector store. Nếu chỉ là `warn`, pipeline vẫn tiếp tục embed chunk có ghi chú migration như `"(ghi chú: bản sync cũ policy-v3 — lỗi migration)"` — khi agent truy vấn sẽ nhận được context không đáng tin cậy.

Ngược lại, E8 (`all_required_docs_present`) và E9 (`no_placeholder_in_chunk`) tôi chọn `warn` vì đây là cảnh báo completeness — pipeline vẫn nên tiếp tục chạy để embed những gì còn lại, thay vì dừng hẳn chỉ vì thiếu một doc.

---

## 3. Một lỗi hoặc anomaly đã xử lý

**Triệu chứng:** Sau khi thêm R7, tôi chạy inject scenario (`--no-refund-fix --skip-validate`) với file `policy_export_dirty.csv` và eval kết quả. Kỳ vọng `q_refund_window` phải có `hits_forbidden=yes` (chunk "14 ngày" được embed), nhưng thực tế cả 2 file `after_inject_bad.csv` và `after_fix_eval.csv` đều cho kết quả **giống hệt nhau** — `hits_forbidden=no`.

**Phát hiện:** Sau khi kiểm tra `quarantine_sprint2.csv`, tôi nhận ra R7 đang quarantine row 3 (`"14 ngày làm việc... (ghi chú: bản sync cũ policy-v3 — lỗi migration)"`) **trước khi** flag `--no-refund-fix` có cơ hội để chunk đó lọt vào cleaned. R7 quá tốt — nó bắt cả chunk stale lẫn chunk inject.

**Fix:** Tôi tạo file `data/raw/policy_export_inject.csv` riêng với chunk "14 ngày làm việc" **không có** migration note, để inject scenario mới thực sự chứng minh được sự khác biệt trước/sau. Kết quả: `run_id=inject-bad` → `hits_forbidden=yes`; `run_id=after-restore` → `hits_forbidden=no`.

---

## 4. Bằng chứng trước / sau

Hai dòng từ file eval, câu hỏi `q_refund_window`:

**Trước (run_id: `inject-bad` — pipeline không fix refund):**
```
q_refund_window, ..., top1_preview="...14 ngày làm việc...", contains_expected=yes, hits_forbidden=yes
```

**Sau (run_id: `after-restore` — pipeline chuẩn):**
```
q_refund_window, ..., top1_preview="...7 ngày làm việc...", contains_expected=yes, hits_forbidden=no
```

Ngoài ra câu `q_leave_version` ở cả 2 run đều đạt: `contains_expected=yes`, `hits_forbidden=no`, `top1_doc_expected=yes` — chứng minh HR policy cũ (10 ngày) đã bị quarantine đúng bởi R3 baseline.

---

## 5. Cải tiến tiếp theo

Nếu có thêm 2 giờ, tôi sẽ đọc giá trị `hr_leave_min_effective_date` từ `contracts/data_contract.yaml` thay vì hard-code `"2026-01-01"` trong `cleaning_rules.py`. Hiện tại nếu chính sách HR thay đổi cutoff date, nhóm phải sửa thẳng vào code — rất dễ bỏ sót. Đọc từ contract giúp rule versioning linh hoạt hơn và đạt tiêu chí Distinction (d) của rubric mà không cần thay đổi logic cleaning.

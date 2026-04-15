# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Hồ Trần Đình Nguyên
**Vai trò:** Cleaning Owner
**Ngày nộp:** 2026-04-15

---

## 1. Tôi phụ trách phần nào?

**File / module:**

- `transform/cleaning_rules.py` — thêm 3 rule cleaning mới: R7 (`internal_migration_note_in_text`), R8 (`missing_exported_at`), R9 (`chunk_text_too_short`)

**Kết nối với thành viên khác:**

Tôi nhận CSV raw (`data/raw/policy_export_dirty.csv`) từ pipeline, viết thêm rule cleaning và trả về `cleaned_sprint2.csv` + `quarantine_sprint2.csv`. Kết quả cleaning trực tiếp ảnh hưởng đến phần Embed của Hồ Trọng Duy Quang — nếu rule sai thì chunk bẩn lọt vào Chroma và eval sẽ fail. Ngoài ra tôi phát hiện anomaly trong inject scenario và đề xuất tạo `policy_export_inject.csv` để nhóm chứng minh before/after đúng cách.

**Bằng chứng:**

Commit `sprint1-2: add cleaning rules R7/R8/R9` trên branch `feature/nguyen`, merge vào main qua PR #1.

---

## 2. Một quyết định kỹ thuật

Khi thiết kế R7 (`internal_migration_note_in_text`), tôi phải chọn giữa **quarantine** và **fix** chunk có ghi chú nội bộ.

Tôi quyết định **quarantine hoàn toàn** thay vì fix (strip ghi chú) vì: chunk có migration note như `"(ghi chú: bản sync cũ policy-v3 — lỗi migration)"` cho thấy dữ liệu nguồn chưa được xác nhận là chính thức. Nếu chỉ strip ghi chú rồi embed phần còn lại, nội dung vẫn có thể sai (chunk đó đang ghi "14 ngày" và ghi chú giải thích đó là version cũ). Quarantine an toàn hơn và tạo bằng chứng rõ ràng trong `quarantine_sprint2.csv` để audit sau.

Kết quả: `run_id=sprint1` → `quarantine_records=4`; `run_id=sprint2` → `quarantine_records=5` (row 3 bị R7 bắt).

---

## 3. Một lỗi hoặc anomaly đã xử lý

**Triệu chứng:** Sau khi chạy inject scenario (`run_id=inject-bad`, flag `--no-refund-fix --skip-validate`) và eval, tôi thấy file `after_inject_bad.csv` và `after_fix_eval.csv` **giống hệt nhau** — `q_refund_window` đều có `hits_forbidden=no`, không có sự khác biệt trước/sau.

**Phát hiện:** Kiểm tra `quarantine_inject-bad.csv` thì thấy row 3 (`"14 ngày làm việc... (ghi chú: bản sync cũ)"`) vẫn bị quarantine bởi R7 ngay cả khi dùng `--no-refund-fix`. Nguyên nhân: R7 chạy **trước** bước fix refund trong `clean_rows()`, nên chunk "14 ngày" bị quarantine trước khi flag `--no-refund-fix` có cơ hội để nó lọt vào cleaned.

**Fix:** Tôi đề xuất tạo file `data/raw/policy_export_inject.csv` riêng — có chunk "14 ngày làm việc" **không chứa** migration note, để R7 không bắt được. Kết quả: `run_id=inject-bad` → `hits_forbidden=yes`; `run_id=after-restore` → `hits_forbidden=no`.

---

## 4. Bằng chứng trước / sau

Hai dòng từ `artifacts/eval/`, câu hỏi `q_refund_window`:

**Trước — `run_id: inject-bad` (pipeline không fix refund, chunk "14 ngày" vào vector store):**
```
q_refund_window, contains_expected=yes, hits_forbidden=yes, top1_preview="...14 ngày làm việc..."
```

**Sau — `run_id: after-restore` (pipeline chuẩn, chunk "7 ngày" sau fix):**
```
q_refund_window, contains_expected=yes, hits_forbidden=no, top1_preview="...7 ngày làm việc..."
```

Câu `q_leave_version` cả 2 run đều đạt: `contains_expected=yes`, `hits_forbidden=no`, `top1_doc_expected=yes` — HR policy cũ (10 ngày) đã bị quarantine đúng bởi R3 baseline.

---

## 5. Cải tiến tiếp theo

Nếu có thêm 2 giờ, tôi sẽ đọc giá trị `hr_leave_min_effective_date` từ `contracts/data_contract.yaml` thay vì hard-code `"2026-01-01"` trong `cleaning_rules.py`. Hiện tại nếu cutoff date thay đổi thì phải sửa thẳng vào code — rất dễ bỏ sót và không audit được. Đọc từ contract giúp rule versioning linh hoạt, không phụ thuộc vào ngày cố định trong code.

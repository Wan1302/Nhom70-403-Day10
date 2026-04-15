# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Ho Dac Toan
**Vai trò:** Monitoring / Docs Owner
**Ngày nộp:** 2026-04-15

## 1. Tôi phụ trách phần nào?

Tôi phụ trách phần Monitoring / Docs: kiểm freshness, viết runbook, data contract, pipeline architecture, quality report, group report và báo cáo cá nhân. Các file tôi trực tiếp hoàn thiện là `docs/runbook.md`, `docs/quality_report.md`, `docs/pipeline_architecture.md`, `docs/data_contract.md`, `contracts/data_contract.yaml`, `reports/group_report.md` và `reports/individual/Ho_Dac_Toan.md`. Phần của tôi không phải viết embed hay toàn bộ cleaning rule, mà là gom bằng chứng thật từ repo để báo cáo không bị nói suông. Các artifact tôi đối chiếu gồm `manifest_sprint2.json`, `manifest_inject-bad.json`, `manifest_after-restore.json`, `after_inject_bad.csv`, `after_fix_eval.csv` và `quarantine_sprint2.csv`.

## 2. Một quyết định kỹ thuật

Tôi chọn ghi freshness theo mốc publish trong manifest, vì đó là nơi dễ kiểm tra lại nhất khi chấm. Manifest `sprint2` có `latest_exported_at=2026-04-10T08:00:00`; khi chạy `python etl_pipeline.py freshness --manifest artifacts/manifests/manifest_sprint2.json`, kết quả là `FAIL` vì dữ liệu đã cũ khoảng 118 giờ, vượt SLA 24 giờ. Với bộ dữ liệu lab, FAIL này là hợp lý, không phải lỗi pipeline. Tôi cũng điền rõ owner trong `contracts/data_contract.yaml`: `owner_team=Nhom70 Data Pipeline`, `alert_channel=nhom70-data-alerts`, để nếu freshness fail trong môi trường thật thì biết ai phải nhận cảnh báo.

## 3. Một lỗi hoặc anomaly đã xử lý

Anomaly quan trọng nhất là run `inject-bad`. Run này cố ý dùng `--no-refund-fix` và `--skip-validate`, nên chunk refund chứa `14 ngày làm việc` lọt vào Chroma. Manifest `manifest_inject-bad.json` xác nhận `no_refund_fix=true`, `skipped_validate=true`, `raw_records=5`, `cleaned_records=5`, `quarantine_records=0`. Trong `after_inject_bad.csv`, dòng `q_refund_window` vẫn có `contains_expected=yes` nhưng `hits_forbidden=yes`; nghĩa là retrieval có tìm thấy tài liệu đúng, nhưng top-k vẫn lẫn context cũ. Tôi đưa case này vào runbook để khi gặp lỗi thì kiểm manifest, so sánh eval, rồi chạy lại pipeline chuẩn bằng run `after-restore`.

## 4. Bằng chứng trước / sau

Trước khi sửa là `run_id=inject-bad`, file `artifacts/eval/after_inject_bad.csv`: `q_refund_window` có `top1_doc_id=policy_refund_v4`, preview chứa `14 ngày làm việc`, `contains_expected=yes`, `hits_forbidden=yes`. Sau khi chạy lại là `run_id=after-restore`, eval nằm ở `artifacts/eval/after_fix_eval.csv`: cùng câu hỏi trả preview `7 ngày làm việc`, `contains_expected=yes`, `hits_forbidden=no`. Ở phần cleaning, `sprint1` có `cleaned_records=6`, `quarantine_records=4`; sang `sprint2` còn `cleaned_records=5`, `quarantine_records=5`, thêm reason `internal_migration_note_in_text`. Đây là bằng chứng rule internal note có tác động thật.

## 5. Cải tiến tiếp theo

Nếu có thêm 2 giờ, tôi sẽ tạo riêng một run inject cho R8/R9 để có artifact chứng minh `missing_exported_at` và `chunk_text_too_short`. Sau đó tôi sẽ nối `freshness_check` vào scheduler để gửi alert thật tới `nhom70-data-alerts`, thay vì chỉ ghi cảnh báo trong tài liệu.

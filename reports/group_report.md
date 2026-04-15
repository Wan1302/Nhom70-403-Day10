# Báo Cáo Nhóm — Lab Day 10: Data Pipeline & Data Observability

**Tên nhóm:** Nhóm 70-403
**Ngày nộp:** 2026-04-15
**Repo:** `Nhom70-403-Day10`

| Tên | Vai trò (Day 10) | Email |
|-----|------------------|-------|
| Hồ Đắc Toàn | Monitoring / Docs Owner; tổng hợp source map, runbook, report, freshness evidence | ___ |
| Hồ Trần Đình Nguyên | Cleaning & Quality Owner | ___ |
| Hồ Trọng Duy Quang | Embed & Idempotency Owner | ___ |

## 1. Pipeline tổng quan

Nguồn raw chính của nhóm là `data/raw/policy_export_dirty.csv`, một file export mô phỏng từ hệ CS/IT với 10 dòng. File này cố tình có nhiều lỗi hay gặp trong thực tế: duplicate, thiếu ngày, `doc_id` lạ, ngày theo format `DD/MM/YYYY`, bản HR 2025 còn `10 ngày phép năm`, và một chunk refund cũ ghi `14 ngày làm việc`. Pipeline xử lý theo luồng: ingest CSV → clean/quarantine → validate expectations → embed vào Chroma collection `day10_kb` → ghi manifest và kiểm freshness. `run_id` được lưu trong manifest và tên artifact; ví dụ `manifest_sprint2.json` ghi `raw_records=10`, `cleaned_records=5`, `quarantine_records=5`.

**Lệnh chạy chuẩn (một luồng đầy đủ):**

```bash
python etl_pipeline.py run --run-id sprint2
python eval_retrieval.py --out artifacts/eval/after_fix_eval.csv
```

## 2. Cleaning & expectation

### 2a. Bảng metric_impact

| Rule / Expectation mới | Trước | Sau / khi inject | Chứng cứ |
|------------------------|-------|------------------|----------|
| R7 `internal_migration_note_in_text` | `sprint1`: `cleaned_records=6`, `quarantine_records=4` | `sprint2`: `cleaned_records=5`, `quarantine_records=5` | `artifacts/manifests/manifest_sprint1.json`, `artifacts/manifests/manifest_sprint2.json`, `artifacts/quarantine/quarantine_sprint2.csv` |
| R8 `missing_exported_at` | `r8r9`: `cleaned_records=2`, `quarantine_records=2` — row sla_p1_2026 thiếu `exported_at` bị bắt | `r8r9`: quarantine tăng 1, reason=`missing_exported_at` | `artifacts/quarantine/quarantine_r8r9.csv`, `artifacts/manifests/manifest_r8r9.json` |
| R9 `chunk_text_too_short` | `r8r9`: `cleaned_records=2`, `quarantine_records=2` — row it_helpdesk_faq với chunk "OK." (3 ký tự) bị bắt | `r8r9`: quarantine tăng 1, reason=`chunk_text_too_short`, `chunk_length=3` | `artifacts/quarantine/quarantine_r8r9.csv`, `artifacts/manifests/manifest_r8r9.json` |
| E7 `no_internal_note_in_cleaned` | Nếu R7 không có, chunk policy-v3 migration note có thể lọt vào cleaned | `sprint2`: PASS, `violations=0` | `quality/expectations.py`, `artifacts/cleaned/cleaned_sprint2.csv` |
| E8 `all_required_docs_present` | `sprint2`: PASS, `missing_docs=[]` | `r8r9`: FAIL (warn), `missing_docs=['it_helpdesk_faq', 'sla_p1_2026']` — R8/R9 quarantine 2 row khiến 2 doc biến khỏi cleaned, E8 cảnh báo đúng | `artifacts/logs/run_r8r9.log`, `quality/expectations.py` |
| E9 `no_placeholder_in_chunk` | Nếu inject `TODO`/`PLACEHOLDER` sẽ WARN | `sprint2`: PASS, `placeholder_chunks=0` | `quality/expectations.py` |

Các rule nền quan trọng gồm allowlist `doc_id`, chuẩn hóa `effective_date`, quarantine HR cũ trước `2026-01-01`, loại text rỗng hoặc thiếu ngày, dedupe nội dung, và sửa refund `14 ngày làm việc` thành `7 ngày làm việc`. Expectation hiện có 9 check, trong đó E7-E9 là phần mở rộng để bắt internal note, thiếu doc bắt buộc và placeholder. Run `inject-bad` sẽ fail halt `refund_no_stale_14d_window` nếu không cố tình dùng `--skip-validate`.

## 3. Before / after ảnh hưởng retrieval

Kịch bản inject dùng `data/raw/policy_export_inject.csv` và lệnh:

```bash
python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate
```

Manifest `inject-bad` xác nhận `raw_records=5`, `cleaned_records=5`, `quarantine_records=0`, `no_refund_fix=true`, `skipped_validate=true`. Vì run này bỏ rule fix refund và bỏ qua validate halt, chunk `14 ngày làm việc` được publish vào Chroma. Đây là tình huống xấu có chủ đích để chứng minh eval bắt được stale context.

| Câu hỏi | File eval | contains_expected | hits_forbidden | top1_doc_expected |
|---------|-----------|-------------------|----------------|-------------------|
| `q_refund_window` | `after_inject_bad.csv` | yes | yes | — |
| `q_refund_window` | `after_fix_eval.csv` | yes | no | — |
| `q_leave_version` | `after_inject_bad.csv` | yes | no | yes |
| `q_leave_version` | `after_fix_eval.csv` | yes | no | yes |

Kết luận: inject làm retrieval xấu đi ở câu refund vì `hits_forbidden=yes`. Run phục hồi `after-restore` đưa refund về `7 ngày làm việc`, và eval sau fix sạch lại với `hits_forbidden=no`. Câu HR vẫn ổn qua hai scenario vì bản HR 2025 đã bị quarantine từ dirty export.

## 4. Freshness & monitoring

Nhóm chọn SLA freshness là 24 giờ, cấu hình trong `.env.example` bằng `FRESHNESS_SLA_HOURS=24`. Lệnh `python etl_pipeline.py freshness --manifest artifacts/manifests/manifest_sprint2.json` trả `FAIL` vì `latest_exported_at=2026-04-10T08:00:00`, tức dữ liệu đã cũ khoảng 118 giờ tại ngày nộp. Đây là kết quả đúng với snapshot lab: dữ liệu có thể sạch về nội dung nhưng vẫn stale theo thời gian, nên nếu lên production thì phải re-ingest hoặc gửi cảnh báo tới `nhom70-data-alerts`.

Nhóm bổ sung đo 2 boundary trong run `bonus-final`: `ingest_freshness_check=FAIL` trên watermark nguồn `2026-04-10T08:00:00`, và `publish_freshness_check=PASS` trên `publish_timestamp` của manifest mới. Log nằm ở `artifacts/logs/run_bonus-final.log`, manifest nằm ở `artifacts/manifests/manifest_bonus-final.json`.

## 4b. Bonus validation

Nhóm bổ sung pydantic validation thật trong `quality/schema_validation.py` và gọi từ `etl_pipeline.py` sau bước clean, trước expectation/embed. Run `bonus-final` có log `schema_validation=OK :: framework=pydantic rows=5 errors=0`, nghĩa là 5 dòng cleaned pass schema `chunk_id`, `doc_id`, `chunk_text`, `effective_date`, `exported_at` và allowlist `doc_id`. Custom expectations cũ vẫn được giữ nguyên để kiểm rule nghiệp vụ.

## 5. Liên hệ Day 09

Pipeline Day 10 dùng collection riêng `day10_kb`, tách khỏi collection Day 09 để dữ liệu raw bẩn không ảnh hưởng trực tiếp tới multi-agent. Khi pipeline chuẩn exit 0, expectation pass và eval sạch, Day 09 có thể đổi env `CHROMA_COLLECTION=day10_kb` để dùng corpus đã được clean.

## 6. Peer Review — Phần E (slide Day 10)

- Artifact log đã có cho các run chính; khi nộp cần bảo đảm `artifacts/logs/run_bonus-final.log` và manifest tương ứng được commit.
- R8/R9 có code nhưng chưa có artifact inject riêng để chứng minh delta số liệu.
- Freshness đã có log 2 boundary ở `bonus-final`, nhưng chưa có alert tự động.
- Chưa tích hợp Great Expectations; validation bonus hiện dùng pydantic model thật.

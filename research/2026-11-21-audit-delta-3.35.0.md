# Audit delta ngày 21/11/2026 (cổng ký 3.35.0)

Mốc rà là `main` tại `29ddf2d85a1c`; phần sửa gộp vào `main` ở `51d4e6cd` (#710, #711, #712). Diff tích luỹ từ lần quét trước `4439d48`: 123 tệp, 10 581 dòng thêm. Năm reviewer-alt (Opus 5.5, effort max) chỉ đọc, mỗi lô một lượt; không lô nào kết luận sạch hoàn toàn vì hết trần lượt, nên cột "Chưa rà" ghi rõ. [Sổ audit](../docs/ops/AUDIT-STATUS.md).

## Lô và kết quả

| Lô | Phạm vi | 🔴 | 🟠 | 🟢 | Chưa rà |
|---|---|---|---|---|---|
| A | `guard.py` và hook, skill/agent, `test_hooks`, oracle guard, fixture | 0 | 0 | 5 | `test_guard_release_oracle.py` chi tiết, `guard.json`, chế độ strict, bench |
| B | `xt.py` làn merge/derived/steward, `xt_derived.py`, test merge | 0 | 1 | 1 | ~600 dòng `xt.py` ngoài làn merge (factory, stage, deploy preview, perf) |
| C | `xt_distribution/acceptance/deploy/scale/field`, test release | 0 | 3 | 1 | 8 tệp test mới chỉ chạy, chưa đọc; `test_perf` |
| D | workflow, `install.py`, mẫu dự án đích, `doctor`/`admin-plan` | 0 | 2 | 2 | `test_install*.py` chi tiết, `routine-check`, `field-export` |
| E | tài liệu khung, ADR 0081–0087, CHANGELOG, mẫu | 0 | 3 | 6 | ADR-0081…0085 so với mã, `docs/ops/FACTORY-PILOT-1*`, `packs/**` |

## Phát hiện đã sửa trước khi ký

- **B-F1 (🟠 có từ trước):** PR fork thường ở L2/L3 với CI xanh ra `merge`; sửa ở #710: `merge-check`/`pr next` coi PR fork, fork đã xoá hoặc tác giả không quyền ghi là `human`; làn `derived` giữ `wait`.
- **C/D (🟠):** `upgrade open-pr` không chạy được ở dự án thật (hook `pre-commit` đỏ, thiếu `BLUEPRINT.md`), token steward lọt vào hook `push`, bản thu hồi giữ PR mở, job lịch luôn bị bỏ qua, `xt-field.yml` mở PR bằng `GITHUB_TOKEN` (không CI); sửa ở #711. Review #711 thêm: điều kiện `if` phải loại tag trùng tên nhánh mặc định, và `pr-steward.yml` (có từ trước) phải luôn checkout nhánh mặc định; đã sửa cùng PR.
- **E (🟠):** `--with-github` thêm bốn tệp vào dự án đích mà tài liệu/CHANGELOG không nói; `WF-REVIEW-007` (MUST) lệch cấu hình mặc định (D-533: sửa câu cho khớp ADR-0079, khôi phục đường miễn); sửa ở #710, #712. Sáu 🟢 tài liệu (`updated`, ADR-0077/0087, mẫu GO-NO-GO, WF-DOC-021) sửa ở #712.

## Nợ ghi sổ (không chặn bản)

- 🟠 chấp nhận tới 2027-01-21 (D-532, cùng họ D-332): AUD-HAR-452 (`gh` sau trình bọc chưa mô hình), AUD-HAR-453 (`"$@"` qua `bash -s`), AUD-HAR-454 (guard chỉ `ask` với PR derived/fork khi agent làm trái `pr next`), AUD-CI-036 (fork khung đổi tên repo lệch tên archive; an toàn).
- 🟢 mở: AUD-HAR-455/456, AUD-CI-037, AUD-DOC-307, AUD-XFEAT-050, AUD-TEST-135.

## Điều chưa xác minh

Hành vi trên GitHub thật: `commit_message` của REST merge thay hay nối thân; PR từ fork đã xoá còn merge được không; payload `schedule` thiếu `repository` (suy từ tài liệu nền tảng, điều kiện mới đúng cả hai trường hợp). Chưa chạy `upgrade open-pr` trên một dự án đích thật với `XT_STEWARD_TOKEN`; việc này nằm trong kế hoạch nâng 3.35.0 vào các dự án đích.

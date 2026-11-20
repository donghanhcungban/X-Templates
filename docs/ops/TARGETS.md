# Dự án đích kéo phản hồi về khung

> Danh sách repo đã cài khung (`.xtemplates/`) mà Routine hằng tuần của repo này đọc `docs/xtemplates-feedback/` để gộp
> phản hồi (ADR-0010, `framework/11-autonomous-loop/framework-feedback.md`). Một dòng một repo, dạng `- owner/repo — ghi chú`.
> Repo không còn dùng khung: xoá dòng. Repo private vẫn đọc được nếu phiên có quyền; báo cáo chỉ trích nội dung đã qua `redact`.
> Bản máy đọc (core/gói/owner/release/ngoại lệ — ADR-0068 lát E): [`registry.json`](registry.json), kiểm bằng
> `python3 scripts/xt.py registry`; đổi phiên bản ở đây thì sửa cả hai (`tests/test_registry.py` đối chiếu).

## Danh sách

Đợt đồng bộ ngày 2026-11-20 dùng X-Templates `3a1cd54`. Phiên bản trong ngoặc là lõi cài tại gốc `.xtemplates/` của từng sản phẩm.

- www-donghanhcungban-org/hotel-manager — có `.xtemplates/` (3.34.0). [PR #160](https://github.com/www-donghanhcungban-org/hotel-manager/pull/160). 188 tệp phản hồi ngày 2026-10-23.
- www-donghanhcungban-org/X-Company — có `.xtemplates/` (3.34.0). [PR #115](https://github.com/www-donghanhcungban-org/X-Company/pull/115). 91 tệp phản hồi ngày 2026-10-23.
- www-donghanhcungban-org/xboss — có `.xtemplates/` (3.34.0). [PR #752](https://github.com/www-donghanhcungban-org/xboss/pull/752). 4 tệp phản hồi ngày 2026-10-23.
- www-donghanhcungban-org/dhcb — có `.xtemplates/` (3.34.0). [PR #1508](https://github.com/www-donghanhcungban-org/dhcb/pull/1508). Chưa có phản hồi ở lần gộp 2026-10-23.
- www-donghanhcungban-org/x-shop — có `.xtemplates/` (3.34.0). [PR #53](https://github.com/www-donghanhcungban-org/x-shop/pull/53). Nhánh chính là `master`.
- www-donghanhcungban-org/X-Scanner — có `.xtemplates/` (3.29.0). [PR #85](https://github.com/www-donghanhcungban-org/X-Scanner/pull/85). Giữ lõi đã cài. Bản cập nhật đưa cách nhóm Gate, xếp test và lệnh Flutter vào quy trình hiện có.
- www-donghanhcungban-org/X-Agents — có `.xtemplates/` (2.0.0). [PR #584](https://github.com/www-donghanhcungban-org/X-Agents/pull/584). Các hook dùng lõi đã cài. Lệnh `/factory` dùng bản `3a1cd54` riêng ở `.xtemplates/factory`.

Lần gộp 2026-10-23 (T-2410, `feedback aggregate --from` bản clone nông cả 4 repo public, exit 0): đủ ngưỡng 63 nhóm —
`mien-tru` 47, `cong-cu` 10, `hook-chan-nham` 5, `hook-lot` 1; dưới ngưỡng 61. Nhóm `cong-cu` đủ ngưỡng cần phân loại
(đã sửa / còn lỗi) thành task: `merge-check` (phân trang `/repositories/{id}` bị proxy 403), `blueprint-status`, `doctor`,
`loop init` (×2), `pr steward`, `feedback collect`, `loop decide`, `loop record` (pipefail — đã sửa `1a877b0`),
`loop record/status` (worktree). Nội dung phản hồi giữ ở repo dự án (dữ liệu dự án), không chép vào đây.

## Dự án phát triển từ mã nguồn khung

X-Office là bản phái sinh chứa mã khung ngay ở gốc. Lần đồng bộ này có [PR riêng cho X-Office](https://github.com/www-donghanhcungban-org/X-Office/pull/16).

## Đã xét, không đưa vào

- seeker19110/x-hotel-manager — 2026-10-15 `main` là bản sao lịch sử của chính repo khung (trùng commit `0d1b62c`), chưa cài khung dạng `.xtemplates/`.

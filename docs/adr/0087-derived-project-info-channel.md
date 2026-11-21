# ADR-0087: Dự án phái sinh tự cập nhật thông tin qua PR một tệp và làn merge `derived`

- **Trạng thái:** Đã chấp nhận ngày 2026-11-21 (phiên chính duyệt theo ADR-0008, yêu cầu của chủ repo).
- **Trạng thái triển khai:** Đang làm — `scripts/xt_derived.py`, làn `derived` của `merge-check`, `xt.py derived`.

## Bối cảnh

Chủ repo cho phép dự án fork hoặc phát triển từ mã X-Templates tự cập nhật thông tin của chính nó trong repo khung bằng
commit/PR. Đây là kênh đẩy từ ngoài vào (khác kênh kéo phản hồi của ADR-0010): nội dung do bên thứ ba viết. Steward hiện
không bao giờ tự merge PR từ fork hay của người không có quyền ghi (review #141). Repo cho phép fork PR chạy workflow
sau khi người duyệt lần chạy đầu của người đóng góp mới (`approval_policy: first_time_contributors`, đọc qua API
2026-11-21).

## Phương án đã xét

1. PR chỉ đổi đúng một tệp dữ liệu `docs/derived/<owner>--<repo>.json`, kiểm bằng mã tin cậy của nhánh chính trong
   `merge-check` (làn `derived`). Steward chỉ đọc nội dung PR qua API như byte, không checkout, không chạy mã PR.
2. Workflow `pull_request_target` kiểm tệp. Loại: chính sách gỡ `pull_request_target` trước 2026-12-02, và trigger này
   chạy với quyền của repo đích.
3. Kênh kéo như `feedback` (repo khung đọc repo phái sinh). Loại: dự án phái sinh không nằm trong `TARGETS.md`, khung
   không biết phải đọc repo nào.

## Quyết định

Chọn phương án 1.

- **Ai:** head repo của PR do GitHub báo (`head.repo.full_name`), khác repo đích; không tin trường khai trong tệp.
- **Được làm gì:** chỉ thêm/sửa đúng tệp `docs/derived/<owner>--<repo>.json` suy ra nguyên văn từ head repo (đặt
  `status: archived` thay vì xoá). Danh sách tệp lấy theo đúng cặp SHA của ảnh chụp PR (`compare` ba chấm), phải khớp
  `changed_files` và có đúng một tệp. Tệp ở head phải là blob `100644`. Cấm đổi tên, xoá, symlink, tệp thực thi và tệp khác.
- **Dữ liệu:** schema 1 trong `scripts/xt_derived.py`. Từ điển trắng, ≤ 2048 B, UTF-8 không BOM, không khoá trùng,
  NaN, số thực hay số lớn. `upstream.version` phải có mục trong `CHANGELOG.md` của nhánh đích. Mô tả là văn bản thuần,
  không có HTML, link, URL, `@` hay ký tự ẩn. `homepage` chỉ nhận `https://` với tên miền công khai.
- **Merge:** bản ghi hợp lệ, ghim head, CI xanh, không nhãn `risk:`, không ngoại lệ cứng thì PR vào làn `derived`. Làn
  này không cần review kể cả khi `merge_review: required`. Steward được tự merge PR fork chỉ ở làn này. Lỗi API hay
  thiếu dữ liệu làm PR rơi về luật cũ. Không thêm check bắt buộc mới vào ruleset (check "skipped" không phải bằng chứng).
- `xt.py derived check [--pr N | TỆP…] [--json]` dùng chung hàm với `merge-check`; `xt.py derived list` đọc mọi bản
  ghi. Mô-đun chỉ có ở repo khung, không cài vào dự án đích. `registry` vẫn chỉ đọc dự án đã cài khung.

## Hệ quả

- Tốt: dự án phái sinh tự cập nhật mà không cần người merge; dữ liệu máy đọc được, không có mã của bên ngoài chạy với
  quyền repo khung.
- Đánh đổi: lần đầu người đóng góp mới vẫn cần người duyệt chạy workflow (cấu hình repo). Nhánh tụt sau `main` chỉ được
  cập nhật khi PR bật "Allow edits by maintainers". Repo phái sinh không phải fork trong mạng fork (vd X-Office) không mở
  PR từ chính repo đó được, nên bản ghi của nó đi luật thường. Mô tả tự do có thể chứa tên người; máy chỉ chặn email,
  `@` và dãy số dài. Khắc phục bằng revert.
- Đường lùi: xoá `scripts/xt_derived.py` thì `merge-check` không còn làn `derived` (PR fork quay về người merge). Bản
  ghi trong `docs/derived/` vẫn là tệp dữ liệu thường.

# ADR-0087: Dự án phái sinh tự cập nhật thông tin qua PR một tệp và làn merge `derived`

- **Trạng thái:** Đã chấp nhận ngày 2026-11-21 (phiên chính duyệt theo ADR-0008, yêu cầu của chủ repo).
- **Trạng thái triển khai:** Đã triển khai — `scripts/xt_derived.py`, làn `derived` của `merge-check` (`derived_lane`, `merge_decision`), `xt.py derived`; test `tests/test_derived.py`.

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

- **Ai:** repo đích là `www-donghanhcungban-org/X-Templates` (fork của khung chạy steward riêng không có làn này). Head
  repo của PR do GitHub báo (`head.repo.full_name`), khác repo đích; không tin trường khai trong tệp. Fork của tài khoản
  cá nhân: tác giả PR phải là chủ fork. Fork của tổ chức: token của repo khung không hỏi được quyền thành viên, nên nhận
  theo head repo.
- **Được làm gì:** chỉ thêm/sửa đúng tệp `docs/derived/<owner>--<repo>.json` suy ra nguyên văn từ head repo (đặt
  `status: archived` thay vì xoá). Danh sách tệp lấy bằng `compare` ba chấm giữa đỉnh nhánh đích đọc lúc kiểm và head
  của ảnh chụp PR, phải khớp `changed_files` và có đúng một tệp. `merge-check` đối chiếu thêm danh sách tệp của PR.
  Tệp ở head phải là blob `100644`. Cấm đổi tên, xoá, symlink, tệp thực thi và tệp khác.
- **Dữ liệu:** schema 1 trong `scripts/xt_derived.py`. Từ điển trắng, ≤ 2048 B, UTF-8 không BOM, không khoá trùng,
  NaN, số thực hay số lớn. `upstream.version` phải có mục trong `CHANGELOG.md` của nhánh đích. Mô tả là văn bản thuần
  NFC, không ký tự điều khiển, ký tự ẩn (Default_Ignorable, variation selector, filler, Braille trống) hay dấu kết hợp.
  Sau NFKC + casefold, mô tả không có HTML, link, URL, tên miền, `@` hay dãy ≥ 9 chữ số. `homepage` chỉ nhận
  `https://` với tên miền công khai.
- **Merge:** bản ghi hợp lệ, ghim head, CI xanh, không có review `CHANGES_REQUESTED`, không nhãn `risk:`, không ngoại
  lệ cứng thì PR vào làn `derived`. Làn này không cần review kể cả khi `merge_review: required`. Lỗi API hay thiếu dữ
  liệu làm PR rơi về luật cũ. Không thêm check bắt buộc mới vào ruleset (check "skipped" không phải bằng chứng).
- **Chỉ steward merge:** tiêu đề, thân và commit của PR fork không lên nhánh chính. Steward gửi `commit_title` cố định
  `docs(derived): cập nhật <owner>--<repo> (#N)` và `commit_message` cố định dựng từ bản ghi đã kiểm. Repo đặt thân
  squash bằng mọi commit, còn guard chặn subject tường minh của phiên agent. Vì vậy `merge-check` và `pr next` trả `wait`
  cho làn này: chỉ `pr next` dừng agent; guard chỉ hỏi (`ask`, mặc định cho qua), chưa chặn hẳn (nợ AUD-HAR-454).
  Tiêu đề PR fork không chặn làn.
- `xt.py derived check [--pr N | TỆP…] [--json]` dùng chung hàm với `merge-check`; `xt.py derived list` đọc mọi bản
  ghi. Mô-đun chỉ có ở repo khung, không cài vào dự án đích. `registry` vẫn chỉ đọc dự án đã cài khung.

## Hệ quả

- Tốt: dự án phái sinh tự cập nhật mà không cần người merge; dữ liệu máy đọc được, không có mã của bên ngoài chạy với
  quyền repo khung; lịch sử nhánh chính chỉ nhận subject và thân do máy dựng.
- Đánh đổi: lần đầu người đóng góp mới vẫn cần người duyệt chạy workflow (cấu hình repo). Nhánh tụt sau `main` chỉ được
  cập nhật khi PR bật "Allow edits by maintainers". Repo phái sinh không phải fork trong mạng fork (vd X-Office) không mở
  PR từ chính repo đó được, nên bản ghi của nó đi luật thường. Máy không nhận ra tên người trong mô tả; chặn mô tả tiếng
  có dấu kết hợp sau NFC (Thái, Hindi…). Đổi đỉnh nhánh đích sau lúc kiểm vẫn có thể làm squash ba chiều khác diff đã
  kiểm nếu nhánh đích sửa cùng tệp; test bản ghi của repo bắt lỗi ở lượt CI kế. Ai cũng có thể review
  `CHANGES_REQUESTED` để đẩy PR về người merge.
- Đường lùi: xoá `scripts/xt_derived.py` thì `merge-check` không còn làn `derived` (PR fork quay về người merge). Bản
  ghi trong `docs/derived/` vẫn là tệp dữ liệu thường.

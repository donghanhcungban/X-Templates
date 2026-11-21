# Dự án phát triển từ X-Templates

Mỗi dự án fork hoặc phát triển từ mã X-Templates có một tệp `<owner>--<repo>.json` ở thư mục này. Dự án tự cập nhật
tệp của mình bằng PR. Quyết định và lý do: [ADR-0087](../adr/0087-derived-project-info-channel.md).

## Gửi cập nhật

1. Fork X-Templates về tài khoản sở hữu dự án, tạo nhánh.
2. Tạo hoặc sửa đúng tệp `docs/derived/<owner>--<repo>.json`, trong đó `<owner>/<repo>` là repo mở PR, giữ nguyên chữ
   hoa/thường. Ví dụ PR từ `alice/X-Templates` dùng tệp `alice--X-Templates.json`.
3. Kiểm: `python3 scripts/xt.py derived check docs/derived/<owner>--<repo>.json` (exit 0 là hợp lệ).
4. Mở PR vào `main`. Sau khi CI xanh, kiểm lại bằng `python3 scripts/xt.py derived check --pr <N>`.

```json
{
  "schema": 1,
  "repo": "alice/X-Templates",
  "kind": "fork",
  "upstream": {"repo": "www-donghanhcungban-org/X-Templates", "version": "3.34.0"},
  "description": "Bản fork dùng cho nhóm nội bộ.",
  "homepage": "https://alice.example.org/du-an",
  "status": "active",
  "updated": "2026-11-21"
}
```

## Quy tắc

- **Danh tính:** repo mở PR do GitHub báo. Trường `repo` và tên tệp phải trùng repo đó. Fork của tài khoản cá nhân
  thì chính chủ tài khoản mở PR.
- **Commit:** máy merge với tiêu đề `docs(derived): cập nhật <owner>--<repo> (#N)` và thân cố định. Tiêu đề, mô tả
  và commit của PR không vào lịch sử `main`.
- **Phạm vi:** PR chỉ đổi đúng một tệp của mình. Tệp phải là tệp thường, không symlink, không quyền thực thi. Không
  đổi tên, không xoá. Dự án ngừng thì đặt `"status": "archived"`.
- **Dữ liệu:** chỉ các trường ở ví dụ, `homepage` là tùy chọn. `kind` là `fork` hoặc `derived`. `upstream.version`
  là bản khung đã phát hành trong `CHANGELOG.md`. `updated` có dạng `YYYY-MM-DD` và không quá 1 ngày sau hôm nay.
- **Mô tả:** văn bản thuần ≤ 280 ký tự, một dòng, Unicode NFC. Không HTML, link, URL, tên miền, `@`, email, số
  điện thoại hay tên người. Không ký tự ẩn hay dấu kết hợp (tiếng Việt NFC có đủ dấu vẫn được).
- **Trang chủ:** `https://` và tên miền công khai, ≤ 200 ký tự. Không IP, cổng, userinfo, query hay fragment.
- **Tệp:** JSON UTF-8 không BOM, ≤ 2048 byte, không khoá trùng.

## Giới hạn

- Lần đầu bạn gửi PR, người duyệt của repo cần cho phép chạy workflow. Trước đó PR chưa có CI và chưa merge được.
- Nếu nhánh tụt sau `main`, máy chỉ tự cập nhật được khi PR bật "Allow edits by maintainers".
- Repo không thuộc mạng fork của X-Templates không mở PR trực tiếp từ chính repo đó được. Bản ghi của nó do người duyệt.
- PR chạm tệp khác, không qua kiểm hoặc có review yêu cầu sửa sẽ chờ người duyệt như PR thường.

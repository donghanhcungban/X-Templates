# Pilot 1 · Sổ ghi chú nội bộ

```json
{
  "idea": "Ghi chú nội bộ cho một nhóm",
  "started": "2026-11-20T10:10:09Z",
  "head": "e8cf3ffb1c2155a472fe2361e062ae1936aa86e6",
  "digest": "fa5ec8031e4711a26d4fdd9deae7332e9024246b31b6837766fbe37fc7a0113a",
  "tasks": 1,
  "failed_gates": 0,
  "human_questions": 0,
  "cost_usd": null
}
```

MVP đầu tiên có receipt ở giây **93**. Sau khi thử quay lui và chạy lại trên cây đã chốt, receipt cuối có ở giây **152**. Giai đoạn 1 được trình ở giây **170**, chờ duyệt trên commit `41a65281f94f`. Bản trình chỉ thêm sổ triển khai vào commit đã dựng. Runner dùng dữ liệu mẫu, PostgreSQL thật, Docker Compose và Chromium. Những số này đo một lượt dùng lại chức năng sẵn có của gói.

| Quyết định | Giả định chưa được chủ dự án xác nhận |
|---|---|
| D-001 | Ghi chú phải còn nguyên sau khi mở lại sổ. |
| D-002 | Người dùng là thành viên một nhóm nội bộ. |
| D-003 | Chỉ số là tỷ lệ tạo và đọc lại đúng ghi chú ở phiên mới. |
| D-004 | Dữ liệu thật, chia sẻ liên nhóm và production nằm ngoài MVP. |
| D-005 | Quy mô S, dùng hai tài khoản mẫu ở hai nhóm độc lập. |
| D-006 | Tận dụng chức năng ghi chú của starter và đặt tên sổ cho nhóm. |

Agent độc lập viết bốn tình huống từ SPEC. Khoá A-001 được ghi trước lần tùy biến giao diện. Trên bản cuối, mật khẩu sai bị từ chối, người viết lưu và đọc lại cùng mã ghi chú trong phiên trình duyệt mới, nhóm khác không thấy ghi chú. Digest từ HTTP khớp receipt và archive. [SPEC](../../tests_e2e/notes/docs/specs/SPEC-notes.md) · [Khoá A-001](FACTORY-PILOT-1/ACCEPTANCE.json)

Cổng T-001 xanh trong lượt này. Ở lượt tích hợp trước, cổng định dạng của gói từ chối sổ nghiệm thu do khung sinh. Cấu hình Biome đã được sửa và cả bốn ca chạy lại. [Lượt CI trước](https://github.com/www-donghanhcungban-org/X-Templates/actions/runs/44716333626)

Bundle `so-ghi-chu.bundle` chứa toàn bộ lịch sử sản phẩm. Sau khi tải, một checkout độc lập đã kiểm bundle, clone và dựng lại archive với cùng SHA-256. Bản dev chỉ phục vụ trên loopback của runner. Giai đoạn 2, giai đoạn 3 và production đang chờ quyết định sau MVP. [Tải artifact chứa bundle](https://github.com/www-donghanhcungban-org/X-Templates/actions/runs/44716857760/artifacts/14620635207)

[Lượt chạy GitHub](https://github.com/www-donghanhcungban-org/X-Templates/actions/runs/44716857760) · [Cổng sản phẩm](FACTORY-PILOT-1/task-gates.json) · [Receipt](FACTORY-PILOT-1/DEPLOYS.json) · [Trình duyệt](FACTORY-PILOT-1/preview-browser.json) · [Nghiệm thu](FACTORY-PILOT-1/acceptance.xml) · [Sổ giai đoạn](FACTORY-PILOT-1/STAGE.json) · [Bàn giao](FACTORY-PILOT-1/handoff.json) · [Checklist](FACTORY-PILOT-1/SETUP-ONCE.md)

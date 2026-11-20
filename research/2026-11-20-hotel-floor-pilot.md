# Pilot bộ lọc tầng trên Hotel Manager

Ngày 20/11/2026, nhóm lấy một phần của user story S-003 trong một sản phẩm có sẵn. Nhân viên buồng phòng chọn tầng trong một cơ sở, xem đúng các phòng theo thứ tự ưu tiên rồi trở về toàn bộ danh sách. Cơ sở thứ hai giữ nguyên danh sách. Mọi phép thử dùng dữ liệu mẫu.

| Mốc (UTC+7) | Kết quả |
|---|---|
| 15:23:25 | Bắt đầu checkout từ `ee8b2a6`. |
| Khoảng 15:28 | Có bản xem thử riêng dùng component thật và dữ liệu mẫu, mở được trên điện thoại. |
| 15:28:28 | Gate nhanh đạt, 237 unit test đạt và một ca được bộ test đánh dấu bỏ qua. |
| 15:29:20 | 19 ca tập trung cho UI và truy vấn với PostgreSQL đạt. |
| 15:31:38 | Build production đạt. Lần thử trước bị dừng với mã 137; lần chạy thành công dùng hai lõi. |
| 15:32:07 | Mở [PR #161](https://github.com/www-donghanhcungban-org/hotel-manager/pull/161) ở `074ee68b`, sau 8 phút 42 giây. |
| 15:35:28 | Có ảnh kiểm thử ứng dụng thực trên Chromium ở 390 × 844 với PostgreSQL 17.11; lọc và bỏ lọc qua liên kết hoạt động khi tắt JavaScript. |
| 15:37:24 | CI chính hoàn tất sau 5 phút 14 giây. Check cuối của đợt PR hoàn tất lúc 15:40:34. |
| 15:41:36 | Merge squash sau 28 check bắt buộc và 12 workflow thành công. Commit trên `main` là [c155b9b1](https://github.com/www-donghanhcungban-org/hotel-manager/commit/c155b9b197a39a9c63c40672d255f90de305ea41). |

Chủ dự án giao quyền quyết định nghiệm thu cho agent. Một reviewer độc lập đã đối chiếu truy vấn lọc trước giới hạn bản ghi, phạm vi dữ liệu theo từng cơ sở, thứ tự phòng và kết quả kiểm thử mobile trên đúng cây mã. Lượt đo từ bắt đầu checkout tới merge là **18 phút 11 giây**. Đây là một thay đổi nhỏ trên sản phẩm có sẵn, với một bộ tiêu chí cụ thể. Chưa có lượt đối chứng để quy thời gian tiết kiệm cho phiên bản khung nào.

Sau merge, nhóm đã diễn tập nâng và quay lui ứng dụng web trên dev localhost bằng hai production build độc lập: `ee8b2a6 → c155b9b1 → ee8b2a6`. Kiểm tra sức khoẻ đạt cả ba lần. Cùng phiên Chromium 390 × 844 tắt JavaScript giữ đăng nhập qua hai lần chuyển. Bộ lọc xuất hiện ở bản mới và biến mất khi quay lại đúng build ID, digest JS cũ. Toàn bộ trường của bốn công việc mẫu ở hai cơ sở giữ cùng SHA-256 trước, trong và sau chuyển phiên bản. Phạm vi diễn tập là web và PostgreSQL, chưa gồm worker.

Hotel Manager dùng lõi `3.34.0 (3a1cd54)`. Workflow phát hành của dự án quản lý bản phát hành trên GitHub. Lượt thử này chưa có bằng chứng triển khai lên VPS.

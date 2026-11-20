# SPEC-notes · Sổ ghi chú nội bộ

| Trạng thái | Approved |
|---|---|

## Người dùng và mục tiêu
Một thành viên đăng nhập và lưu ghi chú để dùng trong lần làm việc tiếp theo. Bản dev dùng hai tài khoản mẫu thuộc hai nhóm độc lập trên PostgreSQL.

## Các tình huống nghiệm thu
### S-101

Với tài khoản mẫu hợp lệ, khi thành viên đăng nhập trên trang sổ ghi chú thì biểu mẫu tạo ghi chú hiện ra. Mật khẩu sai không mở không gian ghi chú.

### S-102

Thành viên lưu một nội dung mới từ giao diện. Máy chủ trả HTTP 201 với mã ghi chú và đúng nội dung; danh sách trên trang hiển thị ghi chú vừa lưu.

### S-103

Trong phiên trình duyệt mới, thành viên đăng nhập lại. Danh sách lấy từ máy chủ chứa đúng mã và nội dung vừa lưu. Thành viên của nhóm khác không đọc được ghi chú đó.

### S-104

Bản dev chạy trên loopback của runner. Trị SHA-256 phục vụ từ HTTP và receipt khớp artifact đã build; trình duyệt hoàn tất S-101 đến S-103 trên cùng bản.


## Phạm vi
Không dùng dữ liệu thật, không xuất bản production và không tuyên bố người dùng đã phê duyệt.

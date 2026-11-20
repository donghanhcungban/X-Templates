# Phản hồi công cụ từ các dự án đích

Ngày 20/11/2026. Đối chiếu mười nhóm đã ghi trong [danh sách đích](TARGETS.md) với mã, test và tag của khung. Phiên bản trong bảng là bản có chứa cách xử lý. Dự án đích có thể vẫn dùng phiên bản cũ.

| Nhóm của lượt gộp 23/10 | Hành vi kiểm lại | Phiên bản và commit |
|---|---|---|
| merge-check | Đọc từng trang theo đường dẫn repo khi proxy từ chối đường dẫn theo ID. | 3.11.1 · `30e0ea6` |
| blueprint-status | Tệp không có mục nhận diện được hoặc một MUST khai miễn không đủ bằng chứng làm strict đỏ. | 3.17.0 · `6b762cf` |
| doctor | Hook riêng dùng dirname để trỏ gốc dự án vẫn được nhận diện. | 3.15.2 · `f42f32a` |
| loop init, lượt mới cùng checkout | Giữ việc hoãn và bằng chứng xanh khi đặc tả khớp. | 3.18.0 · `4faf9d4` |
| loop init, máy mới mất evidence | Cảnh báo task đã tick nhưng thiếu bằng chứng cục bộ. Mẫu PLAN chia từng đợt để thu hẹp phần cần chạy lại. | 3.18.0 · `4faf9d4` |
| pr steward | Đợi kiểm tra đang chạy và ghim head khi merge kể cả khi ruleset không yêu cầu check. | 3.13.0 · `cbe97cf` |
| feedback collect | Gom miễn trừ theo ID và chuẩn hóa lý do trước khi đưa về repo khung. | 3.17.0 · `c20022f` |
| loop decide | Cấp số quyết định theo sổ của mọi worktree cùng repo. | 3.18.0 · `4faf9d4` |
| loop record, pipeline | Gate lấy exit của pipeline với bash pipefail. | 3.0.0 · `324b4e5` |
| loop record/status, worktree | Chạy Gate, đọc trạng thái và tick PLAN trong worktree đang dùng. | 3.17.0 · `c20022f` |

Workflow Feedback routine đọc các repo đã đăng ký và kiểm PR có tệp báo cáo. Lệnh chạy tay là `python3 scripts/xt.py feedback routine-check --from <thư-mục-chứa-clone>`. Khi thiếu clone hoặc GitHub không trả được chứng cứ, kiểm tra báo lỗi. Bản ghi chỉ công bố số lượng; nội dung sản phẩm nằm tại dự án gốc.

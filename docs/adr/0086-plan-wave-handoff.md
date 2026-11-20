# ADR-0086: Xếp việc và lấy ngữ cảnh của đợt kế

- **Trạng thái:** Đã chấp nhận ngày 20/11/2026 theo D-524.

Lịch cũ chờ xong mọi nhóm của một tầng phụ thuộc trước khi mở tầng kế. Với hai người, nếu việc C mở D rồi E còn A và B độc lập, xếp A+B trước sẽ cần bốn đợt. Xếp C+A, D+B, E cần ba đợt.

`plan waves` giữ lịch hiện hành làm mốc. Khi mốc còn cao hơn cận dưới theo độ sâu và số chỗ, máy thử ưu tiên việc có chuỗi hậu nhiệm dài rồi xếp vào đợt sớm nhất còn chỗ sau các tiền nhiệm. Cả hai lịch dùng cùng quy tắc phạm vi file. Chỉ đổi lịch khi số đợt giảm. Số đợt giả định mỗi việc mất một đơn vị thời gian. Khi việc kéo dài khác nhau, đo thời gian thật ở dự án.

Phát lại 42 file `docs/**/PLAN*.md` có task và ID duy nhất ở `3c52255`, đặt 551 task về trạng thái mở, giới hạn bốn việc mỗi đợt. Tổng giảm từ 463 xuống 444 đợt trên 14 PLAN. 28 PLAN giữ nguyên lịch. Với mỗi PLAN, đối chiếu tập task, việc bị chặn, thứ tự phụ thuộc, phạm vi file từng đợt và giới hạn người.

`plan waves --handoff` dùng cùng lịch, trả gói `context` của từng task đợt đầu, topology, tier và lý do chặn. Một đợt bốn task lấy đủ thông tin trong một lần gọi CLI. Trên repo mới tạo bằng gói web-api-ts, bảy cặp chạy luân phiên sau khởi động nóng, trung vị 2,369 giây cho năm lệnh cũ và 0,475 giây cho một lệnh mới. Đối chiếu nội dung bốn gói bằng JSON trước khi đo. Lệnh chỉ đọc, kiểm sổ giai đoạn và điều kiện dừng của vòng đang chạy. Phiên chính vẫn ghi Gate của từng việc bằng `loop record`. Khôi phục cách cũ bằng cách hoàn tác thay đổi và dùng `context --task` cho từng việc.

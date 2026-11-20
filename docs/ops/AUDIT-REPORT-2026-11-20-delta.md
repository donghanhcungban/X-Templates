# Audit delta ngày 20/11/2026

Mốc rà lần đầu là `main` tại `6e134c68eda3f94692c7ead68edca6648741b896`, kể cả khi nạp hai ca hồi quy handoff mới. [Sổ audit](AUDIT-STATUS.md).

## Phạm vi

`audit plan --status docs/ops/AUDIT-STATUS.md` báo 13 nhóm thay đổi. Từ `fe5f1e8e` có 186 tệp đổi. Bảng đầu bao gồm bốn nhóm có số liệu hạ tầng. Bảng sau ghi phạm vi của chín nhóm còn lại.

| Nhóm, mốc trước | Kiểm chứng | Giới hạn |
|---|---|---|
| DEP · `fe5f1e8e` | Hai manifest đổi. Script dev/test giữ dependency JS. Bốn package pip E2E trùng version/hash với lock khung, cài `--require-hashes` thành công. `pnpm audit --audit-level moderate`: 0 advisory. | `license-check` đạt 9 gói dev. Chưa quét CVE của image nền trực tiếp. AUD-DEP-037 ghi riêng giới hạn bộ đọc ngoại lệ. [CI Python](https://github.com/www-donghanhcungban-org/X-Templates/actions/runs/44697721936/job/136158386183) · [CI pnpm](https://github.com/www-donghanhcungban-org/X-Templates/actions/runs/44697721936/job/136158385828) |
| CI · `fe5f1e8e` | Bốn workflow: rà hai ma trận test và job tổng hợp, ngoại lệ phụ thuộc, lọc path/pilot/JUnit gói và chú thích release-tag. Hai tệp CFG bên dưới cũng thuộc CI. `ci-check` đạt 12 workflow. GitHub CI 22/22 job, 11 phút 01 giây. | Test 3/6 dùng 9 phút 53 giây trong hạn 10 phút. Khi rà ban đầu GitHub thiếu `pack-npm-audit`; sau đó chủ repo đã bổ sung ngày 20/11, đủ năm check. Mutation định kỳ 15/11 còn một mutant sống trong 35. [CI tại mốc](https://github.com/www-donghanhcungban-org/X-Templates/actions/runs/44697721941) · [Mutation](https://github.com/www-donghanhcungban-org/X-Templates/actions/runs/43711262853/job/132803104649) |
| DATA · `fa81dd3e` | Với `queue.sql` và PostgreSQL 17.11: chạy ba migration lên, seed 12.000 hàng, truy vấn theo role ứng dụng, trả đúng 50. Seq Scan + Sort 18,969 ms → Index Scan 0,124 ms. Ba migration down thành công, hai bảng đã gỡ. | Một lần đo trên dữ liệu mẫu. Không suy ra độ trễ production. [Truy vấn](../../tests_e2e/repairs/queue.sql) · [Cách chạy lại](../../tests_e2e/factory_lifecycle.py) |
| CFG · `7ca87a6a` | Dockerfile ghim digest, kiểm gói, chạy user node. Compose 2.26.1 `config --format json` từ chối khi thiếu biến; đủ biến thì app dùng loopback và DB nội bộ. | Không có Docker Engine trong lần rà này. Lần CI gói ở `39f982c` đã chạy bản dựng Compose; hai tệp này không đổi đến mốc audit. [Job gói](https://github.com/www-donghanhcungban-org/X-Templates/actions/runs/44684821820) |

Đã rà 19 tệp tính nợ theo SHA nhóm mới nhất: năm agent và hook Codex so với bộ sinh, hai `.gitignore`, `VERSION`, workflow mẫu và action, manifest pack, ngoại lệ, Biome/pnpm, OpenAPI và ruleset mẫu. 111 ca Codex/CI mẫu/pack/ngoại lệ xanh.

## Phần rà bổ sung

| Nhóm | Bằng chứng tại mốc | Còn cần rà |
|---|---|---|
| ARCH, CODE, XFEAT | Rà delta 33 tệp, gồm CLI, guard, công cụ factory, pack và pilot. 33 tệp qua parser, 5/5 shellcheck, Ruff và mypy strict 19 tệp xanh. 44 test chéo receipt/registry xanh. | Nâng SHA cho ARCH, CODE, XFEAT theo hợp đồng của từng nhóm. Review phòng vệ toàn guard thuộc SEC. |
| TEST, HAR | Rà 11 tệp HAR, 23 mirror. Chạy 150 phương thức đổi trong 27 module (0 bỏ qua), 8 E2E dashboard Chromium xanh. Các bộ 49/72/103/185 ca độc lập có giao nhau; một lượt rộng bị dừng exit 137, chưa có kết quả. `doctor --offline` không có lỗi, một cảnh báo phát hiện sandbox; `blueprint-status BLUEPRINT.md --strict --run` thành công với 64 MUST đạt, 6 miễn. | TEST: đã rà 47 tệp (37 module, 4 TS, 3 corpus, 2 helper, 1 E2E), 4.210 test khi discover, 726 lớp được chia đúng một lần ở cả 6/8 shard. Chưa thử runtime hook Codex/Gemini trên host thật. |
| SEC | Gitleaks 8.30.1 đối chiếu checksum của workflow, quét Git với `--all --diff-merges=first-parent HEAD`, chế độ redact, 740 commit và 26,76 MB; kết quả 0 phát hiện. Đã xem quyền Actions, ranh giới dev, receipt và hành vi form của pilot. `/repairs` được phục vụ với CSP `form-action 'none'`. | Hai reviewer rà 39 tệp: guard/hook (phân loại, ngân sách, nối adapter) và 37 tệp còn lại (install, CLI, pack, workflow, pilot). Chưa quét CVE image/host/VPS. |
| PERF, A11Y | Handoff: trung vị năm lượt 1,687 → 0,497 s. Chromium 156, axe 4.10.3, hai trang × ba trạng thái × 320/390/1280 px: 0 vi phạm, 3 ca notes cần xác minh màu. Trên API/PG thật ở 390 px, axe 4.13 đạt 22 luật, 0 incomplete ở login và đã đăng nhập. Tab/Enter đi hết luồng lưu và xử lý. | Ba tệp UI có 4.771/2.634/711 B (CSS, notes, repairs). Chưa đo Core Web Vitals/độ trễ ở đích hoặc dùng screen reader và iOS thật. |
| DOC | 73 tệp gồm 17 mirror. Kiểm links nội bộ, 115 URL ngoài, scale S/M/L, README, ADR, registry, deploy/pilot. 19 ca tài liệu/skill/spec qua. | Checker còn redirect/lỗi HTTP tạm. Bốn file ngành chỉ sửa scale, chưa kiểm nội dung pháp lý. |

## Phát hiện và lần kiểm tiếp theo

- **AUD-XFEAT-049 · 🟠.** Khi tiền nhiệm được tick nhưng thiếu bằng chứng, `plan waves --handoff` ở mốc audit giao cả T-002 và T-004; chỉ T-004 đủ điều kiện. Sau hai Gate đỏ, gói vẫn ghi tier `default` trong khi vòng thực thi chọn `deep`. Hai reviewer xác minh. [PR #696](https://github.com/www-donghanhcungban-org/X-Templates/pull/696) (`25c3f649`) xử lý thêm PLAN lỗi cấu trúc; 27 ca waves qua.
- **AUD-SEC-994 · 🟠.** Smoke xác nhận host từ receipt. Hai reviewer thấy trang sau điều hướng và phản hồi HTTP chỉ được đối chiếu một phần. Bản sửa trong #697 buộc origin dev trước khi nhập tài khoản thử và công nhận digest, login, ghi/đọc. Chưa quan sát thất thoát dữ liệu.
- **AUD-SEC-995 · 🟢.** Guard nhận diện một số quyết định bằng chuỗi lý do. Khi tái cấu trúc cần giữ phân loại ổn định theo mã luật.
- **AUD-ARCH-015 · 🟢.** CLI truyền `ModuleType` vào hai module ops. Mypy strict chấp nhận tên thuộc tính bất kỳ ở ranh giới này.
- **AUD-CODE-065 · 🟢.** Bộ đo lịch sử Git nhóm commit theo ngày-tháng, gộp hai năm có cùng ngày-tháng. Phạm vi đã công bố trong báo cáo tốc độ năm 2026 nằm trong một năm. Ở #697, ngày có năm ISO và repo thử cho hai dòng riêng.
- **AUD-HAR-447 · 🟢.** BASE-SEC-010 khai miễn vì không có cổng lắng nghe. Lệnh `xt.py app` và bộ test xác nhận HTTP bind loopback. Bằng chứng loopback đã ghi trong blueprint của #697.
- **AUD-DOC-305 · 🟢.** Trạng thái triển khai trong ADR-0077 ghi ngày 19/11; kế hoạch và CI ngày 20/11 đã có phần lấy receipt và quay lui bản dev. Khi bàn giao, hướng người đọc tới trạng thái hiện tại của dev và hạng mục production T-3860.
- **AUD-DOC-306 · 🟢.** SPEC learning ghi `registry pull` cập nhật cả phiên bản core/pack. Tại mốc rà, lệnh này đọc môi trường cùng ngày và digest release. SPEC ở #697 ghi đúng các trường.

Phát lại `tests_e2e/factory_lifecycle.py` ở đúng mốc: 4,908 s tạo repo, 87,848 s tới trình MVP, 179,943 s tổng. Chromium/PostgreSQL chạy trên gói dựng từ mã chuẩn bị trước. MVP thật chờ duyệt, 0 lần người duyệt, 3 lần chặn agent tự duyệt. Ba sự kiện duyệt mô phỏng chỉ ở bản sao.

## Hậu kiểm trên main và ứng viên sửa

[PR #696](https://github.com/www-donghanhcungban-org/X-Templates/pull/696) đã merge tại `008b03b0`. Cây Git `f08468d2` trùng cây của head đã rà `25c3f649`. Diff 15 tệp gồm hai workflow CI/tag, bốn tài liệu, hai module CLI, năm module test, hành trình và form pilot. Đã rà trình tự xác minh/đẩy tag, kiểm lại main, CI, parser, handoff và fixture. CI đạt 24/24 job, coverage 100%. [Mutation trên main: 35/35](https://github.com/www-donghanhcungban-org/X-Templates/actions/runs/44706781033). Lần chạy lại pilot với bản sửa đạt PostgreSQL/Chromium, 135,569 s tới MVP chờ duyệt. Trong sổ, mười nhóm có delta lên SHA merge. DEP, DATA, CFG giữ `6e134c68` vì không đổi. Nợ tệp đã đổi giảm từ 141 xuống 0 ở hai mốc `main` đã rà; các điều kiện phát hành khác được xét riêng.

[PR #697](https://github.com/www-donghanhcungban-org/X-Templates/pull/697) tại `48cd8e5c` chứa bản sửa SEC-994, HAR-447, CODE-065 và DOC-306. Chromium được chạy với hai phiên, API fixture cục bộ và kiểm health 200/302. Kiểm lại độc lập ở head xác nhận năm test origin/bind/Host và hai dòng ngày riêng trên repo mẫu hai năm. Đã đối chiếu 12 tệp của [head cuối](https://github.com/www-donghanhcungban-org/X-Templates/pull/697#issuecomment-7034904395) với cây merge `4439d48b`. 32 ca test pack và CI đạt. Năm tệp ngoài tài liệu cùng bảy Markdown đã được rà cho ARCH, SEC, CODE, TEST, DOC, XFEAT và HAR. Trạng thái dev và phần production còn mở của AUD-DOC-305 được cập nhật trong [ADR-0077](../adr/0077-deployment-receipts.md).

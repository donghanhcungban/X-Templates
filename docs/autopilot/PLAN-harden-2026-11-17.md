# PLAN harden X-Templates 2026-11-17 — đợt 2 (🟠)

> Duyệt: D-496 (phiên chính tự duyệt) · Blueprint: BLUEPRINT.md · Quy trình: ADR-0080 (D-494) · Đợt trước: PLAN-harden-2026-11-16 (🔴 = 0)

## Tóm tắt
- Mục tiêu: đóng 42 mục 🟠 còn mở của sổ (32 SEC, 10 HAR). Đợt 3: nợ review 🟢. Sau đó cổng ký (audit delta + nợ review theo lô).
- Hướng chung: D-415 — dạng guard không đọc chắc → BUDGET; mục là thiết kế/SPEC Draft thì đóng bằng quyết định D-NNN hoặc `chấp nhận` có hạn.
- Mỗi task: test hồi quy đỏ trước khi sửa; mỗi lát một PR ≤ 150 dòng mã; không gọi reviewer giữa đợt (ADR-0080).

## Ngân sách
- Số vòng: mặc định `--single-session` · Chi phí ngoài phiên: 0 · Timeout Gate: 1200 giây · Hạn: 72 giờ.

## Task
### Lát A — biến/chương trình chạy lệnh ngầm
- [x] `T-3903` 🟠 AUD-SEC-588/608: biến môi trường git chạy lệnh (`PAGER`, `GIT_SEQUENCE_EDITOR`, `GIT_SSH_COMMAND`, `GIT_EDITOR`…) và trình thông dịch nối argv/stdin chạy shell → BUDGET — Gate: `python3 -m unittest tests.test_hooks.GuardExecEnvMoreTest` (files: .claude/hooks/guard.py, tests/test_hooks.py)
- [x] `T-3904` 🟠 AUD-SEC-636: lệnh git chạy lệnh lồng (`rebase --exec`, `bisect run`, `submodule foreach`, `for-each-repo`) → BUDGET — Gate: `python3 -m unittest tests.test_hooks.GuardGitNestedRunTest` (sau: T-3903; files: .claude/hooks/guard.py, tests/test_hooks.py)
### Lát B — cờ gh dựng lúc chạy
- [x] `T-3905` 🟠 AUD-SEC-591/592/593/746: mở rộng đứng riêng/dính ở vị trí cờ của lệnh gh có luật cờ, lệnh đăng chữ có `$X` riêng → BUDGET — Gate: `python3 -m unittest tests.test_hooks.GuardGhDynFlagTest` (files: .claude/hooks/guard.py, tests/test_hooks.py)
- [x] `T-3906` 🟠 AUD-SEC-600/604: `xargs` nối cờ vào lệnh gh; `-F=force=true` đọc như pflag — Gate: `python3 -m unittest tests.test_hooks.GuardGhXargsFieldTest` (sau: T-3905; files: .claude/hooks/guard.py, tests/test_hooks.py)
### Lát C — nhánh/ref phía máy chủ
- [x] `T-3907` 🟠 AUD-SEC-554/623/626/544: `switch` rồi `push -d HEAD`, `gh repo sync --force`, graphql gỡ bảo vệ nhánh, ghi thẳng nhánh chính qua `gh api` — Gate: `python3 -m unittest tests.test_hooks.GuardRemoteRefWriteTest` (files: .claude/hooks/guard.py, tests/test_hooks.py)
### Lát D — chữ ký và duyệt giai đoạn
- [x] `T-3908` 🟠 AUD-SEC-545/625/637/654/641: nhận dạng lệnh `release-sign`/`stage approve`/`loop decide-prod` qua `python3 -m`, glob, bản sao; khoá đọc từ remote — Gate: `python3 -m unittest tests.test_hooks.GuardSignApproveTest` (files: .claude/hooks/guard.py, scripts/xt.py, tests/)
- [ ] `T-3909` 🟠 AUD-SEC-629/630, AUD-HAR-385: ô Tên có ký tự điều khiển, `subject:` trang trí cuối dòng, hàng N/A BLOCKER của promotion — Gate: `python3 -m unittest tests.test_guard_go_no_go tests.test_release_signoff` (files: .claude/hooks/guard.py, scripts/xt.py, tests/)
### Lát E — đường dẫn, symlink, worktree
- [ ] `T-3910` 🟠 AUD-SEC-612/670/655, AUD-HAR-404/405: đích ghi sau thay lệnh rỗng, `core.hooksPath` qua symlink tổ tiên, `.git`/`.autopilot` là symlink — Gate: `python3 -m unittest tests.test_hooks.GuardPathSymlinkTest tests.test_install` (files: .claude/hooks/guard.py, scripts/install.py, scripts/xt.py, tests/)
- [ ] `T-3911` 🟠 AUD-HAR-371/400: cây chính khi submodule/`--separate-git-dir`; `git worktree list -z` cần git ≥ 2.36 — Gate: `python3 -m unittest tests.test_release_signoff tests.test_release_contract` (files: scripts/xt.py, tests/)
### Lát F — guard còn lại
- [ ] `T-3912` 🟠 AUD-SEC-607/646/681/731/753/624: gán có xuống dòng trước lệnh, `restore --end-of-options`, `git-<tên>` theo PATH của guard, `set --` + `for … do`, `--no-verif` viết tắt, ghi công AI theo repo `-R` — Gate: `python3 -m unittest tests.test_hooks.GuardMiscOrangeTest` (files: .claude/hooks/guard.py, tests/test_hooks.py)
- [ ] `T-3913` 🟠 AUD-SEC-796/740: chặn oan lệnh đọc nhắc tên biến chạy lệnh; idiom `-j$(nproc)` (D-437) — đo và quyết — Gate: `python3 -m unittest tests.test_hooks.GuardReaderExecOptTest tests.test_autonomy_bench` (files: .claude/hooks/guard.py, tests/)
### Lát G — formatter và GO-NO-GO
- [ ] `T-3914` 🟠 AUD-SEC-649, AUD-HAR-394/395: `format_check` đỏ sau khi lập GO-NO-GO; chụp–khôi phục fail-closed có `trap`; `dev-task.sh format` cùng đường bảo vệ — Gate: `python3 -m unittest tests.test_hooks.DevTaskTest` (files: scripts/dev-task.sh, framework/templates/, tests/)
### Lát H — SPEC Draft
- [x] `T-3915` 🟠 AUD-HAR-388/391/392: SPEC-factory F-131/F-121/F-113 — chốt bằng D-NNN (Draft giữ, câu hỏi chặn ghi vào SPEC) — Gate: `python3 scripts/xt.py validate && python3 scripts/check-links.py` (files: docs/specs/)
### Lát I — sổ
- [ ] `T-3916` Sổ audit không còn 🟠 mở — Gate: `python3 scripts/xt.py audit check docs/ops/AUDIT-STATUS.md && ! grep -E '^\| AUD-[A-Z]+-[0-9]+ \| 🟠 \| mở' docs/ops/AUDIT-STATUS.md` (sau: T-3903, T-3904, T-3905, T-3906, T-3907, T-3908, T-3909, T-3910, T-3911, T-3912, T-3913, T-3914, T-3915)

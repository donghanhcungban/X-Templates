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
- [x] `T-3909` 🟠 AUD-SEC-629/630, AUD-HAR-385: ô Tên có ký tự điều khiển, `subject:` trang trí cuối dòng, hàng N/A BLOCKER của promotion — Gate: `python3 -m unittest tests.test_guard_go_no_go tests.test_release_signoff` (files: .claude/hooks/guard.py, scripts/xt.py, tests/)
### Lát E — đường dẫn, symlink, worktree
- [x] `T-3910` 🟠 AUD-SEC-612/670/655, AUD-HAR-404/405: đích ghi sau thay lệnh rỗng, `core.hooksPath` qua symlink tổ tiên, `.git`/`.autopilot` là symlink — Gate: `python3 -m unittest tests.test_guard_strict.GuardAud612FormsTest tests.test_install.HooksRealDirTest tests.test_xt_loop.AutopilotSymlinkStopTest` (files: .claude/hooks/guard.py, scripts/install.py, scripts/xt.py, tests/)
- [x] `T-3911` 🟠 AUD-HAR-371/400: cây chính khi submodule/`--separate-git-dir`; `git worktree list -z` cần git ≥ 2.36 — Gate: `python3 -m unittest tests.test_release_signoff tests.test_release_contract` (files: scripts/xt.py, tests/)
### Lát F — guard còn lại
- [x] `T-3912` 🟠 AUD-SEC-607/646/681/731/753/624: gán có xuống dòng trước lệnh, `restore --end-of-options`, `git-<tên>` theo PATH của guard, `set --` + `for … do`, `--no-verif` viết tắt, ghi công AI theo repo `-R` — Gate: `python3 -m unittest tests.test_hooks.GuardMiscOrangeTest` (files: .claude/hooks/guard.py, tests/test_hooks.py)
- [x] `T-3913` 🟠 AUD-SEC-796/740: chặn oan lệnh đọc nhắc tên biến chạy lệnh; idiom `-j$(nproc)` (D-437) — đo và quyết — Gate: `python3 -m unittest tests.test_hooks.GuardReaderExecOptTest tests.test_autonomy_bench` (files: .claude/hooks/guard.py, tests/)
### Lát G — formatter và GO-NO-GO
- [x] `T-3914` 🟠 AUD-SEC-649, AUD-HAR-394/395: `format_check` đỏ sau khi lập GO-NO-GO; chụp–khôi phục fail-closed có `trap`; `dev-task.sh format` cùng đường bảo vệ — Gate: `python3 -m unittest tests.test_hooks.DevTaskTest` (files: scripts/dev-task.sh, framework/templates/, tests/)
### Lát H — SPEC Draft
- [x] `T-3915` 🟠 AUD-HAR-388/391/392: SPEC-factory F-131/F-121/F-113 — chốt bằng D-NNN (Draft giữ, câu hỏi chặn ghi vào SPEC) — Gate: `python3 scripts/xt.py validate && python3 scripts/check-links.py` (files: docs/specs/)
### Lát I — sổ
- [x] `T-3916` Sổ audit không còn 🟠 mở — Gate: `python3 scripts/xt.py audit check docs/ops/AUDIT-STATUS.md && ! grep -E '^\| AUD-[A-Z]+-[0-9]+ \| 🟠 \| mở' docs/ops/AUDIT-STATUS.md` (sau: T-3903, T-3904, T-3905, T-3906, T-3907, T-3908, T-3909, T-3910, T-3911, T-3912, T-3913, T-3914, T-3915)

## Đợt 3 — nợ review 🟢 (D-499)
> 94 dòng 🟢 `mở` mang `nợ-review: #N`. Mặc định sửa kèm test hồi quy; nghi ngờ chưa tái hiện, ranh giới sandbox, hiệu năng guard (T-3709), đổi thiết kế, lịch sử không viết lại được → `chấp nhận` có hạn 2027-01-21. Test mới ở file riêng mỗi lát.

### Lát J — guard
- [x] `T-3917` 🟢 lệnh `gh`: chặn oan dạng trợ giúp, `GH_POST_RE`/`GH_PR_TEXT_RE`, token qua `gh auth git-credential`/`gh config get`, `DELETE …/labels/%2F`, `updateRef force`, `--delete-branch` (AUD-HAR-342/356/357/360/363…366, AUD-SEC-562/565/589/601/603) — Gate: `python3 -m unittest tests.test_green_gh` (files: .claude/hooks/guard.py, tests/test_green_gh.py)
- [x] `T-3918` 🟢 đọc shell: `REMOTE_DELETE` theo remote, `git_filter_repo`, fd nhiều chữ số, glob/`$!` dính cờ, chặn oan hẹp (AUD-SEC-560/561/602/653/658/667/701/712/720/732/747/751/754/755, AUD-HAR-349/358/359, AUD-TEST-096/097/099) — Gate: `python3 -m unittest tests.test_green_shell` (sau: T-3917; files: .claude/hooks/guard.py, tests/test_green_shell.py)
### Lát K — phát hành, cài đặt, CI
- [x] `T-3919` 🟢 `release-sign`/`release-check`/`stage` (AUD-HAR-335…338/343…346/348/372…374/384/402/403, AUD-TEST-093/098/103, AUD-DOC-279/280) — Gate: `python3 -m unittest tests.test_green_release tests.test_release_signoff` (files: scripts/xt.py, docs/adr/, tests/)
- [x] `T-3920` 🟢 `install.py`, chụp–khôi phục GO-NO-GO của `dev-task.sh` (AUD-SEC-652, AUD-TEST-101/102/104, AUD-HAR-396…399) — Gate: `python3 -m unittest tests.test_green_install tests.test_install` (files: scripts/install.py, scripts/dev-task.sh, tests/)
- [x] `T-3921` 🟢 CI/phụ thuộc, bộ kiểm index của `web-api-ts`, tài liệu (AUD-DEP-023…025/027…029, AUD-DATA-014…018, AUD-DOC-275/276/278/290/291, AUD-SEC-723/728) — Gate: `python3 -m unittest tests.test_green_ci tests.test_ci tests.test_packs` (files: .github/, framework/templates/packs/, docs/, tests/)
### Lát L — đóng đợt
- [x] `T-3922` Chấp nhận có hạn các mục D-499 còn lại (AUD-HAR-341/347/368/375/376, AUD-PERF-026, AUD-SEC-563/564/568/647/662, AUD-DEP-026, AUD-DOC-277/292) — Gate: `python3 scripts/xt.py audit check docs/ops/AUDIT-STATUS.md` (sau: T-3917, T-3918, T-3919, T-3920, T-3921; files: docs/ops/AUDIT-STATUS.md)
- [x] `T-3923` Sổ không còn nợ review mở — Gate: `test "$(python3 scripts/xt.py audit check --strict docs/ops/AUDIT-STATUS.md 2>&1 | grep -c 'nợ review còn mở')" = 0` (sau: T-3922; files: docs/ops/AUDIT-STATUS.md)

## Đợt 4 — sửa phát hiện audit delta cổng ký (ADR-0080, [báo cáo](../ops/AUDIT-REPORT-2026-11-17-delta.md))
> Cổng ký lần 1 (ứng viên `fa81dd3e`): 🔴 3 · 🟠 10 · 🟢 12 → FAIL → đợt này, rồi audit delta lần 2 trên phần sửa và phần INCONCLUSIVE. D-500: harden không audit theo mốc.

### Lát M — guard
- [x] `T-3924` 🔴 AUD-SEC-801/802/803: gán muộn `for`/`select`/`${X:=}`/`getopts` trong phạm vi hàm, `eval --`, mở rộng `${X:+…}`/`${X/…}`/mặc định lồng — Gate: `python3 -m unittest tests.test_guard_audit_red` (files: .claude/hooks/guard.py, tests/test_guard_audit_red.py)
- [x] `T-3925` 🟠 AUD-SEC-804/805/806/807, 🟢 AUD-SEC-808: DECISIONS hai bước Edit/hoa thường/Bash, `_git_external` không tin PATH, `-F branch=@tệp`/`{branch}`, `fetch-pack`/`clone -c`/`instaweb`/`send-email` — Gate: `python3 -m unittest tests.test_guard_audit_orange` (sau: T-3924; files: .claude/hooks/guard.py, tests/test_guard_audit_orange.py)
### Lát N — máy, harness, tài liệu
- [x] `T-3926` 🟠 AUD-HAR-412/413, AUD-TEST-109; 🟢 AUD-HAR-414, AUD-TEST-110/111, AUD-DOC-294/295/297, AUD-DEP-030 — Gate: `python3 -m unittest tests.test_audit_dot4_har` (files: scripts/xt.py, .claude/skills/, framework/, tests/, README.md, CONTRIBUTING.md, docs/ops/RUNBOOK-PR-STEWARD.md, requirements*.txt)
- [x] `T-3927` 🟠 AUD-HAR-415/416/417; 🟢 AUD-HAR-418, AUD-DOC-296: Stop hook kẹt khi `.autopilot` là symlink, `--separate-git-dir`, `go_snapshot` gặp thư mục không đọc được — Gate: `python3 -m unittest tests.test_audit_dot4_scripts` (sau: T-3926; files: scripts/xt.py, scripts/dev-task.sh, tests/test_audit_dot4_scripts.py)
### Lát O — cổng ký lần 2
- [x] `T-3928` Sổ không còn 🔴/🟠 mở — Gate: `python3 scripts/xt.py audit check docs/ops/AUDIT-STATUS.md && ! grep -E '^\| AUD-[A-Z]+-[0-9]+ \| (🔴|🟠) \| mở' docs/ops/AUDIT-STATUS.md` (sau: T-3924, T-3925, T-3926, T-3927; files: docs/ops/AUDIT-STATUS.md)

## Đợt 5 — sửa phát hiện cổng ký lần 2 theo lớp (D-502, [báo cáo](../ops/AUDIT-REPORT-2026-11-17-delta.md))
> Cổng ký lần 2 (ứng viên `b68527fc`): 🔴 11 · 🟠 9 · 🟢 14 — hầu hết có từ trước; AUD-HAR-422, AUD-SEC-832 do bản sửa đợt 4. Sửa theo lớp, rồi cổng ký lần 3 chỉ rà diff sửa + hồi quy.

### Lát P — guard
- [x] `T-3929` 🔴 lớp giá trị không tính chắc ở đích/cờ của lệnh có luật: AUD-SEC-820/821/822/823/828/829/830, 🟠 AUD-SEC-832, 🟢 AUD-SEC-835 — Gate: `python3 -m unittest tests.test_guard_value_class` (files: .claude/hooks/guard.py, tests/test_guard_value_class.py)
- [x] `T-3930` 🔴 lớp kênh chạy lệnh: AUD-SEC-815/816/817/824, 🟠 AUD-SEC-825/827/831/833, 🟢 AUD-SEC-834 — Gate: `python3 -m unittest tests.test_guard_exec_class` (sau: T-3929; files: .claude/hooks/guard.py, tests/test_guard_exec_class.py)
- [x] `T-3931` 🟠 AUD-HAR-419 (heredoc ghi công AI), AUD-HAR-420 (lệnh phá dữ liệu), 🟢 AUD-SEC-818 (in biến token) — Gate: `python3 -m unittest tests.test_guard_har_class` (sau: T-3930; files: .claude/hooks/guard.py, framework/11-autonomous-loop/, tests/test_guard_har_class.py)
### Lát Q — scripts, tests
- [x] `T-3932` 🟠 AUD-HAR-422, AUD-TEST-112; 🟢 AUD-HAR-423, AUD-TEST-113…116, AUD-DOC-298/299/300 — Gate: `python3 -m unittest tests.test_signoff2_scripts` (files: scripts/dev-task.sh, scripts/xt.py, tests/, framework/11-autonomous-loop/harness-files.md)
### Lát R — cổng ký lần 3
- [x] `T-3933` Sổ không còn 🔴/🟠 mở — Gate: `python3 scripts/xt.py audit check docs/ops/AUDIT-STATUS.md && ! grep -E '^\| AUD-[A-Z]+-[0-9]+ \| (🔴|🟠) \| mở' docs/ops/AUDIT-STATUS.md` (sau: T-3929, T-3930, T-3931, T-3932; files: docs/ops/AUDIT-STATUS.md)

## Đợt 6 — mặc định chặn trong lệnh có luật (D-503)
> Cổng ký lần 3 (ứng viên `b5de13e9`): 🔴 13 · 🟠 7 · 🟢 7 — biến thể trong các lớp đợt 5 đã đóng. Đóng bằng cấu trúc, rồi cổng ký lần 4 kiểm bất biến.

- [x] `T-3934` 🔴 AUD-SEC-836…843, AUD-SEC-846…850; 🟠 AUD-SEC-844/851/852, AUD-HAR-424/425; 🟢 AUD-SEC-854: mặc định chặn ở đích/cờ/lệnh con của lệnh có luật, quét mọi hậu tố sau trình bọc, xargs tới shell/trình bọc — Gate: `python3 -m unittest tests.test_guard_default_deny` (files: .claude/hooks/guard.py, tests/test_guard_default_deny.py, tests/test_guard_fuzz.py)
- [x] `T-3935` 🟠 AUD-TEST-117; 🟢 AUD-HAR-427/428, AUD-TEST-118: test không gọi mạng, go_skippable — Gate: `python3 -m unittest tests.test_signoff3_isolation` (files: scripts/dev-task.sh, tests/)
- [x] `T-3936` Sổ không còn 🔴/🟠 mở — Gate: `python3 scripts/xt.py audit check docs/ops/AUDIT-STATUS.md && ! grep -E '^\| AUD-[A-Z]+-[0-9]+ \| (🔴|🟠) \| mở' docs/ops/AUDIT-STATUS.md` (sau: T-3934, T-3935; files: docs/ops/AUDIT-STATUS.md)

## Đợt 7 — đóng bất biến D-503 theo fuzz (cổng ký lần 4)
> 829/15 778 tổ hợp lọt theo 9 gốc + hồi quy. Tiêu chí: bộ fuzz → 0 lọt, tập con tất định ghim thành test.

- [x] `T-3937` 🔴 AUD-SEC-857…862, 🟠 AUD-SEC-863…867, 🟢 AUD-SEC-868, AUD-TEST-119 — Gate: `python3 -m unittest tests.test_guard_d503_invariant tests.test_guard_signoff4` (files: .claude/hooks/guard.py, tests/)
- [x] `T-3939` GHSA-fc5q-39xc-vjpf (picomatch, chưa có bản vá, chỉ qua devDependency vitest) làm `pack-npm-audit` đỏ: ngoại lệ có hạn theo BASE-DEP-004 (D-504) — Gate: `python3 -m unittest tests.test_packs` (files: framework/templates/packs/web-api-ts/starter/, tests/)
- [x] `T-3938` Sổ không còn 🔴/🟠 mở — Gate: `python3 scripts/xt.py audit check docs/ops/AUDIT-STATUS.md && ! grep -E '^\| AUD-[A-Z]+-[0-9]+ \| (🔴|🟠) \| mở' docs/ops/AUDIT-STATUS.md` (sau: T-3937; files: docs/ops/AUDIT-STATUS.md)

## Đợt 8 — sửa phát hiện cổng ký lần 5 (D-503)
> Cổng ký lần 5 (ứng viên `702e006d`): hồi quy 🔴 của #648 (vòng `for` duyệt glob) và ba gốc lọt của fuzz mở rộng 201 179 tổ hợp (2 535 lọt: `sh -c` nháy kép, thư mục làm việc không xác định, xargs miễn theo nguồn), cùng chặn oan sed/`$(date)`.

- [x] `T-3940` 🔴 AUD-SEC-869/870/871, 🟠 AUD-SEC-872/873, 🟢 AUD-SEC-874, AUD-DEP-031 — Gate: `python3 -m unittest tests.test_guard_signoff5 tests.test_guard_d503_invariant` (files: .claude/hooks/guard.py, tests/, framework/templates/packs/web-api-ts/)
- [x] `T-3941` Sổ không còn 🔴/🟠 mở — Gate: `python3 scripts/xt.py audit check docs/ops/AUDIT-STATUS.md && ! grep -E '^\| AUD-[A-Z]+-[0-9]+ \| (🔴|🟠) \| mở' docs/ops/AUDIT-STATUS.md` (sau: T-3940; files: docs/ops/AUDIT-STATUS.md)

## Đợt 9 — sửa phát hiện cổng ký lần 6 (D-503, D-505)
> Cổng ký lần 6 (ứng viên `49ce04a1`): hồi quy 🔴 của #650 (`$(date)`/`$(cat)` tin theo tên lệnh), CDPATH/`popd`, nguồn xargs, hạn giờ chung của quyết định, cùng chặn oan xargs/sed và hiệu năng vòng `for`. #652 (T-3942) sửa hầu hết; còn `parallel`/`sem`.

- [ ] `T-3942` 🔴 AUD-SEC-875/876/877/885/886, 🟠 AUD-SEC-878/880/881/882/884, 🟢 AUD-SEC-879/883, AUD-DEP-032, AUD-HAR-429 — Gate: `python3 -m unittest tests.test_guard_signoff6 tests.test_guard_d503_invariant` (files: .claude/hooks/guard.py, tests/, framework/)
- [ ] `T-3943` 🔴 AUD-SEC-890 (`$(pwd)` + hàm che ở lớp bọc `sh -c`), 🔴 AUD-SEC-887 `parallel`/`sem` chạy chuỗi lệnh từ `:::`/stdin → BUDGET (mặc định chặn); đo lại hạn giờ cho dạng sed/for ~50 KB (AUD-SEC-888) — Gate: `python3 -m unittest tests.test_guard_signoff7 tests.test_guard_d503_invariant` (files: .claude/hooks/guard.py, tests/)
- [ ] `T-3944` Sổ không còn 🔴/🟠 mở — Gate: `python3 scripts/xt.py audit check docs/ops/AUDIT-STATUS.md && ! grep -E '^\| AUD-[A-Z]+-[0-9]+ \| (🔴|🟠) \| mở' docs/ops/AUDIT-STATUS.md` (sau: T-3943; files: docs/ops/AUDIT-STATUS.md)

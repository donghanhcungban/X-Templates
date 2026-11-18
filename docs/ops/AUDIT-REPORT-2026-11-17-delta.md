---
title: Audit delta cổng ký 2026-11-17
kind: report
updated: 2026-11-17
---

# Audit delta cổng ký — 2026-11-17

Quy trình: ADR-0080 (cổng ký sau vét việc). Ứng viên `fa81dd3e` (sau #627). Năm lô reviewer độc lập (`reviewer-alt`, effort max), chỉ đọc, chạy song song trên diff tích luỹ; mọi phát hiện có lệnh tái hiện đã chạy. Dòng sổ: [`AUDIT-STATUS.md`](AUDIT-STATUS.md).

| Lô | Phạm vi | Kết luận | Phát hiện |
|---|---|---|---|
| SEC-A | `guard.py` dòng 1–7000, diff `7ca87a6..fa81dd3e` | CÓ PHÁT HIỆN; INCONCLUSIVE: `_split_why`, `tokenize(strict)`, `_arith_hash_why`, `_extglob_why`, `_wrapper_arguments`, `_set_positional_why`, `_autocorrect_lookup_why`, `_git_cfg_dyn` | 🔴 AUD-SEC-801, AUD-SEC-802 · 🟠 AUD-SEC-804 · 🟢 AUD-SEC-808 |
| SEC-B | `guard.py` dòng 7001–hết, `.claude/hooks/*.sh` | CÓ PHÁT HIỆN; INCONCLUSIVE: `_heredoc_bodies`, `_go_mark_nul`, `_subst_tail`, `_printf_render`, `_record_assigns`, `_rough_budget`, `_exec_env_why`, `_runner_why`, `GATE_PASSIVE` | 🔴 AUD-SEC-803 · 🟠 AUD-SEC-805, AUD-SEC-806, AUD-SEC-807 |
| scripts | `scripts/` (2 832 dòng diff) | ARCH, DATA sạch; CODE/XFEAT có phát hiện; PERF không có số đỏ | 🟠 AUD-HAR-415, AUD-HAR-416, AUD-HAR-417 · 🟢 AUD-DOC-296, AUD-HAR-418, AUD-DOC-297 |
| TEST | `tests/` lấy mẫu (file mới, cấu trúc `test_hooks`, đối chiếu 716 kỳ vọng với 2 617 ca corpus, 6 đột biến) | CÓ PHÁT HIỆN; INCONCLUSIVE ~4 000 dòng ở test sửa khác | 🟠 AUD-TEST-109 · 🟢 AUD-TEST-110, AUD-TEST-111 |
| HAR/CI/DOC | skill, `framework/11-autonomous-loop`, `.github`, tài liệu đổi | HAR có phát hiện; CI sạch; DOC INCONCLUSIVE (phần lớn CHANGELOG, ADR-0074/0078 so với mã) | 🟠 AUD-HAR-412, AUD-HAR-413 · 🟢 AUD-HAR-414, AUD-DOC-294, AUD-DEP-030, AUD-DOC-295, AUD-SEC-809 |

Tổng: 🔴 3 · 🟠 10 · 🟢 12 (kể cả AUD-SEC-810 từ T-3918). Năm 🟠 là bản sửa chưa đủ của mục đã ghi `đã sửa` (AUD-SEC-641/681/544/636, AUD-HAR-371/405) — dòng cũ giữ nguyên, dòng mới mang phần còn thiếu.

Kết quả G7: chưa GO. Theo ADR-0080 — FAIL → đợt kế: PLAN-harden-2026-11-17 đợt 4 (T-3924…T-3928), rồi audit delta lần nữa trên phần sửa và các phần INCONCLUSIVE ở trên.

## Cổng ký lần 2 (ứng viên `b68527fc`, sau đợt 4)

Năm lô: phần sửa của guard (#628/#630/#632), hai lô phần guard INCONCLUSIVE của lần 1, `scripts/`+`tests/`, harness/tài liệu/phụ thuộc. `loop verify --all` XANH (26 Gate + 68 lệnh kiểm blueprint); `pip-audit` ba lockfile pip: 0 lỗ hổng (2026-11-17).

| Lô | Kết luận | Phát hiện |
|---|---|---|
| phần sửa guard (#628/#630/#632) | CÓ PHÁT HIỆN; blueprint `--run` exit 0, không hồi quy idiom lành | 🔴 AUD-SEC-828/829/830 (bản sửa 803/811/801 chưa đủ) · 🟠 AUD-SEC-831/832/833 · 🟢 AUD-SEC-834/835 |
| guard INCONCLUSIVE A | CÓ PHÁT HIỆN (đều có từ trước) | 🔴 AUD-SEC-820…824 · 🟠 AUD-SEC-825 · 🟢 AUD-SEC-826 |
| guard INCONCLUSIVE B | CÓ PHÁT HIỆN (đều có từ trước) | 🔴 AUD-SEC-815/816/817 · 🟠 AUD-HAR-419 · 🟢 AUD-SEC-818 |
| scripts + tests | CODE/TEST có phát hiện; XFEAT sạch | 🟠 AUD-HAR-422, AUD-TEST-112 · 🟢 AUD-HAR-423, AUD-TEST-113…116, AUD-DOC-300 |
| harness/tài liệu/DEP | HAR có phát hiện; README, ADR-0074/0078 sạch; DEP pip sạch | 🟠 AUD-HAR-420, AUD-SEC-827 · 🟢 AUD-DOC-298/299, AUD-HAR-421 |

Mỗi vòng rà đối kháng sâu hơn lại ra lỗ có từ trước của bộ đọc shell heuristic → D-502: sửa theo LỚP (giá trị không tính chắc ở đích/cờ của lệnh có luật → BUDGET; kênh chạy lệnh → BUDGET), cổng ký lần 3 rà diff sửa + hồi quy. Đợt 5: T-3929…T-3933.

## Cổng ký lần 3 (ứng viên `b5de13e9`, sau đợt 5)

Ba lô theo D-502 (diff sửa + hồi quy): #637, #638/#639, #636. Không hồi quy chậm (lệnh 14–30 KB: 1,0–1,2× nền); blueprint `--run` exit 0; idiom lành trong brief đều qua.

| Lô | Kết luận | Phát hiện |
|---|---|---|
| #637 lớp giá trị | CÓ PHÁT HIỆN (biến thể trong lớp, có từ trước) | 🔴 AUD-SEC-836…843 · 🟠 AUD-SEC-844 · 🟢 AUD-SEC-854 |
| #638/#639 kênh chạy lệnh, heredoc, dữ liệu | CÓ PHÁT HIỆN (biến thể trong lớp, có từ trước) | 🔴 AUD-SEC-846…850 · 🟠 AUD-SEC-851/852, AUD-HAR-424/425 · 🟢 AUD-SEC-853, AUD-HAR-426 |
| #636 scripts/tests | CÓ PHÁT HIỆN | 🟠 AUD-TEST-117 · 🟢 AUD-HAR-427/428, AUD-TEST-118 |

Liệt kê biến thể trong lớp không hội tụ → D-503: mặc định chặn (BUDGET) trong lệnh có luật kèm danh sách cho phép hẹp; cổng ký lần 4 kiểm bất biến bằng fuzz có hướng + hồi quy. Đợt 6: T-3934…T-3936.

## Cổng ký lần 4 (ứng viên `a662344e`, sau đợt 6)

Hai lô theo D-503: fuzz bất biến có hướng và hồi quy. Blueprint `--run` exit 0; tốc độ quyết định 1,16× nền (p95 42 ms); #642/#644 đủ.

| Lô | Kết luận | Phát hiện |
|---|---|---|
| Fuzz bất biến (47 lệnh gốc × ~120 dạng, 15 778 tổ hợp; bash thật trong sandbox) | CÓ PHÁT HIỆN: 829 tổ hợp nguy hiểm lọt (815 có từ trước, 14 hồi quy #643) theo 9 gốc | 🔴 AUD-SEC-857…862 · 🟠 AUD-SEC-863/864/865 |
| Hồi quy D-503 + #642/#644 + nguồn AUD-TEST-119 | CÓ PHÁT HIỆN; AUD-TEST-119 do `ConcurrentDecisionTest` vá `os.environ` trong luồng | 🔴 (gộp AUD-SEC-861) · 🟠 AUD-SEC-866 · 🟢 AUD-SEC-868 |

Sự cố: lần chạy oracle đầu dùng đường sandbox tương đối nên 480 ca gọi `/usr/bin/rm` thật; HOME khi đó cũng tương đối (không tồn tại), chỉ thư mục sandbox bị xoá — đã kiểm `/home/liend`, `.ssh`, `git fsck` repo nguyên vẹn. Tiêu chí đợt 7: chạy lại bộ fuzz → 0 ca lọt; tập con tất định thành test hồi quy (`tests/test_guard_d503_invariant.py`).

## Cổng ký lần 5 (ứng viên `702e006d`, sau đợt 7)

Hai lô: fuzz bất biến D-503 mở rộng (kèm dạng bọc) và hồi quy. Lần này oracle bash thật chạy với đường tuyệt đối, PATH chỉ có lệnh giả và canary kiểm trước mỗi tiến trình; không có sự cố. Hồi quy: blueprint `--run` exit 0, tốc độ 1,0–1,1× nền, `tests.test_hooks` sau các `test_guard_*` trong một tiến trình 1263 test OK (AUD-TEST-119 đã đóng).

| Lô | Kết luận | Phát hiện |
|---|---|---|
| Fuzz mở rộng: 201 179 tổ hợp (core 19 369 + bọc env/command/nice/timeout 65 596 + bọc `true &&`, `X=1;`, `bash -c`, `sh -c`, `$(…)`, `cd /tmp &&` 116 214); 166 760 nguy hiểm trong bash thật | 829/829 ca lọt của cổng ký 4 đã chặn; 2 535 lọt (đều có từ trước, 0 hồi quy so nền) theo ba gốc | 🔴 AUD-SEC-870 (`sh -c "…"` nháy kép), AUD-SEC-871 (thư mục làm việc không xác định) · 🟠 AUD-SEC-872 (xargs miễn theo nguồn) |
| Hồi quy #648/#647 | CÓ PHÁT HIỆN | 🔴 AUD-SEC-869 (hồi quy #648: `for` duyệt glob + `${f%…}`) · 🟠 AUD-SEC-873 (sed/`$(date)` chặn oan) · 🟢 AUD-SEC-874, AUD-DEP-031 |

Đợt 8 (T-3940, #650): fuzz mở rộng 2 535 → 0, bộ cổng ký 4 vẫn 0/829; mọi dạng chặn mới vào `tests/fixtures/autonomy/d503_invariant.jsonl`. Một lỗi CI trên đường: nhánh trả về của `_heredoc_shell_why` không còn bị test phủ vì bước quét sớm chặn trước — ghim bằng test gọi thẳng hàm (không đổi mã).

## Cổng ký lần 6 (ứng viên `49ce04a1`, sau đợt 8)

Hai lô reviewer-alt: fuzz họ mới (hàm che lệnh, CDPATH/`popd`, nguồn xargs) và hồi quy #650/#648/#647. Oracle bash thật chạy với đường tuyệt đối, PATH chỉ có lệnh giả và canary; không có sự cố. Lô fuzz: 665/1 848 tổ hợp họ mới lọt ở ứng viên (nền `702e006d`: 755), gồm 213 ca hồi quy; tiền tố/lớp bọc mới 203 218 tổ hợp 0 lọt; tốc độ 1,02–1,15× nền. Chưa rà (INCONCLUSIVE, chuyển cổng ký 7): phần còn lại của `while`, `case`, `coproc`, `time { }`, `sh -c` lồng 2–3 tầng, `sh -c` → `bash -c` (~133 500 tổ hợp).

| Lô | Kết luận | Phát hiện |
|---|---|---|
| Fuzz họ mới | CÓ PHÁT HIỆN | 🔴 AUD-SEC-875 (hồi quy #650), AUD-SEC-876, AUD-SEC-877 · 🟠 AUD-SEC-878 · 🟢 AUD-SEC-879 |
| Hồi quy #650/#648 | CÓ PHÁT HIỆN | 🟠 AUD-SEC-880…882, AUD-SEC-884 · 🟢 AUD-SEC-883, AUD-DEP-032, AUD-HAR-429 · có từ trước: 🔴 AUD-SEC-885 (không có hạn giờ chung), AUD-SEC-886, AUD-SEC-887 · 🟢 AUD-SEC-888, AUD-SEC-889 |

Đợt 9 (T-3942, #652): bộ fuzz chỉ-guard `leaks6.fam` 665, bộ cổng ký 4 (829) và 5 (2 535) → 0 lọt; hạn giờ chung `DECISION_SECONDS` 15 s (D-505) đóng lỗ lệnh 256 KB chạy quá 1300 s. Còn mở: AUD-SEC-887 (`parallel`/`sem`) và AUD-SEC-890 (🔴 `$(pwd)` + hàm che trong thân `sh -c`, do fuzz tất định của CI bắt ở #653), cả hai ở T-3943. Cổng ký lần 7 chạy sau T-3943, gồm cả các họ INCONCLUSIVE.

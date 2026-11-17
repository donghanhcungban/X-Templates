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

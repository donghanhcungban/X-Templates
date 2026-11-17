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

"""Ngoại lệ quét phụ thuộc npm của gói web-api-ts (BASE-DEP-004, D-504): mỗi GHSA bị `pnpm audit` bỏ qua phải có dòng
ngoại lệ chưa hết hạn, mỗi dòng ngoại lệ phải đang được bỏ qua, và job CI giữ ngưỡng `--audit-level moderate`."""

from __future__ import annotations

import datetime as dt
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STARTER = ROOT / "framework" / "templates" / "packs" / "web-api-ts" / "starter"
WORKFLOW = ROOT / ".github" / "workflows" / "dep-audit.yml"
GHSA = re.compile(r"^GHSA(-[2-9cfghjmpqrvwx]{4}){3}$")


def ignored_ghsas(text: str) -> list[str]:
    """Đọc khối `auditConfig.ignoreGhsas` của pnpm-workspace.yaml (chỉ stdlib, đúng dạng danh sách `- ID`)."""
    out: list[str] = []
    in_ignore = False
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if re.match(r"^\s+ignoreGhsas:\s*$", line):
            in_ignore = True
            continue
        m = re.match(r"^\s+-\s+(\S+)\s*(#.*)?$", line)
        if in_ignore and m:
            out.append(m.group(1))
        else:
            in_ignore = False
    return out


def expired(exceptions: list[dict], today: dt.date) -> list[str]:
    return [e["ghsa"] for e in exceptions if dt.date.fromisoformat(e["expires"]) < today]


def load() -> tuple[list[str], list[dict]]:
    ws = (STARTER / "pnpm-workspace.yaml").read_text(encoding="utf-8")
    data = json.loads((STARTER / "audit-exceptions.json").read_text(encoding="utf-8"))
    return ignored_ghsas(ws), data["exceptions"]


class PackAuditExceptionsTest(unittest.TestCase):
    def test_ignored_and_exceptions_match_both_ways(self):
        ignored, exceptions = load()
        listed = [e["ghsa"] for e in exceptions]
        self.assertEqual(sorted(ignored), sorted(listed))
        self.assertEqual(len(set(listed)), len(listed), "GHSA trùng trong audit-exceptions.json")

    def test_exceptions_complete_and_not_expired(self):
        _, exceptions = load()
        today = dt.date.today()
        for e in exceptions:
            with self.subTest(ghsa=e.get("ghsa")):
                for key in ("ghsa", "package", "reason", "owner", "approved_by", "expires"):
                    self.assertTrue(str(e.get(key, "")).strip(), f"thiếu `{key}`")
                self.assertRegex(e["ghsa"], GHSA)
        self.assertEqual(expired(exceptions, today), [], "có ngoại lệ hết hạn: xét lại hoặc bỏ")

    def test_expired_exception_is_red(self):
        ex = [{"ghsa": "GHSA-aaaa-bbbb-cccc", "expires": "2026-12-18"}]
        self.assertEqual(expired(ex, dt.date(2026, 12, 18)), [])  # đúng ngày hạn còn hiệu lực
        self.assertEqual(expired(ex, dt.date(2026, 12, 19)), ["GHSA-aaaa-bbbb-cccc"])

    def test_parser_edge_cases(self):
        self.assertEqual(ignored_ghsas(""), [])
        self.assertEqual(ignored_ghsas("auditConfig:\n  ignoreGhsas: []\n"), [])
        text = "auditConfig:\n  ignoreGhsas:\n    # ghi chú\n    - GHSA-aaaa-bbbb-cccc  # lý do\n    - GHSA-dddd-eeee-ffff\nother: 1\n"
        self.assertEqual(ignored_ghsas(text), ["GHSA-aaaa-bbbb-cccc", "GHSA-dddd-eeee-ffff"])

    def test_ci_job_keeps_moderate_threshold(self):
        wf = WORKFLOW.read_text(encoding="utf-8")
        job = wf.split("  pack-npm-audit:", 1)[1]
        self.assertIn("run: pnpm audit --audit-level moderate\n", job)
        self.assertNotIn("--ignore", job)
        self.assertNotIn("audit-level high", job)
        self.assertNotIn("audit-level critical", job)


if __name__ == "__main__":
    unittest.main()

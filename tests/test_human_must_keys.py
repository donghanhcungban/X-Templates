"""D-529: đủ 16 ID, quyền thực thi và cổng người dùng chung một bảng."""

import re
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_release_contract import ReleaseCase, xt
import xt_ops_setup


LEVELS = {
    "WF-REVIEW-004": "MUST@L",
    "WF-REVIEW-007": "MUST",
    "WF-ENV-008": "MUST",
    "PM-HANDOVER-006": "MUST@L",
    "PM-PLAN-005": "MUST",
    "WF-SDD-010": "MUST@L",
    "SEC-SUPPLY-011": "MUST@L",
    "SEC-SECRET-010": "MUST@L",
    "OPS-IR-006": "MUST",
    "OPS-IAC-006": "MUST",
    "SEC-TM-007": "MUST@L",
    "SEC-LOG-013": "MUST@L",
    "CMP-AUDIT-004": "MUST@L",
    "CMP-AI-001": "MUST",
    "UX-A11Y-017": "MUST@L",
    "WF-TEAM-006": "MUST@L",
}
KEYS = {
    "WF-REVIEW-007": "merge_hard_exceptions",
    "WF-ENV-008": "grant: deploy",
    "PM-PLAN-005": "grant: deploy",
    "PM-HANDOVER-006": "release_signoff_scale",
}
TABLE = Path("11-autonomous-loop/stop-points-and-escalation.md")


class HumanMustCatalogueTest(unittest.TestCase):
    def test_exact_ids_original_levels_and_real_keys(self):
        groups = dict(re.findall(r"^\| `([A-Z0-9-]+)` \| ([ABC]) \|", (xt.DEFAULT_FRAMEWORK / TABLE).read_text(), re.M))
        self.assertEqual(set(groups), set(LEVELS))
        self.assertEqual(xt.human_must_ids(), set(LEVELS) - set(KEYS) - {"WF-REVIEW-004"})
        items = {}
        for path in xt.DEFAULT_FRAMEWORK.rglob("*.md"):
            for rid, level, body in re.findall(
                r"^- \[ \] `([^\x60]+)` \*\*([^*]+)\*\* ([^\n]+)", path.read_text(encoding="utf-8"), re.M
            ):
                if rid in LEVELS:
                    self.assertNotIn(rid, items)
                    items[rid] = level, body
        self.assertEqual({rid: pair[0] for rid, pair in items.items()}, LEVELS)
        for rid, key in KEYS.items():
            self.assertEqual(groups[rid], "A")
            self.assertIn(key, items[rid][1])
        self.assertEqual(groups["WF-REVIEW-004"], "C")
        self.assertIn("xt.py merge-check --pr", items["WF-REVIEW-004"][1])

    def test_truncated_or_conflicting_catalogue_stays_unknown(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(xt, "DEFAULT_FRAMEWORK", Path(tmp)):
            p = Path(tmp) / TABLE
            p.parent.mkdir(parents=True)
            bp = Path(tmp) / "BLUEPRINT.md"
            bp.write_text("- [ ] `OPS-IR-006` **MUST** X\n")
            for raw in ("", "## Phân lớp các mục MUST có công việc của người\n| `OPS-IR-006` | X | lỗi |\n"):
                p.write_text(raw)
                with self.assertRaises(ValueError):
                    xt.human_must_ids()
                self.assertEqual(xt_ops_setup.local_items(xt, Path(tmp))[0]["status"], xt_ops_setup.UNKNOWN)
                self.assertEqual(xt._release_blueprint(Path(tmp), "BLUEPRINT.md")["result"], "FAIL")


class HumanMustReleaseTest(ReleaseCase):
    def test_open_class_b_waits_for_human_and_concrete_waiver_resolves(self):
        bp = self.repo / "BLUEPRINT.md"
        human = "- [ ] `SEC-SUPPLY-011` **MUST** Code owner duyệt bộ cổng.\n"
        bp.write_text(self.BP + human)
        self.setup_xt()
        _, release = self.release()
        row = self.by_id(release)["blueprint"]
        self.assertEqual((row["result"], release["promotion"]["state"]), ("N/A", "pending_human"))
        self.assertIn("SEC-SUPPLY-011", row["evidence"])
        checklist = xt_ops_setup.local_items(xt, self.repo)[0]
        self.assertEqual((checklist["status"], checklist["ids"]), (xt_ops_setup.MISSING, ["SEC-SUPPLY-011"]))
        bp.write_text(self.BP + human + "- [ ] `PM-PLAN-005` **MUST** Còn việc thiết kế.\n")
        self.assertEqual(xt._release_blueprint(self.repo, "BLUEPRINT.md")["result"], "FAIL")
        bp.write_text(
            self.BP
            + human.replace("[ ]", "[~]").rstrip()
            + " — Miễn: không thay cổng trong bản này. — Duyệt: “Chấp thuận riêng cho bản này” 2026-11-20\n"
        )
        self.assertEqual(xt._release_blueprint(self.repo, "BLUEPRINT.md")["result"], "PASS")
        self.assertEqual(xt_ops_setup.local_items(xt, self.repo)[0]["status"], xt_ops_setup.OK)
        bp.write_text(self.BP + human.replace("[ ]", "[~]"))
        self.assertEqual(xt_ops_setup.local_items(xt, self.repo)[0]["status"], xt_ops_setup.UNKNOWN)

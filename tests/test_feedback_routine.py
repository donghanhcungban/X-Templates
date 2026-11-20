"""Trạng thái Routine đọc tệp báo cáo của PR và ngày phản hồi theo UTC."""

import datetime as dt
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.test_xt_cli import run_main, xt


class FeedbackRoutineTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.clone = self.root / "sample"
        self.clone.mkdir()
        self.fb = self.clone / xt.FEEDBACK_DIR
        self.fb.mkdir(parents=True)
        self.enterContext(
            mock.patch.object(xt, "registry_load", return_value=({"products": [{"repo": "Org/Sample"}]}, []))
        )
        self.clones = self.enterContext(
            mock.patch.object(xt, "_registry_clones", return_value={"org/sample": self.clone})
        )
        self.api = self.enterContext(mock.patch.object(xt, "_gh_items", side_effect=self.api_rows))
        self.open = []
        self.history = []
        self.linked = []
        self.files = []

    def api_rows(self, path):
        if "/files?" in path:
            return self.files
        if "/commits/" in path:
            return self.linked
        if "/commits?" in path:
            return self.history
        return self.open

    def write(self, age, number=1):
        date = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=age)
        (self.fb / f"FB-{number:03d}.md").write_text(f"- Ngày: {date.isoformat()}\n")
        return date.isoformat()

    def run_cli(self, *extra):
        return run_main("feedback", "routine-check", "--from", str(self.root), *extra)

    def test_quiet_and_first_report_grace(self):
        self.assertEqual(self.run_cli()[0], 0)
        self.write(1)
        self.assertEqual(self.run_cli()[0], 0)
        self.write(10)
        rc, out, _ = self.run_cli()
        self.assertEqual(rc, 1)
        self.assertIn("1 mục mới", out)

    def test_only_real_report_files_count(self):
        self.open = [
            {"number": 4, "created_at": self.write(12), "head": {"repo": {"id": 7}}, "base": {"repo": {"id": 7}}},
            {"number": 5, "head": {"repo": None}, "base": {"repo": {"id": 7}}},
        ]
        self.write(3, 2)
        self.files = [{"filename": "docs/ops/feedback/REPORT-2026-08-03.md", "status": "removed"}]
        self.assertIn("2 mục mới", self.run_cli()[1])
        self.files[0]["status"] = "added"
        rc, out, _ = self.run_cli()
        self.assertEqual(rc, 1)
        self.assertIn("1 mục mới", out)
        self.assertEqual(self.run_cli("--days", "40")[0], 0)

    def test_merged_pr_same_base_and_no_new_signal(self):
        self.history = [{"sha": "a" * 40}]
        self.linked = [
            {"number": 8, "merged_at": None},
            {"number": 7, "merged_at": "yes", "base": {"ref": "other"}},
            {"number": 6, "merged_at": "yes", "base": {"ref": "main"}, "created_at": self.write(9)},
        ]
        self.files = [{"filename": "docs/ops/feedback/REPORT-2026-08-03.md", "status": "modified"}]
        self.assertIn("0 mục mới", self.run_cli()[1])
        self.assertEqual(self.run_cli()[0], 0)
        self.linked[2]["created_at"] = "?"
        self.assertEqual(self.run_cli()[0], 3)

    def test_incomplete_sources_and_network(self):
        self.clones.return_value = {}
        self.assertEqual(self.run_cli()[0], 2)
        self.assertEqual(self.run_cli("--days", "0")[0], 2)
        self.clones.return_value = {"org/sample": self.clone}
        self.api.side_effect = xt.PrInputError("offline")
        self.assertEqual(self.run_cli()[0], 3)
        with mock.patch.object(xt, "registry_load", return_value=(None, ["registry sai"])):
            self.assertEqual(self.run_cli()[0], 2)

    def test_legacy_feedback_uses_committed_date_only(self):
        f = self.fb / "FB-001.md"
        f.write_text("# legacy\n")
        self.assertEqual(self.run_cli()[0], 2)
        subprocess.run(["git", "init", "-q"], cwd=self.clone, check=True)
        subprocess.run(["git", "add", "."], cwd=self.clone, check=True)
        env = {**os.environ, "GIT_COMMITTER_DATE": "2026-01-01T12:00:00Z", "GIT_AUTHOR_DATE": "2026-01-01T12:00:00Z"}
        subprocess.run(
            ["git", "-c", "user.name=test", "-c", "user.email=t@example.invalid", "commit", "-qm", "feedback"],
            cwd=self.clone,
            env=env,
            check=True,
        )
        self.assertEqual(xt._routine_dates(self.clone)[0].isoformat(), "2026-01-01T12:00:00+00:00")

    def test_refuses_symlinked_sources(self):
        (self.fb / "FB-001.md").symlink_to(self.root / "unrelated")
        self.assertEqual(self.run_cli()[0], 2)
        (self.fb / "FB-001.md").unlink()
        self.fb.rmdir()
        self.fb.symlink_to(self.root, target_is_directory=True)
        self.assertEqual(self.run_cli()[0], 2)

"""The weekly check binds added report blobs and source trees to their GitHub repositories."""

import base64
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
        self.framework = self.root / "framework"
        self.clone = self.root / "sources/product"
        for repo, slug in ((self.framework, "Framework/Rules"), (self.clone, "org/sample")):
            repo.mkdir(parents=True)
            self.git(repo, "init", "-q", "-b", "main")
            self.git(repo, "remote", "add", "origin", f"https://github.com/{slug}.git")
        self.enterContext(
            mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(self.framework), "GH_REPO": "wrong/ambient"})
        )
        self.enterContext(
            mock.patch.object(xt, "registry_load", return_value=({"products": [{"repo": "org/sample"}]}, []))
        )
        self.api = self.enterContext(mock.patch.object(xt, "_gh_api", side_effect=self.api_rows))
        self.open, self.history, self.linked, self.files = [], [], [], []
        self.now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
        self.head = self.commit("empty", 30)
        self.blob = ""

    def git(self, repo, *args, env=None):
        return subprocess.run(
            ["git", "-C", str(repo), "-c", "user.name=Test", "-c", "user.email=test@example.invalid", *args],
            check=True,
            capture_output=True,
            text=True,
            env=env,
        ).stdout.strip()

    def commit(self, note, age=0):
        date = (self.now - dt.timedelta(days=age)).isoformat()
        self.git(self.clone, "add", "-A")
        self.git(
            self.clone,
            "commit",
            "--allow-empty",
            "-qm",
            note,
            env={**os.environ, "GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date},
        )
        self.head = self.git(self.clone, "rev-parse", "HEAD")
        return self.head

    def add(self, number, age, stated="2001-01-01"):
        p = self.clone / xt.FEEDBACK_DIR / f"FB-{number:03}.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"- Ngày: {stated}\n")
        return self.commit(str(number), age)

    def report(self, base, age, pr_age=None):
        stamp = self.now - dt.timedelta(days=age)
        created = self.now - dt.timedelta(days=age if pr_age is None else pr_age)
        self.open = [
            {
                "number": 7,
                "created_at": created.isoformat(),
                "updated_at": self.now.isoformat(),
                "head": {"repo": {"id": 2}},
                "base": {"repo": {"id": 2}},
            }
        ]
        self.files = [{"status": "added", "filename": f"docs/ops/feedback/REPORT-{stamp.date()}.md", "sha": "b" * 40}]
        self.blob = f"Feedback-Cutoff: {stamp.isoformat()}\nFeedback-Source: org/sample {base}\n"

    def api_rows(self, path, *, paginate, host):
        self.assertEqual(host, "github.com")
        if path == "repos/org/sample/commits?per_page=1":
            return [[{"sha": self.head}]]
        self.assertTrue(path.startswith("repos/Framework/Rules/"), path)
        if "/git/blobs/" in path:
            return [
                {
                    "encoding": "base64",
                    "size": len(self.blob.encode()),
                    "content": base64.b64encode(self.blob.encode()).decode(),
                }
            ]
        if "/files?" in path:
            return [self.files]
        if "/commits/" in path:
            return [self.linked]
        if "/commits?" in path:
            return [self.history]
        return [self.open]

    def check(self, *extra):
        return run_main("feedback", "routine-check", "--from", str(self.clone.parent), *extra)

    def test_quiet_and_first_report_grace_uses_committed_history(self):
        self.assertIn("0 mục mới", self.check()[1])
        self.add(1, 1)
        self.assertEqual(self.check()[0], 0)
        self.add(2, 12)
        code, out, _ = self.check()
        self.assertEqual(code, 1)
        self.assertIn("2 mục mới", out)

    def test_newly_merged_backdated_signal_and_old_pr_now_reporting(self):
        old = self.add(1, 22)
        new = self.add(2, 12, stated="2000-01-01")
        self.report(old, 15)
        self.assertEqual(self.check()[0], 1)
        self.assertIn("1 mục mới", self.check()[1])
        self.report(new, 0, pr_age=20)
        self.assertEqual(self.check()[0], 0)
        self.assertIn("0 mục mới", self.check()[1])

    def test_editing_prior_report_or_external_open_pr_does_not_reset_clock(self):
        self.add(1, 12)
        self.report(self.head, 0)
        self.files[0]["status"] = "modified"
        self.assertEqual(self.check()[0], 1)
        self.files[0]["status"] = "added"
        self.open[0]["head"]["repo"] = None
        self.assertEqual(self.check()[0], 1)

    def test_local_dirty_tree_and_unmerged_branch_do_not_create_signals(self):
        reviewed = self.add(1, 20)
        self.report(reviewed, 15)
        self.git(self.clone, "checkout", "-qb", "experiment")
        self.add(2, 1)
        (self.clone / xt.FEEDBACK_DIR / "FB-003.md").write_text("- Ngày: 2099-01-01\n")
        self.head = reviewed
        self.assertIn("0 mục mới trong 1 phản hồi", self.check()[1])

    def test_merged_report_provenance_requires_linked_main_pr(self):
        baseline = self.add(1, 21)
        self.report(baseline, 15)
        pull = self.open.pop()
        self.history = [{"sha": "c" * 40}]
        self.linked = [{**pull, "merged_at": self.now.isoformat(), "base": {"ref": "other"}}]
        self.assertEqual(self.check()[0], 1)
        self.linked[0]["base"]["ref"] = "main"
        self.assertEqual(self.check()[0], 0)

    def test_bad_blob_cutoff_unknown_sha_or_stale_clone_fail_closed(self):
        self.report(self.head, 1)
        original = self.blob
        for broken in (
            "",
            original.replace("Feedback-Source:", ""),
            original + original,
            original.replace("+00:00", ""),
            original.replace(self.blob.split()[1], (self.now + dt.timedelta(days=1)).isoformat()),
        ):
            with self.subTest(broken=broken):
                self.blob = broken
                self.assertEqual(self.check()[0], 3)
        self.blob = original.replace(self.head, "d" * 40)
        self.assertEqual(self.check()[0], 2)
        self.blob = original
        self.head = "f" * 40
        self.assertEqual(self.check()[0], 2)

    def test_missing_clone_invalid_days_or_network(self):
        with mock.patch.object(
            xt, "registry_load", return_value=({"products": [{"repo": "org/sample"}, {"repo": "org/missing"}]}, [])
        ):
            self.assertIn("thiếu clone", self.check()[2])
        self.assertEqual(self.check("--days", "0")[0], 2)
        self.git(self.clone, "remote", "set-url", "origin", "https://github.com/other/product")
        self.assertEqual(self.check()[0], 2)
        self.git(self.clone, "remote", "set-url", "origin", "https://github.com/org/sample")
        self.api.side_effect = xt.PrInputError("offline")
        self.assertEqual(self.check()[0], 3)

    def test_committed_symlink_is_rejected_without_reading_it(self):
        dest = self.clone / xt.FEEDBACK_DIR
        dest.mkdir(parents=True)
        (dest / "FB-001.md").symlink_to(self.root / "unused")
        self.commit("link")
        self.assertEqual(self.check()[0], 2)

    def test_api_shape_page_limit_and_metadata_integrity(self):
        for returned in ([], [{}], [[{}] * 100] * xt.GH_MAX_PAGES):
            with self.subTest(returned=len(returned)), mock.patch.object(xt, "_gh_api", return_value=returned):
                with self.assertRaises(xt.PrInputError):
                    xt._routine_api("repos/Framework/Rules/pulls", True)
        with mock.patch.object(xt, "_gh_api", side_effect=ValueError("non-JSON")):
            self.assertEqual(self.check()[0], 3)
        with mock.patch.object(xt, "_routine_api", return_value=[[{"sha": "invalid"}]]):
            with self.assertRaises(xt.PrInputError):
                xt._routine_target_head("org/sample")

        self.report(self.head, 1)
        self.files[0]["sha"] = "invalid"
        self.assertEqual(self.check()[0], 3)
        self.files[0]["sha"] = "b" * 40
        self.open[0]["updated_at"] = "unknown"
        self.assertEqual(self.check()[0], 3)
        self.open[0]["updated_at"] = self.now.isoformat()
        self.blob += f"Feedback-Source: org/sample {self.head}\n"
        self.assertEqual(self.check()[0], 3)
        native = self.api_rows

        def oversized(path, *, paginate, host):
            if "/git/blobs/" in path:
                return [{"encoding": "base64", "size": 300_000}]
            return native(path, paginate=paginate, host=host)

        self.api.side_effect = oversized
        self.assertEqual(self.check()[0], 3)

    def test_non_github_framework_origin_missing_registry_or_bad_directory(self):
        with mock.patch.object(xt, "registry_load", return_value=(None, ["registry error"])):
            self.assertEqual(self.check()[0], 2)
        self.git(self.framework, "remote", "set-url", "origin", "https://example.invalid/Framework/Rules")
        self.assertEqual(self.check()[0], 2)
        self.git(self.framework, "remote", "set-url", "origin", "https://github.com/Framework/Rules")
        folder = self.clone / xt.FEEDBACK_DIR
        folder.parent.mkdir(parents=True)
        folder.symlink_to(self.root, target_is_directory=True)
        self.commit("invalid directory")
        self.assertEqual(self.check()[0], 2)
        folder.unlink()
        folder.mkdir()
        (folder / "README.md").write_text("not feedback")
        self.commit("no entries")
        self.assertIn("0 mục mới", self.check()[1])
        with self.assertRaisesRegex(ValueError, "lịch sử"):
            xt._first_feedback(self.clone, self.head, {f"{xt.FEEDBACK_DIR}/FB-001.md"})

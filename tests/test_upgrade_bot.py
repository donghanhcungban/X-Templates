"""Consumer waves, withdrawal, failure to obtain provenance, and updating one review branch."""

from __future__ import annotations

import contextlib
import datetime as dt
import json
import os
from unittest import mock

from tests.test_promotion_gate import ReleaseFixture, dist, xt


class UpgradeTest(ReleaseFixture):
    def setUp(self):
        super().setUp()
        self.project = self.temp / "product"
        self.project.mkdir()
        self.git(self.project, "init", "-qb", "main")
        self.git(self.project, "remote", "add", "origin", "https://github.com/test/project.git")
        (self.project / ".xtemplates").mkdir()
        (self.project / dist.MANIFEST).write_text(json.dumps({"source": {"repo": "test/framework"}, "packs": {}}))
        (self.project / ".xtemplates/VERSION").write_text("1.0.0 (abcdef)\n")
        (self.project / "xt.yaml").write_text("upgrade_wave: canary\n")
        self.git(self.project, "add", ".")
        self.git(self.project, "commit", "-qm", "project")
        self.origin = self.temp / "origin.git"
        self.git(self.temp, "clone", "--bare", str(self.project), str(self.origin))
        self.enterContext(contextlib.chdir(self.project))

    def release(self, version, days=0):
        day = dt.datetime.now(dt.UTC) - dt.timedelta(days=days, minutes=2)
        (self.up / "VERSION").write_text(version + "\n")
        (self.up / "CHANGELOG.md").write_text(f"## [{version}] - 2026-11-20\n\n- Framework update\n")
        scripts = self.up / "scripts"
        scripts.mkdir(exist_ok=True)
        (scripts / "install.py").write_text(
            "from pathlib import Path\n"
            "d=Path('.xtemplates/scripts');d.mkdir(exist_ok=True)\n"
            "(d/'xt.py').write_text('from pathlib import Path\\nassert Path(\\\"BLUEPRINT.md\\\").exists()\\n')\n"
            "(Path('.xtemplates')/'VERSION').write_text(Path(__file__).parents[1].joinpath('VERSION').read_text())\n"
            "Path('BLUEPRINT.md').write_text('verified release fixture')\n"
        )
        self.git(self.up, "add", ".")
        with mock.patch.dict(os.environ, {"GIT_COMMITTER_DATE": day.isoformat()}):
            self.git(self.up, "commit", "-qm", version)
            self.git(self.up, "tag", "-am", version, "v" + version)
        self.sign("v" + version)

    def test_select_newest_aged_and_skip_withdrawn(self):
        self.assertEqual(xt.main(["upgrade", "check"]), 0)
        self.release("1.1.0", 5)
        self.release("1.2.0", 1)
        now = int(dt.datetime.now(dt.UTC).timestamp())
        self.assertEqual(dist.tags_for_wave(self.up, "1.0.0", "after-canary", 3, now), (True, ["v1.1.0"]))
        self.assertEqual(xt.main(["upgrade", "check"]), 10)
        withdrawn = self.up / dist.WITHDRAWN
        withdrawn.parent.mkdir(parents=True)
        withdrawn.write_text("# Reason\n\n1.1.0 — withdrawn\n")
        self.git(self.up, "add", ".")
        self.git(self.up, "commit", "-qm", "withdraw")
        (self.project / "xt.yaml").write_text("upgrade_wave: after-canary\n")
        self.assertEqual(xt.main(["upgrade", "check"]), 11)
        self.assertEqual(dist.tags_for_wave(self.up, "1.0.0", "canary", 3, now), (True, ["v1.2.0"]))
        withdrawn.write_text("unparseable withdrawal")
        self.git(self.up, "commit", "-qam", "invalid list")
        self.assertEqual(xt.main(["upgrade", "check"]), 3)

    def test_network_failure_unsigned_and_invalid_configuration_never_install(self):
        self.release("1.1.0")
        self.signed.clear()
        with mock.patch.object(dist, "publish_upgrade") as publish:
            self.assertEqual(xt.main(["upgrade", "open-pr"]), 11)
            with mock.patch.object(dist, "trusted_archive", side_effect=dist.DistributionError("network")):
                self.assertEqual(xt.main(["upgrade", "open-pr"]), 3)
            publish.assert_not_called()
        (self.project / "xt.yaml").write_text("upgrade_wave: invalid\n")
        self.assertEqual(xt.main(["upgrade", "check"]), 2)
        (self.project / dist.MANIFEST).write_text("[]")
        self.assertEqual(xt.main(["upgrade", "check"]), 3)

    def test_target_changes_configuration_or_identity_before_publication(self):
        self.release("1.1.0")
        self.git(self.up, "tag", "notes")
        (self.project / ".xtemplates/VERSION").write_text("0.9.0")
        self.assertEqual(xt.main(["upgrade", "open-pr"]), 3)
        (self.project / ".xtemplates/VERSION").write_text("1.0.0")
        for packs, result in [(False, 2), ({"tool": {}}, 0)]:
            manifest = {"source": {"repo": "test/framework"}, "packs": packs, "adapters": [".codex/hooks.json"]}
            (self.project / dist.MANIFEST).write_text(json.dumps(manifest))
            self.git(self.project, "add", ".")
            self.git(self.project, "commit", "-qm", "update project manifest")
            self.git(self.project, "push", str(self.origin), "HEAD:main")
            self.assertEqual(xt.main(["upgrade", "open-pr"]), result)
        self.git(self.origin, "symbolic-ref", "HEAD", "refs/heads/" + dist.UPGRADE_BRANCH)
        self.assertEqual(xt.main(["upgrade", "open-pr"]), 3)

    def test_historical_attestation_without_promotion_receipt_is_not_auto_installed(self):
        self.release("1.1.0")
        self.has_promotion = False
        self.assertEqual(xt.main(["release-verify", "--tag", "v1.1.0", "--repo", "test/framework"]), 0)
        self.assertEqual(xt.main(["upgrade", "open-pr"]), 11)
        self.assertFalse(any(cmd[:3] == ("gh", "pr", "create") for cmd in self.gh))

    def test_pr_contains_verified_tree_and_retry_updates_same_pr(self):
        self.release("1.1.0")
        (self.up / "VERSION").write_text("1.2.0-dev")
        self.git(self.up, "commit", "-qam", "default branch is ahead")
        self.assertEqual(xt.main(["upgrade", "open-pr"]), 0)
        ref = "refs/heads/" + dist.UPGRADE_BRANCH
        old = self.git(self.origin, "rev-parse", ref)
        receipt = json.loads(self.git(self.origin, "show", f"{ref}:{dist.MANIFEST}"))["source"]
        self.assertEqual(
            receipt,
            {
                "repo": "test/framework",
                "tag": "v1.1.0",
                "commit": self.git(self.up, "rev-parse", "v1.1.0^{commit}"),
                "verified": True,
            },
        )
        self.assertEqual(self.git(self.origin, "show", f"{ref}:.xtemplates/VERSION"), "1.1.0")
        self.prs = [{"number": 17}]
        self.assertEqual(xt.main(["upgrade", "open-pr"]), 0)
        self.assertEqual(self.git(self.origin, "rev-parse", ref), old)
        self.release("1.2.0")
        self.assertEqual(xt.main(["upgrade", "open-pr"]), 0)
        self.assertEqual(self.git(self.origin, "merge-base", ref, old), old)
        self.assertEqual(sum(a[:3] == ("gh", "pr", "create") for a in self.gh), 1)
        self.assertEqual(sum(a[:3] == ("gh", "pr", "edit") for a in self.gh), 2)

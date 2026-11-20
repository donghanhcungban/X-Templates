"""The real acceptance lock, stage ledger, dev adapter and M signoff must agree on one candidate."""

import os
import sys
from contextlib import chdir
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_deploy_run import CONFIG, FAKE_NODE
from test_release_signoff import GO_DOC, HEX, RealCheckRepo
from test_release_signoff_scale import ROW20
from test_stage import human_env
from test_xt_cli import run_main, xt

GATE = """# S-101
from pathlib import Path

source = Path("app_value")
passed = source.exists() and source.read_text() == "ready"
Path("dist/suite.xml").write_text(
    '<testsuite><testcase file="acceptance/test_cases.py" name="output">'
    + ("" if passed else "<failure/>")
    + "</testcase></testsuite>"
)
raise SystemExit(0 if passed else 1)
"""


class StageReleaseFlowTest(RealCheckRepo):
    def cli(self, *args):
        rc, out, err = run_main(*args)
        self.assertEqual(rc, 0, err or out)
        return out

    def prepare_candidate(self):
        self.enterContext(chdir(self.proj))
        self.enterContext(human_env(CLAUDE_PROJECT_DIR=str(self.proj)))
        fake = self.tmp / "node"
        fake.write_text("#!" + sys.executable + "\n" + FAKE_NODE)
        fake.chmod(0o755)
        self.enterContext(
            mock.patch.dict(
                os.environ,
                {
                    "PATH": str(self.tmp) + os.pathsep + os.environ["PATH"],
                    "XT_DEPLOY_STATE": str(self.tmp),
                    "GITHUB_ACTIONS": "false",
                },
            )
        )
        self.write("dist/app.tgz", "packaged output")
        self.write(
            "xt.yaml",
            CONFIG
            + """release_signoff: agent
release_signoff_scale: M
stage_approval: agent
stage_approval_max: 3
delivery_phase: harden
acceptance_paths: acceptance
acceptance: python3 acceptance/test_cases.py
acceptance_report: dist/suite.xml
attack: python3 run_check.py
perf: python3 run_check.py
migration_check: python3 run_check.py
rollback: python3 run_check.py
""",
        )
        self.write("scripts/dev-preview.mjs", "// adapter process supplied by this isolated test\n")
        self.write("run_check.py", 'from pathlib import Path\nassert Path("app_value").read_text() == "ready"\n')
        self.write("docs/specs/SPEC-example.md", "| Trạng thái | Approved |\n### S-101 principal output\n")
        self.write("acceptance/test_cases.py", GATE)
        self.write("BLUEPRINT.md", self.BP.replace("scale: S", "scale: M") + self.MUST_OK)
        self.doc.write_text(GO_DOC.replace("## 4.", ROW20 + "\n\n## 4."))
        self.commit()
        out = self.cli("acceptance", "lock", "--spec", "docs/specs/SPEC-example.md", "--author", "acceptance-author")
        self.assertIn("A-001", out)
        self.write("app_value", "ready")
        self.state.unlink()
        self.cli("stage", "init", "--adopt", "2", "--evidence", "MVP fixture")
        self.commit()

    def deploy_candidate(self):
        self.cli("deploy", "run", "--env", "dev", "--json")
        self.commit()
        return xt.release_check(self.proj, xt.RELEASE_SIGN_BLUEPRINT, xt.RELEASE_SIGN_STATUS, unchecked_must="fail")

    def test_stage_two_and_medium_release_share_real_locked_evidence(self):
        self.prepare_candidate()
        sha = self.git("rev-parse", "HEAD").strip()
        with mock.patch.dict(os.environ, {"CLAUDE_CODE_SESSION_ID": "test-stage-release"}):
            self.cli("stage", "submit", "--evidence", "S-101")
            self.commit()
            rc = self.deploy_candidate()
            rows = {row["id"]: row for row in rc["rows"]}
            self.assertEqual(rc["fails"], [])
            self.assertEqual(rows["acceptance_lock"]["result"], "PASS")
            self.assertEqual(rows["deploy"]["result"], "PASS")
            self.cli("stage", "approve", "--sha", sha, "--note", "A-001 and dev receipt")
            self.assertEqual(xt.read_stage(self.proj)["stage"], 3)
            self.commit()

        # The stage decision changes the tracked release subject. Sign the newly deployed subject.
        subject = self.deploy_candidate()["subject"]
        self.doc.write_text(
            self.doc.read_text()
            .replace(HEX, subject["content"])
            .replace("## 4.", f"subject: digest {subject['digest']}\n\n## 4.")
        )
        self.commit()
        self.state.write_text("{}")  # An existing, idle /complete loop is required for every release-sign.
        self.cli("release-sign", "--note", "A-001 and dev receipt")
        self.commit()
        decision = xt.release_check(self.proj, xt.RELEASE_SIGN_BLUEPRINT, xt.RELEASE_SIGN_STATUS)["promotion"]
        self.assertEqual((decision["state"], decision["by"], decision["simulated"]), ("approved", ["agent"], True))

"""D-526. Stage 2/3 are opt-in and require a merged, unchanged subject and independent evidence."""

import json
import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_stage_agent_approval as stage_fixture
from test_stage import human_env
from test_xt_cli import TmpRepoCase, xt


class StageMaxTest(TmpRepoCase):
    commit = stage_fixture.StageAgentApprovalCliTest.commit
    stage = stage_fixture.StageAgentApprovalCliTest.stage
    led = stage_fixture.StageAgentApprovalCliTest.led

    def setUp(self):
        # Same git fixture as the ADR-0069 CLI tests, with its own real bare origin.
        super().setUp()
        self.init_repo()
        self.git("config", "user.name", "Owner")
        self.git("config", "user.email", "owner@example.invalid")
        self.origin = self.tmp / "origin.git"
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(self.origin)], check=True)
        self.git("remote", "add", "origin", str(self.origin))
        self.enterContext(human_env(CLAUDE_PROJECT_DIR=str(self.repo)))

    def prepare(self, stage, maximum="3"):
        (self.repo / ".gitignore").write_text(".autopilot/\n")
        (self.repo / "app.bin").write_bytes(b"sample application package")
        (self.repo / "xt.yaml").write_text(
            f"stage_approval: agent\nstage_approval_max: {maximum}\nrelease_artifacts: app.bin\ndeploy_envs: dev\n"
        )
        self.commit("khởi tạo")
        self.git("push", "-q", "origin", "main")
        self.assertEqual(self.stage("init", "--adopt", str(stage), "--evidence", "người nghiệm thu")[0], 0)
        submitted = self.commit("ứng viên")
        self.git("push", "-q", "origin", "main")
        self.assertEqual(self.stage("submit", "--evidence", "luồng đã khoá", agent=True)[0], 0)
        self.git("add", "-A")
        self.git("commit", "-qm", "chỉ sổ bản trình")
        return submitted

    def evidence(self, *rows):
        head = self.git("rev-parse", "HEAD").strip()
        return {
            "rows": [xt._release_row(k, v, "bằng chứng có thật") for k, v in rows],
            "head": head,
            "subject": {"digest": self.led()["submitted"]["artifact_digest"]},
            "promotion": {"state": "pending_human"},
        }

    def approve(self, sha):
        return self.stage("approve", "--sha", sha[:12], "--note", "đã đối chiếu receipt dev", agent=True)

    def test_stage_two_then_three_bound_and_auditable(self):
        sha = self.prepare(2)
        self.git("push", "-q", "origin", "main")
        rc = self.evidence(("acceptance_lock", "PASS"), ("deploy", "PASS"))
        with mock.patch.object(xt, "release_check", return_value=rc):
            code, _, err = self.approve(sha)
        self.assertEqual(code, 0, err)
        event = self.led()["history"][-1]
        self.assertEqual((event["by"], event["session"], event["criteria"]["submitted"]), ("agent", "s-1", sha))
        self.assertEqual(set(event["criteria"]["rows"]), {"deploy", "acceptance_lock"})
        self.assertEqual(self.led()["stage"], 3)
        self.assertEqual(self.stage("status")[0], 0)
        event["criteria"]["rows"].pop("deploy")
        self.assertFalse(xt._stage_recorded_criteria(event))

    def test_stage_three_needs_real_perf_and_every_row_nonfail(self):
        sha = self.prepare(3)
        self.git("push", "-q", "origin", "main")
        before = (self.repo / xt.STAGE_LEDGER).read_bytes()
        for extra, why in [([], "perf"), ([("perf", "N/A")], "perf"), ([("perf", "PASS"), ("other", "FAIL")], "other")]:
            rc = self.evidence(("acceptance_lock", "PASS"), ("deploy", "PASS"), *extra)
            with self.subTest(why=why), mock.patch.object(xt, "release_check", return_value=rc):
                code, _, err = self.approve(sha)
                self.assertEqual(code, 2, err)
                self.assertIn(why, err)
                self.assertEqual((self.repo / xt.STAGE_LEDGER).read_bytes(), before)
        rc = self.evidence(("acceptance_lock", "PASS"), ("deploy", "PASS"), ("perf", "PASS"))
        with mock.patch.object(xt, "release_check", return_value=rc):
            self.assertEqual(self.approve(sha)[0], 0)
        self.assertEqual(self.led()["status"], "completed")

    def test_unmerged_checkout_and_remote_withdrawal_do_not_run_gates(self):
        sha = self.prepare(2)
        with mock.patch.object(xt, "release_check", side_effect=AssertionError("unreviewed code executed")):
            code, _, err = self.approve(sha)
            self.assertEqual(code, 2)
            self.assertIn("chưa nằm trên nhánh chính", err)
            self.git("push", "-q", "origin", "main")
            (self.repo / "xt.yaml").write_text("stage_approval: agent\nstage_approval_max: 1\n")
            self.git("add", "-A")
            self.git("commit", "-qm", "chủ hạ trần")
            self.git("push", "-q", "origin", "main")
            self.git("checkout", "-q", "HEAD~1")
            code, _, err = self.approve(sha)
            self.assertEqual(code, 2)
            self.assertIn("ở nhánh chính", err)

    def test_missing_acceptance_lock_from_real_release_check(self):
        sha = self.prepare(2)
        self.git("push", "-q", "origin", "main")
        code, _, err = self.approve(sha)
        self.assertEqual(code, 2, err)
        self.assertIn("acceptance_lock", err)
        self.assertEqual(self.led()["status"], "awaiting_approval")

    def test_hard_keys_and_invalid_ceiling(self):
        for key, value in (("stage_approval_max", "4"), ("release_signoff_scale", "XL")):
            conf = f"{key}: {value}\n"
            (self.repo / "xt.yaml").write_text(conf)
            self.assertEqual(xt._ceiling(key, {key: value}), 0)
            self.assertEqual(xt._hard_key_lines(conf), [f"{key}={value}"])
            self.assertTrue(any(k.level == "error" and key in k.msg for k in xt._doctor_xt_yaml(self.repo, self.tmp)))

    def test_real_dev_receipt_after_submit_and_ignored_artifact_drift(self):
        from test_deploy_release_row import UNDEPLOYED, ledger, receipt

        sha = self.prepare(2)

        def checked():
            _, artifacts = xt._release_artifacts(self.repo)
            tree, head, readable = xt._release_tree(self.repo)
            subject, why = xt._release_subject(
                self.repo, artifacts, head, tree_readable=readable, tree_clean=tree["result"] == "PASS"
            )
            self.assertFalse(why)
            return {
                "head": head,
                "subject": subject,
                "promotion": {"state": "pending_human"},
                "rows": [
                    tree,
                    xt._release_row("acceptance_lock", "PASS", "A-001"),
                    *xt._release_deploy(self.repo, subject),
                ],
            }

        first = checked()
        self.assertEqual(first["rows"][-1]["result"], "FAIL")
        identity = {k: first["subject"][k] for k in ("head", "digest", "content")}
        event = receipt(subject=identity, served_digest=identity["digest"])
        ledger(self.repo, {"dev": {**UNDEPLOYED, "current": event}}, [event])
        self.git("add", "-A")
        self.git("commit", "-qm", "receipt de l’artefact soumis")
        self.git("push", "-q", "origin", "main")
        result = checked()
        self.assertEqual(result["rows"][-1]["result"], "PASS")
        with mock.patch.object(
            xt, "release_check", return_value={**result, "subject": {**result["subject"], "digest": "0" * 64}}
        ):
            code, _, err = self.approve(sha)
            self.assertEqual(code, 2, err)
            self.assertIn("digest", err)
        with mock.patch.object(xt, "release_check", return_value=result):
            code, _, err = self.approve(sha)
            self.assertEqual(code, 0, err)

    def test_offline_handoff_routes_an_enabled_stage_without_authorizing_it(self):
        import xt_flow

        self.prepare(2)
        stage = self.led()
        facts = {"stage": {"changed": [], "sha": stage["submitted"]["sha"]}}
        with mock.patch.object(xt, "_scale_origin", side_effect=AssertionError("offline")):
            action = xt_flow.next_action(self.repo, stage, facts, {}, {})
        self.assertEqual((action["action"], action["owner"]), ("check-approval-policy", "coordinator"))
        self.assertIn("xt.py stage approve --sha", action["reason"])
        (self.repo / "xt.yaml").write_text("stage_approval: agent\n")
        self.assertEqual(xt_flow.next_action(self.repo, stage, facts, {}, {})["owner"], "project-owner")

    def test_blank_note_rejection_and_moving_head_refuse_without_recording(self):
        sha = self.prepare(2)
        self.git("push", "-q", "origin", "main")
        before = (self.repo / xt.STAGE_LEDGER).read_bytes()
        rc = self.evidence(("acceptance_lock", "PASS"), ("deploy", "PASS"))
        for result, note, why in (
            (rc, "   ", "ghi tiêu chí"),
            ({**rc, "promotion": {"state": "rejected"}}, "đã kiểm", "NO-GO"),
            ({**rc, "head": "0" * 40}, "đã kiểm", "HEAD đã đổi"),
        ):
            with self.subTest(why=why), mock.patch.object(xt, "release_check", return_value=result):
                code, _, err = self.stage("approve", "--sha", sha[:12], "--note", note, agent=True)
                self.assertEqual(code, 2, err)
                self.assertIn(why, err)
                self.assertEqual((self.repo / xt.STAGE_LEDGER).read_bytes(), before)

    def test_scale_proof_rereads_local_lock_and_lost_submission_is_changed(self):
        sha = self.prepare(2)
        digest = self.led()["submitted"]["artifact_digest"]
        conf = self.repo / "xt.yaml"
        for content, why in ((b"stage_approval: human\n", "chỉ người duyệt"), (b"\xff\xfe", "decode")):
            conf.write_bytes(content)
            with self.subTest(why=why), self.assertRaisesRegex(xt.StageError, why):
                xt._stage_scale_proof(self.repo, 2, sha, digest)
        led = self.led()
        led["submitted"]["sha"] = "0" * 40  # the submitted commit no longer exists in this clone
        self.assertIsNone(xt._stage_changed(self.repo, led["submitted"]))
        with self.assertRaisesRegex(xt.StageError, "không duyệt được bản đã đổi"):
            xt._stage_approve(led, "0" * 12, xt.STAGE_AGENT_BY, "đã kiểm", self.repo)

    def test_replayed_agent_approval_without_recorded_criteria_is_invalid(self):
        sha = self.prepare(2)
        self.git("push", "-q", "origin", "main")
        with mock.patch.object(
            xt, "release_check", return_value=self.evidence(("acceptance_lock", "PASS"), ("deploy", "PASS"))
        ):
            self.assertEqual(self.approve(sha)[0], 0)
        led = self.led()
        led["history"][-1].pop("criteria")
        (self.repo / xt.STAGE_LEDGER).write_text(json.dumps(led))
        code, _, err = self.stage("status")
        self.assertNotEqual(code, 0)
        self.assertIn("thiếu session hoặc bằng chứng", err)

    def test_codex_thread_is_an_agent_and_cannot_adopt_as_human(self):
        with mock.patch.dict(os.environ, {"CODEX_THREAD_ID": "thread-123"}):
            code, _, err = self.stage("init", "--adopt", "2", "--evidence", "mốc")
            self.assertEqual(code, 2, err)
            self.assertIn("chỉ người", err)
            self.assertEqual(xt._stage_actor(), {"session": "thread-123"})

    def test_agent_without_session_records_distinct_decision_identifier(self):
        sha = self.prepare(2)
        self.git("push", "-q", "origin", "main")
        rc = self.evidence(("acceptance_lock", "PASS"), ("deploy", "PASS"))
        with mock.patch.dict(os.environ, {"AI_AGENT": "1"}), mock.patch.object(xt, "release_check", return_value=rc):
            code, _, err = self.stage("approve", "--sha", sha, "--note", "đã kiểm SHA")
        self.assertEqual(code, 0, err)
        event = self.led()["history"][-1]
        self.assertEqual((event["by"], event["session"], event["agent_environment"]), ("agent", "", "AI_AGENT"))
        self.assertRegex(event["decision_id"], "^[a-f0-9]{32}$")
        self.assertEqual(self.stage("status")[0], 0)

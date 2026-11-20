"""D-526: machine signoffs and human waivers carry distinct, subject-bound evidence."""

import datetime as dt
import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_release_signoff as fixture

import xt
import xt_scale

ROW20 = "| 20 | BLOCKER (M/L) | Người đã thử | — | real-path | <bản/URL đã thử, ngày> | <tên · ngày — bắt buộc> |"
HEX = "f" * 64


class ScaleSignTest(fixture.SignoffRepo):
    def prepare(self, scale="M", limit="M", row=ROW20):
        self.blueprint(scale)
        conf = self.proj / "xt.yaml"
        conf.write_text(f"release_signoff: agent\nrelease_signoff_scale: {limit}\n")
        self.doc.write_text(
            fixture.GO_DOC.replace("## 4.", row + "\n\n## 4.").replace("## 4.", f"subject: digest {HEX}\n\n## 4.")
        )
        self.git("add", "-A")
        self.git("commit", "-qm", "ứng viên ở nhánh chính")
        self.git("push", "-q", "origin", "main")
        head = self.git("rev-parse", "HEAD").strip()
        self.report = fixture.rc(subject={**fixture.SUBJECT, "head": head, "digest": HEX})
        self.report.update(
            head=head,
            rows=[xt._release_row(key, "PASS", f"{key} verified") for key, _ in xt.RELEASE_RUN_KEYS]
            + [xt._release_row("deploy", "PASS", HEX), xt._release_row("acceptance_lock", "PASS", "A-001, A-002")],
        )

    def sign(self):
        return xt.release_sign(self.proj, "", "kiểm đúng ứng viên", self.report)

    def rejects(self, why):
        original = self.doc.read_bytes()
        with self.assertRaisesRegex(xt.ReleaseSignError, why):
            self.sign()
        self.assertEqual(original, self.doc.read_bytes())

    def test_m_signs_and_binds_simulated_evidence(self):
        self.prepare()
        self.sign()
        doc = self.doc.read_text()
        for value in (
            "MÁY MÔ PHỎNG",
            "chưa có người dùng thật dùng thử",
            HEX,
            "A-001, A-002",
            "rollback PASS",
            "| agent | GO |",
        ):
            self.assertIn(value, doc)
        subject = self.report["subject"]
        result = xt._release_promotion(self.proj, [], [], subject)
        self.assertEqual((result["state"], result["by"], result.get("simulated")), ("approved", ["agent"], True))
        self.doc.write_text(doc.replace("A-001, A-002", "A-999"))
        self.assertEqual(xt._release_promotion(self.proj, [], [], subject)["state"], "pending_human")

    def test_missing_or_waived_operational_evidence_and_partial_ids_refuse(self):
        self.prepare()
        for key in ("deploy", "acceptance_lock", *(key for key, _ in xt.RELEASE_RUN_KEYS)):
            row = next(r for r in self.report["rows"] if r["id"] == key)
            with self.subTest(key=key):
                row["result"] = "N/A"
                self.report["waived"] = {key: {"by": "Người thử"}}
                self.rejects(key)
                row["result"] = "PASS"
        self.report["rows"][-1]["evidence"] = "PASS"
        self.rejects("ID bộ nghiệm thu")

    def test_human_result_never_replaced_including_failure(self):
        self.prepare(row=ROW20.replace("| — |", "| FAIL |"))
        self.rejects("dòng 20 đã có kết quả của người")

    def test_unmerged_head_cannot_sign_and_remote_downgrade_wins(self):
        self.prepare()
        self.git("checkout", "-qb", "feature")
        (self.proj / "thing").write_text("chưa duyệt")
        self.git("add", "-A")
        self.git("commit", "-qm", "chưa merge")
        head = self.git("rev-parse", "HEAD").strip()
        self.report["head"] = self.report["subject"]["head"] = head
        self.rejects("chưa nằm trên nhánh chính")
        self.git("checkout", "-q", "main")
        conf = self.proj / "xt.yaml"
        conf.write_text(conf.read_text().replace("scale: M", "scale: S"))
        self.git("add", "-A")
        self.git("commit", "-qm", "chủ hạ trần")
        self.git("push", "-q", "origin", "main")
        self.git("checkout", "-q", "HEAD~1")
        self.report["head"] = self.report["subject"]["head"] = self.git("rev-parse", "HEAD").strip()
        self.rejects("ở nhánh chính")

    def test_l_closed_when_window_unmeasured(self):
        self.prepare("L", "L")
        self.rejects("đo được escaped trong 14 ngày")

    def test_human_waiver_requires_full_signed_reason_and_valid_subject(self):
        self.prepare()
        day = dt.datetime.now(dt.timezone.utc).date().isoformat()
        missing = [xt._release_row(key, "N/A", "chưa khai") for key in ("perf", "prod_switch")]
        waived = lambda: xt._human_na_waivers(self.proj, missing, self.report["subject"])
        raw = self.doc.read_text()
        for signer, dec, valid in [("agent", "GO", False), ("Human", "NO-GO", False), ("Human", "GO", True)]:
            with self.subTest(signer=signer, dec=dec):
                signature = f"| Miễn perf: thư viện chạy ngoại tuyến | {signer} | {dec} | {day} |"
                self.doc.write_text(xt._sign_insert(raw, signature, ""))
                result = waived()
                self.assertEqual(set(result), {"perf"} if valid else set())
                if valid:
                    self.assertEqual(result["perf"]["reason"], "thư viện chạy ngoại tuyến")
        self.doc.write_text(self.doc.read_text().replace(HEX, "0" * 64))
        self.assertEqual(waived(), {})

    def test_protect_partial_human_entry_hidden_or_duplicate_row(self):
        self.prepare()
        evidence = {r["id"]: r["evidence"] for r in self.report["rows"]}
        for row in (
            ROW20 + "\n" + ROW20,
            "<!--\n" + ROW20 + "\n-->",
            ROW20.replace("<bản/URL đã thử, ngày>", "người đang thử"),
        ):
            with self.subTest(row=row), self.assertRaises(ValueError):
                xt_scale.simulate(row, xt._markdown_shown(row), "M", HEX, evidence, "Agent")

    def test_l_requires_zero_over_fixed_window(self):
        self.prepare("L", "L")
        with mock.patch.object(xt, "_sign_escaped", return_value=[10]):
            self.rejects("#10")
        with mock.patch.object(xt, "_sign_escaped", return_value=[]):
            self.sign()
        self.assertIn("MÁY MÔ PHỎNG L", self.doc.read_text())

    def test_measured_defects_include_audit_and_reverts_not_reverted_revert(self):
        end = dt.datetime(2026, 11, 20, tzinfo=dt.timezone.utc)
        start = end - dt.timedelta(days=14)
        scan = "+| 4 | TEST | Tests | đã quét | " + "a" * 40 + " | 2026-11-19 | ok |"
        audit = "+| AUD-TEST-123 | 🟠 | mở | lỗi do #10 |"
        old = "-| AUD-TEST-125 | 🔴 | mở | do #14 |"
        revert = lambda n, body: dict(
            number=n, updated_at=end.isoformat(), merged_at=end.isoformat(), title='Revert "x"', body=body
        )
        api = {
            "repos/o/r/pulls?state=closed&sort=updated&direction=desc&per_page=100&page=1": [
                revert(13, "Reverts #12"),
                revert(12, "This reverts commit abcdef0."),
            ],
            "repos/o/r/commits/abcdef0/pulls": [{"number": 11}],
            "repos/o/r/pulls/11": {"number": 11, "title": "fix: original", "merged_at": start.isoformat()},
            "repos/o/r/pulls/12": revert(12, "Reverts #11"),
        }
        measure = lambda patch: xt_scale.escaped_window("o/r", api.get, xt.PR_REVERT_RE, patch, start, end)
        self.assertEqual(measure("\n".join((scan, audit, old))), [10, 11])
        self.assertIsNone(measure(audit))
        amended = "-| AUD-TEST-130 | 🟠 | mở | do #88 |\n+| AUD-TEST-130 | 🟠 | đã sửa | do #88 |"
        self.assertEqual(measure(scan + "\n" + amended), [11])
        api["repos/o/r/pulls?state=closed&sort=updated&direction=desc&per_page=100&page=1"] = []
        self.assertEqual(measure(scan), [])

    def test_l_measure_reads_real_remote_history_and_incomplete_github_is_unknown(self):
        self.prepare("L", "L")
        today = dt.datetime.now(dt.timezone.utc).date().isoformat()
        audit = self.proj / xt.RELEASE_SIGN_STATUS
        audit.write_text(
            "| 2 | TEST | Tests | đã quét | " + self.report["head"] + f" | {today} | ok |\n"
            "| AUD-TEST-126 | 🟠 | mở | do #21 |\n"
        )
        self.git("add", "-A")
        self.git("commit", "-qm", "audit đã quét")
        self.git("push", "-q", "origin", "main")
        with mock.patch.object(xt, "github_origin_slug", return_value="o/r"):
            with mock.patch.object(xt, "_gh_api_once", return_value=[[]]) as gets:
                self.assertEqual(xt._sign_escaped(self.proj), [21])
                self.assertEqual(gets.call_args.kwargs["host"], "github.com")
            with mock.patch.object(xt, "_gh_api_once", side_effect=xt.PrInputError("offline")):
                self.assertIsNone(xt._sign_escaped(self.proj))

    def test_remote_human_result_written_after_candidate_is_preserved(self):
        self.prepare()
        self.doc.write_text(self.doc.read_text().replace("| — |", "| FAIL |"))
        self.git("add", "-A")
        self.git("commit", "-qm", "người thử vừa ghi FAIL")
        self.git("push", "-q", "origin", "main")
        self.git("checkout", "-q", "HEAD~1")
        self.rejects("GO-NO-GO đã đổi trên nhánh chính")

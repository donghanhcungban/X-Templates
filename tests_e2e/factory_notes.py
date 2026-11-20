"""Giao một repo ghi chú mới từ pack-clean, dựa trên preview Compose đã chạy thật."""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tests_e2e.verify_factory_pilot import verify

FIX = ROOT / "tests_e2e/notes"
XT = [sys.executable, ".xtemplates/scripts/xt.py"]
SPEC = "docs/specs/SPEC-notes.md"
SUITE = "acceptance/notes-journey.py"
PLAN = "docs/autopilot/PLAN-notes.md"
GATE = ["python3", SUITE]
LEDGER = "docs/ops/DEPLOYS.json"
STAGE = "docs/autopilot/STAGE.json"
DECISIONS = "docs/autopilot/DECISIONS.md"
CHECKLIST = "docs/ops/SETUP-ONCE.md"
DEFAULTS = {
    "Vấn đề": "Ghi chú cần còn nguyên khi mở lại sổ.",
    "Người dùng": "Thành viên của một nhóm nội bộ.",
    "Một chỉ số": "Tỷ lệ tạo và đọc lại đúng nội dung trong phiên mới.",
    "Không làm": "Dữ liệu thật, chia sẻ liên nhóm và triển khai production.",
}


def run(app, *args):
    result = subprocess.run(
        args,
        cwd=app,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(app)},
        check=False,
        text=True,
        stdout=subprocess.PIPE,
    )
    if result.returncode:
        print(result.stdout[-3500:], file=sys.stderr)
        result.check_returncode()
    return result.stdout.strip()


def commit(app, reason):
    run(app, "git", "add", "--all")
    run(app, "git", "commit", "-qm", reason)
    return run(app, "git", "rev-parse", "HEAD")


def copy(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)


def locked(app, baseline):
    result = run(
        app, sys.executable, str(ROOT / "scripts/xt_acceptance.py"), "check", "--base", baseline, "--project", str(app)
    )
    check = json.loads(result)
    if check["status"] != "unchanged":
        raise ValueError("Bộ nghiệm thu đã đổi")
    return check


def checked_junit(app):
    cases = ElementTree.parse(app / "reports/acceptance.xml").getroot().findall("testcase")
    if sorted(t.get("name") for t in cases) != ["S-101", "S-102", "S-103", "S-104"] or any(len(t) for t in cases):
        raise ValueError("JUnit thiếu tình huống hoặc có ca thất bại")


def prepare(app, state):
    state.mkdir()
    if run(app, "git", "rev-list", "--count", "HEAD") != "1" or run(app, "git", "remote"):
        raise ValueError("Cần một repo mới từ --new, chưa có remote")
    for src, dest in (
        ("SPEC-notes.md", SPEC),
        ("notes-journey.py", SUITE),
        ("PLAN-notes.md", PLAN),
        ("SETUP-ONCE.md", CHECKLIST),
    ):
        copy(FIX / src, app / dest)
    project = app / "PROJECT.md"
    source = project.read_text()
    ds = []
    for n, (label, value) in enumerate(DEFAULTS.items(), 1):
        source, count = re.subn(
            r"^- " + label + r":$",
            "- " + label + ": " + value + " (mặc định khung — chưa chủ xác nhận)",
            source,
            flags=re.M,
        )
        if count != 1:
            raise ValueError(f"Thiếu trường {label} trong PROJECT.md")
        ds.append(f"### D-{n:03d} · {label}\n\n{value}\n")
    project.write_text(source)
    (app / DECISIONS).write_text(
        "# Quyết định pilot\n\n" + "\n".join(ds) + "\n### D-005 · Quy mô\n\nChọn S cho bản dev dùng dữ liệu mẫu.\n"
        "### D-006 · Sổ có sẵn trong gói\n\nChốt SPEC và test độc lập trước khi tùy biến.\n"
    )
    (app / ".gitignore").write_text((app / ".gitignore").read_text() + "\n/reports/acceptance.xml\n")
    config = app / "xt.yaml"
    text = re.sub(r"^acceptance:.*$", "acceptance: python3 " + SUITE, config.read_text(), flags=re.M)
    text = re.sub(r"^acceptance_report:.*$", "acceptance_report: reports/acceptance.xml", text, flags=re.M)
    if re.search(r"^acceptance_paths:", text, flags=re.M):
        text = re.sub(r"^acceptance_paths:.*$", "acceptance_paths: " + SUITE, text, flags=re.M)
    else:
        text += "\nacceptance_paths: " + SUITE + "\n"
    config.write_text(text)
    (app / "docs/autopilot/ACCEPTANCE.paths").write_text(f"{SPEC}\n{SUITE}\nxt.yaml\n")
    baseline = commit(app, "test: chốt SPEC và nghiệm thu sổ ghi chú trước khi tùy biến")
    (state / "baseline").write_text(baseline)
    locked(app, baseline)
    run(app, "pnpm", "build")
    run(app, *XT, "deploy", "run", "--env", "dev")
    run(app, *XT, "acceptance", "lock", "--spec", SPEC, "--author", "acceptance-author", "--existing", "D-006")
    lock = json.loads((app / "docs/autopilot/ACCEPTANCE.json").read_text())["locks"]
    if len(lock) != 1 or lock[0]["cases"] != 4 or lock[0]["head"] != baseline:
        raise ValueError("Thiếu bốn ca trên starter thật trước lúc tùy biến")
    checked_junit(app)
    ui = app / "src/notes-ui/index.html"
    html = ui.read_text()
    if html.count("Sổ tay nhóm") != 2:
        raise ValueError("Không nhận diện được màn hình starter để đặt tên sổ")
    ui.write_text(html.replace("Sổ tay nhóm", "Sổ ghi chú nội bộ"))
    commit(app, "feat: đặt tên sổ ghi chú nội bộ trên màn hình đăng nhập")
    run(app, *XT, "loop", "init", "--plan", PLAN)


def finish(app, state, out, started):
    out.mkdir()
    proof = out / "FACTORY-PILOT-1"
    proof.mkdir()
    baseline = (state / "baseline").read_text()
    locked(app, baseline)
    run(app, *XT, "loop", "record", "--task", "T-001", "--", *GATE)
    commit(app, "test: ghi cổng nghiệm thu MVP và receipt dev")
    # Ticking the plan changes the product tree. Obtain a receipt for the final tree, then commit just its machine ledger.
    run(app, *XT, "deploy", "run", "--env", "dev")
    run(app, sys.executable, "tests_e2e/pack_preview.py", "--output", str(proof / "preview-browser.json"))
    receipt = json.loads((app / LEDGER).read_text())["envs"]["dev"]["current"]
    final = commit(app, "chore: lưu receipt dev của cây đã nghiệm thu")
    if run(app, "git", "diff", "--name-only", receipt["subject"]["head"], final).splitlines() != [LEDGER]:
        raise ValueError("SHA sắp trình khác ứng viên ngoài sổ triển khai")
    check = locked(app, baseline)
    if not json.loads(run(app, *XT, "acceptance", "check", "--json"))["ok"]:
        raise ValueError("Kiểm tra khoá nghiệm thu thất bại")
    run(app, *XT, "loop", "verify", "--all")
    verified = json.loads((app / ".autopilot/verified.json").read_text())
    if not verified["ok"] or not any(
        r["task"] == "T-001" and r["exit_code"] == 0 and not r.get("kept") for r in verified["results"]
    ):
        raise ValueError("Cổng nghiệm thu nghiệp vụ chưa chạy lại trên cây cuối")
    checked_junit(app)
    run(
        app,
        *XT,
        "stage",
        "submit",
        "--evidence",
        "Bốn ca nghiệm thu độc lập xanh trên Chromium/PostgreSQL; dev " + receipt["subject"]["digest"],
    )
    stage = json.loads((app / STAGE).read_text())
    if (stage["stage"], stage["status"], stage["submitted"]["sha"]) != (1, "awaiting_approval", final):
        raise ValueError("Sổ không ở giai đoạn 1 chờ duyệt trên đúng commit")
    for src, name in (
        (LEDGER, "DEPLOYS.json"),
        (STAGE, "STAGE.json"),
        ("docs/autopilot/ACCEPTANCE.json", "ACCEPTANCE.json"),
        (CHECKLIST, "SETUP-ONCE.md"),
        ("reports/acceptance.xml", "acceptance.xml"),
    ):
        copy(app / src, proof / name)
    commit(app, "chore: bàn giao MVP đang chờ duyệt")
    bundle = out / "so-ghi-chu.bundle"
    run(app, "git", "bundle", "create", str(bundle), "refs/heads/main", "HEAD")
    run(app, "git", "bundle", "verify", str(bundle))
    with bundle.open("rb") as stream:
        bundle_digest = hashlib.file_digest(stream, "sha256").hexdigest()
    check.update(
        bundle_sha256=bundle_digest,
        implementation_head=receipt["subject"]["head"],
        submitted_head=final,
        started=started.read_text().strip(),
    )
    (proof / "handoff.json").write_text(json.dumps(check, ensure_ascii=False, indent=2) + "\n")
    idea = (app / "PROJECT.md").read_text().split("## Ý tưởng gốc\n\n> ", 1)[1].split("\n\n", 1)[0]
    report = out / "FACTORY-PILOT-1.md"
    runs = [json.loads(line) for line in (app / ".autopilot/runs.jsonl").read_text().splitlines()]
    if not runs or any(row["task"] != "T-001" for row in runs):
        raise ValueError("Thiếu lịch sử chạy task sản phẩm của pilot")
    (proof / "task-gates.json").write_text(json.dumps(runs, indent=2) + "\n")
    summary = dict(
        idea=idea,
        started=check["started"],
        head=receipt["subject"]["head"],
        digest=receipt["subject"]["digest"],
        tasks=len({row["task"] for row in runs}),
        failed_gates=sum(row["exit_code"] != 0 for row in runs),
        human_questions=0,
        cost_usd=None,
    )
    report.write_text(
        "# Pilot 1 · Sổ ghi chú nội bộ\n\n```json\n" + json.dumps(summary, indent=2, ensure_ascii=False) + "\n```\n"
    )
    seconds = verify(report)
    with report.open("a") as stream:
        stream.write(
            f"\nTừ lúc tạo repo đến receipt của cây cuối mất **{seconds:g} giây**. "
            "Một task sản phẩm T-001 chạy qua bốn tình huống JUnit. "
            "Chromium và PostgreSQL chạy trong runner với hai tài khoản mẫu. "
            "Đăng nhập sai bị từ chối, người viết đọc lại ghi chú trong phiên mới và nhóm khác không thấy ghi chú.\n\n"
            "D-001 đến D-005 ghi bốn giả định và việc chọn quy mô S. D-006 ghi phạm vi ứng dụng dùng lại từ starter. "
            "Bộ nghiệm thu được soạn độc lập, ghim trước khi đổi tên sổ. Thời gian này tính cả dựng hạ tầng và chạy các cổng CI. "
            "Mục cổng đỏ đếm task sản phẩm; phép thử quay lui mong đợi lỗi ứng viên B.\n\n"
            "Repo đã đóng bundle và kiểm lại. Bản dev chỉ mở trên loopback runner. Giai đoạn 1 đang chờ duyệt. "
            "Hai giai đoạn sau và phát hành production chưa diễn ra trên sản phẩm này.\n\n"
            f"[Lượt chạy GitHub]({receipt['runner']['run_url']}) · [Cổng sản phẩm](FACTORY-PILOT-1/task-gates.json) · "
            "[Receipt](FACTORY-PILOT-1/DEPLOYS.json) · [Trình duyệt](FACTORY-PILOT-1/preview-browser.json) · "
            "[Nghiệm thu](FACTORY-PILOT-1/acceptance.xml) · [Sổ giai đoạn](FACTORY-PILOT-1/STAGE.json) · "
            "[Bàn giao](FACTORY-PILOT-1/handoff.json) · [Checklist](FACTORY-PILOT-1/SETUP-ONCE.md)\n"
        )
    verify(report)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "finish"])
    parser.add_argument("--app", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--started-file", type=Path)
    a = parser.parse_args()
    if a.action == "prepare":
        prepare(a.app.resolve(), a.state.resolve())
    else:
        if not a.output or not a.started_file:
            parser.error("finish cần --output và --started-file")
        finish(a.app.resolve(), a.state.resolve(), a.output.resolve(), a.started_file.resolve())

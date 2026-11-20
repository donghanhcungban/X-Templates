"""Nghiệm thu độc lập SPEC-notes, chạy trên bản dev đang phục vụ."""
import hashlib
import json
import os
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright, expect

BASE = os.environ.get("XT_NOTES_URL", "http://127.0.0.1:4317")
SOURCE = "acceptance/notes-journey.py"


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def login(page, account):
    page.goto(BASE)
    page.locator("#email").fill(account["email"])
    page.locator("#password").fill(account["password"])
    with page.expect_response(lambda r: urlsplit(r.url).path == "/v1/login") as reply:
        page.locator("#login-form").get_by_role("button").click()
    return reply.value


def local_context(browser):
    if urlsplit(BASE).hostname not in ("127.0.0.1", "::1", "localhost") or urlsplit(BASE).scheme != "http":
        raise ValueError("Đích dev phải dùng HTTP trên loopback")
    context = browser.new_context(service_workers="block")
    expected = urlsplit(BASE)
    def fence(route):
        target = urlsplit(route.request.url)
        if (target.scheme, target.hostname, target.port) == (expected.scheme, expected.hostname, expected.port):
            response = route.fetch(max_redirects=0)
            if 300 <= response.status < 400:
                route.abort()
            else:
                route.fulfill(response=response)
        else:
            route.abort()
    context.route("**/*", fence)
    context.route_web_socket("**/*", lambda socket: socket.close(code=1000, reason="WebSocket ngoài hợp đồng nghiệm thu"))
    return context


def journey(browser, run):
    accounts = json.loads(subprocess.check_output(["node", "scripts/dev-preview.mjs", "credentials"], text=True))
    owner = accounts["owner"]
    unique = "Ghi chú nghiệm thu " + uuid.uuid4().hex
    first = local_context(browser)
    page = first.new_page()

    def signin():
        wrong = login(page, {**owner, "password": uuid.uuid4().hex})
        require(wrong.status == 401, "Mật khẩu sai phải trả 401")
        expect(page.locator("#note-form")).to_be_hidden()
        require(login(page, owner).status == 200, "Đăng nhập đúng phải trả 200")
        expect(page.locator("#note-form")).to_be_visible()

    run("S-101", signin)
    def create():
        page.locator("#note-body").fill(unique)
        with page.expect_response(lambda r: urlsplit(r.url).path == "/v1/notes" and r.request.method == "POST") as res:
            page.locator("#note-form").get_by_role("button").click()
        note = res.value.json()
        require(res.value.status == 201 and note.get("body") == unique and note.get("id"), "Kết quả tạo ghi chú sai")
        expect(page.locator("#notes-list")).to_contain_text(unique)
        return note["id"]

    identifier = run("S-102", create)
    first.close()
    def reopen():
        require(identifier, "Thiếu mã ghi chú ở S-102")
        for role in ("owner", "guest"):
            context = local_context(browser)
            try:
                other = context.new_page()
                reply = login(other, accounts[role])
                require(reply.status == 200, "Không đăng nhập được vào phiên mới")
                headers = {"Authorization": "Bearer " + reply.json()["token"]}
                response = context.request.get(BASE + "/v1/notes", headers=headers, max_redirects=0)
                require(response.status == 200, "Không đọc được danh sách")
                notes = response.json()["notes"]
                matches = [n for n in notes if n["id"] == identifier]
                if role == "owner":
                    require(len(matches) == 1 and matches[0]["body"] == unique, "Không tìm lại được ghi chú")
                    expect(other.locator("#notes-list")).to_contain_text(unique)
                else:
                    require(not matches, "Ghi chú xuất hiện trong danh sách của nhóm khác")
                    direct = context.request.get(BASE + "/v1/notes/" + str(identifier), headers=headers, max_redirects=0)
                    require(direct.status == 404, "Nhóm khác đọc được ghi chú qua mã")
                    expect(other.locator("#notes-list")).not_to_contain_text(unique)
            finally:
                context.close()

    run("S-103", reopen)
    def artifact():
        require(urlsplit(BASE).hostname in ("127.0.0.1", "::1", "localhost"), "Đích dev phải ở loopback")
        context = local_context(browser)
        page = context.new_page()
        try:
            response = page.request.get(BASE + "/healthz", max_redirects=0)
            receipt = json.loads(Path("docs/ops/DEPLOYS.json").read_text())["envs"]["dev"]["current"]
            with Path("dist/app.tgz").open("rb") as source:
                expected = hashlib.file_digest(source, "sha256").hexdigest()
            health = response.json()
            require(response.status == 200 and health["status"] == "ok", "Đích dev chưa khỏe")
            artifacts = [a for a in receipt["artifacts"] if a["path"] == "dist/app.tgz"]
            require(len(artifacts) == 1 and artifacts[0]["sha256"] == expected, "Artifact không khớp receipt")
            subject = hashlib.sha256(("dist/app.tgz\0" + expected + "\n").encode()).hexdigest()
            require(subject == health["digest"] == receipt["subject"]["digest"], "Digest đích phục vụ lệch")
        finally:
            context.close()
    run("S-104", artifact)


def main():
    report = ET.Element("testsuite", name="SPEC-notes")
    def run(scenario, operation):
        case = ET.SubElement(report, "testcase", name=scenario, file=SOURCE)
        try:
            return operation()
        except Exception as exc:
            ET.SubElement(case, "failure").text = str(exc)
            return None
    try:
        with sync_playwright() as engine:
            browser = engine.chromium.launch(executable_path=os.environ.get("XT_E2E_CHROMIUM"))
            journey(browser, run)
            browser.close()
    except Exception as exc:
        ET.SubElement(ET.SubElement(report, "testcase", name="Dựng trình duyệt", file=SOURCE), "error").text = str(exc)
    path = Path("reports/acceptance.xml")
    path.parent.mkdir(exist_ok=True)
    report.set("tests", str(len(report.findall("testcase"))))
    report.set("failures", str(len(report.findall(".//failure"))))
    report.set("errors", str(len(report.findall(".//error"))))
    ET.ElementTree(report).write(path, encoding="utf-8", xml_declaration=True)
    return int(bool(report.findall(".//failure") or report.findall(".//error")))


if __name__ == "__main__":
    sys.exit(main())

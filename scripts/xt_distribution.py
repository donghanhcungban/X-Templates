"""Authenticated release sources and pull-based framework upgrades."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tempfile
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

CANONICAL = "www-donghanhcungban-org/X-Templates"
TAG = re.compile(r"v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")
SLUG = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9][A-Za-z0-9._-]*")
UPGRADE_BRANCH = "chore/xt-upgrade"
MANIFEST = ".xtemplates/manifest.json"
WITHDRAWN = "docs/ops/WITHDRAWN-VERSIONS.txt"
# WF-DOC-021: chữ hiển thị trên GitHub của dự án đích mô tả dự án; khung chỉ có MỘT ghi chú nguồn (`adopted_note`).
ADOPTED = re.compile(r"Áp dụng từ phiên bản v?\d+\.\d+\.\d+ của dự án X-Templates", re.I)
MENTION = re.compile(r"x-templates", re.I)


def adopted_note(version: str, repo: object = None) -> str:
    """Ghi chú nguồn duy nhất ở dự án đích (`.xtemplates/README.md`, chân trang README của `--new`); repo sai dạng → CANONICAL."""
    slug = repo if isinstance(repo, str) and SLUG.fullmatch(repo) else CANONICAL
    return f"Áp dụng từ phiên bản v{version.removeprefix('v')} của dự án X-Templates (https://github.com/{slug})."


def stray_mentions(text: str) -> list[int]:
    """Số dòng (từ 1) nhắc X-Templates ngoài dòng ghi chú nguồn hợp lệ."""
    return [n for n, line in enumerate(text.splitlines(), 1) if MENTION.search(line) and not ADOPTED.search(line)]


class DistributionError(ValueError):
    def __init__(self, message: str, code: int = 3):
        super().__init__(message)
        self.code = code


def command(
    cwd: Path, *argv: str, check: bool = True, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=300, env=env)
    if check and result.returncode:
        raise DistributionError(f"{argv[0]} {argv[1]}: {result.stderr.strip() or 'lệnh thất bại'}")
    return result


def read_manifest(base: Path) -> dict[str, Any]:
    contents = json.loads((base / MANIFEST).read_text(encoding="utf-8"))
    if not isinstance(contents, dict):
        raise DistributionError("manifest cần là object")
    return contents


def repo_slug(url: str) -> str:
    slug = url.removeprefix("https://github.com/").removeprefix("git@github.com:").removesuffix(".git")
    if not url.startswith(("https://github.com/", "git@github.com:")) or not SLUG.fullmatch(slug):
        raise DistributionError("nguồn cài cần là repository trên github.com")
    return slug


def framework_repo(manifest: dict[str, Any]) -> str:
    source = manifest.get("source", {})
    repo = source.get("repo", CANONICAL) if isinstance(source, dict) else None
    if not isinstance(repo, str) or not SLUG.fullmatch(repo):
        raise DistributionError("source.repo không hợp lệ")
    return repo


def clone_source(temp: Path, repo: str) -> Path:
    if not SLUG.fullmatch(repo):
        raise DistributionError("repo cần có dạng owner/name", 2)
    git = temp / "upstream.git"
    # Bare clone fetches all tags and the default branch without checking out any upstream content.
    command(temp, "git", "clone", "--quiet", "--bare", "--", f"https://github.com/{repo}.git", str(git))
    return git


def verified_archive(git: Path, repo: str, tag: str, temp: Path, promotion: bool = False) -> tuple[str, Path]:
    if not TAG.fullmatch(tag):
        raise DistributionError("tag cần có dạng vX.Y.Z", 2)
    ref = f"refs/tags/{tag}"
    git_type = command(git, "git", "cat-file", "-t", ref, check=False)
    if git_type.stdout.strip() != "tag":
        raise DistributionError(f"{tag} thiếu annotated tag", 1)
    head = command(git, "git", "rev-parse", f"{ref}^{{commit}}").stdout.strip()
    ancestry = command(git, "git", "merge-base", "--is-ancestor", head, "HEAD", check=False)
    if ancestry.returncode:
        raise DistributionError(f"{tag} chưa xác nhận trong lịch sử nhánh chính", 1 if ancestry.returncode == 1 else 3)
    version = command(git, "git", "show", f"{head}:VERSION", check=False)
    if version.returncode or version.stdout.strip() != tag[1:]:
        raise DistributionError(f"VERSION ở {tag} không khớp tên tag", 1)
    artifact = temp / f"X-Templates-{tag}.tar.gz"
    command(git, "git", "archive", "--format=tar.gz", f"--prefix=X-Templates-{tag}/", "-o", str(artifact), head)
    verify_signature(temp, repo, artifact)
    if promotion:
        with artifact.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        receipt = temp / f"X-Templates-{tag}.promotion.json"
        receipt.write_bytes(
            (
                json.dumps(
                    {"repo": repo.casefold(), "tag": tag, "commit": head, "sha256": digest, "promotion": "approved"},
                    separators=(",", ":"),
                )
                + "\n"
            ).encode("ascii")
        )
        verify_signature(temp, repo, receipt)
    return head, artifact


def public_bundles(temp: Path, repo: str, artifact: Path) -> Path:
    """Fetch the bundles associated with the live public repository, then let gh verify offline without a login."""
    with artifact.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    output = temp / (artifact.name + ".jsonl")
    page = 1
    with output.open("w", encoding="utf-8") as dest:
        while True:
            url = f"https://api.github.com/repos/{repo}/attestations/sha256:{digest}?per_page=100&page={page}"
            try:
                with urlopen(Request(url, headers={"Accept": "application/vnd.github+json"}), timeout=30) as response:
                    payload = json.load(response)
                    records = payload.get("attestations") if isinstance(payload, dict) else None
            except HTTPError as exc:
                if exc.code == 404:
                    raise DistributionError(f"{artifact.name}: không có attestation", 1) from exc
                raise
            if not isinstance(records, list):
                raise DistributionError("GitHub trả danh sách attestation không hợp lệ")
            for record in records:
                if not isinstance(record, dict) or not isinstance(record.get("bundle"), dict):
                    raise DistributionError("GitHub trả attestation bundle không hợp lệ")
                dest.write(json.dumps(record["bundle"]) + "\n")
            if len(records) < 100:
                break
            page += 1
    if not output.stat().st_size:
        raise DistributionError(f"{artifact.name}: không có attestation", 1)
    return output


def verify_signature(temp: Path, repo: str, artifact: Path) -> None:
    signer = f"https://github.com/{repo}/.github/workflows/release-tag.yml@refs/heads/main"
    offline = (
        []
        if os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
        else ["--bundle", str(public_bundles(temp, repo, artifact))]
    )
    verify = command(
        temp,
        "gh",
        "attestation",
        "verify",
        str(artifact),
        "--repo",
        repo,
        "--cert-identity",
        signer,
        "--source-ref",
        "refs/heads/main",
        *offline,
        check=False,
    )
    if verify.returncode:
        diagnostic = verify.stderr.strip()
        missing = re.search(
            r"no attestations? (?:were )?found|no matching attestations|failed to verify any attestations",
            diagnostic,
            re.I,
        )
        raise DistributionError(
            f"{artifact.name}: chưa xác minh attestation của workflow phát hành. {diagnostic}", 1 if missing else 3
        )


def matches_checkout(src: Path, tag: str, archive: Path) -> bool:
    """Git index flags and checkout filters can hide differences. Read the actual files that install.py will copy."""
    prefix = f"X-Templates-{tag}/"
    paths = set(command(src, "git", "ls-files", "-z").stdout.split("\0")[:-1])
    with tarfile.open(archive, "r:gz") as bundle:
        for member in bundle:
            if member.isdir():
                continue
            name = member.name.removeprefix(prefix)
            paths.discard(name)
            path = src / name
            if member.issym():
                if not path.is_symlink() or os.readlink(path) != member.linkname:
                    return False
            else:
                data = bundle.extractfile(member)
                if data is None or path.is_symlink() or data.read() != path.read_bytes():
                    return False
    return not paths


def install_source(src: Path) -> dict[str, Any]:
    """A label cannot confer provenance. Untracked/modified installer input also keeps the receipt unverified."""
    source: dict[str, Any] = {"untagged": "unknown"}
    try:
        top = command(src, "git", "rev-parse", "--show-toplevel").stdout.strip()
        if Path(top).resolve() != src.resolve():
            return source
        head = command(src, "git", "rev-parse", "HEAD").stdout.strip()
        source = {"untagged": head}
        version = (src / "VERSION").read_text(encoding="utf-8").strip()
        tag = "v" + version
        if not TAG.fullmatch(tag) or tag not in command(src, "git", "tag", "--points-at", head).stdout.splitlines():
            return source
        repo = repo_slug(command(src, "git", "remote", "get-url", "origin").stdout.strip())
        source = {"repo": repo, "tag": tag, "commit": head, "verified": False}
        dirty = command(src, "git", "status", "--porcelain", "--ignored", "--untracked-files=all").stdout.splitlines()
        if any("/__pycache__/" not in line or not line.endswith(".pyc") for line in dirty):
            return source
        with tempfile.TemporaryDirectory() as tmp:
            temp = Path(tmp)
            signed_head, archive = verified_archive(clone_source(temp, repo), repo, tag, temp)
            source["verified"] = signed_head == head and matches_checkout(src, tag, archive)
    except OSError, ValueError, subprocess.SubprocessError:
        pass  # a normal development install remains usable offline
    return source


def tags_for_wave(git: Path, installed: str, wave: str, soak: int, now: int) -> tuple[bool, list[str]]:
    current = TAG.fullmatch("v" + installed.partition(" ")[0].strip())
    if not current or wave not in {"canary", "after-canary"} or soak < 0:
        raise DistributionError("VERSION, upgrade_wave hoặc upgrade_soak_days không hợp lệ", 2)
    present = command(git, "git", "ls-tree", "HEAD", "--", WITHDRAWN).stdout
    withdrawn = set()
    if present:
        for line in command(git, "git", "show", f"HEAD:{WITHDRAWN}").stdout.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                version = line.split()[0]
                if not TAG.fullmatch("v" + version):
                    raise DistributionError(f"{WITHDRAWN} có phiên bản không hợp lệ")
                withdrawn.add("v" + version)
    listing = command(git, "git", "for-each-ref", "--format=%(refname:strip=2) %(taggerdate:unix)", "refs/tags").stdout
    newer = False
    eligible = []
    for line in listing.splitlines():
        tag, _, age = line.partition(" ")
        match = TAG.fullmatch(tag)
        if not match:
            continue
        number = tuple(map(int, match.groups()))
        if number > tuple(map(int, current.groups())):
            newer = True
            if tag not in withdrawn and age.isdecimal() and (wave == "canary" or now - int(age) >= soak * 86400):
                eligible.append((number, tag))
    return newer, [tag for _, tag in sorted(eligible, reverse=True)]


def publish_upgrade(base: Path, repo: str, tag: str, head: str, archive: Path, temp: Path) -> None:
    """Build a reviewable PR in an isolated clone. Existing upgrade branches advance by fast-forward."""
    origin = repo_slug(command(base, "git", "remote", "get-url", "origin").stdout.strip())
    project = temp / "project"
    command(temp, "git", "clone", "--quiet", "--", f"https://github.com/{origin}.git", str(project))
    branch = command(project, "git", "branch", "--show-current").stdout.strip()
    if branch == UPGRADE_BRANCH:
        raise DistributionError("nhánh nâng khung phải khác nhánh mặc định")
    old = command(project, "git", "rev-parse", "--verify", f"refs/remotes/origin/{UPGRADE_BRANCH}", check=False)
    manifest = read_manifest(project)
    packs = manifest.get("packs", {})
    if not isinstance(packs, dict):
        raise DistributionError("manifest.packs không hợp lệ", 2)
    label = (project / ".xtemplates/VERSION").read_text(encoding="utf-8").split()[:1]
    if (
        framework_repo(manifest) != repo
        or label != (base / ".xtemplates/VERSION").read_text(encoding="utf-8").split()[:1]
    ):
        raise DistributionError("nhánh chính của dự án đã đổi nguồn hoặc phiên bản, kiểm lại trước khi nâng")
    if not old.returncode:
        # Base the new review tree on the protected default branch; retain the old bot branch as a parent.
        command(project, "git", "merge", "--no-commit", "--no-ff", "-s", "ours", old.stdout.strip())
    # Run only installer bytes from the verified archive. Never execute the default branch or a PR checkout upstream.
    with tarfile.open(archive, "r:gz") as bundle:
        bundle.extractall(temp / "release", filter="data")
    release = temp / "release" / f"X-Templates-{tag}"
    # Give product checks no bot credentials. GitHub authentication for the push/PR stays in the parent process.
    local_env = {k: v for k, v in os.environ.items() if k not in {"GH_TOKEN", "GITHUB_TOKEN", "XT_STEWARD_TOKEN"}}
    for pack in list(packs) or [None]:
        options = ["--pack", pack] if pack is not None else []
        if ".codex/hooks.json" in manifest.get("adapters", []) or manifest.get("codex_files"):
            options.extend(["--harness", "codex"])
        command(
            project, sys.executable, str(release / "scripts/install.py"), ".", "--with-github", *options, env=local_env
        )
    installed = read_manifest(project)
    installed["source"] = {"repo": repo, "tag": tag, "commit": head, "verified": True}
    (project / MANIFEST).write_text(
        json.dumps(installed, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    command(project, "git", "add", "--all")
    command(
        project, sys.executable, ".xtemplates/scripts/xt.py", "blueprint-status", "BLUEPRINT.md", "--run", env=local_env
    )
    tree = command(project, "git", "write-tree").stdout.strip()
    title = f"chore(xt): nâng khung {tag[1:]}"
    if old.returncode or tree != command(project, "git", "rev-parse", f"{old.stdout.strip()}^{{tree}}").stdout.strip():
        command(project, "git", "commit", "-m", title, env=local_env)
        command(project, "git", "push", "origin", f"HEAD:refs/heads/{UPGRADE_BRANCH}")
    body = temp / "pr-body.md"
    changes = (release / "CHANGELOG.md").read_text(encoding="utf-8")
    match = re.search(rf"^## \[{re.escape(tag[1:])}\][^\n]*\n(.*?)(?=^## |\Z)", changes, re.M | re.S)
    body.write_text(
        f"Nâng khung lên {repo}@{head} ({tag}).\n\n" + (match[1].strip() if match else tag), encoding="utf-8"
    )
    prs = json.loads(
        command(
            project,
            "gh",
            "api",
            f"repos/{origin}/pulls?state=open&base={branch}&head={origin.split('/')[0]}:{UPGRADE_BRANCH}",
        ).stdout
    )
    if prs:
        command(
            project,
            "gh",
            "pr",
            "edit",
            str(prs[0]["number"]),
            "--repo",
            origin,
            "--title",
            title,
            "--body-file",
            str(body),
        )
    else:
        command(
            project,
            "gh",
            "pr",
            "create",
            "--repo",
            origin,
            "--base",
            branch,
            "--head",
            UPGRADE_BRANCH,
            "--title",
            title,
            "--body-file",
            str(body),
        )


def run(core: Any, args: argparse.Namespace) -> int:
    base = Path.cwd()
    try:
        with tempfile.TemporaryDirectory(prefix="xt-release-") as directory:
            temp = Path(directory)
            if args.cmd == "release-verify":
                repo = args.repo
                git = clone_source(temp, repo)
                head, _ = verified_archive(git, repo, args.tag, temp)
                print(f"{repo} {args.tag} {head}: attestation hợp lệ")
                return 0
            manifest = read_manifest(base)
            repo = framework_repo(manifest)
            git = clone_source(temp, repo)
            keys = core._xt_keys(base)
            wave = keys.get("upgrade_wave", "after-canary")
            soak = int(keys.get("upgrade_soak_days", "3"))
            label = (base / ".xtemplates/VERSION").read_text(encoding="utf-8")
            newer, tags = tags_for_wave(git, label, wave, soak, int(dt.datetime.now(dt.UTC).timestamp()))
            for tag in tags:
                try:
                    head, archive = verified_archive(git, repo, tag, temp, promotion=True)
                except DistributionError as exc:
                    if exc.code != 1:
                        raise
                    print(exc, file=sys.stderr)
                    continue
                if args.upgrade_action == "check":
                    print(tag)
                    return 10
                publish_upgrade(base, repo, tag, head, archive, temp)
                print(f"PR nâng khung {tag} đã sẵn sàng")
                return 0
            print(
                "Có bản mới nhưng chưa đủ tuổi hoặc thiếu bản chưa thu hồi có attestation hợp lệ."
                if newer
                else "Không có bản mới."
            )
            return 11 if newer else 0
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(exc, file=sys.stderr)
        return exc.code if isinstance(exc, DistributionError) else 3

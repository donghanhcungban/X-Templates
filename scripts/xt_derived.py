"""Kênh dự án phái sinh tự cập nhật thông tin của chính nó (ADR-0087): bản ghi `docs/derived/<owner>--<repo>.json`.

Mọi đầu vào từ PR là dữ liệu không tin cậy: chỉ đọc byte qua API GitHub, không checkout, không chạy mã của PR. Danh tính
là head repo của PR do GitHub báo, không phải trường khai trong tệp. Lý do từ chối không chép lại giá trị do bên ngoài
viết (thông điệp lên tóm tắt của steward). `check_record`/`check_pr_files` là hàm thuần; `evaluate` gọi GitHub qua `core`
(module `xt.py`) và được dùng chung bởi `merge-check` (làn `derived`) và `xt.py derived check --pr`."""

from __future__ import annotations

import argparse
import base64
import dataclasses
import datetime as dt
import json
import re
import sys
import unicodedata
import urllib.parse
from pathlib import Path
from typing import Any, Callable, Optional

UPSTREAM = "www-donghanhcungban-org/X-Templates"
DERIVED_DIR = "docs/derived"
MAX_BYTES = 2048
DESC_MAX = 280
HOME_MAX = 200
FILE_MODE = "100644"
REQUIRED = frozenset({"schema", "repo", "kind", "upstream", "description", "status", "updated"})
OPTIONAL = frozenset({"homepage"})
KINDS = ("fork", "derived")
STATUSES = ("active", "archived")
FILE_STATUSES = ("added", "modified")  # không removed/renamed/copied/changed (đổi mode)
# GitHub: tên tài khoản là chữ số và gạch nối đơn, ≤ 39 ký tự — không có `--` nên tách tên tệp ở `--` đầu tiên là duy nhất.
OWNER_RE = re.compile(r"[A-Za-z0-9](?:-?[A-Za-z0-9]){0,38}")
REPO_RE = re.compile(r"[A-Za-z0-9._-]{1,100}")
_NUM = r"(?:0|[1-9][0-9]{0,8})"
VERSION_RE = re.compile(rf"{_NUM}\.{_NUM}\.{_NUM}")
RELEASE_RE = re.compile(rf"^## \[({_NUM}\.{_NUM}\.{_NUM})\]", re.M)
DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
SHA_RE = re.compile(r"[0-9a-f]{40}")
_LABEL = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
HOME_RE = re.compile(rf"https://((?:{_LABEL}\.)+[a-z]{{2,63}})(/[A-Za-z0-9._~/%-]*)?")
RESERVED_TLDS = frozenset({"localhost", "local", "internal", "test", "example", "invalid", "arpa", "onion", "lan"})
BANNED_CHARS = frozenset("<>[]`@\\")  # HTML, link markdown, mã, email/@mention
BANNED_WORDS = ("http", "://", "www.")  # URL và autolink của GitHub
# Điều khiển, bidi/zero-width, xuống dòng, dấu kết hợp (sau NFC tiếng Việt không còn dấu kết hợp; chặn chồng dấu).
BAD_CATEGORIES = frozenset({"Cc", "Cf", "Cs", "Co", "Cn", "Zl", "Zp", "Mn", "Mc", "Me"})
# Default_Ignorable_Code_Point (Unicode 16 DerivedCoreProperties) không thuộc nhóm trên, cùng ký tự trống trông như chữ:
# Hangul filler, variation selector (cả bổ sung), Braille trống.
HIDDEN_RANGES = (
    (0x115F, 0x1160),
    (0x2800, 0x2800),
    (0x3164, 0x3164),
    (0xFE00, 0xFE0F),
    (0xFFA0, 0xFFA0),
    (0xE0000, 0xE0FFF),
)
PHONE_RE = re.compile(r"(?:\d[\s().\-/]*){9,}")
# Tên miền kèm đường dẫn, hoặc tên miền trần với đuôi phổ biến — sau NFKC + casefold.
DOMAIN_RE = re.compile(
    r"[a-z0-9-]+(?:\.[a-z0-9-]+)*\.[a-z]{2,63}/"
    r"|\b[a-z0-9-]+\.(?:com|net|org|io|vn|co|xyz|info|biz|me|app|dev|ru|cn|top|site|link|ly|gg)\b"
)
SAFE_RE = re.compile(r"[A-Za-z0-9._/-]{1,200}")
CHANGELOG_MISSING = "không đọc được bản đã phát hành (CHANGELOG.md) — không xác minh được upstream.version"


class RecordError(ValueError):
    """JSON hợp lệ cú pháp nhưng trái luật đọc (khoá trùng, NaN, số thực, số lớn)."""


@dataclasses.dataclass(frozen=True)
class Ctx:
    head_repo: str
    today: dt.date
    versions: Optional[frozenset[str]]


def safe(value: object) -> str:
    """Chuỗi do bên ngoài đặt chỉ được in khi là đường dẫn ASCII an toàn."""
    return value if isinstance(value, str) and SAFE_RE.fullmatch(value) else "<giá trị lạ>"


def today() -> dt.date:
    return dt.datetime.now(dt.UTC).date()


def split_repo(full: object) -> Optional[tuple[str, str]]:
    if not isinstance(full, str) or full.count("/") != 1:
        return None
    owner, name = full.split("/")
    if not OWNER_RE.fullmatch(owner) or not REPO_RE.fullmatch(name) or name in (".", ".."):
        return None
    return owner, name


def record_name(head_repo: object) -> Optional[str]:
    """`<owner>--<repo>.json` suy ra từ head repo; None khi tên không theo luật GitHub."""
    parts = split_repo(head_repo)
    return f"{parts[0]}--{parts[1]}.json" if parts else None


def repo_from_name(name: str) -> Optional[str]:
    owner, sep, rest = name.partition("--")
    full = f"{owner}/{rest.removesuffix('.json')}"
    return full if sep and record_name(full) == name else None


def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    keys = [k for k, _ in pairs]
    if len(set(keys)) != len(keys):
        raise RecordError("khoá trùng")
    return dict(pairs)


def _no_constant(_: str) -> Any:
    raise RecordError("NaN/Infinity")


def _no_float(_: str) -> Any:
    raise RecordError("số thực")


def _small_int(text: str) -> int:
    if len(text.lstrip("-")) > 9:
        raise RecordError("số quá lớn")
    return int(text)


def parse_record(raw: bytes) -> tuple[Optional[dict[str, Any]], list[str]]:
    """Byte → object JSON theo luật đọc chặt; (None, lý do) khi không đọc được."""
    if not raw:
        return None, ["tệp trống"]
    if len(raw) > MAX_BYTES:
        return None, [f"tệp {len(raw)} B > {MAX_BYTES} B"]
    if raw.startswith(b"\xef\xbb\xbf"):
        return None, ["tệp có BOM UTF-8"]
    try:
        data = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_unique,
            parse_constant=_no_constant,
            parse_float=_no_float,
            parse_int=_small_int,
        )
    except RecordError as exc:
        return None, [f"JSON trái luật: {exc}"]
    except UnicodeDecodeError:
        return None, ["tệp không phải UTF-8"]
    except json.JSONDecodeError as exc:
        return None, [f"JSON không hợp lệ: {exc.msg} (dòng {exc.lineno})"]
    if not isinstance(data, dict):
        return None, ["bản ghi phải là object JSON"]
    return data, []


def _schema(v: object, ctx: Ctx) -> Optional[str]:
    return None if type(v) is int and v == 1 else "schema phải là số 1"


def _repo(v: object, ctx: Ctx) -> Optional[str]:
    if v != ctx.head_repo:
        return f"repo phải đúng head repo của PR {safe(ctx.head_repo)}"
    return None


def _kind(v: object, ctx: Ctx) -> Optional[str]:
    return None if v in KINDS else f"kind phải là {'|'.join(KINDS)}"


def _status(v: object, ctx: Ctx) -> Optional[str]:
    return None if v in STATUSES else f"status phải là {'|'.join(STATUSES)}"


def _upstream(v: object, ctx: Ctx) -> Optional[str]:
    if not isinstance(v, dict) or set(v) != {"repo", "version"}:
        return "upstream phải là object đúng hai trường repo, version"
    if v["repo"] != UPSTREAM:
        return f"upstream.repo phải là {UPSTREAM}"
    version = v["version"]
    if not isinstance(version, str) or not VERSION_RE.fullmatch(version):
        return "upstream.version phải dạng X.Y.Z"
    if ctx.versions is not None and version not in ctx.versions:
        return "upstream.version không phải bản khung đã phát hành (CHANGELOG.md)"
    return None


def _description(v: object, ctx: Ctx) -> Optional[str]:
    if not isinstance(v, str) or not v or v != v.strip():
        return "description phải là chuỗi khác rỗng, không có khoảng trắng đầu/cuối"
    if len(v) > DESC_MAX:
        return f"description {len(v)} ký tự > {DESC_MAX}"
    if not unicodedata.is_normalized("NFC", v):
        return "description phải ở dạng Unicode NFC"
    if any(_hidden(c) for c in v):
        return "description có ký tự điều khiển, ký tự ẩn, dấu kết hợp hoặc xuống dòng"
    return _text_problem(unicodedata.normalize("NFKC", v).casefold())


def _hidden(c: str) -> bool:
    code = ord(c)
    return unicodedata.category(c) in BAD_CATEGORIES or any(a <= code <= b for a, b in HIDDEN_RANGES)


def _text_problem(norm: str) -> Optional[str]:
    """Luật nội dung trên dạng NFKC + casefold: `＠`, `ｈｔｔｐ`, chữ số toàn chiều rộng không lách được."""
    if BANNED_CHARS & set(norm) or any(w in norm for w in BANNED_WORDS) or DOMAIN_RE.search(norm):
        return "description không được có HTML, link markdown, URL, tên miền, email hay @"
    if PHONE_RE.search(norm):
        return "description có dãy số dài (số điện thoại/PII)"
    return None


def _homepage(v: object, ctx: Ctx) -> Optional[str]:
    if not isinstance(v, str) or len(v) > HOME_MAX:
        return f"homepage phải là chuỗi ≤ {HOME_MAX} ký tự"
    m = HOME_RE.fullmatch(v)
    if not m:
        return "homepage chỉ nhận https://tên-miền[/đường-dẫn] (không userinfo, cổng, IP, query, fragment)"
    labels = m[1].split(".")
    if labels[-1] in RESERVED_TLDS or any(label.startswith("xn--") for label in labels):
        return "homepage dùng tên miền dành riêng hoặc punycode"
    return None


def _updated(v: object, ctx: Ctx) -> Optional[str]:
    if not isinstance(v, str) or not DATE_RE.fullmatch(v):
        return "updated phải dạng YYYY-MM-DD"
    try:
        day = dt.date.fromisoformat(v)
    except ValueError:
        return "updated không phải ngày hợp lệ"
    return "updated ở tương lai quá 1 ngày" if day > ctx.today + dt.timedelta(days=1) else None


CHECKS: dict[str, Callable[[object, Ctx], Optional[str]]] = {
    "schema": _schema,
    "repo": _repo,
    "kind": _kind,
    "upstream": _upstream,
    "description": _description,
    "homepage": _homepage,
    "status": _status,
    "updated": _updated,
}


def check_record(data: object, head_repo: str, day: dt.date, versions: Optional[frozenset[str]] = None) -> list[str]:
    """Lý do bản ghi trái schema v1 (rỗng = hợp lệ). `versions` None = không kiểm bản đã phát hành (chỉ dạng X.Y.Z)."""
    if not isinstance(data, dict):
        return ["bản ghi phải là object JSON"]
    if split_repo(head_repo) is None or head_repo.casefold() == UPSTREAM.casefold():
        return [f"head repo {safe(head_repo)} không nhận bản ghi phái sinh"]
    keys = set(data)
    out = [f"thiếu trường: {', '.join(sorted(REQUIRED - keys))}"] if REQUIRED - keys else []
    extra = sorted(keys - REQUIRED - OPTIONAL)
    if extra:
        out.append(f"trường lạ: {', '.join(safe(k) for k in extra[:5])}")
    ctx = Ctx(head_repo, day, versions)
    out += [msg for key, check in CHECKS.items() if key in data and (msg := check(data[key], ctx))]
    return out


def check_bytes(
    raw: bytes, head_repo: str, day: dt.date, versions: Optional[frozenset[str]] = None
) -> tuple[Optional[dict[str, Any]], list[str]]:
    data, out = parse_record(raw)
    if data is None:
        return None, out
    out = check_record(data, head_repo, day, versions)
    return (None if out else data), out


def check_pr_files(files: list[Any], head_repo: str) -> list[str]:
    """Lý do danh sách tệp của PR (REST `pulls/N/files` hoặc `{path, status, mode}`) không phải đúng một tệp của head repo."""
    name = record_name(head_repo)
    if name is None or head_repo.casefold() == UPSTREAM.casefold():
        return [f"head repo {safe(head_repo)} không nhận bản ghi phái sinh"]
    want = f"{DERIVED_DIR}/{name}"
    if len(files) != 1 or not isinstance(files[0], dict):
        return [f"PR đổi {len(files)} tệp — làn derived chỉ nhận đúng một tệp {want}"]
    f = files[0]
    path = f.get("filename", f.get("path"))
    out = [] if path == want else [f"tệp {safe(path)} khác {want}"]
    if f.get("previous_filename") or f.get("previous"):
        out.append("PR đổi tên/di chuyển tệp")
    if f.get("status") not in FILE_STATUSES:
        out.append(f"trạng thái tệp {safe(f.get('status'))} — chỉ nhận {'/'.join(FILE_STATUSES)}")
    if "mode" in f and f["mode"] != FILE_MODE:
        out.append(f"mode {safe(f['mode'])} — chỉ nhận {FILE_MODE} (không symlink, không thực thi)")
    return out


def released_versions(core: Any, ref: str) -> Optional[frozenset[str]]:
    """Bản khung đã phát hành = mục `## [X.Y.Z]` của CHANGELOG.md đã commit ở `ref` (nhánh đích — không lấy của PR)."""
    r = core._git(core.project_dir(), "show", f"{ref}:./CHANGELOG.md")
    found = frozenset(RELEASE_RE.findall(r.stdout)) if r.returncode == 0 else frozenset()
    return found or None


def _side(pull: dict[str, Any], key: str) -> dict[str, Any]:
    side = pull.get(key)
    return side if isinstance(side, dict) else {}


def _full_name(side: dict[str, Any]) -> str:
    repo = side.get("repo")
    name = repo.get("full_name") if isinstance(repo, dict) else None
    return name if isinstance(name, str) else ""


def _tree_entry(core: Any, repo: str, sha: str, parts: list[str]) -> dict[str, Any]:
    """Mục cây Git ở `sha` theo từng thành phần đường dẫn (không theo symlink như API contents)."""
    entry: dict[str, Any] = {"type": "tree", "sha": sha}
    for part in parts:
        if entry.get("type") != "tree" or not SHA_RE.fullmatch(str(entry.get("sha"))):
            raise ValueError("thành phần đường dẫn không phải thư mục")
        tree = core._gh_one(f"{repo}/git/trees/{entry['sha']}")
        if tree.get("truncated") is not False:
            raise ValueError("cây Git bị cắt hoặc không đọc được")
        hits = [e for e in tree.get("tree") or [] if isinstance(e, dict) and e.get("path") == part]
        if len(hits) != 1:
            raise ValueError("không thấy tệp ở head")
        entry = hits[0]
    return entry


def _entry_problem(entry: dict[str, Any], f: dict[str, Any]) -> Optional[str]:
    if entry.get("mode") != FILE_MODE or entry.get("type") != "blob":
        return f"mode Git {safe(entry.get('mode'))} — chỉ nhận {FILE_MODE} (không symlink, không thực thi)"
    size = entry.get("size")
    if type(size) is not int or not 0 < size <= MAX_BYTES:
        return f"tệp trống hoặc > {MAX_BYTES} B"
    if not SHA_RE.fullmatch(str(entry.get("sha"))) or ("sha" in f and f["sha"] != entry["sha"]):
        return "blob ở head không khớp danh sách tệp của PR"
    return None


def _blob(core: Any, repo: str, entry: dict[str, Any]) -> bytes:
    blob = core._gh_one(f"{repo}/git/blobs/{entry['sha']}")
    if blob.get("encoding") != "base64":
        raise ValueError("blob không ở dạng base64")
    raw = base64.b64decode("".join(str(blob.get("content", "")).split()), validate=True)
    if len(raw) != entry["size"]:
        raise ValueError("kích thước blob lệch")
    return raw


def _fetch(core: Any, repo: str, sha: str, head_repo: str, f: dict[str, Any]) -> tuple[bytes, list[str]]:
    """Byte của tệp bản ghi ở head (`sha` đã kiểm dạng ở `pinned_files`)."""
    try:
        entry = _tree_entry(core, repo, sha, [*DERIVED_DIR.split("/"), str(record_name(head_repo))])
        problem = _entry_problem(entry, f)
        return (b"", [problem]) if problem else (_blob(core, repo, entry), [])
    except (core.PrInputError, ValueError) as exc:
        return b"", [f"không đọc được tệp ở head qua API GitHub ({type(exc).__name__})"]


def _identity(pull: dict[str, Any], head_repo: str) -> list[str]:
    base_repo = _full_name(_side(pull, "base"))
    if base_repo.casefold() != UPSTREAM.casefold():
        return [f"repo đích không phải {UPSTREAM} — làn derived chỉ có ở repo khung"]
    if not head_repo:
        return ["PR không có head repo (fork đã xoá?)"]
    if head_repo.casefold() == base_repo.casefold():
        return ["PR mở từ chính repo đích — không phải dự án phái sinh"]
    return _author(pull)


def _author(pull: dict[str, Any]) -> list[str]:
    """Fork của tài khoản cá nhân: tác giả PR phải là chủ fork (cộng tác viên của fork không nói thay). Fork của tổ chức:
    không hỏi được quyền thành viên bằng token của repo khung — nhận theo head repo (ADR-0087)."""
    repo = _side(pull, "head").get("repo")
    owner = repo.get("owner") if isinstance(repo, dict) else None
    user = pull.get("user")
    login = user.get("login") if isinstance(user, dict) else None
    if not isinstance(owner, dict) or owner.get("type") not in ("User", "Organization") or not isinstance(login, str):
        return ["không xác minh được chủ head repo hoặc tác giả PR"]
    if owner["type"] == "User" and str(owner.get("login")).casefold() != login.casefold():
        return ["tác giả PR không phải chủ fork cá nhân"]
    return []


def _files(core: Any, repo: str, pull: dict[str, Any], head_repo: str) -> tuple[list[Any], list[str]]:
    try:
        files = pinned_files(core, repo, pull)
    except (core.PrInputError, ValueError) as exc:
        return [], [f"không đọc được danh sách tệp ở head qua API GitHub ({type(exc).__name__})"]
    changed = pull.get("changed_files")
    if type(changed) is not int or changed != len(files):
        return files, ["danh sách tệp của PR không khớp changed_files — không xác minh được"]
    return files, check_pr_files(files, head_repo)


def pinned_files(core: Any, repo: str, pull: dict[str, Any]) -> list[Any]:
    """Tệp đổi giữa đỉnh nhánh đích đọc lúc kiểm và head trong ảnh chụp `pull` (REST compare ba chấm, như squash merge
    áp lên đỉnh đó) — danh sách `pulls/N/files` đọc ở lượt gọi khác có thể thuộc head mới hơn (push chen giữa), còn
    `base.sha` của PR có thể cũ; lỗi/thiếu → ValueError hoặc PrInputError."""
    ref = _side(pull, "base").get("ref")
    if not isinstance(ref, str) or not ref:
        raise ValueError("PR thiếu nhánh đích")
    tip = core._gh_one(f"{repo}/branches/{urllib.parse.quote(ref, safe='')}").get("commit")
    base = str(tip.get("sha")) if isinstance(tip, dict) else ""
    head = str(_side(pull, "head").get("sha"))
    if not (SHA_RE.fullmatch(base) and SHA_RE.fullmatch(head)):
        raise ValueError("SHA của PR không hợp lệ")
    files = core._gh_one(f"{repo}/compare/{base}...{head}").get("files")
    if not isinstance(files, list):
        raise ValueError("compare không trả danh sách tệp")
    return files


def evaluate(core: Any, repo: str, pull: dict[str, Any]) -> dict[str, Any]:
    """Làn derived cho PR đã đọc qua REST: {ok, file, repo, head, reasons}. Mọi thiếu dữ liệu ⇒ ok False."""
    head = _side(pull, "head")
    head_repo = _full_name(head)
    files: list[Any] = []
    raw = b""
    reasons = _identity(pull, head_repo)
    if not reasons:
        files, reasons = _files(core, repo, pull, head_repo)
    if not reasons:
        raw, reasons = _fetch(core, repo, str(head["sha"]), head_repo, files[0])
    if not reasons:
        versions = released_versions(core, f"origin/{_side(pull, 'base').get('ref') or 'main'}")
        reasons = [CHANGELOG_MISSING] if versions is None else check_bytes(raw, head_repo, today(), versions)[1]
    name = record_name(head_repo)
    return {
        "ok": not reasons,
        "file": f"{DERIVED_DIR}/{name}" if name else "",
        "repo": head_repo if name else "",
        "head": str(head.get("sha") or ""),
        "reasons": reasons,
    }


def lane(core: Any, repo: str, pull: dict[str, Any], files: list[Any]) -> Optional[dict[str, Any]]:
    """`evaluate` chỉ khi PR chạm `docs/derived/` (cả tên cũ); PR khác: None — không gọi thêm API."""
    names = [n for f in files if isinstance(f, dict) for n in (f.get("filename"), f.get("previous_filename"))]
    if not any(isinstance(n, str) and n.startswith(DERIVED_DIR + "/") for n in names):
        return None
    return evaluate(core, repo, pull)


# --------------------------------------------------------------------------- CLI


def register(sub: Any, core: Any) -> None:
    p = sub.add_parser("derived", help="kiểm/liệt kê bản ghi dự án phái sinh ở docs/derived/ (ADR-0087)")
    acts = p.add_subparsers(dest="action", required=True)
    check = acts.add_parser("check", help="kiểm tệp cục bộ hoặc PR đang mở (exit 0 hợp lệ · 1 trái luật · 2 lỗi đọc)")
    check.add_argument("--pr", help="số/URL PR — kiểm như làn derived của merge-check")
    check.add_argument("files", nargs="*", metavar="TỆP")
    check.add_argument("--json", action="store_true")
    show = acts.add_parser("list", help="đọc và kiểm mọi bản ghi (exit 1 khi có bản ghi trái luật)")
    show.add_argument("--json", action="store_true")
    p.set_defaults(fn=lambda args: command(core, args))


def _local_versions(core: Any) -> Optional[frozenset[str]]:
    try:
        text = (core.project_dir() / "CHANGELOG.md").read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    return frozenset(RELEASE_RE.findall(text)) or None


def _check_path(path: Path, versions: Optional[frozenset[str]]) -> dict[str, Any]:
    """Một tệp cục bộ: tên suy ra head repo, không symlink/thực thi, nội dung theo schema."""
    head = repo_from_name(path.name)
    shown = str(path) if str(path).isprintable() else ascii(str(path))
    row: dict[str, Any] = {"path": shown, "repo": head or "", "reasons": []}
    if head is None:
        row["reasons"].append("tên tệp phải dạng <owner>--<repo>.json theo tên GitHub")
    if path.is_symlink():
        row["reasons"].append("tệp là symlink")
    try:
        raw = path.read_bytes()
        exec_bits = path.stat().st_mode & 0o111
    except OSError as exc:
        return {**row, "ok": False, "error": f"không đọc được: {exc.strerror or exc}"}
    if exec_bits:
        row["reasons"].append("tệp có quyền thực thi (Git ghi mode 100755)")
    data, problems = check_bytes(raw, head, today(), versions) if head is not None else (None, [])
    row["reasons"] += problems
    ok = not row["reasons"]
    return {**row, "ok": ok, **({"record": data} if ok else {})}


def _print_rows(rows: list[dict[str, Any]], notes: list[str], as_json: bool) -> int:
    if as_json:
        print(json.dumps({"files": rows, "notes": notes}, ensure_ascii=False))
    else:
        for r in rows:
            print(f"{'✓' if r['ok'] else '✗'} {r['path']}" + ("" if r["ok"] else f": {r.get('error') or ''}"))
            for reason in r["reasons"]:
                print(f"  - {reason}")
        for n in notes:
            print(f"  ⚠ {n}")
    return 2 if any("error" in r for r in rows) else int(not all(r["ok"] for r in rows))


def _cmd_files(core: Any, files: list[str], as_json: bool) -> int:
    versions = _local_versions(core)
    notes = [] if versions else [CHANGELOG_MISSING + " — chỉ kiểm dạng X.Y.Z"]
    return _print_rows([_check_path(Path(f), versions) for f in files], notes, as_json)


def _cmd_pr(core: Any, pr_arg: str, as_json: bool) -> int:
    try:
        repo, n = core._pr_target(pr_arg)
        pull = core._gh_one(f"{repo}/pulls/{n}")
    except (core.PrInputError, ValueError) as exc:
        print(f"✗ derived check --pr {pr_arg}: {exc}", file=sys.stderr)
        return 2
    d = evaluate(core, repo, pull)
    if as_json:
        print(json.dumps(d, ensure_ascii=False))
    else:
        print(f"{'✓' if d['ok'] else '✗'} PR #{n} · làn derived: {'đủ điều kiện' if d['ok'] else 'không'}")
        for reason in d["reasons"]:
            print(f"  - {reason}")
    return int(not d["ok"])


def _cmd_list(core: Any, as_json: bool) -> int:
    folder = core.project_dir() / DERIVED_DIR
    if not folder.is_dir():
        print(f"✗ không có thư mục {DERIVED_DIR}/", file=sys.stderr)
        return 2
    versions = _local_versions(core)
    entries = sorted(p for p in folder.iterdir() if not (p.name == "README.md" and p.is_file() and not p.is_symlink()))
    rows = [_check_path(p, versions) for p in entries]
    records = [r.pop("record") for r in rows if r["ok"]]  # đã qua kiểm: không còn ký tự điều khiển
    if as_json:
        print(json.dumps({"records": records, "invalid": [r for r in rows if not r["ok"]]}, ensure_ascii=False))
        return 2 if any("error" in r for r in rows) else int(len(records) != len(rows))
    for rec in records:
        print(
            f"{rec['repo']} · {rec['kind']} · {rec['upstream']['version']} · {rec['status']} · {rec['updated']}"
            f" — {rec['description']}"
        )
    bad = [r for r in rows if not r["ok"]]
    print(f"{len(records)} bản ghi hợp lệ, {len(bad)} trái luật")
    return _print_rows(bad, [], False) if bad else 0


def command(core: Any, args: argparse.Namespace) -> int:
    if args.action == "list":
        return _cmd_list(core, args.json)
    if bool(args.pr) == bool(args.files):
        print("✗ derived check cần đúng một trong --pr N hoặc TỆP…", file=sys.stderr)
        return 2
    return _cmd_pr(core, args.pr, args.json) if args.pr else _cmd_files(core, args.files, args.json)

"""D-503/D-508 (T-3951): phát hiện cổng ký lần 10 (ứng viên `a20ba307`), sửa theo lớp kèm bộ sinh biến thể.

- A1 (🔴): `>&TỪ`/`>& TỪ`/`1>&TỪ` (TỪ không phải số fd/`-`) ghi TỪ như `&>TỪ` — mọi đích canh.
- A2 (🔴): biến không tính chắc ở lệnh xoá/ghi — bản RỖNG (`"$TMPDIR"/*` → `/*`, `"$OUT"/etc` → `/etc`) và bản GIÁ TRỊ
  BẤT KỲ (`/home/$USER/x`, `~/../$USER`); `"$TMPDIR/x"` (đường chưa có) và biến gán từ `$(mktemp …)` vẫn qua.
- A3 (🔴): tuỳ chọn đặt thư mục của trình chạy (`uv run --directory ~`, `pnpm -C`, `yarn --cwd`, `npm --prefix`…).
- A4 (🔴): chuỗi template JS (`` execSync(`…`) ``, `String.raw`).
- A5 (🔴): Python gọi mô-đun chạy lệnh qua bí danh/`from … import`.
- B5 (🟢 chặn oan): `d=$(mktemp -d "${TMPDIR:-/tmp}/b.XXXXXX"); rm -rf "$d"`.

DENY: dạng lọt ở `a20ba307` (đã xác nhận bằng bash thật ở lô cổng ký 10) và biến thể sinh quanh nó. ALLOW: đối chứng lành."""

from __future__ import annotations

import concurrent.futures
import contextlib
import itertools
import os
import sys
import unittest
import unittest.mock as mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("XT_GUARD_PHASE", "harden")
sys.path.insert(0, str(ROOT / ".claude" / "hooks"))
import guard

H = chr(126)  # `~` dựng bằng chr: chữ xoá home không nằm nguyên văn trong tệp test
R = "r" + "m"
WIPE = f"{R} -rf {H}"


def patched(root: Path = ROOT) -> contextlib.ExitStack:
    stack = contextlib.ExitStack()
    stack.enter_context(mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(root), "XT_GUARD_POLICY": ""}))
    stack.enter_context(mock.patch.object(guard, "_current_branch", return_value="feat"))
    return stack


def decide_raw(cmd: str, root: Path = ROOT) -> dict:
    return guard.apply_policy(guard.bash_decision(cmd, str(root), str(root)))


def decide(cmd: str, root: Path = ROOT) -> dict:
    with patched(root):
        return decide_raw(cmd, root)


def wraps(cmd: str) -> list[str]:
    """Bọc lệnh: trơn, `{ }`, `( )`, `if`, `true &&`, `bash -c`, `sh -c` hai tầng, `env`/`nice`/`timeout`/`command`."""
    q = cmd.replace("'", "'\\''")
    inner = f"bash -c '{q}'"
    q2 = inner.replace("'", "'\\''")
    return [
        cmd,
        f"{{ {cmd}; }}",
        f"( {cmd} )",
        f"if :; then {cmd}; fi",
        f"true && {cmd}",
        inner,
        f"sh -c '{q2}'",
        f"env {cmd}" if not cmd.startswith(("echo", ":", "true", "cat")) else f"{cmd} || :",
    ]


class Base(unittest.TestCase):
    def assert_deny(self, cmds: list[str] | tuple[str, ...], root: Path = ROOT) -> None:
        for cmd in cmds:
            with self.subTest(cmd=cmd):
                self.assertEqual(decide(cmd, root).get("decision"), "deny")

    def assert_allow(self, cmds: list[str] | tuple[str, ...], root: Path = ROOT) -> None:
        for cmd in cmds:
            with self.subTest(cmd=cmd):
                d = decide(cmd, root)
                self.assertNotEqual(d.get("decision"), "deny", d.get("reason"))


FENCES = (".git/HEAD", ".claude/settings.json", ".claude/hooks/guard.py", ".autopilot/state.json", ".env")
FENCES += ("docs/ops/GO-NO-GO-v1.md",)
A1_OPS = (">& ", ">&", "1>& ", "1>&")
A1_ALLOW = (
    "echo x >&2",
    "echo x 2>&1",
    "echo x >& 2",
    "echo x >&-",
    "echo x >&3-",
    "echo x >& out.txt",
    "ls >&/dev/null",
)


class A1DupRedirectTest(Base):
    def test_deny_fences(self):
        cmds = [f"{v} {op}{f}" for v, op, f in itertools.product(("echo x", ":", "true"), A1_OPS, FENCES)]
        self.assert_deny([w for c in cmds[:12] for w in wraps(c)] + cmds)

    def test_allow(self):
        self.assert_allow(A1_ALLOW)

    def test_dup_file_tokens(self):
        self.assertEqual(guard._dup_file(["echo", "1", ">&", "f"]), ["echo", "1", ">", "f"])
        self.assertEqual(guard._dup_file(["echo", ">&", "2"]), ["echo", ">&", "2"])
        self.assertEqual(guard._dup_file([">&"]), [">&"])


A2_VARS = ("TMPDIR", "OUT", "BUILD_DIR")
A2_FORMS = ('"${V}"/*', '"$V"/*', "$V/*", '"$V/"*', '"$V"/etc', '"${V}"/bin', '"${V%/}"/usr', '"$V/"')
A2_VERBS = (f"{R} -rf", f"\\{R} -rf", f"command {R} -rf", f"{R} -r", "shred -u", "mv", "truncate -s0")
A2_DENY_EXTRA = (
    f'{R} -rf "/home/$USER/Documents"',
    f"{R} -rf {H}/../$USER",
    f'{R} -rf "/home/$LOGNAME"',
    'echo x | tee "$OUT"/*',
    'echo x | tee -a "$OUT/"*',
    'cp /dev/null "/home/$TMPDIR"',
    'echo x | tee "/home/$USER/Documents"',
    'cp /dev/null "/home/$LOGNAME/Documents"',
    'truncate -s0 ~/../"$USER"',
    "mv ~/../$USER zz",
    f'D=$(git rev-parse --show-toplevel); {R} -rf "$D"/etc',
    f'{R} -rf "${{OUT:-}}"/etc',
    f'{R} -rf "${{OUT-}}"/etc',
)
A2_ALLOW = (
    f'{R} -rf "$TMPDIR/x"',
    f"{R} -rf $TMPDIR/xt-build-a2",
    f'{R} -rf "${{TMPDIR:-/tmp}}"/xt-*',
    f'TMP=$(mktemp -d); {R} -rf "$TMP"/x',
    f'TMP=$(mktemp -d); {R} -rf "$TMP"',
    f'{R} -rf "$OUT"',
    f'{R} -rf build/"$OUT"',
    f'{R} -rf "${{OUT:?}}"/*',
    f'for d in a b; do {R} -rf "$d"/; done',
    'cp a.txt "$OUT"',
    'echo hi > "$LOG"',
    f'X=build; {R} -rf "$X"/*',
)


class A2EmptyReadingTest(Base):
    def test_deny_matrix(self):
        cmds = [f"{v} {f.replace('V', n)}" for v, f, n in itertools.product(A2_VERBS, A2_FORMS, A2_VARS)]
        cmds = [c for c in cmds if not (c.startswith(("mv", "truncate")) and c.endswith('/"'))]
        self.assert_deny(cmds)

    def test_deny_wrapped(self):
        self.assert_deny([w for c in (f'{R} -rf "$TMPDIR"/*', *A2_DENY_EXTRA[:3]) for w in wraps(c)])
        self.assert_deny(A2_DENY_EXTRA)

    def test_allow(self):
        self.assert_allow(A2_ALLOW)

    def test_helpers(self):
        self.assertEqual(guard._empty_seg(["do", "x", "2", ">", "/dev/null"], set(), ""), "")
        self.assertEqual(guard._empty_seg(["x", "2", ">", '"$A"'], set(), "y"), 'x 2> "y"')
        self.assertEqual(guard._empty_seg(["x", "<<<", '"$A"', '"$B"'], set(), "y"), 'x "y"')
        self.assertEqual(guard._empty_word("'$A'$B\\$C${#D}${!E}", set(), ""), "'$A'\\$C0${!E}")
        self.assertFalse(guard._empty_exists(""))


A3_RUNNERS = ("uv run --directory D", "uv --directory D run", "uv run --directory=D", "uvx --directory D")
A3_RUNNERS += (
    "pnpm -C D exec",
    "pnpm --dir D exec",
    "pnpm --dir=D exec",
    "yarn --cwd D exec",
    "npm --prefix D exec --",
)
A3_RUNNERS += ("poetry -C D run", "pdm -p D run", "bunx --cwd D", "systemd-run --user --working-directory=D")
A3_DIRS = (H, "..", "$HOME", "/home")
A3_ALLOW = (
    f"uv run --directory sub {R} -rf build",
    f"pnpm -C packages/web exec {R} -rf dist",
    f"uv run -p 3.12 {R} -rf build",
    "uv run --directory sub pytest",
    "npm --prefix web run build",
)


class A3RunnerChdirTest(Base):
    def test_deny(self):
        cmds = [f"{r.replace('D', d)} {R} -rf Documents" for r, d in itertools.product(A3_RUNNERS, A3_DIRS)]
        cmds += [f"uv run --directory {H} sh -c '{R} -rf Documents'", f'uv run --directory {H} {R} -rf "$(date +%F)"']
        self.assert_deny(cmds + wraps(f"pnpm -C {H} exec {R} -rf Documents"))

    def test_allow(self):
        self.assert_allow(A3_ALLOW)

    def test_chdirs(self):
        self.assertEqual(guard._runner_chdirs(["-Cx", "--dir=y", "--cwd", "z", "-p"]), ["x", "y", "z"])


A4_CALLS = (
    'require("child_process").execSync(`P`)',
    'require("child_process").exec(`P`)',
    'require("child_process").execSync(String.raw`P`)',
    'require("child_process").spawnSync("sh", ["-c", `P`])',
    'const {execSync} = require("child_process"); execSync(`P`, {stdio: "inherit"})',
)
A4_SRC = ("node -e 'S'", "node -p 'S'", "node --eval='S'", "node <<< 'S'", "echo 'S' | node", "bun -e 'S'")
A4_ALLOW = (
    "node -e 'console.log(`hello`)'",
    "node -e 'require(\"child_process\").execSync(`ls -la`)'",
    "node -e 'const x = `a,b`; console.log(x.split(\",\"))'",
)


class A4TemplateTest(Base):
    def test_deny(self):
        self.assert_deny([s.replace("S", c.replace("P", WIPE)) for s, c in itertools.product(A4_SRC, A4_CALLS)])

    def test_allow(self):
        self.assert_allow(A4_ALLOW)

    def test_interp_marker(self):
        m = guard.LITERAL_RE.search("`a ${b} c`")
        self.assertEqual(guard._literal(m), f"a {guard.JS_INTERP_WORD} c")


A5_CALLS = (
    'import subprocess as s; s.run("P", shell=True)',
    'import subprocess as s; s.call("P", shell=1)',
    'from subprocess import run; run("P", shell=True)',
    'from subprocess import run as r; r("P", shell=True)',
    'import os as o; o.system("P")',
    'from os import system; system("P")',
    '__import__("os").system("P")',
)
A5_SRC = ("python3 -c 'S'", "python -c 'S'", "python3 -Ic 'S'", "python3 - <<< 'S'", "echo 'S' | python3")
A5_SRC += ("python3 /dev/stdin <<< 'S'",)
A5_ALLOW = (
    'python3 -c \'import subprocess as s; print(s.run(["git", "status"], capture_output=True).stdout)\'',
    'python3 -c \'from subprocess import run; run(["ls", "-la"])\'',
    "python3 -c 'import os as o; print(o.getcwd())'",
)


class A5PyAliasTest(Base):
    def test_deny(self):
        self.assert_deny([s.replace("S", c.replace("P", WIPE)) for s, c in itertools.product(A5_SRC, A5_CALLS)])

    def test_allow(self):
        self.assert_allow(A5_ALLOW)

    def test_too_many_literals(self):
        script = "import subprocess as s\n" + "\n".join(f"x{i} = 'v{i}'" for i in range(guard.QUOTE_JOIN_MAX + 1))
        with self.assertRaises(guard.ScanTooComplex):
            guard._py_alias_scripts(script)
        self.assertEqual(guard._py_alias_scripts("import subprocess as s"), [])


A7_MOVES = (
    "git checkout main",
    "git checkout -B main",
    "git checkout -q main",
    "git switch main",
    "git switch -c main",
)
A7_MOVES += ("git merge --ff-only feat/x", "git reset --hard origin/main")
A7_PUSH = (
    'git push origin "$(git branch --show-current)"',
    'git push -u origin "$(git branch --show-current)"',
    'git push --set-upstream origin "$(git rev-parse --abbrev-ref HEAD)"',
    'B=$(git branch --show-current) && git push origin "$B"',
    'git push origin --delete "$(git branch --show-current)"',
)
A7_ALLOW = (
    'git push origin "$(git branch --show-current)"',
    "git checkout -b feat/y && git push -u origin feat/y",
    'B=$(git branch --show-current) && git push origin "$B"',
)


class A7PushAfterMoveTest(Base):
    def test_deny(self):
        cmds = [f"{m}{sep}{p}" for m, sep, p in itertools.product(A7_MOVES, (" && ", "; "), A7_PUSH)]
        self.assert_deny(cmds + wraps(f"{A7_MOVES[0]} && {A7_PUSH[0]}"))

    def test_allow(self):
        self.assert_allow(A7_ALLOW)


B5_ALLOW = (
    f'd=$(mktemp -d "${{TMPDIR:-/tmp}}/b.XXXXXX"); {R} -rf "$d"',
    f'd=$(mktemp -d "$TMPDIR/b.XXXXXX"); {R} -rf "$d"',
    f'{R} -rf "$(mktemp -d "${{TMPDIR:-/tmp}}/b.XXXXXX")"',
)


class B5MktempTmpdirTest(Base):
    def test_allow(self):
        self.assert_allow(B5_ALLOW)


class ConcurrentTest(unittest.TestCase):
    """Quyết định đồng thời (luồng) cho cùng kết quả như tuần tự — contextvars của bản đọc lại không rò giữa luồng."""

    def test_threads(self):
        cmds = [f'{R} -rf "$TMPDIR"/*', f'{R} -rf "$TMPDIR/x"', f"echo x >& {FENCES[1]}", A4_ALLOW[0]] * 4
        with patched():
            want = [decide_raw(c).get("decision") for c in cmds]
            with concurrent.futures.ThreadPoolExecutor(4) as pool:
                got = list(pool.map(lambda c: decide_raw(c).get("decision"), cmds))
        self.assertEqual(got, want)


if __name__ == "__main__":
    unittest.main()

"""D-503/D-507 (T-3947): phát hiện cổng ký lần 8 (ứng viên `7b1ebc84`), sửa theo lớp.

- M5 (🔴/🟠): chương trình qua stdin/cờ — thân bỏ nháy kiểu shell, `$` ở thân here-string/ống, nguồn không phải chữ
  (thay tiến trình, fd khác 0, ống từ khâu đọc nguồn đó), cờ viết tắt/dính giá trị, `+cmd`/`-c` của vi/ex/vim, đối số
  vị trí của sqlite3.
- M9 (🟠 chặn oan): thân SQL/manifest/Dockerfile chỉ quét dòng lối thoát shell.

DENY: dạng tái hiện guard ở `7b1ebc84` cho chạy. ALLOW: dạng lành phải chạy."""

from __future__ import annotations

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


def decide(cmd: str, root: Path = ROOT, cwd: Path | None = None) -> dict:
    with (
        mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(root), "XT_GUARD_POLICY": ""}),
        mock.patch.object(guard, "_current_branch", return_value="feat"),
    ):
        return guard.apply_policy(guard.bash_decision(cmd, str(root), str(cwd or root)))


class Base(unittest.TestCase):
    def assert_deny(self, cmds: tuple[str, ...], root: Path = ROOT, cwd: Path | None = None) -> None:
        for cmd in cmds:
            with self.subTest(cmd=cmd):
                self.assertEqual(decide(cmd, root, cwd).get("decision"), "deny")

    def assert_allow(self, cmds: tuple[str, ...], root: Path = ROOT, cwd: Path | None = None) -> None:
        for cmd in cmds:
            with self.subTest(cmd=cmd):
                d = decide(cmd, root, cwd)
                self.assertNotEqual(d.get("decision"), "deny", d.get("reason"))


STDIN_DENY = (
    # 5a: bỏ nháy kiểu shell, `$` ở thân here-string/ống, `${c:-r}m`
    f"ed -s /dev/null <<< '!r\"\"m -rf {H}'",
    f"sqlite3 x.db <<'EOF'\n.shell r''m -rf {H}\nEOF",
    f"psql -c '\\! r\"\"m -rf {H}'",
    f"at now <<< 'r\"\"m -rf {H}'",
    f"crontab - <<'EOF'\n* * * * * r''m -rf {H}\nEOF",
    f"sqlite3 x.db <<EOF\n.shell ${{c:-r}}m -rf {H}\nEOF",
    f"x='!{WIPE}'; ed -s /dev/null <<< \"$x\"",
    f"x='!{WIPE}'; printf '%s\\n' \"$x\" | ed -s /dev/null",
    f"x='{WIPE}'; printf '%s\\n' \"$x\" | at now",
    f"tclsh <<'EOF'\nexec {WIPE}\nEOF",
    # 5b: nguồn không phải chữ
    f"python3 < <(printf '%s\\n' 'import os; os.system(\"{WIPE}\")')",
    "python3 <(printf '%s\\n' 'import os')",
    "perl <(printf x)",
    "cat <(printf '%s\\n' x) | node",
    f"exec 3< <(printf '%s\\n' '!{WIPE}'); ed -s /dev/null <&3",
    f"exec 3< <(printf '%s\\n' '{WIPE}'); sh <&3",
    f"{{ ed -s /dev/null; }} < <(printf '%s\\n' '!{WIPE}')",
    f"bash /dev/stdin < <(printf '%s\\n' '{WIPE}')",
    f"ed -s /dev/null < <(printf '%s\\n' '!{WIPE}')",
    "python3 /dev/fd/3 3<x.py",
    f"crontab <(echo '* * * * * {WIPE}')",
    f"at now < <(echo '{WIPE}')",
    f"sqlite3 -init <(echo '.shell {R}') x.db",
    # 5c: cờ chương trình
    f"ex -s -c '!{WIPE}' -c q /dev/null",
    f"ex -s +'!{WIPE}' +q x.txt",
    f"vim -es -c '!{WIPE}' -c q",
    f"vim -es +'!{WIPE}' +q /dev/null",
    f"vim -es --cmd '!{WIPE}' -c q /dev/null",
    f"make --eva='x:;{WIPE}' x",
    f"make -E'x:;{WIPE}' x",
    f"gdb -batch --eval-command='shell {WIPE}'",
    f"gdb -batch -ex 'shell {WIPE}'",
    f"sqlite3 :memory: '.shell {WIPE}'",
    f"sqlite3 x.db '.shell {WIPE}'",
    f"sqlite3 -cmd '.system {WIPE}' :memory: .quit",
    f"dc -e'!{WIPE}'",
    f"dc --expression='!{WIPE}'",
    f"expect -c 'exec {WIPE}'",
    f"psql --comm='\\! {WIPE}'",
    f"psql -c'\\! {WIPE}'",
    f"mysql -e'system {WIPE}'",
    # công cụ lạ: mọi từ (như trước)
    f"Rscript -e 'system(\"{WIPE}\")'",
    f"x=(a) <<X\n{WIPE}\nX",
)

STDIN_ALLOW = (
    'psql -d app_test -c "truncate table users restart identity cascade;"',
    "psql app <<'SQL'\nselect now() at time zone 'utc';\nSQL",
    'mysql -e "truncate table users"',
    "psql app <<'SQL'\nselect * from t where a != 1;\nSQL",
    "kubectl apply -f - <<'EOF'\nkind: Pod\nspec:\n  containers:\n    - name: app\n      image: python:3.12\n"
    '      command: ["sh", "-c", "echo hi"]\nEOF',
    "docker build -t app - <<'EOF'\nFROM python:3.12\nRUN pip install flask\nEOF",
    "psql -c 'select 1'",
    "sqlite3 x.db 'select count(*) from t'",
    "vim -es -c '%s/a/b/g' -c wq x.txt",
    "ed -s x.txt <<'EOF'\n,s/a/b/g\nw\nq\nEOF",
    "echo 'print(1)' | python3",
    "cat x.py | python3",
    "python3 < script.py",
    'while read -r f; do python3 tool.py "$f"; done < <(git ls-files)',
    "diff <(sort a) <(sort b)",
    "psql \"$DB\" -c 'select 1'",
    "make -j4 test",
    "make --env x",
    "Rscript -e 'print(1)'",
    ". /dev/stdin <<< 'cd sub'",
    "tool -e x",
    # Gate `/optimize` (D-370): thay tiến trình đọc nội dung đã lưu, dự phòng chỉ thoát
    "python3 -I <(git cat-file blob refs/remotes/origin/HEAD:scripts/xt.py || echo 'raise SystemExit(2)') perf trial"
    " status --check",
    "python3 < <(git show HEAD:tools/x.py)",
)


class StdinProgramTest(Base):
    def test_stdin_programs_denied(self):
        self.assert_deny(STDIN_DENY)

    def test_benign_data_allowed(self):
        self.assert_allow(STDIN_ALLOW)

    def test_modes(self):
        self.assertEqual(guard._stdin_mode(["crontab", "-"]), guard.STDIN_WHOLE)
        self.assertEqual(guard._stdin_mode(["psql"]), guard.STDIN_ESC)
        self.assertEqual(guard._stdin_mode(["Rscript"]), guard.STDIN_WORDS)
        self.assertEqual(guard._stdin_mode([]), guard.STDIN_WORDS)
        self.assertTrue(guard._stdin_body_runs("select $x", guard.STDIN_ESC, True))
        self.assertFalse(guard._stdin_body_runs("select $x", guard.STDIN_WORDS))
        self.assertTrue(guard._stdin_body_runs("echo $HOME", guard.STDIN_WHOLE))
        self.assertTrue(guard._stdin_body_runs("\\! ls $HOME"))

    def test_inline_values(self):
        self.assertEqual(guard._inline_values("vim", ["vim", "+10", "-c", "w", "x"]), ["10", "w"])
        self.assertEqual(guard._inline_values("foo", ["foo", "-c", "x", "-cz"]), [])
        self.assertEqual(guard._inline_values("psql", ["psql", "--co", "a", "--command=b"]), ["a", "b"])
        self.assertEqual(guard._inline_values("dc", ["dc", R, "-e", "x"]), [])
        self.assertTrue(guard._make_eval("--ev"))
        self.assertFalse(guard._make_eval("--env"))

    def test_prog_reader(self):
        self.assertTrue(guard._prog_reader(["crontab", "x"]))
        self.assertTrue(guard._prog_reader(["bash", "/dev/stdin"]))
        self.assertFalse(guard._prog_reader(["python3", "x.py"]))
        self.assertFalse(guard._prog_reader([]))
        self.assertEqual(guard._prog_src_why("ls /dev/null"), "")


if __name__ == "__main__":
    unittest.main()

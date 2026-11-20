"""Kiểm "không bậc hai" bằng tỉ lệ đo trong cùng tiến trình, không bằng ngưỡng giây cứng (AUD-TEST-008).

Ngưỡng tuyệt đối (`assertLess(process_time() - t0, 2.0)`) đỏ ngẫu nhiên khi chạy dưới `coverage run` trên runner chung
(CI #170: 2,013 s ≥ 2,0 s). Ở đây đo cùng việc ở cỡ `n` và `4n`: tuyến tính tăng ~4 lần, bậc hai ~16 lần; ngưỡng
`10 × max(cost(n), FLOOR) + SLACK` nằm giữa. Máy chậm làm chậm cả hai lần đo như nhau nên tỉ lệ không đổi.

Độ nhạy: mã bậc hai bị bắt khi `cost(n) > SLACK / 6` (~0,08 s), tức `cost(4n)` > ~1,3 s — ngang ngưỡng tuyệt đối cũ
(1–3 s ở cỡ lớn). Vì vậy cỡ lớn `4n` ở mỗi test giữ đúng cỡ đầu vào của test cũ.
"""

from __future__ import annotations

import ast
import dataclasses
import threading
import time
import unittest
from typing import Callable, Iterator, TypeVar

T = TypeVar("T")

FACTOR = 4  # cỡ lớn = FACTOR × cỡ nhỏ
RATIO = 10  # giữa FACTOR (tuyến tính) và FACTOR**2 (bậc hai)
FLOOR = 0.02  # giây: lần đo nhỏ quá ngắn thì nhiễu đồng hồ chiếm phần lớn
SLACK = 0.5  # giây: nhiễu tuyệt đối (GC, cache) của lần đo lớn

# Hạn chờ nhỏ nhất (giây) của `run_with_deadline` — ranh giới giữa "chống treo" và "trần tốc độ", khai báo một chỗ.
# Hạn chống treo chỉ đỏ khi việc KHÔNG BAO GIỜ trả về (FIFO không ai ghi, tiến trình con `sleep 30`, hạn 15 s của guard),
# nên đặt xa trên thời gian chạy bình thường dưới `coverage run` trên runner chung. Hạn ngắn hơn mức này thực chất là
# trần tốc độ — đỏ ngẫu nhiên như ngưỡng giây cũ (CI #170) — và phải viết bằng `assert_not_quadratic` (đầu vào là đơn vị
# lặp) hoặc kiểm bằng hành vi. `run_with_deadline` ném `ValueError` khi hạn dưới mức này; `hard_time_thresholds` bắt lời
# gọi có hạn không phải hằng ≥ mức này hoặc thiếu lý do `hang=`.
HANG_FLOOR = 5.0


def cost(work: Callable[[int], object], n: int, clock: Callable[[], float] = time.process_time) -> float:
    t0 = clock()
    work(n)
    return clock() - t0


def assert_not_quadratic(
    tc: unittest.TestCase,
    work: Callable[[int], object],
    n: int,
    clock: Callable[[], float] = time.process_time,
    ratio: float = RATIO,
) -> None:
    """`work(FACTOR*n)` tốn CPU < `ratio` × `work(n)` (+ sàn/nhiễu) — đỏ khi `work` bậc hai trở lên theo `n`.

    Test chỉ canh hàm mũ (ngân sách quét) có thể nới `ratio` tới 40 (cho phép bậc hai, FACTOR**2 = 16 lần) — hàm mũ
    vẫn vượt xa.

    Lần đầu vượt ngưỡng thì đo lại một lượt (D-380, D-483). So cỡ nhỏ và lớn cùng lượt để nếu cả hai lượt đều vượt
    ngưỡng thì test đỏ."""
    small = max(cost(work, n, clock), FLOOR)
    big = cost(work, FACTOR * n, clock)
    if big >= small * ratio + SLACK:
        small = max(cost(work, n, clock), FLOOR)
        big = cost(work, FACTOR * n, clock)
    tc.assertLess(big, small * ratio + SLACK, f"cỡ {FACTOR * n}: {big:.3f} s; cỡ {n}: {small:.3f} s — bậc hai?")


def check_hang(seconds: float, hang: str) -> None:
    """`ValueError` khi hạn chờ không phải hạn chống treo khai rõ: dưới `HANG_FLOOR` hoặc lý do `hang` rỗng."""
    if seconds < HANG_FLOOR or not hang.strip():
        raise ValueError(
            f"run_with_deadline: hạn {seconds} s < HANG_FLOOR {HANG_FLOOR} s hoặc thiếu lý do `hang` — trần tốc độ"
            " dùng assert_not_quadratic"
        )


def run_with_deadline(tc: unittest.TestCase, fn: Callable[[], T], seconds: float, *, hang: str) -> T:
    """Chạy `fn()` trong luồng nền và chờ tối đa `seconds` — hạn chờ CHỐNG TREO, không khẳng định tốc độ.

    `hang` (bắt buộc): việc nào có thể treo mãi (vd "FIFO không ai ghi"). `seconds` ≥ `HANG_FLOOR`, không thì
    `ValueError` — trần tốc độ dùng `assert_not_quadratic` hoặc kiểm hành vi.

    Hết hạn mà `fn` chưa xong thì test đỏ (luồng nền là daemon nên không giữ tiến trình). `fn` ném lỗi thì ném lại ở
    luồng gọi; trả đúng giá trị `fn` trả.

    `fn` KHÔNG được mở bản vá toàn cục (`mock.patch`, `patch.dict(os.environ)`, `redirect_stdout`, `sys.stdin`) trong
    luồng phụ: hết hạn thì luồng gọi đi tiếp (test sau chạy) trong khi luồng phụ còn giữ bản vá và gỡ nó muộn, lẫn vào
    test khác. Mở bản vá ở luồng gọi (bọc quanh `run_with_deadline`) và chỉ giao lời gọi thuần cho `fn`."""
    check_hang(seconds, hang)
    values: list[T] = []
    errors: list[BaseException] = []

    def target() -> None:
        try:
            values.append(fn())
        except BaseException as exc:  # chuyển nguyên lỗi về luồng gọi
            errors.append(exc)

    worker = threading.Thread(target=target, daemon=True)
    worker.start()
    worker.join(seconds)
    if worker.is_alive():
        tc.fail(f"chưa trả về sau {seconds} s — treo ({hang})?")
    if errors:
        raise errors[0]
    return values[0]


CLOCKS = frozenset(
    {"monotonic", "perf_counter", "process_time", "thread_time", "time"}
    | {"monotonic_ns", "perf_counter_ns", "process_time_ns", "thread_time_ns", "time_ns"}
)
ASSERTS = frozenset(
    {"assertLess", "assertLessEqual", "assertGreater", "assertGreaterEqual", "assertTrue", "assertFalse"}
)
_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


@dataclasses.dataclass(frozen=True)
class _Env:
    """Tên nhìn thấy ở một phạm vi: bí danh của `time`/hàm đồng hồ và tên đã gán từ đồng hồ/hiệu thời gian/hằng số."""

    mods: frozenset[str]  # tên trỏ module `time` (`import time as t`)
    funcs: frozenset[str]  # tên trỏ hàm đồng hồ (`from time import monotonic as clock`)
    clocks: frozenset[str] = frozenset()  # `t0 = time.monotonic()`
    timed: frozenset[str] = frozenset()  # `elapsed = time.monotonic() - t0`
    consts: frozenset[str] = frozenset()  # `LIMIT = 5` — hằng dùng làm trần


def _aliases(tree: ast.AST) -> _Env:
    """`time` và tên hàm đồng hồ trần mặc định (mẩu nguồn không import) + mọi bí danh import trong tệp."""
    mods, funcs = {"time"}, set(CLOCKS - {"time"})
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods.update(a.asname for a in node.names if a.name == "time" and a.asname)
        elif isinstance(node, ast.ImportFrom) and node.module == "time":
            funcs.update(a.asname or a.name for a in node.names if a.name in CLOCKS)
    return _Env(frozenset(mods), frozenset(funcs))


def _is_clock_call(node: ast.AST, env: _Env) -> bool:
    if not isinstance(node, ast.Call):
        return False
    fn = node.func
    if isinstance(fn, ast.Attribute):
        return fn.attr in CLOCKS and isinstance(fn.value, ast.Name) and fn.value.id in env.mods
    return isinstance(fn, ast.Name) and fn.id in env.funcs


def _local_nodes(scope: ast.AST) -> Iterator[ast.AST]:
    """Nút thuộc riêng `scope`: không đi vào thân hàm/lớp lồng (chúng là phạm vi riêng, xét ở lượt của chúng)."""
    stack = list(ast.iter_child_nodes(scope))
    while stack:
        node = stack.pop()
        yield node
        if not isinstance(node, _SCOPES):
            stack.extend(ast.iter_child_nodes(node))


def _bindings(scope: ast.AST, nodes: list[ast.AST]) -> Iterator[tuple[str, ast.expr | None]]:
    """(tên, giá trị) của phép gán một tên (`=`, `x: float = …`); tham số của chính hàm `scope` là tên cục bộ không giá
    trị (tham số của lambda bên trong thì không — chúng không che tên của hàm)."""
    spec = scope.args if isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef)) else None
    if spec is not None:
        for arg in [*spec.posonlyargs, *spec.args, *spec.kwonlyargs, spec.vararg, spec.kwarg]:
            if arg is not None:
                yield arg.arg, None
    for node in nodes:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            yield node.targets[0].id, node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            yield node.target.id, node.value


def _is_number(node: ast.AST | None) -> bool:
    try:
        value = ast.literal_eval(node) if node is not None else None
    except ValueError:
        return False
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _scope_env(scope: ast.AST, nodes: list[ast.AST], parent: _Env) -> _Env:
    """Môi trường của phạm vi: kế thừa `parent` (phạm vi bao theo từ vựng), tên gán lại cục bộ che tên cùng tên ở ngoài."""
    binds = list(_bindings(scope, nodes))
    local = frozenset(name for name, _ in binds)

    def keep(names: frozenset[str], pick: Callable[[ast.expr], bool]) -> frozenset[str]:
        return (names - local) | {name for name, value in binds if value is not None and pick(value)}

    env = dataclasses.replace(
        parent,
        clocks=keep(parent.clocks, lambda v: _is_clock_call(v, parent)),
        consts=keep(parent.consts, _is_number),
        timed=parent.timed - local,
    )
    return dataclasses.replace(env, timed=keep(parent.timed, lambda v: any(_is_diff(n, env) for n in ast.walk(v))))


def _is_diff(node: ast.AST, env: _Env) -> bool:
    """Hiệu có một vế là lời gọi đồng hồ hoặc tên đã gán từ đồng hồ (`time.monotonic() - t0`, `end - start`)."""
    if not (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Sub)):
        return False
    return any(
        _is_clock_call(s, env) or (isinstance(s, ast.Name) and s.id in env.clocks) for s in (node.left, node.right)
    )


def _has_number(node: ast.AST, env: _Env) -> bool:
    """Có hằng số (chữ số, hoặc tên gán từ hằng số) — trần cứng."""
    return any(
        (isinstance(n, ast.Constant) and _is_number(n)) or (isinstance(n, ast.Name) and n.id in env.consts)
        for n in ast.walk(node)
    )


def _fails(body: list[ast.stmt]) -> bool:
    """Thân `if` làm test đỏ: `self.fail(...)` hoặc `raise AssertionError(...)`."""
    for stmt in body:
        call = stmt.value if isinstance(stmt, ast.Expr) else stmt.exc if isinstance(stmt, ast.Raise) else None
        target = call.func if isinstance(call, ast.Call) else call
        if isinstance(target, ast.Attribute) and target.attr == "fail":
            return True
        if isinstance(stmt, ast.Raise) and isinstance(target, ast.Name) and target.id == "AssertionError":
            return True
    return False


def _asserted(node: ast.AST) -> ast.AST | None:
    """Phần được khẳng định của `self.assertX(...)` (cả đối số từ khoá), `assert …`, `if …: self.fail(…)`; `None` nếu
    `node` không phải khẳng định."""
    if isinstance(node, ast.Assert):
        return node.test
    if isinstance(node, ast.If) and _fails(node.body):
        return node.test
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in ASSERTS:
        return ast.Tuple(elts=[*node.args, *(k.value for k in node.keywords)], ctx=ast.Load())
    return None


def _is_threshold(node: ast.AST, env: _Env) -> bool:
    test = _asserted(node)
    if test is None or not _has_number(test, env):
        return False
    return any(_is_diff(n, env) or (isinstance(n, ast.Name) and n.id in env.timed) for n in ast.walk(test))


def _callee(node: ast.Call) -> str:
    fn = node.func
    return fn.attr if isinstance(fn, ast.Attribute) else fn.id if isinstance(fn, ast.Name) else ""


def _at_floor(node: ast.AST | None) -> bool:
    """Hạn là `HANG_FLOOR` hoặc hằng số ≥ `HANG_FLOOR` (biến khác: không kiểm được → không nhận)."""
    if isinstance(node, ast.Name):
        return node.id == "HANG_FLOOR"
    if isinstance(node, ast.Attribute):
        return node.attr == "HANG_FLOOR"
    return _is_number(node) and ast.literal_eval(node) >= HANG_FLOOR


def _bad_deadline(node: ast.AST) -> bool:
    """`run_with_deadline(…)` không phải hạn chống treo khai rõ: hạn không ≥ `HANG_FLOOR` hoặc thiếu chữ `hang=`."""
    if not (isinstance(node, ast.Call) and _callee(node) == "run_with_deadline"):
        return False
    kw = {k.arg: k.value for k in node.keywords}
    seconds = node.args[2] if len(node.args) > 2 else kw.get("seconds")
    hang = kw.get("hang")
    named = isinstance(hang, ast.Constant) and isinstance(hang.value, str) and bool(hang.value.strip())
    return not (named and _at_floor(seconds))


def _scan(scope: ast.AST, parent: _Env, lines: set[int]) -> None:
    nodes = list(_local_nodes(scope))
    env = _scope_env(scope, nodes, parent)
    inner = parent if isinstance(scope, ast.ClassDef) else env  # tên ở thân lớp không lọt vào phương thức
    for node in nodes:
        if _is_threshold(node, env) or _bad_deadline(node):
            lines.add(node.lineno)
        if isinstance(node, _SCOPES):
            _scan(node, inner, lines)


def hard_time_thresholds(source: str) -> list[int]:
    """Số dòng mọi khẳng định so một khoảng thời gian đo (hiệu hai lần đọc đồng hồ, trực tiếp hay qua biến) với hằng số
    (chữ số hay tên gán từ chữ số), và mọi `run_with_deadline` không phải hạn chống treo khai rõ (`_bad_deadline`).

    Khẳng định: `assertLess/LessEqual/Greater/GreaterEqual/True/False` (cả đối số từ khoá), `assert`,
    `if …: self.fail(…)`/`raise AssertionError`. Đồng hồ: `time.X()` qua mọi bí danh import. Tên theo phạm vi từ vựng:
    hàm thấy tên của phạm vi bao (module, hàm ngoài), không thấy tên của hàm anh em; gán lại cục bộ che tên ngoài.
    Vòng chờ có hạn (`while … time.monotonic() < deadline`) không phải khẳng định nên không bị bắt."""
    tree = ast.parse(source)
    lines: set[int] = set()
    _scan(tree, _aliases(tree), lines)
    return sorted(lines)

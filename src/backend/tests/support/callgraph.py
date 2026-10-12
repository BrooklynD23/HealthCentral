"""Static call graph over api/, core/, modules/ for the HC-AUD-ORD-030 guard.

Name-based and deliberately over-approximate: `x.foo()` reaches every def named
`foo`. Unknown names are library calls and are ignored.
"""

from __future__ import annotations

import ast
from collections import defaultdict, deque
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
ROOTS = ("api", "core", "modules")
HTTP = {"get", "post", "put", "patch", "delete"}
# ponytail: heuristic for injected callables; misses a callable with another
# name. Upgrade: resolve types instead of names.
DYNAMIC_SUFFIXES = ("_factory", "_fn", "_callback")

Fn = tuple[str, str, ast.AST]  # relpath, qualname, node


def _walk_defs(tree: ast.AST, rel: str):
    def rec(node, prefix):
        for ch in ast.iter_child_nodes(node):
            if isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef)):
                q = f"{prefix}{ch.name}"
                yield (rel, q, ch)
                yield from rec(ch, q + ".")
            elif isinstance(ch, ast.ClassDef):
                yield from rec(ch, f"{prefix}{ch.name}.")
            else:
                yield from rec(ch, prefix)

    yield from rec(tree, "")


def _own_nodes(fn: ast.AST):
    """Nodes of fn's body, not descending into nested defs (they are indexed)."""
    stack = list(ast.iter_child_nodes(fn))
    while stack:
        n = stack.pop()
        yield n
        if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            stack.extend(ast.iter_child_nodes(n))


class Graph:
    def __init__(self, backend: Path = BACKEND, roots: tuple[str, ...] = ROOTS) -> None:
        self.by_name: dict[str, list[Fn]] = defaultdict(list)
        self.all: list[Fn] = []
        for root in roots:
            for path in sorted((backend / root).rglob("*.py")):
                rel = path.relative_to(backend).as_posix()
                for fn in _walk_defs(ast.parse(path.read_text(encoding="utf-8")), rel):
                    self.by_name[fn[2].name].append(fn)
                    self.all.append(fn)

    def calls(self, fn: Fn):
        return [n for n in _own_nodes(fn[2]) if isinstance(n, ast.Call)]

    def callee_name(self, call: ast.Call):
        f = call.func
        return f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else None

    def handlers(self) -> list[Fn]:
        out = []
        for fn in self.all:
            if not fn[0].startswith("api/"):
                continue
            for d in fn[2].decorator_list:
                f = d.func if isinstance(d, ast.Call) else d
                if isinstance(f, ast.Attribute) and f.attr in HTTP:
                    out.append(fn)
                    break
        return out

    def reachable(self, start: Fn) -> list[Fn]:
        seen = {(start[0], start[1])}
        order, q = [start], deque([start])
        while q:
            cur = q.popleft()
            for call in self.calls(cur):
                for tgt in self.by_name.get(self.callee_name(call) or "", []):
                    k = (tgt[0], tgt[1])
                    if k not in seen:
                        seen.add(k)
                        order.append(tgt)
                        q.append(tgt)
        return order

    def commits(self, fns: list[Fn]) -> bool:
        return any(self.callee_name(c) == "commit" and isinstance(c.func, ast.Attribute)
                   for fn in fns for c in self.calls(fn))

    def reaches(self, fns: list[Fn], name: str) -> bool:
        return any(self.callee_name(c) == name for fn in fns for c in self.calls(fn))

    def dynamic_sites(self, fns: list[Fn]) -> set[str]:
        sites = set()
        for fn in fns:
            args = fn[2].args
            params = {a.arg for a in args.posonlyargs + args.args + args.kwonlyargs}
            assigned = {t.id for n in _own_nodes(fn[2]) if isinstance(n, ast.Assign)
                        for t in n.targets if isinstance(t, ast.Name)}
            for c in self.calls(fn):
                f = c.func
                dyn = isinstance(f, (ast.Call, ast.Subscript))
                if isinstance(f, ast.Name):
                    # `cls(...)` is a classmethod constructor, not an injected callable.
                    dyn = f.id != "cls" and f.id in (params | assigned) and f.id not in self.by_name
                elif isinstance(f, ast.Attribute):
                    dyn = f.attr.endswith(DYNAMIC_SUFFIXES) and f.attr not in self.by_name
                if dyn:
                    sites.add(f"{fn[0]}::{fn[1]}::{ast.unparse(f)}")
                # A def passed as an argument is called somewhere we cannot see.
                # Skipped: FastAPI Depends(), the log_fn pattern (one named
                # exclusion on audit_and_commit), locals/params that merely share
                # a def's name, and attribute refs other than self.<def>.
                if self.callee_name(c) in {"Depends", "audit_and_commit", "audit_intent"}:
                    continue
                for v in list(c.args) + [k.value for k in c.keywords]:
                    if isinstance(v, ast.Name):
                        ref = v.id
                    elif isinstance(v, ast.Attribute) and isinstance(v.value, ast.Name) \
                            and v.value.id in {"self", "cls"}:
                        ref = v.attr
                    else:
                        continue
                    if ref in self.by_name and ref not in (params | assigned) \
                            and ref != self.callee_name(c):
                        sites.add(f"{fn[0]}::{fn[1]}::{ast.unparse(f)}({ref})")
        return sites

    def _commits_on(self, fn: Fn, var: str, seen: set) -> bool:
        """fn calls `<var>.commit()`, or passes `var` to a def that does."""
        if (fn[0], fn[1], var) in seen:
            return False
        seen.add((fn[0], fn[1], var))
        for c in self.calls(fn):
            f = c.func
            if (isinstance(f, ast.Attribute) and f.attr == "commit"
                    and isinstance(f.value, ast.Name) and f.value.id == var):
                return True
            for pos, v in enumerate(c.args):
                if isinstance(v, ast.Name) and v.id == var:
                    if self._passes(c, pos, None, seen):
                        return True
            for k in c.keywords:
                if isinstance(k.value, ast.Name) and k.value.id == var:
                    if self._passes(c, None, k.arg, seen):
                        return True
        return False

    def _passes(self, call: ast.Call, pos, kw, seen) -> bool:
        for tgt in self.by_name.get(self.callee_name(call) or "", []):
            a = tgt[2].args
            names = [x.arg for x in a.posonlyargs + a.args]
            if isinstance(call.func, ast.Attribute) and names[:1] in (["self"], ["cls"]):
                names = names[1:]
            param = kw if kw else (names[pos] if pos is not None and pos < len(names) else None)
            if param and self._commits_on(tgt, param, seen):
                return True
        return False

    def unscoped_vault_writes(self, h: Fn) -> bool:
        """Handler writes the vault session directly but nothing commits `profile_db`."""
        a = h[2].args
        if "profile_db" not in {x.arg for x in a.args + a.kwonlyargs}:
            return False
        for c in self.calls(h):
            f = c.func
            if not (isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name)
                    and f.value.id == "profile_db"):
                continue
            writes = f.attr in {"add", "delete"} or (
                f.attr == "execute" and c.args and isinstance(c.args[0], ast.Call)
                and self.callee_name(c.args[0]) in {"insert", "update", "delete"})
            if writes:
                return not self._commits_on(h, "profile_db", set())
        return False

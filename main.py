#!/usr/bin/env python3
"""
make_report.py · single-file project report generator  v4
────────────────────────────────────────────────────────

Report layout
1. Project structure (ASCII tree)
2. Function signatures
3. Class definitions  ← now lists attribute *types*
4. Dependencies
5. Combined source code  (only when --include-source is given)

Paths in SKIP_ALWAYS and any pattern in the project’s .gitignore are excluded.
"""

from __future__ import annotations

import argparse
import ast
import fnmatch
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Set

try:
    import tomllib  # Python ≥3.11
except ModuleNotFoundError:  # Python 3.8–3.10
    import tomli as tomllib  # type: ignore


# ────────────────────────── ignore config ──────────────────────────
SKIP_ALWAYS: Set[str] = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".idea",
    ".vscode",
    "node_modules",
    "dist",
    "build",
}
B_MID, B_LAST, P_PIPE, P_BLANK = "├── ", "└── ", "│   ", "    "


def load_gitignore(root: Path) -> List[str]:
    gi = root / ".gitignore"
    if not gi.exists():
        return []
    patterns: List[str] = []
    for raw in gi.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("!"):
            continue
        patterns.append(line.rstrip("/"))
    return patterns


def should_ignore(p: Path, root: Path, git_patterns: List[str]) -> bool:
    if set(p.parts) & SKIP_ALWAYS:
        return True
    rel = str(p.relative_to(root))
    return any(
        fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(rel, pat + "/**")
        for pat in git_patterns
    )


# ─────────────────────────── tree view ────────────────────────────
def ascii_tree(root: Path, git_patterns: List[str]) -> str:
    lines: List[str] = [root.name]

    def _walk(dir_path: Path, prefix: str = "") -> None:
        kids = sorted(
            [k for k in dir_path.iterdir() if not should_ignore(k, root, git_patterns)]
        )
        for i, child in enumerate(kids):
            conn = B_LAST if i == len(kids) - 1 else B_MID
            lines.append(f"{prefix}{conn}{child.name}")
            if child.is_dir():
                ext = P_BLANK if i == len(kids) - 1 else P_PIPE
                _walk(child, prefix + ext)

    _walk(root)
    return "\n".join(lines)


# ────────────────────── python file discovery ─────────────────────
def list_py_files(root: Path, git_patterns: List[str]) -> List[Path]:
    return sorted(
        p for p in root.rglob("*.py") if not should_ignore(p, root, git_patterns)
    )


# ─────────────────── class / func extraction helpers ──────────────
def _type_of_assign(node: ast.AST) -> str:
    """
    Return a string representation of the type annotation on an assignment node,
    or "Unknown" if none.
    """
    if isinstance(node, ast.AnnAssign) and node.annotation:
        return ast.unparse(node.annotation)
    if isinstance(node, (ast.AnnAssign, ast.Assign)) and getattr(
        node, "type_comment", None
    ):
        return node.type_comment or "Unknown"
    return "Unknown"


def _collect_class_attrs(cls: ast.ClassDef) -> List[Tuple[str, str]]:
    attrs: List[Tuple[str, str]] = []
    for stmt in cls.body:
        if isinstance(stmt, (ast.Assign, ast.AnnAssign)):
            targets = [stmt.target] if isinstance(stmt, ast.AnnAssign) else stmt.targets
            for tgt in targets:
                if isinstance(tgt, ast.Name):
                    attrs.append((tgt.id, _type_of_assign(stmt)))
    return attrs


def _collect_instance_attrs(cls: ast.ClassDef) -> List[Tuple[str, str]]:
    pairs: List[Tuple[str, str]] = []
    for stmt in cls.body:
        if isinstance(stmt, ast.FunctionDef) and stmt.name == "__init__":
            for node in ast.walk(stmt):
                if isinstance(node, (ast.Assign, ast.AnnAssign)):
                    targets = (
                        [node.target]
                        if isinstance(node, ast.AnnAssign)
                        else node.targets
                    )
                    for tgt in targets:
                        if (
                            isinstance(tgt, ast.Attribute)
                            and isinstance(tgt.value, ast.Name)
                            and tgt.value.id == "self"
                        ):
                            pairs.append((tgt.attr, _type_of_assign(node)))
    return pairs


def _collect_properties(cls: ast.ClassDef) -> List[Tuple[str, str]]:
    props: List[Tuple[str, str]] = []
    for stmt in cls.body:
        if isinstance(stmt, ast.FunctionDef):
            for dec in stmt.decorator_list:
                if (isinstance(dec, ast.Name) and dec.id == "property") or (
                    isinstance(dec, ast.Attribute) and dec.attr == "property"
                ):
                    ret = ast.unparse(stmt.returns) if stmt.returns else "Unknown"
                    props.append((stmt.name, ret))
    return props


def extract_from_file(file: Path, project_root: Path) -> Tuple[List[str], List[str]]:
    """
    Return two lists: [function-lines], [class-lines] extracted from *file*.
    """
    try:
        tree = ast.parse(
            file.read_text(encoding="utf-8", errors="ignore"), filename=str(file)
        )
    except SyntaxError:
        return [], []

    func_lines: List[str] = []
    cls_lines: List[str] = []
    rel = file.relative_to(project_root)

    for node in ast.walk(tree):
        # functions / async functions
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args: List[str] = []
            for a in node.args.args:
                ann = ast.unparse(a.annotation) if a.annotation else None
                args.append(f"{a.arg}: {ann}" if ann else a.arg)
            if node.args.vararg:
                args.append(f"*{node.args.vararg.arg}")
            if node.args.kwarg:
                args.append(f"**{node.args.kwarg.arg}")
            ret = ast.unparse(node.returns) if node.returns else "Unknown"
            func_lines.append(
                f"{rel}:{node.lineno}: {node.name}({', '.join(args)}) -> {ret}"
            )

        # classes
        elif isinstance(node, ast.ClassDef):
            header = f"{rel}:{node.lineno}: class {node.name}"
            bases = ", ".join(ast.unparse(b) for b in node.bases) if node.bases else ""
            if bases:
                header += f"({bases})"
            cls_lines.append(header)

            indent = "    • "

            # class-level attributes
            class_attrs = _collect_class_attrs(node)
            if class_attrs:
                cls_lines.append(
                    indent
                    + "class_attrs: "
                    + ", ".join(f"{n} -> {t}" for n, t in sorted(class_attrs))
                )

            # instance attributes
            inst_attrs = _collect_instance_attrs(node)
            if inst_attrs:
                cls_lines.append(
                    indent
                    + "instance_attrs: "
                    + ", ".join(f"{n} -> {t}" for n, t in sorted(inst_attrs))
                )

            # properties
            props = _collect_properties(node)
            if props:
                cls_lines.append(
                    indent + "properties: " + ", ".join(f"{n} -> {t}" for n, t in props)
                )

    return func_lines, cls_lines


# ───────────────────────── dependencies ──────────────────────────
def gather_dependencies(root: Path) -> List[str]:
    pj = root / "pyproject.toml"
    if pj.exists():
        data = tomllib.loads(pj.read_text(encoding="utf-8"))
        deps: List[str] = []
        deps.extend(data.get("project", {}).get("dependencies", []) or [])
        tool = data.get("tool", {})
        deps.extend(tool.get("poetry", {}).get("dependencies", {}).keys())
        deps.extend(tool.get("pdm", {}).get("dependencies", {}).keys())
        return sorted(set(deps))

    req = root / "requirements.txt"
    if req.exists():
        lines = [
            ln.split("#")[0].strip()
            for ln in req.read_text(encoding="utf-8").splitlines()
        ]
        return sorted({ln for ln in lines if ln})
    return []


# ───────────────────────── source combiner ───────────────────────
def combined_source(files: List[Path], project_root: Path) -> str:
    blocks: List[str] = []
    for f in files:
        blocks.append(f"# === {f.relative_to(project_root)} ===")
        blocks.append(f.read_text(encoding="utf-8", errors="ignore"))
        blocks.append("")
    return "\n".join(blocks)


# ───────────────────────────── main ─────────────────────────────
def main() -> None:
    ap = argparse.ArgumentParser(
        description="Generate a single-file project audit report."
    )
    ap.add_argument("root", type=Path, help="Project root directory")
    ap.add_argument(
        "--out", type=Path, default="project_context.txt", help="Output file"
    )
    ap.add_argument(
        "--include-source", action="store_true", help="Append full source code"
    )
    args = ap.parse_args()

    root = args.root.resolve()
    if not root.is_dir():
        sys.exit(f"[ERR] {root} is not a directory")

    git_patterns = load_gitignore(root)
    py_files = list_py_files(root, git_patterns)
    if not py_files:
        sys.exit("[ERR] No Python files found (after filtering).")

    # 1. Project structure
    report: List[str] = [
        "# ───────────── Project Structure ─────────────",
        ascii_tree(root, git_patterns),
    ]

    # 2 & 3. Functions and classes
    all_funcs: List[str] = []
    all_classes: List[str] = []
    for f in py_files:
        funcs, classes = extract_from_file(f, root)
        all_funcs.extend(funcs)
        all_classes.extend(classes)

    report.append("# ───────────── Function Signatures ─────────────")
    report.extend(all_funcs if all_funcs else ["<no functions found>"])

    report.append("# ───────────── Class Definitions ─────────────")
    report.extend(all_classes if all_classes else ["<no classes found>"])

    # 4. Dependencies
    report.append("# ───────────── Dependencies ─────────────")
    deps = gather_dependencies(root)
    report.extend(deps if deps else ["<none detected>"])

    # 5. Combined source (optional)
    if args.include_source:
        report.append("# ───────────── Combined Source ─────────────")
        report.append(combined_source(py_files, root))

    args.out.write_text("\n".join(report), encoding="utf-8")
    print(f"[OK] Report written → {args.out}")


if __name__ == "__main__":
    main()

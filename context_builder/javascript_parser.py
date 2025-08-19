#!/usr/bin/env python3
"""JavaScript parser for context builder.

This parser uses regex-based heuristics to extract function signatures,
class definitions, and default exports from JavaScript and JSX files.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Tuple


class JavaScriptParser:
    """Parser for JavaScript/JSX files using regex-based parsing."""

    def parse_file(self, file_path: Path) -> Tuple[List[str], List[str]]:
        """Parse a JavaScript file and return function and class definitions."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            return self._parse_with_regex(content, file_path)
        except Exception:
            return [], []

    def _parse_with_regex(self, content: str, file_path: Path) -> Tuple[List[str], List[str]]:
        func_lines: List[str] = []
        cls_lines: List[str] = []
        rel_path = file_path.name

        # Function patterns
        function_patterns = [
            # export default function foo(params)
            r"export\s+default\s+function\s*(\w+)?\s*\(([^)]*)\)",
            # export function foo(params)
            r"export\s+(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)",
            # regular function
            r"(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)",
            # const foo = (params) =>
            r"(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\(([^)]*)\)\s*=>",
            # export default (params) =>
            r"export\s+default\s*(?:async\s+)?\(([^)]*)\)\s*=>",
            # method definitions in classes/objects
            r"(\w+)\s*\(([^)]*)\)\s*{",
        ]

        # Class patterns
        class_patterns = [
            r"export\s+default\s+class\s+(\w+)?",
            r"export\s+class\s+(\w+)",
            r"class\s+(\w+)",
        ]

        # default export of identifier
        default_export_pattern = r"export\s+default\s+(\w+)\s*;"

        lines = content.split("\n")
        for i, raw in enumerate(lines, 1):
            line = raw.strip()
            if not line:
                continue

            # Check for functions
            matched = False
            for idx, pattern in enumerate(function_patterns):
                match = re.search(pattern, line)
                if match:
                    matched = True
                    if idx == 4:  # anonymous default exported arrow func
                        params = match.group(1).strip()
                        func_name = "<anonymous>"
                    else:
                        func_name = match.group(1)
                        params = match.group(2) if len(match.groups()) > 1 else ""
                        func_name = func_name if func_name else "<anonymous>"
                        params = params.strip()

                    params = self._clean_js_params(params)
                    func_lines.append(f"{rel_path}:{i}: {func_name}({params})")
                    break

            if matched:
                continue

            # Check for default export of identifier
            match = re.search(default_export_pattern, line)
            if match:
                func_lines.append(f"{rel_path}:{i}: export default {match.group(1)}")
                continue

            # Check for classes
            for pattern in class_patterns:
                match = re.search(pattern, line)
                if match:
                    class_name = match.group(1) if match.group(1) else "<anonymous>"
                    cls_lines.append(f"{rel_path}:{i}: class {class_name}")
                    break

        return func_lines, cls_lines

    def _clean_js_params(self, params: str) -> str:
        """Clean parameter string by removing default values and excess whitespace."""
        if not params:
            return ""

        param_list: List[str] = []
        current = ""
        paren_count = 0
        for char in params:
            if char == "(":
                paren_count += 1
            elif char == ")":
                paren_count -= 1
            elif char == "," and paren_count == 0:
                param_list.append(current.strip())
                current = ""
                continue
            current += char

        if current.strip():
            param_list.append(current.strip())

        cleaned: List[str] = []
        for param in param_list:
            if "=" in param:
                param = param.split("=", 1)[0].strip()
            cleaned.append(param.strip())

        return ", ".join(cleaned)


# Global parser instance
js_parser = JavaScriptParser()


def parse_file(file_path: Path) -> Tuple[List[str], List[str]]:
    """Convenience wrapper that uses the global :class:`JavaScriptParser`."""
    return js_parser.parse_file(file_path)

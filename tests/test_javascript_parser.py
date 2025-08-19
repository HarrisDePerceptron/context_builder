import textwrap
from pathlib import Path
from context_builder.javascript_parser import parse_file


def test_extract_functions(tmp_path: Path) -> None:
    code = textwrap.dedent(
        """
        export function foo(a,b) {}
        const bar = (x, y=1) => {};
        export default function (z) {}
        export default (q)=>{};
        function qux() {}
        export default qux;
        """
    ).strip()
    file_path = tmp_path / "sample.js"
    file_path.write_text(code)

    funcs, classes = parse_file(file_path)

    assert funcs == [
        "sample.js:1: foo(a, b)",
        "sample.js:2: bar(x, y)",
        "sample.js:3: <anonymous>(z)",
        "sample.js:4: <anonymous>(q)",
        "sample.js:5: qux()",
        "sample.js:6: export default qux",
    ]
    assert classes == []


def test_extract_classes(tmp_path: Path) -> None:
    code = textwrap.dedent(
        """
        export default class Foo {}
        class Bar extends Baz {}
        export class Baz {}
        """
    ).strip()
    file_path = tmp_path / "classes.js"
    file_path.write_text(code)

    funcs, classes = parse_file(file_path)

    assert funcs == []
    assert classes == [
        "classes.js:1: class Foo",
        "classes.js:2: class Bar",
        "classes.js:3: class Baz",
    ]

#!/usr/bin/env python3
"""Remove LLM-exported private-use citation markers from text files."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


MARKER_RE = re.compile("\ue200cite\ue202[^\ue201]*\ue201")
PRIVATE_MARKER_RE = re.compile("[\ue200\ue201\ue202]")
DEFAULT_SUFFIXES = {".md", ".markdown", ".mdx", ".txt"}


def iter_targets(paths: list[Path], recursive: bool) -> list[Path]:
    targets: list[Path] = []
    for path in paths:
        if path.is_file():
            targets.append(path)
            continue
        if path.is_dir() and recursive:
            targets.extend(
                p
                for p in path.rglob("*")
                if p.is_file() and p.suffix.lower() in DEFAULT_SUFFIXES
            )
            continue
        if path.is_dir():
            raise SystemExit(f"{path}: is a directory; pass --recursive to process it")
        raise SystemExit(f"{path}: no such file or directory")
    return sorted(dict.fromkeys(targets))


def analyze(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    text = data.decode("utf-8")
    markers = MARKER_RE.findall(text)
    cleaned = MARKER_RE.sub("", text)
    return {
        "path": str(path),
        "markers": len(markers),
        "private_marker_chars_after_clean": len(PRIVATE_MARKER_RE.findall(cleaned)),
        "changed": cleaned != text,
        "cleaned": cleaned,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Remove complete U+E200 cite U+E202 ... U+E201 citation artifacts."
    )
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--check", action="store_true", help="report only; do not write")
    parser.add_argument("--recursive", action="store_true", help="process Markdown-like files under directories")
    parser.add_argument("--json", action="store_true", help="emit JSON summary")
    args = parser.parse_args()

    targets = iter_targets(args.paths, args.recursive)
    results = []
    for path in targets:
        try:
            result = analyze(path)
        except UnicodeDecodeError as exc:
            raise SystemExit(f"{path}: not valid UTF-8: {exc}") from exc
        if not args.check and result["changed"]:
            path.write_bytes(str(result["cleaned"]).encode("utf-8"))
        result.pop("cleaned")
        results.append(result)

    total_markers = sum(int(r["markers"]) for r in results)
    total_private_after = sum(int(r["private_marker_chars_after_clean"]) for r in results)
    changed_files = sum(1 for r in results if r["changed"])
    summary = {
        "files": len(results),
        "changed_files": changed_files,
        "markers": total_markers,
        "private_marker_chars_after_clean": total_private_after,
        "results": results,
    }

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        action = "would remove" if args.check else "removed"
        print(
            f"{action} {total_markers} marker(s) across {len(results)} file(s); "
            f"changed_files={changed_files}; "
            f"{total_private_after} private marker char(s) would remain after cleanup"
        )
        for result in results:
            print(
                f"{result['path']}: markers={result['markers']}, "
                f"private_marker_chars_after_clean={result['private_marker_chars_after_clean']}"
            )

    if args.check and (total_markers or total_private_after):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

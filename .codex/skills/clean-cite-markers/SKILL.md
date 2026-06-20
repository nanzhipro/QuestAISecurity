---
name: clean-cite-markers
description: Remove LLM citation artifacts such as `citeturn31view0turn16view0` from Markdown or text reports while preserving all report content. Use when the user asks to delete citation markers, cite artifacts, `turn...view/search` markers, or private-use glyph sequences from generated files without editing the surrounding prose, tables, punctuation, or whitespace.
---

# Clean Cite Markers

## Overview

Use this skill to make citation-marker cleanup deterministic. The marker delimiters are private-use Unicode characters (`U+E200`, `U+E202`, `U+E201`), so copied glyphs and shell regexes can fail even when they look correct in the terminal.

## Workflow

1. Identify the target file or directory from the user request.
2. Run `scripts/clean_cite_markers.py --check <path>` first when practical to count complete markers and malformed marker characters.
3. Run `scripts/clean_cite_markers.py <path>` to remove only complete `U+E200 cite U+E202 ... U+E201` marker spans.
4. Run `scripts/clean_cite_markers.py --check <path>` again and confirm both marker counts are zero.
5. Report the number of removed markers and any limitations.

Never normalize text, reformat Markdown, trim whitespace, rewrite links, change line endings intentionally, or edit prose while using this skill. The task is deletion of out-of-band citation artifacts only.

Do not hardcode repository paths, report names, language-specific directory names, or concrete filenames into the workflow. Take all target files or directories from the user request.

## Script

Use the bundled script from the skill folder:

```bash
SKILL_DIR="<path-to-this-skill-folder>"
python3 "$SKILL_DIR/scripts/clean_cite_markers.py" --check "<target-file>"
python3 "$SKILL_DIR/scripts/clean_cite_markers.py" "<target-file>"
```

For a directory, use `--recursive` to process Markdown-like files:

```bash
python3 "$SKILL_DIR/scripts/clean_cite_markers.py" --recursive "<target-directory>"
```

`--check` exits nonzero when complete markers or malformed private marker characters remain. Malformed marker characters are reported but not removed automatically, because removing them could modify content outside the known artifact shape.

## Matching Rule

The safe removal pattern is:

```text
\uE200 cite \uE202 [anything except \uE201] \uE201
```

This corresponds visually to:

```text
citeturn31view0turn16view0
```

Use code points rather than visually copied glyphs whenever writing ad hoc checks.

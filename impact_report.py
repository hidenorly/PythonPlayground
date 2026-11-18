#!/usr/bin/env python3
# coding: utf-8
#   Copyright 2026 hidenorly
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# Summarize, per top-level subdirectory of a root (e.g. work/cdc/aaa,
# work/cdc/bbb, ...), which Removed components and which version-upped
# (Diffed) components each subdirectory references in its build files
# (CMakeLists.txt, *.cmake, *.bb, *.inc, meson.build, ...).
#
# Usage:
#   python3 impact_report.py --root ~/work/cdc --removed removed.txt --diffed diffed.txt
#   python3 impact_report.py --root ~/work/cdc --delta delta.md   # parse yocto-util output directly
#
# removed.txt: one component name per line.
# diffed.txt : TSV, one per line:  name <TAB> before <TAB> after
#              (whitespace-separated "name before after" also accepted)
#
# Output (markdown):
#   # aaa
#
#   * Impactable removed component: xxx, yyy, zzz
#   * Potentially impacted by version up : xxx(111->222), yyy(333->444)

import argparse
import os
import re
import sys

DEFAULT_PATTERNS = [
    "CMakeLists.txt", "*.cmake",
    "*.bb", "*.bbappend", "*.inc",
    "meson.build", "Makefile*", "*.mk",
]

TEXT_EXTS_SKIP = {".o", ".a", ".so", ".bin", ".elf", ".img", ".tar", ".gz", ".zip", ".xz", ".bz2", ".png", ".jpg", ".gif", ".ico", ".pdf"}


def load_removed(path):
    names = []
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            name = line.strip()
            if name and not name.startswith("#"):
                names.append(name)
    return names


def load_diffed(path):
    rows = []  # (name, before, after)
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t") if "\t" in line else line.split()
            if len(parts) >= 3:
                rows.append((parts[0], parts[1], parts[2]))
            elif len(parts) == 1:
                rows.append((parts[0], "", ""))
    return rows


def parse_delta_markdown(path):
    """Parse yocto-util.py markdown output (# Added / # Removed / # Diffed tables)."""
    with open(path, encoding="utf-8", errors="ignore") as f:
        text = f.read()

    def section(name, nxt):
        m = re.search(rf"^# {re.escape(name)}\s*$", text, re.M)
        if not m:
            return ""
        start = m.end()
        end = text.index(f"# {nxt}", start) if nxt and f"# {nxt}" in text[start:] else len(text)
        return text[start:end]

    def is_sep(cell):
        return bool(cell) and set(cell) <= set(":- ")

    removed = []
    for line in section("Removed", "Diffed").splitlines():
        line = line.strip()
        if line.startswith("|") and line.endswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if cells and cells[0] and cells[0] != "Removed" and not is_sep(cells[0]):
                removed.append(cells[0])

    diffed = []
    for line in section("Diffed", None).splitlines():
        line = line.strip()
        if line.startswith("|") and line.endswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) == 3 and cells[0] and cells[0] != "Componet" and not is_sep(cells[0]):
                diffed.append((cells[0], cells[1], cells[2]))
    return removed, diffed


def build_pattern(names, ignore_case=False):
    # longest first so e.g. "libusb1" wins over "libusb" at the same position
    uniq = sorted(set(names), key=len, reverse=True)
    if not uniq:
        return None
    alt = "|".join(re.escape(n) for n in uniq)
    flags = re.IGNORECASE if ignore_case else 0
    # word-ish boundary: hyphen/dot/plus may follow (libnl -> libnl-3.0 still hits)
    return re.compile(r"(?<![A-Za-z0-9_])(" + alt + r")(?![A-Za-z0-9_])", flags)


def iter_target_files(base, patterns):
    import fnmatch
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in (".git", ".hg", ".svn", "__pycache__")]
        for fn in filenames:
            if os.path.splitext(fn)[1].lower() in TEXT_EXTS_SKIP:
                continue
            if any(fnmatch.fnmatch(fn, p) for p in patterns):
                yield os.path.join(dirpath, fn)


def main():
    parser = argparse.ArgumentParser(description="Per-project impact summary for removed / version-upped Yocto components",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--root", required=True, help="root directory whose immediate subdirectories are the projects (e.g. ~/work/cdc)")
    parser.add_argument("--removed", help="removed.txt (one component per line)")
    parser.add_argument("--diffed", help="diffed.txt (TSV: name <TAB> before <TAB> after)")
    parser.add_argument("--delta", help="yocto-util.py markdown output; parse Removed/Diffed from it instead")
    parser.add_argument("--ignore-case", action="store_true", help="case-insensitive match (e.g. find_package(EXPAT))")
    parser.add_argument("--skip-empty", action="store_true", help="omit projects with no hits")
    parser.add_argument("--include", action="append", help="extra filename glob to scan (repeatable)")
    args = parser.parse_args()

    if args.delta:
        removed_names, diffed_rows = parse_delta_markdown(args.delta)
    else:
        if not args.removed and not args.diffed:
            parser.error("specify --delta, or --removed and/or --diffed")
        removed_names = load_removed(args.removed) if args.removed else []
        diffed_rows = load_diffed(args.diffed) if args.diffed else []

    diffed_map = {}
    diffed_order = []
    for name, before, after in diffed_rows:
        if name not in diffed_map:
            diffed_order.append(name)
        diffed_map[name] = (before, after)

    removed_re = build_pattern(removed_names, args.ignore_case)
    diffed_re = build_pattern(list(diffed_map.keys()), args.ignore_case)

    patterns = DEFAULT_PATTERNS + (args.include or [])
    root = os.path.realpath(os.path.expanduser(args.root))
    projects = sorted(d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d)))

    out_lines = []
    for proj in projects:
        base = os.path.join(root, proj)
        removed_hits = set()
        diffed_hits = set()
        for filepath in iter_target_files(base, patterns):
            try:
                with open(filepath, encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except OSError:
                continue
            if removed_re:
                removed_hits.update(m.group(1) for m in removed_re.finditer(content))
            if diffed_re:
                diffed_hits.update(m.group(1) for m in diffed_re.finditer(content))

        removed_out = [n for n in removed_names if n in removed_hits]
        diffed_out = [(n, diffed_map[n][0], diffed_map[n][1]) for n in diffed_order if n in diffed_hits]

        if args.skip_empty and not removed_out and not diffed_out:
            continue
        out_lines.append(f"# {proj}")
        out_lines.append("")
        if removed_out:
            out_lines.append("* Impactable removed component: " + ", ".join(removed_out))
        if diffed_out:
            out_lines.append("* Potentially impacted by version up : " + ", ".join(f"{n}({b}->{a})" for n, b, a in diffed_out))
        if not removed_out and not diffed_out:
            out_lines.append("* No removed / version-upped component references found")
        out_lines.append("")

    print("\n".join(out_lines).rstrip())
    return 0


if __name__ == "__main__":
    sys.exit(main())

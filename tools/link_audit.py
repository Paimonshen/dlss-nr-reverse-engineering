#!/usr/bin/env python3
"""link_audit.py — audit Markdown link integrity, anchor slugs and leak patterns.

A general-purpose, read-only checker for documentation trees. It answers four
questions about a set of Markdown files:

  1. Do every in-page anchor links (``](#some-heading)``) resolve to a real
     heading, using GitHub's heading-slug rules?
  2. Do every relative file links (``](path/to/file.md)``) point at a file that
     actually exists?
  3. Do any configured "leak" patterns appear (internal paths, internal file
     names, member/role names, scratch-file names, ...)?
  4. Do any configured "banned phrasing" patterns appear, optionally exempting
     specified files that legitimately define those patterns?

Nothing is ever written: this tool only reads. Exit code is 0 when the audit is
clean, 1 when any finding is reported.

Usage
-----
    # audit the current directory tree
    python tools/link_audit.py .

    # audit a docs tree and show per-file detail
    python tools/link_audit.py path/to/repo --verbose

    # add your own leak patterns and exempt files
    python tools/link_audit.py . --leak '_internal' --leak 'DRAFT_' \
        --banned 'we should probably' --exempt docs/glossary.md

    # machine-readable output
    python tools/link_audit.py . --json

Why this exists
---------------
Anchor slugs and relative-depth links are *conventions*: a single mistake made
once gets copied into every translation or every sibling document. Machine
re-derivation against the target platform's real rules catches that class of
error, which manual review reliably misses. See the reasoning in the project's
methodology notes.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Iterable

# ---------------------------------------------------------------------------
# Slugging — mirror GitHub's heading-anchor algorithm
# ---------------------------------------------------------------------------

_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"  # symbols & pictographs, supplemental
    "\U0001F000-\U0001F2FF"  # mahjong / dominoes / enclosed
    "\U00002600-\U000027BF"  # misc symbols, dingbats
    "\U0001F1E6-\U0001F1FF"  # regional indicators
    "\U00002B00-\U00002BFF"  # arrows, misc
    "\U0000FE0F"             # variation selector-16
    "\U0000200D"             # zero-width joiner
    "]+",
    flags=re.UNICODE,
)

# Punctuation GitHub strips when slugging (kept conservative and explicit).
_PUNCT_STRIP = set(
    "!\"#$%&'()*+,./:;<=>?@[\\]^`{|}~"      # ASCII punctuation
    "，。、；：？！“”‘’（）【】《》〈〉「」『』…—–·"  # CJK / typographic
)


def gh_slug(heading_text: str) -> str:
    """Return the GitHub-style anchor for a heading line or its text.

    Rules applied (matching GitHub's behaviour closely enough for auditing):
      * drop the leading ``#`` markers and surrounding whitespace;
      * drop emoji / symbol runs entirely (they do **not** leave a hyphen);
      * drop punctuation;
      * lowercase, then replace each whitespace run with a single ``-``.
    """
    s = heading_text.strip()
    s = re.sub(r"^#+\s*", "", s)
    s = _EMOJI_RE.sub("", s)
    kept = []
    for ch in s:
        if ch in _PUNCT_STRIP:
            continue
        kept.append(ch)
    s = "".join(kept).strip().lower()
    s = re.sub(r"\s+", "-", s)
    return "#" + s


# ---------------------------------------------------------------------------
# Markdown scanning
# ---------------------------------------------------------------------------

_FENCE_RE = re.compile(r"^\s*(```|~~~)")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_LINK_RE = re.compile(r"\]\(\s*([^)\s]+?)(?:\s+\"[^\"]*\")?\s*\)")

DEFAULT_LEAKS = (
    "F:\\",
    "C:\\Users",
    "_team",
    "ground_truth",
    "FINAL_STATUS",
    "INVENTORY",
    ".tmp_",
    "TODO_INTERNAL",
)

DEFAULT_BANNED = (
    "应该是",
    "通常是",
    "大概是",
    "极可能是",
    "大约为",
    "估计是",
)


def iter_markdown(root: str, skip_dirs: Iterable[str]) -> list[str]:
    """Collect .md files under root, skipping the given directory names."""
    skip = set(skip_dirs)
    out: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip]
        for name in filenames:
            if name.lower().endswith(".md"):
                out.append(os.path.join(dirpath, name))
    out.sort()
    return out


def strip_fences(text: str) -> str:
    """Blank out fenced code blocks so their contents are not scanned.

    Fenced blocks routinely contain shell snippets, sample paths and command
    text that would otherwise produce noise for the link and pattern checks.
    """
    lines = text.split("\n")
    out: list[str] = []
    in_fence = False
    for line in lines:
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            out.append("")
            continue
        out.append("" if in_fence else line)
    return "\n".join(out)


def read_text(path: str) -> str:
    """Read a text file, stripping a UTF-8 BOM if present.

    A byte-order mark would otherwise sit in front of the first line and cause
    the first heading of the file to be missed — a silent false negative.
    """
    raw = open(path, "rb").read()
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    return raw.decode("utf-8", errors="replace")


def audit_file(path: str, root: str, leaks: Iterable[str], banned: Iterable[str],
               exempt: set[str], scan_code_blocks: bool) -> dict:
    rel = os.path.relpath(path, root).replace(os.sep, "/")
    raw = read_text(path)
    text = raw if scan_code_blocks else strip_fences(raw)

    headings = set()
    for line in text.split("\n"):
        m = _HEADING_RE.match(line)
        if m:
            headings.add(gh_slug(m.group(2)))

    anchors_checked = anchors_broken = 0
    links_checked = links_broken = 0
    broken: list[str] = []

    for m in _LINK_RE.finditer(text):
        target = m.group(1)
        if target.startswith("#"):
            anchors_checked += 1
            if target not in headings:
                anchors_broken += 1
                broken.append(f"anchor not found: {target}")
            continue
        if target.startswith(("http://", "https://", "mailto:", "<")):
            continue
        links_checked += 1
        path_part = target.split("#", 1)[0].strip("`").replace("%20", " ")
        resolved = os.path.normpath(os.path.join(os.path.dirname(path), path_part))
        if not os.path.exists(resolved):
            links_broken += 1
            broken.append(f"file not found: {target}")

    leak_hits = []
    for pat in leaks:
        if pat and pat in text:
            leak_hits.append(pat)

    banned_hits = []
    if rel not in exempt:
        for pat in banned:
            if pat and pat in text:
                banned_hits.append(pat)

    return {
        "file": rel,
        "anchors_checked": anchors_checked,
        "anchors_broken": anchors_broken,
        "links_checked": links_checked,
        "links_broken": links_broken,
        "broken": broken,
        "leaks": leak_hits,
        "banned": banned_hits,
        "headings": len(headings),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="link_audit.py",
        description="Audit Markdown anchors, relative links and configured pattern leaks (read-only).",
    )
    ap.add_argument("root", nargs="?", default=".", help="directory to scan (default: .)")
    ap.add_argument("--skip", action="append", default=[".git", "node_modules", "venv", ".venv"],
                    help="directory name to skip (repeatable)")
    ap.add_argument("--leak", action="append", default=None,
                    help="extra leak pattern (repeatable); replaces the built-in defaults if given")
    ap.add_argument("--banned", action="append", default=None,
                    help="extra banned-phrasing pattern (repeatable); replaces the built-in defaults if given")
    ap.add_argument("--exempt", action="append", default=None,
                    help="repo-relative file to exempt from the banned-phrasing check (repeatable)")
    ap.add_argument("--scan-code-blocks", action="store_true",
                    help="also scan fenced code blocks (default: they are skipped)")
    ap.add_argument("--verbose", "-v", action="store_true", help="print per-file detail")
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = ap.parse_args(argv)

    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print(f"error: not a directory: {root}", file=sys.stderr)
        return 2

    leaks = list(args.leak) if args.leak else list(DEFAULT_LEAKS)
    banned = list(args.banned) if args.banned else list(DEFAULT_BANNED)
    exempt = set(args.exempt or [])

    files = iter_markdown(root, args.skip)
    results = [
        audit_file(p, root, leaks, banned, exempt, args.scan_code_blocks)
        for p in files
    ]

    totals = {
        "files": len(results),
        "anchors_checked": sum(r["anchors_checked"] for r in results),
        "anchors_broken": sum(r["anchors_broken"] for r in results),
        "links_checked": sum(r["links_checked"] for r in results),
        "links_broken": sum(r["links_broken"] for r in results),
        "files_with_leaks": sum(1 for r in results if r["leaks"]),
        "files_with_banned": sum(1 for r in results if r["banned"]),
    }
    findings = totals["anchors_broken"] + totals["links_broken"] \
        + totals["files_with_leaks"] + totals["files_with_banned"]

    if args.json:
        print(json.dumps({"root": root, "totals": totals,
                          "files": [r for r in results
                                    if r["broken"] or r["leaks"] or r["banned"]]},
                         ensure_ascii=False, indent=2))
        return 1 if findings else 0

    print(f"root: {root}")
    print(f"markdown files scanned: {totals['files']}")
    print()
    print("anchors : checked %d, broken %d" % (totals["anchors_checked"], totals["anchors_broken"]))
    print("links   : checked %d, broken %d" % (totals["links_checked"], totals["links_broken"]))
    print("leaks   : files with hits %d" % totals["files_with_leaks"])
    print("banned  : files with hits %d (exempt: %s)"
          % (totals["files_with_banned"], ", ".join(sorted(exempt)) or "none"))

    if args.verbose or findings:
        for r in results:
            if not (r["broken"] or r["leaks"] or r["banned"]):
                if args.verbose:
                    print(f"\n  ok  {r['file']}  (headings {r['headings']}, "
                          f"anchors {r['anchors_checked']}, links {r['links_checked']})")
                continue
            print(f"\n  !!  {r['file']}")
            for b in r["broken"]:
                print(f"        broken  {b}")
            for l in r["leaks"]:
                print(f"        leak    {l}")
            for b in r["banned"]:
                print(f"        banned  {b}")

    print()
    if findings:
        print(f"RESULT: {findings} finding group(s) — review the items above")
        return 1
    print("RESULT: clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

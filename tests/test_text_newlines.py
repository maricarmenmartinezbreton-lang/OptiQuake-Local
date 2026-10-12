"""Reject accidentally serialized line breaks in public documentation/configuration.

This intentionally checks literal PowerShell backtick-r/backtick-n sequences,
not legitimate Python or JSON escaped newline strings.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
EXTENSIONS = {".md", ".rst", ".txt", ".toml", ".yml", ".yaml", ".ini", ".cfg"}
EXACT_NAMES = {"COPYRIGHT", "LICENSE", ".gitattributes", ".gitignore"}
SKIP_PARTS = {".git", ".venv", "venv", "node_modules", "dist", "build", "__pycache__"}
BAD = chr(96) + "r" + chr(96) + "n"


def find_bad_newlines(root):
    findings = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(p in SKIP_PARTS for p in path.relative_to(root).parts):
            continue
        if path.suffix.lower() not in EXTENSIONS and path.name not in EXACT_NAMES:
            continue
        # Exclude this checker itself and generated/non-text files.
        try:
            content = path.read_text(encoding="utf-8-sig")
        except (UnicodeError, OSError):
            continue
        for line_no, line in enumerate(content.splitlines(), 1):
            if BAD in line:
                findings.append(f"{path.relative_to(root)}:{line_no}")
    return findings


def main():
    findings = find_bad_newlines(ROOT)
    if findings:
        print("FAIL: literal PowerShell CRLF escapes found in:")
        for finding in findings:
            print(" -", finding)
        return 1
    print("PASS: no accidental literal PowerShell CRLF sequences in docs/config")
    return 0


if __name__ == "__main__":
    sys.exit(main())

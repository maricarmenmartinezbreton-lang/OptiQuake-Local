#!/usr/bin/env python3
"""Release guardrails for OptiQuake Local."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
AUTHOR = "Lic. Juan Esteban Ramírez"
LICENSE_ID = "AGPL-3.0"

required = ["README.md", "COPYRIGHT", "CITATION.cff", "LICENSE", "pyproject.toml"]
for name in required:
    assert (ROOT / name).is_file(), f"Missing required file: {name}"

assert AUTHOR in (ROOT / "README.md").read_text(encoding="utf-8")
assert AUTHOR in (ROOT / "COPYRIGHT").read_text(encoding="utf-8")
assert LICENSE_ID in (ROOT / "CITATION.cff").read_text(encoding="utf-8")
assert "GNU AFFERO GENERAL PUBLIC LICENSE" in (ROOT / "LICENSE").read_text(encoding="utf-8")

secret_rx = re.compile(r"(ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9]{20,}|BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY)")
skip_parts = {".git", ".build-venv", ".wheel-test", "dist", "build", "__pycache__"}
for path in ROOT.rglob("*"):
    if not path.is_file() or any(part in skip_parts for part in path.parts):
        continue
    if path.suffix.lower() not in {".py", ".md", ".toml", ".json", ".yml", ".yaml", ".cff", ""}:
        continue
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue
    assert not secret_rx.search(text), f"Potential secret in {path.relative_to(ROOT)}"

print("RELEASE_INTEGRITY_OK")

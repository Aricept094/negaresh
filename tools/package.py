"""Make the release files in dist/:

- dist/negaresh/                 clean plugin folder (Claude Code plugin + marketplace, MCP server source, rules)
- dist/negaresh-<v>-py3-none-any.whl   the Python package with the MCP server
- dist/negaresh-skill.zip         the skill alone, for upload to Claude.ai or copy to ~/.claude/skills
- dist/negaresh-<v>.zip           the clean folder as one archive

Internal files (status notes, page-check logs, tools that read private sources) are left out.
Run tools/build.py first; this script checks that the bundle is current.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
OUT = DIST / "negaresh"

INCLUDE = [
    ".claude-plugin",
    ".mcp.json",
    ".gitignore",
    ".gitattributes",
    ".github",
    "clients",
    "gemini-extension.json",
    "GEMINI.md",
    "server.json",
    "skills",
    "src",
    "corpus",
    "tests",
    "docs/RULEBOOK__NEEDS-INPUT.md",
    "tools/build.py",
    "tools/package.py",
    "pyproject.toml",
    "README.md",
    "NOTICE.md",
    "CHANGELOG.md",
    "LICENSE",
]
SKIP_PARTS = {"__pycache__", ".pytest_cache", ".venv", "dist", "build"}
PRIVATE_MARKERS = ("C:\\", "/mnt/", "/home/", "/Users/", "_notes\\", "_notes/", "not-for-submission")


def _copy(rel: str) -> None:
    src = ROOT / rel
    dst = OUT / rel
    if src.is_dir():
        shutil.copytree(src, dst, ignore=lambda d, names: [n for n in names if n in SKIP_PARTS or n.endswith(".egg-info")])
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def _scan_private() -> list[str]:
    hits = []
    for p in OUT.rglob("*"):
        if p.is_file() and p.suffix in {".py", ".md", ".json", ".toml", ".txt"}:
            text = p.read_text(encoding="utf-8", errors="ignore")
            for m in PRIVATE_MARKERS:
                if m in text and p.name not in ("package.py", "build.py"):
                    hits.append(f"{p.relative_to(OUT)}: {m}")
    return hits


def main() -> int:
    check = subprocess.run([sys.executable, str(ROOT / "tools" / "build.py"), "--check"], capture_output=True, text=True)
    if check.returncode:
        print(check.stdout, check.stderr)
        return 1
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    for rel in INCLUDE:
        _copy(rel)
    hits = _scan_private()
    if hits:
        print("private markers found:\n  " + "\n  ".join(hits))
        return 1

    version = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
    for old in DIST.glob("negaresh-*"):
        old.unlink()

    skill_zip = DIST / "negaresh-skill.zip"
    with zipfile.ZipFile(skill_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted((OUT / "skills" / "negaresh").rglob("*")):
            if p.is_file():
                z.write(p, Path("negaresh") / p.relative_to(OUT / "skills" / "negaresh"))

    built = subprocess.run(["uv", "build", "--wheel", "--out-dir", str(DIST), str(OUT)], capture_output=True, text=True)
    if built.returncode:
        print(built.stdout, built.stderr)
        return 1
    for junk in list(OUT.glob("build")) + list(OUT.rglob("*.egg-info")):
        shutil.rmtree(junk, ignore_errors=True)

    folder_zip = DIST / f"negaresh-{version}.zip"
    with zipfile.ZipFile(folder_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(OUT.rglob("*")):
            if p.is_file():
                z.write(p, Path("negaresh") / p.relative_to(OUT))

    for p in sorted(DIST.iterdir()):
        print(p.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

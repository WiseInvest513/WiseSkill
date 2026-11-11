#!/usr/bin/env python3
"""Install complete local skill directories without replacing existing work."""
import argparse
import os
from pathlib import Path
import shutil
import sys


def main():
    root = Path(__file__).resolve().parents[1]
    skills = root / "skills"
    available = sorted(p.name for p in skills.iterdir() if (p / "SKILL.md").is_file())
    parser = argparse.ArgumentParser(description=__doc__)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--all", action="store_true")
    choice.add_argument("--video", action="store_true", help="Install the paired video and publishing skills")
    choice.add_argument("--skill", choices=available, action="append")
    parser.add_argument("--agent", choices=["codex", "claude"], default="codex")
    parser.add_argument("--dest", type=Path, help="Explicit skill directory; overrides --agent destination")
    args = parser.parse_args()
    names = available if args.all else (["wise-video", "wise-thumbnail"] if args.video else list(dict.fromkeys(args.skill)))
    # Cover templates share the background, and a complete video includes publishing.
    if any(name in names for name in ("wise-video", "wise-thumbnail")):
        names = list(dict.fromkeys(names + ["wise-video", "wise-thumbnail"]))
    default = Path.home() / ".claude" / "skills" if args.agent == "claude" else Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "skills"
    dest = (args.dest or default).expanduser().resolve()
    conflicts = [str(dest / name) for name in names if (dest / name).exists() or (dest / name).is_symlink()]
    if conflicts:
        parser.error("Refusing to overwrite existing skills: " + ", ".join(conflicts))
    for name in names:
        source = skills / name
        target = dest / name
        if target == source or source in target.parents:
            parser.error("Destination cannot be inside the source skill")
    dest.mkdir(parents=True, exist_ok=True)
    for name in names:
        shutil.copytree(skills / name, dest / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store", "node_modules"))
        print("Installed " + str(dest / name))
    print("Video runtime: see WiseSkill README before rendering.")
    return 0

if __name__ == "__main__":
    sys.exit(main())

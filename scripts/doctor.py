#!/usr/bin/env python3
"""Read-only, offline capability check; does not install or claim visual approval."""
import argparse
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys


def supported_node(version):
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)(?:[-+].*)?", version.strip())
    return bool(match and tuple(map(int, match.groups())) >= (22, 12, 0))


def command_version(name, args):
    path = shutil.which(name)
    if not path:
        return {"status": "missing", "hint": "Install " + name + " or add it to PATH"}
    try:
        proc = subprocess.run([path] + args, capture_output=True, text=True, timeout=10)
        output = (proc.stdout or proc.stderr).strip().splitlines()
        return {"status": "available" if proc.returncode == 0 else "error", "path": path,
                "version": output[0][:180] if output else "unknown"}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "error", "hint": str(exc)}


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill-root", type=Path, default=root / "skills/wise-video")
    parser.add_argument("--chrome", type=Path)
    parser.add_argument("--render", action="store_true", help="Require local render tools, not only planning")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    skill = args.skill_root.expanduser().resolve()
    checks = {"python": {"status": "available" if sys.version_info >= (3, 10) else "missing", "version": sys.version.split()[0]}}
    checks["skill"] = {"status": "available" if (skill / "SKILL.md").is_file() else "missing", "path": str(skill)}
    for name, flags in [("node", ["--version"]), ("npm", ["--version"]), ("ffmpeg", ["-version"]), ("ffprobe", ["-version"]), ("hyperframes", ["--version"])]:
        checks[name] = command_version(name, flags)
    # Local runtime binaries after npm install also count; no npx/network side effects.
    hf = skill / "node_modules/.bin" / ("hyperframes.cmd" if os.name == "nt" else "hyperframes")
    if hf.is_file():
        checks["hyperframes"] = {"status": "available", "path": str(hf), "hint": "Use the installed local CLI; run --version before rendering"}
    gsap = skill / "assets/background/assets/gsap.min.js"
    checks["gsap"] = {"status": "available" if gsap.is_file() else "missing", "hint": "In wise-video: npm ci --ignore-scripts && npm run prepare-assets"}
    candidates = [args.chrome, Path(os.environ["WISE_CHROME"]) if os.environ.get("WISE_CHROME") else None,
                  Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")]
    for name in ("google-chrome", "chromium", "chromium-browser", "chrome", "msedge"):
        found = shutil.which(name)
        if found:
            candidates.append(Path(found))
    for base in (os.environ.get("PROGRAMFILES"), os.environ.get("PROGRAMFILES(X86)"), os.environ.get("LOCALAPPDATA")):
        if base:
            candidates.append(Path(base) / "Google/Chrome/Application/chrome.exe")
    chrome = next((p for p in candidates if p and p.is_file()), None)
    checks["chrome"] = {"status": "available" if chrome else "missing", "path": str(chrome) if chrome else None, "hint": "Use --chrome PATH or WISE_CHROME; browser launch/WebGL not tested by doctor"}
    checks["visual_runtime"] = {"status": "not_checked", "hint": "Inspect Chinese fonts, WebGL, actual frames and audio alignment in target environment"}
    required = ["python", "skill"] + (["node", "ffmpeg", "ffprobe", "hyperframes", "gsap", "chrome"] if args.render else [])
    failures = [k for k in required if checks[k]["status"] != "available"]
    node_version = checks.get("node", {}).get("version", "")
    if args.render and checks["node"]["status"] == "available" and not supported_node(node_version):
        failures.append("node_22_12_required")
        checks["node"]["hint"] = "Locked browser dependencies require Node.js >=22.12.0"
    report = {"status": "blocked" if failures else "capabilities_available", "mode": "render" if args.render else "planning", "missing": failures, "checks": checks, "visual_approval": False}
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

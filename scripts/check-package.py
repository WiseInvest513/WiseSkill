#!/usr/bin/env python3
"""Validate shipped dependencies. This is not a video/artistic quality test."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import sys

SKILLS = ['wise-video', 'wise-thumbnail', 'wise-editorial-3d', 'wiseinvest-company-research', 'wiseinvest-stock-writer', 'wise-silver-glass']
IGNORED = {'.git', 'node_modules', '__pycache__', '.venv'}


def check(root):
    root = root.resolve()
    errors, count = [], 0
    for p in root.rglob('*'):
        if any(x in p.relative_to(root).parts for x in IGNORED):
            continue
        if p.is_symlink():
            errors.append('Symlink is not a portable asset: ' + str(p.relative_to(root)))
            continue
        if not p.is_file():
            continue
        count += 1
        if p.suffix.lower() in ('.mp3', '.wav', '.mp4', '.mov', '.m4a'):
            errors.append('History media in package: ' + str(p.relative_to(root)))
        if p.name.startswith('.env') and not p.name.endswith('.example'):
            errors.append('Environment credentials/config in package: ' + str(p.relative_to(root)))
        if p.stat().st_size > 90_000_000:
            errors.append('Unexpected large file: ' + str(p.relative_to(root)))
        if p.suffix.lower() not in ('.md', '.py', '.html', '.json', '.yaml', '.yml', '.cjs', '.js', '.css'):
            continue
        text = p.read_text(encoding='utf-8')
        if ('/Users/' in text or '/private/var/folders/' in text) and p.name != 'check-package.py':
            errors.append('Author path in ' + str(p.relative_to(root)))
        if p.suffix == '.md':
            for target in re.findall(r'\]\(([^\s)]+)\)', text):
                if '://' not in target and not target.startswith('#'):
                    if not (p.parent / target.split('#')[0]).exists():
                        errors.append('Broken link in ' + str(p.relative_to(root)) + ': ' + target)
            # Mandatory local learning mirrors were previously invisible to link-only checks.
            for target in re.findall(r'`(?:\.agents/skills/)?(_external/[^`\s]+)`', text):
                if not (root / 'skills' / target).exists():
                    errors.append('Unshipped external method in ' + str(p.relative_to(root)) + ': ' + target)
    contract = root / 'video-package.json'
    if not contract.is_file():
        errors.append('Missing video-package.json dependency contract')
    else:
        data = json.loads(contract.read_text(encoding='utf-8'))
        for rel in data['required_files']:
            resolved = (root / rel).resolve()
            if root not in resolved.parents or not resolved.is_file():
                errors.append('Missing required video resource: ' + rel)
    for manifest in root.glob('skills/*/assets/**/manifest.json'):
        data = json.loads(manifest.read_text(encoding='utf-8'))
        for rel, expected in data['files'].items():
            p = (manifest.parent / rel).resolve()
            if root not in p.parents or not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != expected:
                errors.append('Missing or modified template file: ' + str(manifest.relative_to(root)) + ': ' + rel)
    for name in SKILLS:
        p = root / 'skills' / name / 'SKILL.md'
        if not p.is_file() or not p.read_text(encoding='utf-8').startswith('---\nname: ' + name + '\n'):
            errors.append('Invalid skill entry: ' + name)
    return count, errors


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    count, errors = check(args.root)
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        raise SystemExit(1)
    print('PASS: %d files; required resources, links, template hashes, skill entries and excluded-media checks. Video quality not assessed.' % count)

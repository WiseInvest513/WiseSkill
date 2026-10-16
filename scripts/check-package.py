#!/usr/bin/env python3
"""Check the distribution without network, history projects or rendering."""
from pathlib import Path
import hashlib
import json
import re
import sys

root = Path(__file__).resolve().parents[1]
errors = []
count = 0
for p in root.rglob('*'):
    if not p.is_file() or any(x in p.parts for x in ('.git', 'node_modules', '__pycache__')):
        continue
    count += 1
    if p.suffix.lower() in ('.mp3', '.wav', '.mp4', '.mov', '.m4a'):
        errors.append('History media in package: ' + str(p.relative_to(root)))
    if p.suffix in ('.md', '.py', '.html', '.json', '.yaml', '.cjs'):
        text = p.read_text(encoding='utf-8')
        if '/Users/' in text or '/private/var/folders/' in text:
            # This checker itself names forbidden path prefixes.
            if p != Path(__file__).resolve():
                errors.append('Author path in ' + str(p.relative_to(root)))
        if p.suffix == '.md':
            for target in re.findall(r'\]\(([^\s)]+)\)', text):
                if '://' not in target and not target.startswith('#'):
                    if not (p.parent / target.split('#')[0]).exists():
                        errors.append('Broken link in ' + str(p.relative_to(root)) + ': ' + target)
for manifest in list(root.glob('skills/wise-video/assets/*/manifest.json')) + list(root.glob('skills/wise-thumbnail/assets/*/manifest.json')):
    data = json.loads(manifest.read_text(encoding='utf-8'))
    for rel, expected in data['files'].items():
        p = manifest.parent / rel
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != expected:
            errors.append('Missing or modified template file: ' + rel)
for name in ['wise-video', 'wise-thumbnail', 'wise-editorial-3d', 'wiseinvest-company-research']:
    p = root / 'skills' / name / 'SKILL.md'
    if not p.is_file() or not p.read_text(encoding='utf-8').startswith('---\nname: ' + name + '\n'):
        errors.append('Invalid skill entry: ' + name)
if errors:
    print('\n'.join(errors), file=sys.stderr)
    raise SystemExit(1)
print('PASS: %d source files; links, template hashes, skill entries and excluded-media checks.' % count)

#!/usr/bin/env python3
"""Read-only concept inventory wiring check; cannot judge extraction or visuals."""
import argparse
import json
from pathlib import Path

DECISIONS = {'text', 'exact_identity', 'concept_asset', 'data_chart', 'relationship'}


def validate(inventory, captions, asset_root, stage='planning'):
    errors, gaps = [], []
    def need(condition, message):
        if not condition:
            errors.append(message)

    source_ids = {c['caption_id'] for c in captions}
    scope = inventory.get('scope_caption_ids', sorted(source_ids))
    need(inventory.get('schema_version') == 1, 'unsupported schema_version')
    need(bool(scope) and len(scope) == len(set(scope)), 'scope is empty or duplicated')
    need(set(scope) == source_ids, 'scope must match supplied source captions; pass an explicitly scoped source for partial work')
    records = inventory.get('concepts', [])
    concepts = {c.get('id'): c for c in records}
    need(bool(records), 'concepts are empty')
    need(len(concepts) == len(records) and None not in concepts, 'duplicate/missing concept ID')
    for cid, concept in concepts.items():
        for key in ('id', 'name', 'category', 'reason', 'visual_role', 'representation_hint'):
            need(isinstance(concept.get(key), str) and bool(concept[key].strip()), f'{cid}: missing {key}')
        need(concept.get('decision') in DECISIONS, f'{cid}: invalid decision')
        need(isinstance(concept.get('aliases'), list), f'{cid}: aliases must be a list')
        occurrences = concept.get('caption_ids', [])
        need(bool(occurrences) and len(occurrences) == len(set(occurrences)), f'{cid}: missing/duplicate occurrences')
        need(set(occurrences) <= set(scope), f'{cid}: occurrence outside source scope')
        missing = concept.get('missing')
        need(isinstance(missing, bool), f'{cid}: missing must be boolean')
        assets = concept.get('available_asset', [])
        need(isinstance(assets, list), f'{cid}: available_asset must be a list')
        for asset in assets if isinstance(assets, list) else []:
            if not isinstance(asset, str) or not asset:
                errors.append(f'{cid}: asset must be a local path')
                continue
            path = Path(asset)
            path = path if path.is_absolute() else Path(asset_root) / path
            need(path.is_file(), f'{cid}: missing file: {asset}')
        if missing:
            need(bool(concept.get('missing_detail')), f'{cid}: missing_detail required')
            gaps.append({'id': cid, 'name': concept.get('name'), 'detail': concept.get('missing_detail')})
        elif concept.get('decision') in {'exact_identity', 'concept_asset'} and not assets:
            if concept.get('decision') == 'exact_identity':
                need(bool(concept.get('fallback_evidence')) and concept.get('fallback_approved') is True,
                     f'{cid}: exact identity has no file or approved fallback')
            else:
                need(bool(concept.get('implementation_basis')),
                     f'{cid}: concept asset has no file or code component basis')

    coverage = inventory.get('source_coverage', [])
    coverage_map = {r.get('caption_id'): r for r in coverage}
    need(len(coverage_map) == len(coverage) and set(coverage_map) == set(scope), 'source_coverage must match full scope once')
    for source_id, row in coverage_map.items():
        direct = row.get('concept_ids', [])
        context = row.get('context_concept_ids', [])
        need(bool(direct or context or row.get('text_only_reason')), f'caption {source_id}: unexplained coverage')
        need(set(direct + context) <= set(concepts), f'caption {source_id}: unknown concept reference')
        for ref in direct:
            if ref in concepts:
                need(source_id in concepts[ref].get('caption_ids', []), f'caption {source_id}: {ref} not an explicit occurrence; use context reference if appropriate')
    for cid, concept in concepts.items():
        for source_id in concept.get('caption_ids', []):
            row = coverage_map.get(source_id, {})
            need(cid in row.get('concept_ids', []), f'{cid}: occurrence {source_id} absent from source_coverage')
    if stage == 'assets':
        for gap in gaps:
            errors.append(f"{gap['id']}: required visual gap unresolved")
    return {'ok': not errors, 'stage': stage, 'concept_count': len(records), 'source_caption_count': len(scope),
            'errors': errors, 'unresolved_gaps': gaps,
            'limit': 'Checks declared coverage and file references only; extraction completeness, semantic fit, actual rendering and aesthetics require review.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inventory', type=Path)
    parser.add_argument('--captions', required=True, type=Path)
    parser.add_argument('--asset-root', required=True, type=Path)
    parser.add_argument('--stage', choices=['planning', 'assets'], default='planning')
    args = parser.parse_args()
    try:
        result = validate(json.loads(args.inventory.read_text(encoding="utf-8")), json.loads(args.captions.read_text(encoding="utf-8")), args.asset_root, args.stage)
    except (ValueError, KeyError, TypeError, AttributeError, OSError) as exc:
        result = {'ok': False, 'errors': ['invalid input: ' + str(exc)]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

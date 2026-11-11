#!/usr/bin/env python3
"""Fail-able sentence display-point + outro parity auditor for WiseVideo.

Catches the gap layout-hard-gates miss: structure passes while a whole spoken
sentence is covered by one text box / decorative frame, nouns/verbs lack
on-screen assets, or the ending invents farewell cards instead of
wise-outro-approved-v1.

Exit codes:
  0 = status pass
  1 = status fail
  2 = tool / input error
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

BOX_CLASS_RE = re.compile(
    r'class="[^"]*\b(?:claim|card|board|chip|hold|step|metric|result|panel)\b[^"]*"',
    re.I,
)
PROP_CLASS_RE = re.compile(r'class="[^"]*\b(?:prop|gauge-wrap)\b[^"]*"', re.I)
IMG_RE = re.compile(r'<img\b[^>]*>', re.I)
PATH_RE = re.compile(r'<(?:path|line|polyline|svg)\b', re.I)

VERB_HINTS = re.compile(
    r'买入|卖出|传导|回撤|加息|降息|增长|压缩|比较|汇聚|转移|关注|订阅|锁定|开启|告诉|发送|变成|进入|退出|持有|定投|纠结|进场|买完|买回|等跌|赚钱|再买|全部卖|全部买'
)
NOUN_SKIP = re.compile(r'^(的|了|呢|啊|哦|吗|吧|和|与|或|就|都|也|还|那|这|我|你|他|她|它|我们|大家)$')

OUTRO_PORTRAIT = re.compile(r'signature-portrait|(?<![\w-])assets/portrait\.png|wise-outro-approved', re.I)
OUTRO_SUBSCRIBE = re.compile(r'signature-subscribe|class="[^"]*\bsubscribe\b|object subscribe', re.I)
OUTRO_BYE = re.compile(r'signature-bye|我们下期再见')
OUTRO_TG = re.compile(r'community-tg|tg\.png|电报', re.I)


def _load_json(path: Optional[Path]) -> Optional[Dict[str, Any]]:
    if not path:
        return None
    return json.loads(path.read_text(encoding='utf-8'))


def _strip_tags(html: str) -> str:
    return re.sub(r'<[^>]+>', ' ', html)


def _object_block(html: str, obj_id: str) -> str:
    m = re.search(
        rf'id="{re.escape(obj_id)}"[^>]*>([\s\S]*?)(?=<div[^>]*id="|</section|</main|$)',
        html,
        re.I,
    )
    if m:
        return m.group(0)[:4000]
    m = re.search(rf'id="{re.escape(obj_id)}"[^>]*>', html, re.I)
    return m.group(0) if m else ''


def _block_has_asset(block: str) -> bool:
    if not block:
        return False
    if IMG_RE.search(block) or PROP_CLASS_RE.search(block) or PATH_RE.search(block):
        return True
    if re.search(r'class="[^"]*\b(?:prop|chart|gauge|path|flow)\b', block, re.I):
        return True
    return False


def _is_box_only(block: str) -> bool:
    if not block:
        return True
    if _block_has_asset(block):
        return False
    return bool(BOX_CLASS_RE.search(block))


def _uniq(xs: List[str]) -> List[str]:
    seen: Set[str] = set()
    out: List[str] = []
    for x in xs:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def _tokens_from_text(text: str) -> Dict[str, List[str]]:
    verbs = VERB_HINTS.findall(text or '')
    nouns: List[str] = []
    for m in re.finditer(r'[\u4e00-\u9fffA-Za-z0-9%]{2,}', text or ''):
        tok = m.group(0)
        if NOUN_SKIP.match(tok):
            continue
        if VERB_HINTS.fullmatch(tok):
            continue
        nouns.append(tok)
    return {'nouns': _uniq(nouns)[:12], 'verbs': _uniq(verbs)}


LAYOUT_AUDITOR = Path(__file__).resolve().parent / "audit_layout_hard_gates.py"

CHROME_OR_INTRO = {
    "wise-brand-logo", "caption", "surface", "earth", "motion", "copy-scrim",
    "halo", "halo-path", "seriesCard", "series-card", "root", "identity-group",
    "channel-mask", "rule",
}
IDENTITY_HINT = re.compile(r"纳指|标普|nasdaq|s&p|logo|徽章|频道", re.I)
SPOKEN_NEEDS_SCENE = re.compile(
    r"纠结|进场|买之前|买完|买回|卖出|卖|等跌|比较|赚钱|问题|持有|再买|全部卖|全部买"
)
PATH_LABEL_NEAR_PX = 90.0


def _layout_mod():
    spec = importlib.util.spec_from_file_location("audit_layout_hard_gates", LAYOUT_AUDITOR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _chrome_mod():
    spec = importlib.util.spec_from_file_location("audit_chrome_outro", Path(__file__).with_name("audit_chrome_outro.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _caption_records(captions):
    out = []
    for i, row in enumerate(captions or [], 1):
        if isinstance(row, dict):
            cid = int(row.get("caption_id") or i)
            start = row.get("start_ms")
            end = row.get("end_ms")
            if start is None:
                start = row.get("start")
            if end is None:
                end = row.get("end")
            if start is None:
                continue
            start = float(start)
            end = float(end if end is not None else start)
            # seconds if small
            if start < 600 and end <= 600:
                start, end = start * 1000, end * 1000
            out.append({"caption_id": cid, "start_ms": int(start), "end_ms": int(end), "text": row.get("text") or row.get("caption") or ""})
        elif isinstance(row, (list, tuple)) and len(row) >= 3:
            a, b, text = row[0], row[1], row[2]
            start = float(a)
            end = float(b)
            if start < 600 and end <= 600:
                start, end = start * 1000, end * 1000
            out.append({"caption_id": i, "start_ms": int(start), "end_ms": int(end), "text": text})
    return out


def opacity_at(cues, target, t_ms):
    events = [c for c in (cues or []) if c.get("target") == target]
    events.sort(key=lambda c: c.get("at_ms") or 0)
    op = 0.0
    for c in events:
        start = int(c.get("at_ms") or 0)
        dur = int(c.get("duration_ms") or 0)
        end = start + dur
        init = (c.get("initial") or {}).get("opacity")
        val = (c.get("values") or {}).get("opacity")
        if init is None and val is None:
            continue
        if t_ms < start:
            break
        if t_ms >= end:
            if val is not None:
                op = float(val)
            continue
        p = (t_ms - start) / dur if dur else 1.0
        a = float(init) if init is not None else op
        b = float(val) if val is not None else a
        op = a + (b - a) * p
    return op


def first_visible_ms(cues, target, threshold=0.15):
    events = [c for c in (cues or []) if c.get("target") == target]
    events.sort(key=lambda c: c.get("at_ms") or 0)
    for c in events:
        val = (c.get("values") or {}).get("opacity")
        init = (c.get("initial") or {}).get("opacity")
        if val is not None and float(val) >= threshold:
            return int(c.get("at_ms") or 0)
        if init is not None and float(init) >= threshold and (val is None or float(val) >= threshold):
            return int(c.get("at_ms") or 0)
    return None


def visible_targets_at(cues, t_ms, threshold=0.15):
    ids = {c.get("target") for c in (cues or []) if c.get("target")}
    return [tid for tid in ids if tid not in CHROME_OR_INTRO and opacity_at(cues, tid, t_ms) >= threshold]


def _is_identity_badge(el):
    if not el:
        return False
    text = (el.get("text") or "")
    classes = el.get("classes") or []
    if el.get("kind") in {"prop", "other"} or "prop" in classes:
        if IDENTITY_HINT.search(text) or IDENTITY_HINT.search(el.get("id") or ""):
            return True
        # short name-only label under a prop
        compact = re.sub(r"\s+", "", text)
        if "prop" in classes and 0 < len(compact) <= 8 and not SPOKEN_NEEDS_SCENE.search(text):
            return True
    return False


def audit_stale_identity(plan, html, cues, captions):
    """A spoken sentence cannot be covered only by a leftover identity badge with no noun+verb scene."""
    findings = []
    if not cues or not captions:
        return findings
    caps = {c["caption_id"]: c for c in _caption_records(captions)}
    lay = _layout_mod()
    cues_scene = lay._cues_scene_map(cues)
    elements = {e["id"]: e for e in lay.parse_html_boxes(html, cues_scene)}
    for st in plan.get("sentence_states") or []:
        sid = st.get("scene_id") or st.get("id") or "unknown"
        if sid in {"outro"}:
            continue
        for cid in st.get("caption_ids") or []:
            cap = caps.get(int(cid))
            if not cap:
                continue
            mid = (cap["start_ms"] + cap["end_ms"]) / 2.0
            visible = visible_targets_at(cues, mid)
            # ignore leftover intro pieces and series chrome
            content = []
            for tid in visible:
                if tid in CHROME_OR_INTRO:
                    continue
                el = elements.get(tid)
                scene = (el or {}).get("scene") or cues_scene.get(tid)
                if scene == "intro":
                    continue
                content.append(tid)
            if not content:
                # empty scene during a spoken sentence also fails if the line needs a scene
                if SPOKEN_NEEDS_SCENE.search(cap.get("text") or "") or VERB_HINTS.search(cap.get("text") or ""):
                    findings.append({
                        "code": "sentence_covered_by_stale_identity",
                        "gate": "sentence_display_points",
                        "scene_id": sid,
                        "evidence": {
                            "caption_id": cid,
                            "t_ms": int(mid),
                            "text": cap.get("text"),
                            "visible": content,
                            "reason": "no noun+verb scene during spoken sentence",
                        },
                    })
                continue
            els = [elements.get(tid) for tid in content if elements.get(tid)]
            badges = [e["id"] for e in els if _is_identity_badge(e)]
            verbish = [
                e["id"] for e in els
                if e.get("kind") in {"path", "text"} or any(
                    c in (e.get("classes") or []) for c in ("step", "claim", "metric-tile", "acct-tile", "chart-frame")
                )
            ]
            spoken = cap.get("text") or ""
            needs = bool(SPOKEN_NEEDS_SCENE.search(spoken) or VERB_HINTS.search(spoken))
            # leftover: every visible content object is an identity badge, no verb/noun scene,
            # and the badge entered before this caption started.
            if needs and content and not verbish and set(content) <= set(badges) or (
                needs and len(content) == 1 and content[0] in badges and not verbish
            ):
                leftover = []
                for tid in content:
                    entered = first_visible_ms(cues, tid)
                    if entered is not None and entered < cap["start_ms"] - 50:
                        leftover.append(tid)
                if leftover == content or (len(content) == 1 and content[0] in leftover):
                    findings.append({
                        "code": "sentence_covered_by_stale_identity",
                        "gate": "sentence_display_points",
                        "scene_id": sid,
                        "evidence": {
                            "caption_id": cid,
                            "t_ms": int(mid),
                            "text": spoken,
                            "visible": content,
                            "leftover_identity": leftover,
                            "reason": "spoken sentence covered only by leftover identity badge, no noun+verb scene",
                        },
                    })
    return findings


def _path_bbox(pts):
    if not pts:
        return None
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return {"x": min(xs), "y": min(ys), "right": max(xs), "bottom": max(ys), "width": max(xs) - min(xs), "height": max(ys) - min(ys)}


def _near(a, b, pad=PATH_LABEL_NEAR_PX):
    if not a or not b:
        return False
    dx = min(a["right"], b["right"]) - max(a["x"], b["x"])
    dy = min(a["bottom"], b["bottom"]) - max(a["y"], b["y"])
    if dx > -pad and dy > -pad:
        # reject "near" if the only nearby object is a large account board sitting above
        return True
    return False


def audit_unlabeled_strokes(html, plan, cues, captions):
    """Unlabeled leftover strokes that do not express the spoken action must FAIL."""
    findings = []
    lay = _layout_mod()
    cues_scene = lay._cues_scene_map(cues or [])
    elements = lay.parse_html_boxes(html, cues_scene)
    label_els = []
    for e in elements:
        if e["kind"] in {"text", "label"} and e.get("box"):
            # large account boards are not path labels
            if "acct-tile" in (e.get("classes") or []):
                continue
            label_els.append(e)
    verb_caps = []
    for cap in _caption_records(captions or []):
        text = cap.get("text") or ""
        if VERB_HINTS.search(text) or SPOKEN_NEEDS_SCENE.search(text):
            verb_caps.append(cap)

    for e in elements:
        if e["kind"] != "path" or not e.get("d"):
            continue
        if e["id"] in {"halo-path", "earth-path"}:
            continue
        pts = lay.parse_path_points(e["d"])
        bbox = _path_bbox(pts)
        # If this path is visible while a verb is spoken in the same scene, FAIL
        # unless a *visible* adjacent label expresses the action. Large account
        # boards are not path labels (see filter above).
        times = []
        if verb_caps and cues:
            for cap in verb_caps:
                mid = (cap["start_ms"] + cap["end_ms"]) / 2.0
                if opacity_at(cues, e["id"], mid) < 0.15:
                    continue
                labeled = False
                for lab in label_els:
                    if e.get("scene") and lab.get("scene") and e["scene"] != lab["scene"]:
                        continue
                    if cues and opacity_at(cues, lab["id"], mid) < 0.15:
                        continue
                    name_hit = lab["id"] in {e["id"] + "Label", e["id"] + "Step", e["id"].replace("Path", "Step")}
                    if name_hit or (bbox and _near(bbox, lab["box"])):
                        labeled = True
                        break
                if not labeled:
                    times.append({"caption_id": cap["caption_id"], "t_ms": int(mid), "text": cap.get("text")})
        elif not cues:
            labeled = False
            for lab in label_els:
                if e.get("scene") and lab.get("scene") and e["scene"] != lab["scene"]:
                    continue
                name_hit = lab["id"] in {e["id"] + "Label", e["id"] + "Step", e["id"].replace("Path", "Step")}
                if name_hit or (bbox and _near(bbox, lab["box"])):
                    labeled = True
                    break
            if not labeled:
                times = [{"caption_id": None, "t_ms": None, "text": None}]
        if times:
            findings.append({
                "code": "unlabeled_stroke",
                "gate": "sentence_display_points",
                "scene_id": e.get("scene"),
                "evidence": {
                    "path_id": e["id"],
                    "d": (e.get("d") or "")[:160],
                    "visible_during": times[:4],
                    "reason": "relationship path has no adjacent label and does not express the spoken action",
                },
            })
    return findings



def audit_sentence_states(
    plan: Dict[str, Any], html: str, inventory: Optional[Dict[str, Any]], strict: bool
) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    states = plan.get('sentence_states') or []
    concepts = {c.get('id'): c for c in (inventory or {}).get('concepts') or []}

    for st in states:
        sid = st.get('scene_id') or st.get('id') or 'unknown'
        focus = list(st.get('focus_object_ids') or [])
        dps = st.get('display_points') or []
        text = ' '.join(filter(None, [st.get('meaning_delta') or '', st.get('text') or '']))
        for bid in st.get('beat_ids') or []:
            for b in plan.get('beats') or []:
                if b.get('id') == bid:
                    text += ' ' + (b.get('text') or '') + ' ' + (b.get('meaning') or '')

        if sid in {'outro'} or (st.get('meaning_delta') or '').strip() in {'再见'}:
            continue

        blocks = [_object_block(html, oid) for oid in focus]
        any_asset = any(_block_has_asset(b) for b in blocks)
        all_boxish = bool(focus) and all(_is_box_only(b) for b in blocks if b) and not any_asset

        if focus and all_boxish:
            findings.append({
                'code': 'sentence_covered_by_lone_box',
                'gate': 'sentence_display_points',
                'scene_id': sid,
                'evidence': {
                    'focus_object_ids': focus,
                    'meaning_delta': (st.get('meaning_delta') or '')[:80],
                },
            })

        if not dps and strict and focus and not any_asset:
            cap_ids = set(st.get('caption_ids') or [])
            needs_asset = False
            for c in concepts.values():
                if set(c.get('caption_ids') or []) & cap_ids and c.get('decision') in {
                    'concept_asset', 'exact_identity', 'data_chart', 'relationship'
                }:
                    needs_asset = True
                    break
            if needs_asset or (st.get('meaning_delta') or ''):
                findings.append({
                    'code': 'display_points_unproven',
                    'gate': 'sentence_display_points',
                    'scene_id': sid,
                    'evidence': {
                        'focus_object_ids': focus,
                        'hint': 'no display_points and no img/prop in focus',
                    },
                })

        for dp in dps:
            kind = dp.get('kind')
            oid = dp.get('object_id')
            role = dp.get('role')
            if kind in {'concept_asset', 'exact_identity', 'data_chart'} and oid:
                if not _block_has_asset(_object_block(html, oid)):
                    findings.append({
                        'code': 'display_point_missing_asset',
                        'gate': 'sentence_display_points',
                        'scene_id': sid,
                        'evidence': dp,
                    })
            if role == 'verb' and kind in {'text', None, 'claim'}:
                findings.append({
                    'code': 'missing_verb_action',
                    'gate': 'sentence_display_points',
                    'scene_id': sid,
                    'evidence': dp,
                })

        toks = _tokens_from_text(text + ' ' + (st.get('meaning_delta') or ''))
        if toks['verbs'] and focus and not any_asset and all_boxish:
            findings.append({
                'code': 'missing_verb_action',
                'gate': 'sentence_display_points',
                'scene_id': sid,
                'evidence': {'verbs': toks['verbs'], 'focus_object_ids': focus},
            })

    return findings


def audit_decorative_boxes(html: str) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    for m in re.finditer(r'<div[^>]*class="([^"]*)"[^>]*>([\s\S]*?)</div>', html, re.I):
        cls, inner = m.group(1), m.group(2)
        if not re.search(r'\b(?:claim|card|chip|board)\b', cls, re.I):
            continue
        if re.search(r'\b(?:chapter|nav|brand|caption)\b', cls, re.I):
            continue
        if IMG_RE.search(inner) or PROP_CLASS_RE.search(inner) or PATH_RE.search(inner):
            continue
        text = re.sub(r'\s+', '', _strip_tags(inner))
        if 0 < len(text) <= 8:
            if re.fullmatch(r'[0-9.%+\-]+', text):
                continue
            id_m = re.search(r'id="([^"]+)"', m.group(0))
            findings.append({
                'code': 'decorative_box',
                'gate': 'no_decorative_boxes',
                'evidence': {
                    'id': id_m.group(1) if id_m else None,
                    'class': cls,
                    'text': text,
                },
            })
    seen = set()
    uniq = []
    for f in findings:
        key = (f['evidence'].get('id'), f['evidence'].get('text'))
        if key in seen:
            continue
        seen.add(key)
        uniq.append(f)
    return uniq


def audit_outro(html: str, plan: Optional[Dict[str, Any]], check_tg: bool) -> List[Dict[str, Any]]:
    """Legacy source heuristics only; no color, visibility, icon or timing proof."""
    findings: List[Dict[str, Any]] = []
    has_portrait = bool(OUTRO_PORTRAIT.search(html))
    has_sub = bool(OUTRO_SUBSCRIBE.search(html))
    farewell_bits = len(re.findall(r'欢迎关注|下期再见|我是\s*Wise|我是 Wise', html))
    if farewell_bits >= 2 and not (has_portrait and has_sub):
        findings.append({
            'code': 'outro_box_stack_farewell',
            'gate': 'outro_parity',
            'evidence': {
                'farewell_bits': farewell_bits,
                'has_portrait': has_portrait,
                'has_subscribe': has_sub,
            },
        })
    if not has_portrait:
        findings.append({'code': 'outro_missing_portrait', 'gate': 'outro_parity', 'evidence': {}})
    if not has_sub:
        findings.append({'code': 'outro_missing_red_subscribe', 'gate': 'outro_parity', 'evidence': {}})
    if 'wise-outro' not in html and 'signature-subscribe' not in html and 'signature-portrait' not in html:
        findings.append({'code': 'outro_template_missing', 'gate': 'outro_parity', 'evidence': {}})
    if re.search(r'下一期|下期我们', html):
        block = _object_block(html, 'nextClaim') or ''
        if block and not _block_has_asset(block):
            findings.append({
                'code': 'next_ep_text_only',
                'gate': 'outro_parity',
                'evidence': {'object_id': 'nextClaim'},
            })
    if check_tg and not OUTRO_TG.search(html):
        findings.append({
            'code': 'outro_missing_tg_community',
            'gate': 'outro_parity',
            'evidence': {'note': 'VO/plan requested TG'},
        })
    return findings


def audit(args: argparse.Namespace) -> Dict[str, Any]:
    html_path = Path(args.html)
    if not html_path.exists():
        raise FileNotFoundError(html_path)
    html = html_path.read_text(encoding='utf-8')
    plan = _load_json(Path(args.plan) if args.plan else None) or {}
    inventory = _load_json(Path(args.inventory) if args.inventory else None)

    findings: List[Dict[str, Any]] = []
    html_path = Path(args.html)
    lay = _layout_mod()
    cues = lay.discover_cues(html, html_path, Path(args.cues) if getattr(args, "cues", None) else None)
    captions = lay.discover_captions(html, html_path, Path(args.captions) if getattr(args, "captions", None) else None)
    if plan:
        findings.extend(audit_sentence_states(plan, html, inventory, strict=not args.legacy_soft))
        findings.extend(audit_stale_identity(plan, html, cues, captions))
    findings.extend(audit_unlabeled_strokes(html, plan, cues, captions))
    findings.extend(audit_decorative_boxes(html))
    dom_report = None
    if args.check_outro:
        blob = html
        if plan:
            blob += json.dumps(plan, ensure_ascii=False)
        need_tg = bool(re.search(r'电报|Telegram|交流群', blob))
        # Browser evidence supersedes legacy identifier regexes (portable templates
        # use data roles). Without it retain useful source-level negative checks.
        if not getattr(args, 'dom_evidence', None):
            findings.extend(audit_outro(html, plan, check_tg=need_tg and args.require_tg))
    if args.check_outro or getattr(args, 'check_series', False) or getattr(args, 'outro_policy', None):
        dom_report = _chrome_mod().from_args(args)
        if getattr(args, 'dom_evidence', None):
            evidence = _load_json(Path(args.dom_evidence)) or {}
            source_sha = evidence.get('document_sha256')
            if not source_sha:
                dom_report['not_checked'].append({'code': 'dom_source_hash_missing'})
                if dom_report['status'] == 'pass':
                    dom_report['status'] = 'not_checked'
                    dom_report['encode_allowed'] = False
            elif source_sha != hashlib.sha256(html_path.read_bytes()).hexdigest():
                dom_report['findings'].append({'code': 'dom_source_hash_mismatch', 'gate': 'sampled_chrome_outro',
                                               'evidence': {'html': str(html_path), 'captured_url': evidence.get('url')}})
                dom_report['status'] = 'fail'
                dom_report['encode_allowed'] = False
                dom_report['finding_count'] = len(dom_report['findings'])
        findings.extend(dom_report['findings'])

    dedup = []
    seen = set()
    for f in findings:
        key = (
            f.get('code'),
            f.get('scene_id'),
            json.dumps(f.get('evidence'), ensure_ascii=False, sort_keys=True)[:200],
        )
        if key in seen:
            continue
        seen.add(key)
        dedup.append(f)

    status = 'fail' if dedup else 'not_checked' if dom_report and dom_report['status'] != 'pass' else 'pass'
    return {
        'schema_version': 1,
        'status': status,
        'gates_doc': 'references/sentence-display-points.md + references/outro-parity.md',
        'finding_count': len(dedup),
        'findings': dedup,
        'encode_allowed': status == 'pass',
        'scope': 'source_heuristics_plus_optional_sampled_dom',
        'visual_review': 'not_checked',
        'chrome_outro': dom_report,
        'inputs': {
            'html': str(html_path),
            'plan': args.plan,
            'inventory': args.inventory,
            'check_outro': bool(args.check_outro),
        },
        'secondary_form_reference': 'https://www.youtube.com/@xuanyuancoding (method only)',
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--html', required=True)
    ap.add_argument('--plan')
    ap.add_argument('--inventory')
    ap.add_argument('--out')
    ap.add_argument('--check-outro', action='store_true')
    _chrome_mod().add_arguments(ap)
    ap.add_argument('--require-tg', action='store_true')
    ap.add_argument('--legacy-soft', action='store_true')
    ap.add_argument('--cues', help='optional cue_sheet.json')
    ap.add_argument('--captions', help='optional captions.local.json')
    ap.add_argument('--expect-fail', action='store_true')
    args = ap.parse_args()
    try:
        report = audit(args)
    except Exception as e:
        print(f'ERROR: {e}', file=sys.stderr)
        return 2
    out = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(out + '\n', encoding='utf-8')
    print(out)
    if args.expect_fail:
        return 0 if report['status'] == 'fail' else 1
    return 0 if report['status'] == 'pass' else 1


if __name__ == '__main__':
    sys.exit(main())

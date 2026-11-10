#!/usr/bin/env python3
"""Fail-able layout hard-gate auditor for WiseVideo.

Combines:
  1) static HTML / plan metaphor + lifecycle intent checks
  2) optional DOM measurements from measure_layout_dom.cjs

Exit codes:
  0 = status pass
  1 = status fail (hard gates tripped)
  2 = tool / input error
"""
from __future__ import annotations

import argparse
import os
import math
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


DEFAULT_CENTER_MIN = 0.46
DEFAULT_CENTER_MAX = 0.54
LEFT_BIAS_FAIL = 0.45
MIN_GAP_PX = 16
SIBLING_TOL = 0.08
SAFE_LEFT = 0.08
SAFE_RIGHT = 0.92
CONTRACT_SAFE_RIGHT_MIN = 0.88
EARTH_RESERVED_CENTER_MAX = 0.48
EARTH_RESERVED_RIGHT_MAX = 0.74
PATH_TEXT_PAD_PX = 6
CANVAS_W = 1920.0
CANVAS_H = 1080.0

METAPHOR_FAIL_PATTERNS = [
    # (concept regex on label/alt/text, asset regex on src, code detail)
    (re.compile(r"卖出|降息卖出"), re.compile(r"wallet", re.I), "sell_as_wallet"),
    (re.compile(r"回撤|腰斩"), re.compile(r"wallet", re.I), "drawdown_as_wallet"),
]

CHROME_IDS = {
    "wise-brand-logo", "caption", "surface", "earth", "motion",
    "copy-scrim", "halo", "halo-path", "seriesCard", "series-card",
    "root",
}
CHROME_CLASSES = {"series-card", "series-chip", "base", "rel", "caption"}
SKIP_SCENES_FOR_CENTER = {"intro"}


def _load_json(path: Optional[Path]) -> Optional[Dict[str, Any]]:
    if not path:
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _overlap_gap(a: Dict[str, float], b: Dict[str, float]) -> float:
    """Positive = separation; negative = overlap depth (min axis)."""
    dx = min(a["right"], b["right"]) - max(a["x"], b["x"])
    dy = min(a["bottom"], b["bottom"]) - max(a["y"], b["y"])
    if dx > 0 and dy > 0:
        return -min(dx, dy)
    # separation on at least one axis
    sep_x = 0.0 if dx > 0 else -dx
    sep_y = 0.0 if dy > 0 else -dy
    if dx <= 0 and dy <= 0:
        return (sep_x ** 2 + sep_y ** 2) ** 0.5
    return sep_x if dx <= 0 else sep_y


def _allowed_pair(a_id: str, b_id: str, allowed: List[Dict[str, Any]]) -> bool:
    for item in allowed or []:
        pair = set(item.get("ids") or item.get("object_ids") or [])
        if a_id in pair and b_id in pair:
            return True
    return False


def scan_html_metaphor(html: str) -> List[Dict[str, Any]]:
    findings = []
    # prop blocks with img + label
    for m in re.finditer(
        r'<div[^>]*class="[^"]*prop[^"]*"[^>]*>(.*?)</div>\s*(?=<div|</section|$)',
        html,
        re.S | re.I,
    ):
        block = m.group(0)
        src_m = re.search(r'<img[^>]*src="([^"]+)"[^>]*alt="([^"]*)"', block, re.I)
        if not src_m:
            src_m = re.search(r'<img[^>]*alt="([^"]*)"[^>]*src="([^"]+)"', block, re.I)
            if src_m:
                alt, src = src_m.group(1), src_m.group(2)
            else:
                continue
        else:
            src, alt = src_m.group(1), src_m.group(2)
        label_m = re.search(r'class="label"[^>]*>([^<]+)', block)
        label = (label_m.group(1) if label_m else "") + " " + (alt or "")
        for cre, are, code in METAPHOR_FAIL_PATTERNS:
            if cre.search(label) and are.search(src):
                findings.append({
                    "code": "metaphor_mismatch",
                    "detail": code,
                    "evidence": {"src": src, "label_or_alt": label.strip(), "snippet": block[:180]},
                    "gate": "metaphor",
                })
    # also catch explicit id methodWallet / resultWallet patterns in planless HTML
    if re.search(r'id="methodWallet"[^>]*>[\s\S]*?wallet\.png[\s\S]*?卖出', html):
        findings.append({
            "code": "metaphor_mismatch",
            "detail": "sell_as_wallet",
            "evidence": {"id": "methodWallet"},
            "gate": "metaphor",
        })
    if re.search(r'id="resultWallet"[^>]*>[\s\S]*?wallet\.png[\s\S]*?(回撤|腰斩)', html):
        findings.append({
            "code": "metaphor_mismatch",
            "detail": "drawdown_as_wallet",
            "evidence": {"id": "resultWallet"},
            "gate": "metaphor",
        })
    # de-dupe by detail+id/src
    uniq = []
    seen = set()
    for f in findings:
        key = (f["detail"], json.dumps(f.get("evidence"), sort_keys=True, ensure_ascii=False))
        if key in seen:
            continue
        seen.add(key)
        uniq.append(f)
    return uniq


def scan_plan_metaphor(plan: Optional[Dict[str, Any]], inventory: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    findings = []
    concepts = []
    if inventory and isinstance(inventory.get("concepts"), list):
        concepts = inventory["concepts"]
    if plan and isinstance(plan.get("concept_inventory"), dict):
        pass
    for c in concepts:
        name = str(c.get("name") or "") + " " + str(c.get("id") or "") + " " + str(c.get("representation_hint") or "")
        assets = " ".join(str(a) for a in (c.get("available_asset") or []))
        label = name
        for cre, are, code in METAPHOR_FAIL_PATTERNS:
            # concept name about sell/drawdown with wallet asset
            if cre.search(label) and are.search(assets):
                findings.append({
                    "code": "metaphor_mismatch",
                    "detail": code,
                    "evidence": {"concept_id": c.get("id"), "assets": c.get("available_asset")},
                    "gate": "metaphor",
                })
        # special: wallet-support used for drawdown
        if re.search(r"wallet", str(c.get("id") or ""), re.I) and re.search(r"回撤|腰斩|卖出", name):
            findings.append({
                "code": "metaphor_mismatch",
                "detail": "wallet_support_misuse",
                "evidence": {"concept_id": c.get("id"), "name": c.get("name")},
                "gate": "metaphor",
            })
        if re.search(r"wallet", assets, re.I) and re.search(r"回撤|腰斩|卖出", name + " " + str(c.get("representation_hint") or "")):
            findings.append({
                "code": "metaphor_mismatch",
                "detail": "wallet_in_hint",
                "evidence": {"concept_id": c.get("id")},
                "gate": "metaphor",
            })
    # HTML-free: method wallet in inventory as sell - also flag wallet-support for 回撤
    for c in concepts:
        if c.get("id") == "wallet-support":
            findings.append({
                "code": "metaphor_mismatch",
                "detail": "drawdown_as_wallet",
                "evidence": {
                    "concept_id": "wallet-support",
                    "name": c.get("name"),
                    "hint": c.get("representation_hint"),
                    "note": "semantic-v2 used wallet for 途中回撤",
                },
                "gate": "metaphor",
            })
    return findings


FALLBACK_BOX = {
    "step": (400.0, 88.0),
    "acct-tile": (440.0, 300.0),
    "metric-tile": (300.0, 92.0),
    "claim": (None, 90.0),
    "fact": (None, 52.0),
    "headline": (None, 64.0),
    "tile-img": (150.0, 150.0),
    "chart-frame": (None, 640.0),
    "prop": (None, None),
}


def _px_val(blob: str, prop: str):
    if not blob:
        return None
    m = re.search(rf'(?:^|[;\s]){re.escape(prop)}\s*:\s*([-\d.]+)px', ";" + blob)
    return float(m.group(1)) if m else None


def parse_css_box_defaults(html: str):
    defaults = {k: v for k, v in FALLBACK_BOX.items()}
    m = re.search(r"<style[^>]*>([\s\S]*?)</style>", html, re.I)
    if not m:
        return defaults
    for rm in re.finditer(r'([^{}@]+)\{([^{}]+)\}', m.group(1)):
        sel, body = rm.group(1), rm.group(2)
        w, h = _px_val(body, "width"), _px_val(body, "height")
        if w is None and h is None:
            continue
        for cls in re.findall(r'\.([A-Za-z0-9_-]+)', sel):
            prev = defaults.get(cls, (None, None))
            defaults[cls] = (w if w is not None else prev[0], h if h is not None else prev[1])
    return defaults


def _attr(attrs: str, name: str) -> str:
    # Require a non-identifier boundary so name "d" does not match "id=".
    m = re.search(rf'(?:^|[\s;]){re.escape(name)}="([^"]*)"', attrs or "", re.I)
    return m.group(1) if m else ""


def _classes(attrs: str):
    return [c for c in _attr(attrs, "class").split() if c]


def _scene_from_id(eid: str, cues_scene=None) -> str:
    if cues_scene and eid in cues_scene:
        return cues_scene[eid]
    if eid in {"seriesTitle"}:
        return "seriesQ"
    if eid.startswith("hook"):
        return "hook"
    if eid.startswith("acc"):
        return "accounts"
    if eid in {"chartFig", "holdResult", "dipResult", "gapResult"} or eid.startswith("chart"):
        return "chartMain"
    if eid.startswith("q") and len(eid) > 1 and eid[1].isupper():
        return "seriesQ"
    if eid in {"portrait", "hello", "channel", "channel-mask", "name", "rule", "welcome", "identity-group", "copy-scrim", "halo"}:
        return "intro"
    return "other"


def _text_inner(html: str, start: int, limit: int = 1800) -> str:
    chunk = html[start:start + limit]
    end = re.search(r"</(?:div|p|h1|h2|h3|span|g)>", chunk, re.I)
    if end:
        chunk = chunk[:end.end()]
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", chunk)).strip()


def parse_html_boxes(html: str, cues_scene=None):
    """Static boxes from inline left/top/width/height plus CSS class defaults."""
    defaults = parse_css_box_defaults(html)
    boxes = []
    for m in re.finditer(r'<(div|path|img|h1|h2|p|span|section|g)([^>]*id="([^"]+)"[^>]*)(/?)>', html, re.I):
        tag, attrs, eid = m.group(1).lower(), m.group(2), m.group(3)
        classes = _classes(attrs)
        style = _attr(attrs, "style")
        if eid in CHROME_IDS or (set(classes) & CHROME_CLASSES):
            kind = "chrome"
        elif tag == "path":
            kind = "path"
        elif "label" in classes:
            kind = "label"
        elif any(c in classes for c in ("step", "claim", "fact", "metric-tile", "headline", "acct-tile")):
            kind = "text"
        elif "prop" in classes or "chart-frame" in classes or "tile-img" in classes:
            kind = "prop"
        else:
            kind = "other"
        left = _px_val(style, "left")
        top = _px_val(style, "top")
        width = _px_val(style, "width")
        height = _px_val(style, "height")
        for cls in classes:
            dw, dh = defaults.get(cls, (None, None))
            if width is None and dw is not None:
                width = dw
            if height is None and dh is not None:
                height = dh
        if kind == "prop" and width is not None and height is None:
            height = width + 36.0
        d = _attr(attrs, "d")
        text = ""
        if tag != "path":
            text = _text_inner(html, m.end())
        label_box = None
        if kind == "prop" and width is not None and left is not None and top is not None:
            img_h = width
            label_box = {
                "x": left,
                "y": top + img_h + 4.0,
                "width": width,
                "height": 28.0,
                "right": left + width,
                "bottom": top + img_h + 32.0,
            }
        box = None
        if left is not None and top is not None and width and width > 1:
            h = height if height and height > 1 else 40.0
            box = {
                "x": left,
                "y": top,
                "width": width,
                "height": h,
                "right": left + width,
                "bottom": top + h,
            }
        boxes.append({
            "id": eid,
            "tag": tag,
            "classes": classes,
            "kind": kind,
            "scene": _scene_from_id(eid, cues_scene),
            "box": box,
            "label_box": label_box,
            "d": d,
            "text": text[:160],
        })
    return boxes


def _union(boxes):
    if not boxes:
        return None
    minx = min(b["x"] for b in boxes)
    miny = min(b["y"] for b in boxes)
    maxx = max(b["right"] for b in boxes)
    maxy = max(b["bottom"] for b in boxes)
    return {
        "x": minx,
        "y": miny,
        "width": maxx - minx,
        "height": maxy - miny,
        "cx": (minx + maxx) / 2.0,
        "cy": (miny + maxy) / 2.0,
        "center_x_ratio": (minx + maxx) / 2.0 / CANVAS_W,
        "center_y_ratio": (miny + maxy) / 2.0 / CANVAS_H,
        "left_ratio": minx / CANVAS_W,
        "right_ratio": maxx / CANVAS_W,
    }


def _effective_center_band(contract):
    raw_min = float((contract or {}).get("center_x_min", DEFAULT_CENTER_MIN))
    raw_max = float((contract or {}).get("center_x_max", DEFAULT_CENTER_MAX))
    return max(raw_min, DEFAULT_CENTER_MIN), min(raw_max, DEFAULT_CENTER_MAX)


def has_earth_background(html: str, contract=None) -> bool:
    if (contract or {}).get("earth_is_background") is True:
        return True
    if (contract or {}).get("earth_is_background") is False:
        return False
    return bool(re.search(r'\bid="earth"|earth-bg|wise-background|globe', html, re.I))


def scan_contract_layout_floors(contract):
    findings = []
    if not contract:
        return findings
    raw_min = float(contract.get("center_x_min", DEFAULT_CENTER_MIN))
    raw_max = float(contract.get("center_x_max", DEFAULT_CENTER_MAX))
    if raw_min < DEFAULT_CENTER_MIN - 1e-9 or raw_max > DEFAULT_CENTER_MAX + 1e-9:
        findings.append({
            "code": "contract_loosens_center_band",
            "detail": f"contract center band [{raw_min},{raw_max}] is looser than skill floor [{DEFAULT_CENTER_MIN},{DEFAULT_CENTER_MAX}]",
            "evidence": {"center_x_min": raw_min, "center_x_max": raw_max, "floor": [DEFAULT_CENTER_MIN, DEFAULT_CENTER_MAX]},
            "gate": "safe_frame_center",
        })
    sf = contract.get("safe_frame_x_ratio") or []
    if len(sf) == 2 and float(sf[1]) < CONTRACT_SAFE_RIGHT_MIN:
        findings.append({
            "code": "contract_reserves_earth_column",
            "detail": f"safe_frame_x_ratio right={float(sf[1]):.2f} < {CONTRACT_SAFE_RIGHT_MIN} reserves a right column for Earth",
            "evidence": {"safe_frame_x_ratio": sf, "min_right": CONTRACT_SAFE_RIGHT_MIN},
            "gate": "safe_frame_center",
        })
    return findings


def _center_findings_for_union(union, *, layout_mode, earth_bg, t, group, source):
    findings = []
    if not union or layout_mode != "center":
        return findings
    cxr = float(union["center_x_ratio"])
    rratio = float(union.get("right_ratio") or 0)
    ev = {"t": t, "union": union, "group": group, "source": source, "layout_mode": layout_mode}
    if earth_bg and cxr < EARTH_RESERVED_CENTER_MAX and rratio <= EARTH_RESERVED_RIGHT_MAX:
        findings.append({
            "code": "earth_reserved_column",
            "detail": (
                f"{group} center_x_ratio={cxr:.3f} < {EARTH_RESERVED_CENTER_MAX} and "
                f"right_ratio={rratio:.3f} <= {EARTH_RESERVED_RIGHT_MAX} (Earth treated as a reserved right column)"
            ),
            "evidence": ev,
            "gate": "safe_frame_center",
        })
    if cxr < LEFT_BIAS_FAIL:
        findings.append({
            "code": "left_bias_against_earth_bg",
            "detail": f"{group} center_x_ratio={cxr:.3f} < {LEFT_BIAS_FAIL}",
            "evidence": ev,
            "gate": "safe_frame_center",
        })
    elif not (DEFAULT_CENTER_MIN <= cxr <= DEFAULT_CENTER_MAX):
        findings.append({
            "code": "content_center_outside_band",
            "detail": f"{group} center_x_ratio={cxr:.3f} not in [{DEFAULT_CENTER_MIN},{DEFAULT_CENTER_MAX}]",
            "evidence": ev,
            "gate": "safe_frame_center",
        })
    return findings


def scan_html_scene_centers(html: str, contract=None, cues_scene=None):
    """Static full-canvas centering + Earth-as-column gates (no live DOM required)."""
    findings = []
    layout_mode = (contract or {}).get("layout_mode", "center")
    earth_bg = has_earth_background(html, contract)
    elements = parse_html_boxes(html, cues_scene)
    content = [e for e in elements if e.get("box") and e["kind"] not in {"chrome", "path"}]

    by_scene = {}
    for e in content:
        if e["scene"] in SKIP_SCENES_FOR_CENTER or e["scene"] == "other":
            continue
        by_scene.setdefault(e["scene"], []).append(e["box"])
    for scene, boxes in by_scene.items():
        union = _union(boxes)
        if union:
            findings.extend(_center_findings_for_union(
                union, layout_mode=layout_mode, earth_bg=earth_bg, t=None,
                group=f"scene:{scene}", source="static_html",
            ))

    id_map = {e["id"]: e for e in content}
    groups = []
    for sset in (contract or {}).get("sibling_sets") or []:
        ids = [i for i in (sset.get("ids") or []) if i in id_map and id_map[i].get("box")]
        if len(ids) >= 2:
            groups.append((sset.get("id") or sset.get("scene") or "+".join(ids), ids))
    acct = [e["id"] for e in content if "acct-tile" in (e.get("classes") or [])]
    if len(acct) >= 2:
        groups.append(("account_boards", acct))
    chart_ids = []
    seen_g = set()
    for e in content:
        if (
            "chart-frame" in (e.get("classes") or [])
            or e["id"] in {"chartFig", "holdResult", "dipResult", "gapResult"}
            or ("metric-tile" in (e.get("classes") or []) and e["scene"] == "chartMain")
        ):
            if e["id"] not in seen_g:
                seen_g.add(e["id"])
                chart_ids.append(e["id"])
    if any(i in id_map and ("chart-frame" in id_map[i]["classes"] or i == "chartFig") for i in chart_ids) and len(chart_ids) >= 2:
        groups.append(("chart_and_result_chips", chart_ids))

    seen_key = set()
    for name, ids in groups:
        key = tuple(sorted(ids))
        if key in seen_key:
            continue
        seen_key.add(key)
        union = _union([id_map[i]["box"] for i in ids if i in id_map and id_map[i].get("box")])
        if union:
            findings.extend(_center_findings_for_union(
                union, layout_mode=layout_mode, earth_bg=earth_bg, t=None,
                group=name, source="primary_group",
            ))
    return findings


def _cubic(p0, p1, p2, p3, n: int = 24):
    pts = []
    for i in range(n + 1):
        t = i / n
        u = 1 - t
        pts.append((
            u**3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t**3 * p3[0],
            u**3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t**3 * p3[1],
        ))
    return pts


def parse_path_points(d: str):
    if not d:
        return []
    tokens = re.findall(r"[A-Za-z]|[-+]?(?:\d*\.\d+|\d+)(?:e[-+]?\d+)?", d)
    pts = []
    i = 0
    cx = cy = 0.0
    start = (0.0, 0.0)
    cmd = None

    def num():
        nonlocal i
        v = float(tokens[i])
        i += 1
        return v

    while i < len(tokens):
        t = tokens[i]
        if re.match(r"[A-Za-z]$", t):
            cmd = t
            i += 1
            if cmd in "Zz":
                pts.append(start)
                cx, cy = start
                continue
        if cmd is None:
            break
        try:
            if cmd in "Mm":
                x, y = num(), num()
                if cmd == "m" and pts:
                    x += cx
                    y += cy
                cx, cy = x, y
                start = (cx, cy)
                pts.append((cx, cy))
                cmd = "L" if cmd == "M" else "l"
            elif cmd in "Ll":
                x, y = num(), num()
                if cmd == "l":
                    x += cx
                    y += cy
                cx, cy = x, y
                pts.append((cx, cy))
            elif cmd in "Hh":
                x = num()
                if cmd == "h":
                    x += cx
                cx = x
                pts.append((cx, cy))
            elif cmd in "Vv":
                y = num()
                if cmd == "v":
                    y += cy
                cy = y
                pts.append((cx, cy))
            elif cmd in "Cc":
                x1, y1, x2, y2, x, y = num(), num(), num(), num(), num(), num()
                if cmd == "c":
                    x1, y1, x2, y2, x, y = x1 + cx, y1 + cy, x2 + cx, y2 + cy, x + cx, y + cy
                pts.extend(_cubic((cx, cy), (x1, y1), (x2, y2), (x, y)))
                cx, cy = x, y
            elif cmd in "Qq":
                x1, y1, x, y = num(), num(), num(), num()
                if cmd == "q":
                    x1, y1, x, y = x1 + cx, y1 + cy, x + cx, y + cy
                for k in range(13):
                    tt = k / 12
                    u = 1 - tt
                    pts.append((u * u * cx + 2 * u * tt * x1 + tt * tt * x, u * u * cy + 2 * u * tt * y1 + tt * tt * y))
                cx, cy = x, y
            elif cmd in "Ss":
                x2, y2, x, y = num(), num(), num(), num()
                if cmd == "s":
                    x2, y2, x, y = x2 + cx, y2 + cy, x + cx, y + cy
                pts.extend(_cubic((cx, cy), (cx, cy), (x2, y2), (x, y)))
                cx, cy = x, y
            else:
                if i < len(tokens) and re.match(r"[-+]?(?:\d|\.)", tokens[i]):
                    i += 1
                else:
                    break
        except (IndexError, ValueError):
            break
    return pts


def _point_in_box(x, y, box, pad=PATH_TEXT_PAD_PX) -> bool:
    return (box["x"] - pad) <= x <= (box["right"] + pad) and (box["y"] - pad) <= y <= (box["bottom"] + pad)


def scan_path_text_collisions(html: str, cues_scene=None):
    """FAIL when a relationship path/line covers or collides with text (labels, steps, claims)."""
    findings = []
    elements = parse_html_boxes(html, cues_scene)
    text_targets = []
    for e in elements:
        if e["kind"] == "chrome":
            continue
        if e.get("label_box") and (e.get("text") or e["kind"] == "prop"):
            text_targets.append((e["id"] + "#label", e["label_box"], e["scene"]))
        if e["kind"] == "text" and e.get("box"):
            text_targets.append((e["id"], e["box"], e["scene"]))
        if e["kind"] == "label" and e.get("box"):
            text_targets.append((e["id"], e["box"], e["scene"]))
    for e in elements:
        if e["kind"] != "path" or not e.get("d"):
            continue
        if e["id"] in {"halo-path", "earth-path"}:
            continue
        pts = parse_path_points(e["d"])
        if not pts:
            continue
        hits = []
        for tid, box, scene in text_targets:
            if scene and e["scene"] and scene != e["scene"] and scene != "other" and e["scene"] != "other":
                continue
            for (x, y) in pts:
                if _point_in_box(x, y, box):
                    hits.append({"text_id": tid, "scene": scene, "point": [round(x, 1), round(y, 1)]})
                    break
        if hits:
            findings.append({
                "code": "path_covers_text",
                "detail": f"path {e['id']} covers/collides with " + ", ".join(h["text_id"] for h in hits),
                "evidence": {"path_id": e["id"], "scene": e["scene"], "hits": hits[:6], "d": (e["d"] or "")[:160]},
                "gate": "path_text_collision",
            })
    return findings


def _cues_scene_map(cues):
    out = {}
    for c in cues or []:
        tid, sid = c.get("target"), c.get("scene_id")
        if tid and sid and tid not in out:
            out[tid] = sid
    return out


def extract_js_array(html: str, name: str):
    m = re.search(rf"const\s+{re.escape(name)}\s*=\s*\[", html)
    if not m:
        return None
    start = html.find("[", m.start())
    depth = 0
    for i, ch in enumerate(html[start:]):
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                blob = html[start:start + i + 1]
                try:
                    return json.loads(blob)
                except json.JSONDecodeError:
                    return None
    return None


def discover_cues(html: str, html_path=None, explicit=None):
    if explicit and Path(explicit).exists():
        data = json.loads(Path(explicit).read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data.get("cues") or []
        return data if isinstance(data, list) else []
    if html_path:
        side = Path(html_path).parent / "cue_sheet.json"
        if side.exists():
            data = json.loads(side.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data.get("cues") or []
            return data if isinstance(data, list) else []
    return extract_js_array(html, "cues") or []


def discover_captions(html: str, html_path=None, explicit=None):
    if explicit and Path(explicit).exists():
        data = json.loads(Path(explicit).read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("captions") or data.get("cues") or []
    if html_path:
        for name in ("captions.local.json", "captions.json"):
            side = Path(html_path).parent / name
            if side.exists():
                data = json.loads(side.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    return data
                if isinstance(data, dict):
                    return data.get("captions") or data.get("cues") or []
    raw = extract_js_array(html, "captions") or []
    out = []
    for i, row in enumerate(raw, 1):
        if isinstance(row, (list, tuple)) and len(row) >= 3:
            a, b, text = row[0], row[1], row[2]
            start_ms = int(round(float(a) * 1000)) if float(a) < 1000 else int(a)
            end_ms = int(round(float(b) * 1000)) if float(b) < 1000 else int(b)
            out.append({"caption_id": i, "start_ms": start_ms, "end_ms": end_ms, "text": text})
        elif isinstance(row, dict):
            out.append(row)
    return out



def audit_dom_frame(
    frame: Dict[str, Any],
    contract: Optional[Dict[str, Any]],
    lifecycle_retire_when: Optional[Dict[str, List[str]]] = None,
) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    nodes = frame.get("nodes") or []
    union = frame.get("union")
    t = frame.get("t")
    canvas_w = (frame.get("canvas") or {}).get("width") or 1920

    layout_mode = (contract or {}).get("layout_mode", "center")
    # Contract may tighten the skill floor, never loosen it.
    raw_min = float((contract or {}).get("center_x_min", DEFAULT_CENTER_MIN))
    raw_max = float((contract or {}).get("center_x_max", DEFAULT_CENTER_MAX))
    center_min = max(raw_min, DEFAULT_CENTER_MIN)
    center_max = min(raw_max, DEFAULT_CENTER_MAX)
    min_gap = float((contract or {}).get("min_gap_px", MIN_GAP_PX))
    allowed = (contract or {}).get("allowed_overlaps") or []
    earth_bg = (contract or {}).get("earth_is_background", True)

    if union and nodes:
        findings.extend(_center_findings_for_union(
            union, layout_mode=layout_mode, earth_bg=bool(earth_bg), t=t,
            group="dom_union", source="dom_measure",
        ))
        if layout_mode == "left_rail":
            findings.append({
                "code": "earth_bg_left_rail",
                "detail": "left_rail declared against approved Earth background",
                "evidence": {"t": t},
                "gate": "safe_frame_center",
            })
        # Primary sibling groups (account boards, result chips) must themselves be canvas-centered.
        id_map_early = {n.get("id"): n for n in nodes if n.get("id")}
        for sset in (contract or {}).get("sibling_sets") or []:
            ids = sset.get("ids") or []
            present = []
            for i in ids:
                n = id_map_early.get(i)
                if not n:
                    continue
                present.append({
                    "x": n["x"], "y": n["y"], "width": n["width"], "height": n["height"],
                    "right": n.get("right", n["x"] + n["width"]),
                    "bottom": n.get("bottom", n["y"] + n["height"]),
                })
            if len(present) >= 2:
                u = _union(present)
                if u:
                    findings.extend(_center_findings_for_union(
                        u, layout_mode=layout_mode, earth_bg=bool(earth_bg), t=t,
                        group=sset.get("id") or "sibling_set", source="dom_primary_group",
                    ))

    # pairwise overlap among top-level measured nodes
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            a, b = nodes[i], nodes[j]
            # skip parent/child-ish: if one fully contains the other and shares id prefix, ignore? keep simple: all pairs
            aid, bid = a.get("id") or f"anon{i}", b.get("id") or f"anon{j}"
            if _allowed_pair(aid, bid, allowed):
                continue
            # ignore channel text pieces that are intentionally grouped
            groupish = {"portrait", "hello", "channel", "channel-mask", "name", "rule", "welcome"}
            if aid in groupish and bid in groupish:
                continue
            gap = _overlap_gap(a, b)
            if gap < min_gap:
                findings.append({
                    "code": "unintended_overlap" if gap < 0 else "insufficient_gap",
                    "detail": f"gap={gap:.1f}px between {aid} and {bid}",
                    "evidence": {"t": t, "a": {"id": aid, "box": {k: a[k] for k in ('x','y','width','height')}},
                                 "b": {"id": bid, "box": {k: b[k] for k in ('x','y','width','height')}},
                                 "min_gap_px": min_gap},
                    "gate": "overlap",
                })

    # sibling equality from contract or heuristic claim pairs in same vertical stack
    sibling_sets = (contract or {}).get("sibling_sets") or []
    id_map = {n.get("id"): n for n in nodes if n.get("id")}
    for sset in sibling_sets:
        ids = sset.get("ids") or []
        present = [id_map[i] for i in ids if i in id_map]
        if len(present) < 2:
            continue
        w0, h0 = present[0]["width"], present[0]["height"]
        for n in present[1:]:
            if w0 <= 0 or h0 <= 0:
                continue
            dw = abs(n["width"] - w0) / w0
            dh = abs(n["height"] - h0) / h0
            if dw > SIBLING_TOL or dh > SIBLING_TOL:
                findings.append({
                    "code": "sibling_size_mismatch",
                    "detail": f"{present[0].get('id')} vs {n.get('id')} dw={dw:.3f} dh={dh:.3f}",
                    "evidence": {"t": t, "set": ids, "sizes": [(x.get("id"), x["width"], x["height"]) for x in present]},
                    "gate": "sibling_equality",
                })

    # heuristic: all visible .claim in frame should match if >=2 and contract missing
    if not sibling_sets:
        claims = [n for n in nodes if "claim" in (n.get("classes") or [])]
        if len(claims) >= 2:
            w0, h0 = claims[0]["width"], claims[0]["height"]
            for n in claims[1:]:
                dw = abs(n["width"] - w0) / max(w0, 1)
                dh = abs(n["height"] - h0) / max(h0, 1)
                if dw > SIBLING_TOL or dh > SIBLING_TOL:
                    findings.append({
                        "code": "sibling_size_mismatch",
                        "detail": f"claim {claims[0].get('id')} vs {n.get('id')} dw={dw:.3f} dh={dh:.3f}",
                        "evidence": {"t": t, "sizes": [(x.get("id"), x["width"], x["height"]) for x in claims]},
                        "gate": "sibling_equality",
                    })

    # metaphor on measured nodes
    for n in nodes:
        blob = " ".join([n.get("img_alt") or "", n.get("label") or "", n.get("text") or ""])
        src = n.get("img_src") or ""
        for cre, are, code in METAPHOR_FAIL_PATTERNS:
            if cre.search(blob) and are.search(src):
                findings.append({
                    "code": "metaphor_mismatch",
                    "detail": code,
                    "evidence": {"t": t, "id": n.get("id"), "src": src, "text": blob[:80]},
                    "gate": "metaphor",
                })

    # lifecycle
    lifecycle_retire_when = lifecycle_retire_when or {}
    # map: trigger_id -> list of must-be-gone ids when trigger visible
    id_op = {n.get("id"): n.get("opacity", 0) for n in nodes if n.get("id")}
    # also need absent ids as opacity 0 — check triggers present
    for trigger, retirees in lifecycle_retire_when.items():
        if id_op.get(trigger, 0) >= 0.5:
            stale = [rid for rid in retirees if id_op.get(rid, 0) >= 0.2]
            if stale:
                findings.append({
                    "code": "lifecycle_stale",
                    "detail": f"trigger={trigger} visible but stale={stale}",
                    "evidence": {"t": t, "trigger": trigger, "stale": stale, "opacity": {k: id_op.get(k) for k in [trigger] + retirees}},
                    "gate": "lifecycle",
                })

    return findings


def run_measure(url: str, times: List[float], out_path: Path, measure_js: Path, chrome: str, puppeteer: str) -> Dict[str, Any]:
    cmd = [
        "node", str(measure_js),
        "--url", url,
        "--times", ",".join(str(t) for t in times),
        "--out", str(out_path),
        "--chrome", chrome,
        "--puppeteer", puppeteer,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"measure_layout_dom failed: {proc.stderr or proc.stdout}")
    return json.loads(out_path.read_text(encoding="utf-8"))


def audit(args: argparse.Namespace) -> Dict[str, Any]:
    findings: List[Dict[str, Any]] = []
    contract = _load_json(Path(args.contract) if args.contract else None) or {}
    plan = _load_json(Path(args.plan) if args.plan else None)
    inventory = _load_json(Path(args.inventory) if args.inventory else None)

    html_text = ""
    html_path = Path(args.html) if args.html else None
    cues = []
    if args.html:
        html_text = Path(args.html).read_text(encoding="utf-8")
        findings.extend(scan_html_metaphor(html_text))
        cues = discover_cues(html_text, html_path, Path(args.cues) if getattr(args, "cues", None) else None)
        cues_scene = _cues_scene_map(cues)
        findings.extend(scan_contract_layout_floors(contract))
        findings.extend(scan_html_scene_centers(html_text, contract, cues_scene))
        findings.extend(scan_path_text_collisions(html_text, cues_scene))

    findings.extend(scan_plan_metaphor(plan, inventory))

    # missing contract is itself a fail for semantic rebuilds when required
    if args.require_contract and not contract:
        findings.append({
            "code": "missing_layout_contract",
            "detail": "layout_contract.json required for semantic rebuild",
            "evidence": {},
            "gate": "contract",
        })

    measure_data = None
    if args.dom_json:
        measure_data = _load_json(Path(args.dom_json))
    elif args.url:
        measure_js = Path(args.measure_js)
        times = [float(x) for x in args.times.split(",") if x.strip()]
        out_meas = Path(args.measure_out or (Path(args.out).parent / "layout-hard-gates-dom.json"))
        measure_data = run_measure(
            args.url, times, out_meas, measure_js, args.chrome, args.puppeteer
        )

    lifecycle = {
        # when 25bp gauge is primary, retire completed define explainers
        "defineGauge": ["defineFed", "defineReport", "defineRulerClaim", "defineFFR"],
    }
    if contract.get("lifecycle_retire_when"):
        lifecycle.update(contract["lifecycle_retire_when"])

    if measure_data:
        for frame in measure_data.get("frames") or []:
            findings.extend(audit_dom_frame(frame, contract, lifecycle))

    # de-dupe roughly
    uniq = []
    seen = set()
    for f in findings:
        key = (f.get("code"), f.get("detail"), json.dumps(f.get("evidence"), sort_keys=True, ensure_ascii=False)[:240])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(f)
    findings = uniq

    status = "fail" if findings else "pass"
    report = {
        "schema_version": 1,
        "status": status,
        "gates_doc": "references/layout-hard-gates.md",
        "thresholds": {
            "center_x_band": [DEFAULT_CENTER_MIN, DEFAULT_CENTER_MAX],
            "left_bias_fail_below": LEFT_BIAS_FAIL,
            "safe_frame_x_ratio": [SAFE_LEFT, SAFE_RIGHT],
            "contract_safe_right_min": CONTRACT_SAFE_RIGHT_MIN,
            "earth_reserved_center_max": EARTH_RESERVED_CENTER_MAX,
            "earth_reserved_right_max": EARTH_RESERVED_RIGHT_MAX,
            "min_gap_px": MIN_GAP_PX,
            "sibling_tol": SIBLING_TOL,
        },
        "inputs": {
            "html": args.html,
            "url": args.url,
            "contract": args.contract,
            "plan": args.plan,
            "inventory": args.inventory,
            "dom_json": args.dom_json,
        },
        "finding_count": len(findings),
        "findings": findings,
        "encode_allowed": status == "pass",
    }
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description="Audit layout hard gates (fail-able)")
    ap.add_argument("--html", help="composition HTML path for static metaphor scan")
    ap.add_argument("--url", help="composition URL for live DOM measure")
    ap.add_argument("--times", default="4.8,26.5,35.5,54.5")
    ap.add_argument("--contract", help="layout_contract.json")
    ap.add_argument("--plan", help="semantic_plan.json")
    ap.add_argument("--inventory", help="concept-inventory.json")
    ap.add_argument("--dom-json", dest="dom_json", help="precomputed measure_layout_dom JSON")
    ap.add_argument("--measure-js", dest="measure_js",
                    default=str(Path(__file__).resolve().parent / "measure_layout_dom.cjs"))
    ap.add_argument("--measure-out", dest="measure_out")
    ap.add_argument("--chrome", default=os.environ.get("WISE_CHROME", ""))
    ap.add_argument("--puppeteer", default=os.environ.get("WISE_PUPPETEER", ""))
    ap.add_argument("--cues", help="optional cue_sheet.json (defaults to composition/cue_sheet.json)")
    ap.add_argument("--require-contract", action="store_true")
    ap.add_argument("--out", required=True)
    ap.add_argument("--expect-fail", action="store_true", help="exit 0 if status=fail (baseline proof)")
    args = ap.parse_args()

    try:
        report = audit(args)
    except Exception as e:
        err = {"status": "tool_error", "error": str(e)}
        Path(args.out).write_text(json.dumps(err, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(err, ensure_ascii=False), file=sys.stderr)
        return 2

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "finding_count": report["finding_count"], "out": args.out}, ensure_ascii=False))

    if args.expect_fail:
        return 0 if report["status"] == "fail" else 1
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())

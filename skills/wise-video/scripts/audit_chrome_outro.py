#!/usr/bin/env python3
"""Audit sampled, computed DOM evidence; never certify pixels or unsampled time.

Input: measure_layout_dom.cjs JSON with chrome_outro.capture_version=1.
Exit 0: requested DOM checks pass; 1: fail or not_checked; 2: invalid input.
No evidence, missing requested times, or unknown icon geometry => not_checked.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path


OPTIONAL_OUTRO_COPY = {"slogan": "用大白话，讲清楚市场", "support": "你的支持，是持续更新的动力"}
SUBSCRIBE_OBJECTS = ["portrait", "brand", "topics", "slogan", "subscribe", "bookmark", "support", "bye"]
COMMUNITY_SIGNATURE_OBJECTS = ["portrait", "brand", "subscribe", "bye"]


def resolve_outro_policy(policy, *, check_outro, require_tg):
    """Explicit narration exceptions only remove optional copy requirements.

    They do not assert that a line is absent from the recording or that the
    object must be invisible. Actual narration alignment remains review work.
    """
    if policy is not None and (not check_outro or require_tg):
        raise ValueError("--outro-policy requires --check-outro without --require-tg (subscribe-only)")
    if not check_outro:
        return None
    expected = list(COMMUNITY_SIGNATURE_OBJECTS if require_tg else SUBSCRIBE_OBJECTS)
    not_required = {}
    if policy is not None:
        if not isinstance(policy, dict) or set(policy) != {"schema_version", "optional_objects"}:
            raise ValueError("outro policy requires only schema_version and optional_objects")
        if type(policy["schema_version"]) is not int or policy["schema_version"] != 1:
            raise ValueError("outro policy schema_version must be 1")
        overrides = policy["optional_objects"]
        if not isinstance(overrides, dict) or not set(overrides) <= OPTIONAL_OUTRO_COPY.keys():
            raise ValueError("outro policy optional_objects only allows slogan and support")
        for role, rule in overrides.items():
            if not isinstance(rule, dict) or not {"expected"} <= rule.keys() or not set(rule) <= {"expected", "reason"}:
                raise ValueError(f"outro policy {role} needs expected and an optional reason")
            if type(rule["expected"]) is not bool:
                raise ValueError(f"outro policy {role}.expected must be a boolean")
            reason = rule.get("reason", "")
            if not isinstance(reason, str) or (not rule["expected"] and not reason.strip()):
                raise ValueError(f"outro policy {role} omission needs a nonempty narration reason")
            if not rule["expected"]:
                expected.remove(role)
                not_required[role] = reason.strip()
    return {"basis": "explicit_policy" if policy is not None else "approved_default",
            "expected_objects": expected, "not_required": not_required}


def compact(value):
    return re.sub(r"\s+", "", str(value or ""))


def times_arg(value):
    result = [float(t) for t in value.split(",") if t.strip()]
    if any(not math.isfinite(t) or t < 0 for t in result):
        raise ValueError("times must be finite, nonnegative seconds")
    return result


def visible(node):
    return bool(node and node.get("visible") is True and node.get("opacity", 0) >= .15
                and node.get("visible_area_ratio", 0) >= .5)


def rgb(value):
    match = re.fullmatch(r"rgba?\(\s*([\d.]+)[, ]+([\d.]+)[, ]+([\d.]+)(?:\s*[,/]\s*([\d.]+))?\s*\)", str(value or ""))
    if not match:
        return None
    return tuple(float(n) for n in match.groups()[:3]) + (float(match[4] or 1),)


def color_near(value, expected, tolerance=8):
    actual = rgb(value)
    return actual is not None and actual[3] >= .8 and all(abs(a-b) <= tolerance for a, b in zip(actual, expected))


def is_red(value):
    color = rgb(value)
    return bool(color and color[0] >= 180 and color[1] <= 115 and color[2] <= 115
                and color[0] >= color[1] * 1.5 and color[3] >= .8)


def overlap(a, b):
    a, b = a.get("rect", {}), b.get("rect", {})
    return (min(a.get("right", 0), b.get("right", 0)) > max(a.get("x", 0), b.get("x", 0))
            and min(a.get("bottom", 0), b.get("bottom", 0)) > max(a.get("y", 0), b.get("y", 0)))


def approved_bookmark(node):
    # Match actual measured geometry + paint, not data-role/aria-label claims.
    return any(re.sub(r"[\s,]+", "", s.get("d", "")).upper() == "M22H38V52L2040L252Z"
               and color_near(s.get("fill"), (183, 154, 96), 16)
               for s in node.get("svg_shapes", []))


def audit_evidence(evidence=None, *, check_series=False, check_outro=False,
                   episode=None, topic=None, outro_times=(), intro_times=(0, 4), require_tg=False, community_times=(),
                   outro_policy=None):
    object_policy = resolve_outro_policy(outro_policy, check_outro=check_outro, require_tg=require_tg)
    if evidence is not None and not isinstance(evidence, dict):
        raise ValueError("DOM evidence must be a JSON object")
    findings, unchecked = [], []

    def fail(code, t=None, **detail):
        findings.append({"code": code, "gate": "sampled_chrome_outro", "evidence": {"t": t, **detail}})

    def unknown(code, **detail):
        unchecked.append({"code": code, **detail})

    if not check_series and not check_outro:
        unknown("no_checks_requested")
    if (evidence or {}).get('page_errors'):
        unknown("browser_runtime_errors", errors=evidence['page_errors'])
    frames = (evidence or {}).get("frames", [])
    if not isinstance(frames, list) or any(not isinstance(f, dict) for f in frames):
        raise ValueError("frames must be a list of objects")
    usable = []
    for frame in frames:
        capture = frame.get("chrome_outro", {})
        if not isinstance(capture, dict):
            raise ValueError("chrome_outro must be an object")
        if capture.get("capture_version") != 1 or capture.get("source") != "browser_computed_dom":
            continue
        if not isinstance(capture.get("nodes"), list):
            raise ValueError("chrome_outro.nodes must be a list")
        if not isinstance(frame.get("t"), (int, float)) or not math.isfinite(frame["t"]):
            raise ValueError("frame.t must be finite seconds")
        if frame.get("canvas", {}).get("width") != 1920 or frame.get("canvas", {}).get("height") != 1080:
            unknown("unsupported_canvas", t=frame["t"])
            continue
        required = {"role", "visible", "opacity", "visible_area_ratio", "rect", "text", "background_color", "color"}
        for node in capture["nodes"]:
            if not isinstance(node, dict) or not isinstance(node.get("rect"), dict):
                raise ValueError("measured node and rect must be objects")
            if not required <= node.keys():
                raise ValueError("incomplete measured node: " + str(node.get("role")))
            if not all(isinstance(node.get(k), (int, float)) and math.isfinite(node[k])
                       for k in ("opacity", "visible_area_ratio")):
                raise ValueError("invalid measured visibility")
            if not all(isinstance(node["rect"].get(k), (int, float)) and math.isfinite(node["rect"][k])
                       for k in ("x", "y", "width", "height", "right", "bottom")):
                raise ValueError("invalid measured rect")
        usable.append(frame)

    def selected(requested, kind):
        result = []
        for t in requested:
            matches = [f for f in usable if abs(f["t"] - t) < .02]
            if not matches:
                unknown("missing_sample", phase=kind, t=t)
            result.extend(matches[:1])
        return result

    def nodes(frame, role):
        return [n for n in frame["chrome_outro"]["nodes"] if n["role"] == role]

    def one(frame, role):
        candidates = nodes(frame, role)
        return next((n for n in candidates if visible(n)), candidates[0] if candidates else None)

    if not usable:
        unknown("browser_evidence_missing", hint="Run measure_layout_dom.cjs; source markers cannot prove visibility/color/time.")
    if check_series:
        selected(sorted(set([0, *intro_times])), "intro")
        if episode is None or not topic:
            unknown("series_expected_copy_missing", hint="Supply --episode and --topic from the current script.")
        for f in usable:
            t = f["t"]
            card, logo = one(f, "series-card"), one(f, "signature")
            is_outro = check_outro and any(abs(t-x) < .02 for x in outro_times)
            missing_code = ("series_chrome_missing_in_outro" if is_outro else
                            "series_chrome_missing_t0" if abs(t) < .02 else "series_chrome_missing_during_sample")
            if not visible(card) or not visible(logo):
                fail(missing_code, t, card_visible=visible(card), signature_visible=visible(logo))
            if visible(logo):
                rect = logo["rect"]
                if abs(rect["x"]-1634) > 24 or abs(rect["y"]-32) > 16:
                    fail("series_chrome_logo_left", t, rect=rect, expected="right top, x≈1634 y≈32")
                if not logo.get("image_loaded"):
                    fail("series_chrome_signature_image_missing", t)
            if visible(card):
                num = one(f, "episode-number")
                if not visible(num) or not color_near(num["background_color"], (235, 113, 105)):
                    fail("series_chrome_num_navy", t, background=(num or {}).get("background_color"))
                if visible(num) and not color_near(num.get("color"), (23, 39, 53), 24):
                    fail("series_chrome_num_text_wrong", t, color=num.get("color"), expected="dark #172735")
                series, current_topic = one(f, "series-name"), one(f, "episode-topic")
                expected = f"纳斯达克投资·第{episode}期"
                actual_num = compact((num or {}).get("text"))
                number_ok = actual_num.isdigit() and episode is not None and int(actual_num) == int(episode)
                if (not visible(series) or not visible(current_topic) or
                    (episode is not None and (compact((series or {}).get("text")) != expected or not number_ok)) or
                    (topic and compact((current_topic or {}).get("text")) != compact(topic))):
                    fail("series_chrome_copy_wrong", t, series=(series or {}).get("text"),
                         topic=(current_topic or {}).get("text"), episode=actual_num)

    if check_outro:
        if require_tg:
            if not community_times:
                unknown("community_times_missing", hint="Supply --community-times for the Telegram segment, separate from signature --outro-times.")
            community = selected(community_times, "community")
            if community:
                valid = []
                for f in community:
                    group = [n for n in nodes(f, "community-label") if visible(n)]
                    image = [n for n in nodes(f, "community-image") if visible(n) and n.get("image_loaded")]
                    links = [n for n in nodes(f, "community-link") if visible(n) and re.match(r"https://(?:t\.me|telegram\.me)/[^/]+", n.get("href", ""))]
                    if any(re.search(r"电报|Telegram|交流群", n["text"], re.I) for n in group) and (image or links):
                        valid.append(f["t"])
                if not valid:
                    fail("outro_missing_tg_community", detail="No simultaneous visible group label plus decoded group image or Telegram link at community samples")
        if not outro_times:
            unknown("outro_times_missing", hint="Supply signature-phase --outro-times in seconds, covering the staged objects.")
        ending = selected(outro_times, "outro")
        if ending:
            observed = lambda role: [(f, n) for f in ending for n in nodes(f, role) if visible(n)]
            if not any(nodes(f, "outro-root") for f in ending):
                fail("outro_template_missing", detail="No signature root; its actual visible objects are checked separately")
            if not any(n.get("image_loaded") for _, n in observed("portrait")):
                fail("outro_missing_portrait", detail="No visible, decoded portrait image (identity still requires review)")
            if not any(is_red(n["background_color"]) and "关注" in n["text"] and "订阅" in n["text"]
                       for _, n in observed("subscribe")):
                fail("outro_missing_red_subscribe")
            expected_copy = [("brand", "WiseInvest"), ("bye", "我们下期再见")]
            if not require_tg:
                topics = observed("topics")
                if not any(compact(n["text"]) == "美股·宏观·科技·AI" and not n.get("boxed_descendants")
                           and (rgb(n["background_color"]) or (0, 0, 0, 0))[3] < .1 for _, n in topics):
                    fail("outro_missing_topics_line")
                expected_copy += [(role, text) for role, text in OPTIONAL_OUTRO_COPY.items()
                                  if role in object_policy["expected_objects"]]
            for role, expected in expected_copy:
                if not any(compact(expected) in compact(n["text"]) for _, n in observed(role)):
                    fail("outro_missing_" + role)
            if not require_tg:
                bookmarks = observed("bookmark")
                if not any("收藏" in n["text"] and n.get("svg_shapes") for _, n in bookmarks):
                    fail("outro_bell_instead_of_bookmark", bell_visible=bool(observed("bell")))
                elif not any(approved_bookmark(n) for _, n in bookmarks):
                    unknown("bookmark_geometry_unverified", hint="DOM label is not icon identity; compare against the packaged bookmark geometry or review rendered frames.")
            for f in ending:
                portraits = [n for n in nodes(f, "portrait") if visible(n)]
                for chip in nodes(f, "interest-chip"):
                    if visible(chip) and any(overlap(chip, p) for p in portraits):
                        fail("outro_interest_chips_on_portrait", f["t"], chip=chip.get("id"))
    status = "fail" if findings else "not_checked" if unchecked else "pass"
    return {"schema_version": 1, "status": status, "encode_allowed": status == "pass",
            "scope": "sampled_computed_dom_only", "visual_review": "not_checked",
            "requested_checks": {"series": bool(check_series), "outro": bool(check_outro)},
            "outro_variant": ("community-signature" if require_tg else "subscribe-only") if check_outro else None,
            "outro_object_policy": object_policy,
            "finding_count": len(findings), "findings": findings, "not_checked": unchecked,
            "sampled_times": [f["t"] for f in usable],
            "limitations": ["No pixel/encoded-video review, portrait identity, aesthetic approval, narration alignment, or unsampled-time guarantee.",
                            "Visibility uses CSS opacity, viewport and rectangular overflow clipping; complex masks and paint occlusion need frame review."]}


def add_arguments(parser):
    parser.add_argument("--dom-evidence", help="JSON from measure_layout_dom.cjs")
    parser.add_argument("--check-series", action="store_true")
    parser.add_argument("--episode", type=int)
    parser.add_argument("--topic")
    parser.add_argument("--outro-times", default="", help="signature phase sample times in seconds, comma-separated")
    parser.add_argument("--intro-times", default="0,4", help="required series intro samples (default 0,4)")
    parser.add_argument("--community-times", default="", help="Telegram/community sample seconds (with --require-tg)")
    parser.add_argument("--outro-policy", help="JSON narration policy; only slogan/support may explicitly be not required")


def from_args(args):
    source = getattr(args, "dom_evidence", None)
    evidence = json.loads(Path(source).read_text(encoding="utf-8")) if source else None
    policy_path = getattr(args, "outro_policy", None)
    policy_bytes = Path(policy_path).read_bytes() if policy_path else None
    policy = json.loads(policy_bytes) if policy_bytes is not None else None
    if policy_bytes is not None and policy is None:
        raise ValueError("outro policy must be an object, not null")
    report = audit_evidence(evidence, check_series=getattr(args, "check_series", False),
                          check_outro=getattr(args, "check_outro", False),
                          episode=getattr(args, "episode", None), topic=getattr(args, "topic", None),
                          outro_times=times_arg(getattr(args, "outro_times", "")),
                          intro_times=times_arg(getattr(args, "intro_times", "0,4")),
                          require_tg=getattr(args, "require_tg", False),
                          community_times=times_arg(getattr(args, "community_times", "")), outro_policy=policy)
    if policy_path:
        report["outro_object_policy"]["source"] = {"path": str(policy_path), "sha256": hashlib.sha256(policy_bytes).hexdigest()}
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_arguments(parser)
    parser.add_argument("--check-outro", action="store_true")
    parser.add_argument("--require-tg", action="store_true", help="audit the community + signature variant instead of subscribe-only")
    parser.add_argument("--out")
    args = parser.parse_args()
    try:
        report = from_args(args)
        text = json.dumps(report, ensure_ascii=False, indent=2)
        if args.out:
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(text)
        return 0 if report["status"] == "pass" else 1
    except (ValueError, OSError, TypeError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

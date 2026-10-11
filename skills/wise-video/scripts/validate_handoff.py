#!/usr/bin/env python3
"""Validate mechanical SRT -> semantic plan -> rendered composition handoff.

This does not infer meaning, inspect pixels, or accept self-declared QA passes.
All source/binding/plan times are absolute SRT milliseconds. Composition and cue
sheet times are local by default (offset by intake effective_start_ms).
"""
from __future__ import annotations

import argparse
from collections import Counter
from decimal import Decimal, InvalidOperation
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlparse

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
UNVERIFIED = {"geometry": "not_verified", "runtime_visibility": "not_verified", "semantic_expression": "not_verified", "audio_content_sync": "not_verified"}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def millis(value):
    try:
        number = Decimal(str(value)) * 1000
        if not number.is_finite():
            raise ValueError("non-finite time")
        return int(number.to_integral_value())
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"invalid seconds value {value!r}") from exc


def integer(value):
    return isinstance(value, int) and not isinstance(value, bool)


class CompositionDOM(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.nodes = []
        self.stack = []
        self.ids = {}
        self.duplicates = []
        self.media = []
        self.roots = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = attrs.get("class", "").split()
        is_scene = "scene" in classes
        parent_scene = next((node["id"] for node in reversed(self.stack) if node["is_scene"]), None)
        node = {"tag": tag, "attrs": attrs, "id": attrs.get("id"), "is_scene": is_scene,
                "scene_id": attrs.get("id") if is_scene else parent_scene,
                "ancestors": [node["id"] for node in self.stack if node["id"]], "text": ""}
        self.nodes.append(node)
        if node["id"]:
            if node["id"] in self.ids:
                self.duplicates.append(node["id"])
            self.ids[node["id"]] = node
        if "data-composition-id" in attrs:
            self.roots.append(node)
        if tag in {"img", "audio", "video", "source", "script"} and attrs.get("src"):
            self.media.append({"tag": tag, "src": attrs["src"], "scene_id": node["scene_id"], "ancestors": node["ancestors"]})
        if tag == "br":
            self.handle_data("\n")
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index]["tag"] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        for node in self.stack:
            node["text"] += data


def validate(intake_dir, plan_path, composition_dir, *, composition_timebase="local"):
    intake_dir, plan_path, composition_dir = map(Path, (intake_dir, plan_path, composition_dir))
    findings, caption_results, assets = [], [], []

    def add(status, code, message, **context):
        findings.append({"status": status, "code": code, "message": message, **context})

    def result(extra=None):
        status = "failed" if any(row["status"] == "failed" for row in findings) else "pending" if any(row["status"] == "pending" for row in findings) else "passed"
        return {"schema_version": 1, "status": status,
                "scope": "mechanical_handoff_only", "review_layers": UNVERIFIED.copy(),
                "counts": {state: sum(row["status"] == state for row in findings) for state in ("failed", "pending", "passed")},
                "findings": findings, "caption_bindings": caption_results, "assets": assets,
                "evidence": extra or {},
                "note": "passed 只表示原文、范围、引用、时间和生成接线成立；不表示画面可见、布局不重叠、语义正确或声音已同步。计划自填的 status/pass/review 字段不参与判定。"}

    try:
        report = load(intake_dir / "intake-report.json")
        captions = load(intake_dir / "captions.scope.json")
        all_captions = load(intake_dir / "captions.parsed.json")
        plan = load(plan_path)
        html_path = composition_dir / "index.html"
        html = html_path.read_text(encoding="utf-8")
        cue_sheet = load(composition_dir / "cue_sheet.json")
    except (OSError, ValueError, TypeError) as exc:
        add("failed", "input_unreadable", str(exc))
        return result()
    evidence = {"plan_sha256": sha(plan_path), "html_sha256": sha(html_path),
                "intake_report_sha256": sha(intake_dir / "intake-report.json"),
                "cue_sheet_sha256": sha(composition_dir / "cue_sheet.json"),
                "composition_timebase": composition_timebase}
    if not isinstance(plan, dict) or not isinstance(captions, list) or not isinstance(all_captions, list):
        add("failed", "invalid_input_schema", "计划必须为对象，字幕必须为数组。")
        return result(evidence)
    try:
        start, end = report["range"]["effective_start_ms"], report["range"]["effective_end_ms"]
        if not integer(start) or not integer(end) or end <= start:
            raise ValueError("invalid intake range")
        source = Path(report["input_srt"]["path"])
        if sha(source) != report["input_srt"]["sha256"]:
            add("failed", "source_hash_mismatch", "原始 SRT 已改变，必须重新接入。")
        # Reparse the locked source, rather than trusting editable intake JSON.
        try:
            import srt_intake
        except ModuleNotFoundError:
            import importlib.util
            spec = importlib.util.spec_from_file_location("srt_intake", Path(__file__).with_name("srt_intake.py"))
            srt_intake = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(srt_intake)
        reparsed, parse_issues = srt_intake.parse_srt(source.read_text(encoding="utf-8-sig"))
        if any(item["severity"] == "error" for item in parse_issues):
            add("failed", "source_parse_errors", "原始 SRT 含解析错误。")
        fields = ("caption_id", "start_ms", "end_ms", "text")
        core = lambda rows: [{key: row.get(key) for key in fields} for row in rows]
        if core(reparsed) != core(all_captions):
            add("failed", "parsed_source_changed", "parsed 字幕的原文、ID、顺序或时间与原始 SRT 不符。")
        expected_rows = [row for row in reparsed if row["end_ms"] > start and row["start_ms"] < end]
        if core(expected_rows) != core(captions):
            add("failed", "scope_source_changed", "范围字幕与原始 SRT 不一致或缺少条目。")
    except (KeyError, OSError, ValueError, TypeError) as exc:
        add("failed", "intake_source_unverifiable", str(exc))
        return result(evidence)
    if not report.get("readiness", {}).get("intake_valid") or report.get("status") == "failed":
        add("failed", "intake_not_valid", "接入报告含硬错误，不可跳过。")
    # A fully wired set of supplied captions does not fulfill an exact range
    # extending beyond the supplied source. Preserve pending dependencies even
    # when every object, cue, and hash is mechanically valid. Recompute the
    # source end as well, so a self-edited readiness flag cannot bypass it.
    source_end_ms = max((row["end_ms"] for row in reparsed), default=0)
    if report.get("status") == "pending" or report.get("range", {}).get("effective_range_content_complete") is False or end > source_end_ms:
        add("pending", "effective_source_content_pending", "有效制作范围仍包含尚未提供的正文；已有字幕全部接线也不能据此声称完整范围通过。",
            effective_end_ms=end, source_end_ms=source_end_ms,
            missing_content_intervals=report.get("range", {}).get("missing_content_intervals", []))
    offset = start if composition_timebase == "local" else 0
    expected_ids = [row["caption_id"] for row in expected_rows]
    caption_index = {row["caption_id"]: row for row in expected_rows}
    if report.get("range", {}).get("scope_caption_ids") != expected_ids:
        add("failed", "intake_scope_ids_changed", "接入 scope ID 与原 SRT 计算结果不符。")
    if plan.get("scope_caption_ids") != expected_ids:
        add("failed", "plan_scope_mismatch", "计划必须覆盖目标范围全部原字幕 ID，且保留顺序。", expected=expected_ids, actual=plan.get("scope_caption_ids"))
    for row in plan.get("sentence_coverage", []):
        source_row = caption_index.get(row.get("caption_id"))
        if source_row is None or any(row.get(key) != source_row[key] for key in ("text", "start_ms", "end_ms")):
            add("failed", "sentence_source_mismatch", "sentence_coverage 不得改写原文或时间。", caption_id=row.get("caption_id"))
    beats = plan.get("beats", [])
    beat_index = {row.get("id"): row for row in beats}
    if len(beat_index) != len(beats):
        add("failed", "duplicate_beat_id", "语义 beat ID 重复。")
    for beat in beats:
        ids = beat.get("source_caption_ids", [])
        if not ids or any(cid not in caption_index for cid in ids):
            add("failed", "beat_source_unknown", "beat 引用未知或空的原字幕。", beat_id=beat.get("id"))
        elif beat.get("text") != "".join(caption_index[cid]["text"] for cid in ids):
            add("failed", "beat_text_changed", "beat.text 必须按引用顺序完整拼接原字幕。", beat_id=beat.get("id"))
    coverage = plan.get("coverage", [])
    coverage_index = {row.get("caption_id"): row for row in coverage}
    if len(coverage_index) != len(coverage):
        add("failed", "duplicate_coverage", "coverage 中同一字幕重复。")
    for cid in expected_ids:
        row = coverage_index.get(cid)
        if row is None:
            add("failed", "semantic_coverage_missing", "缺少语义 coverage。", caption_id=cid)
        elif not row.get("beat_ids") and not row.get("hold_reason"):
            add("failed", "semantic_coverage_empty", "语义 coverage 需要 beat 或明确停留理由。", caption_id=cid)
        elif any(bid not in beat_index or cid not in beat_index[bid].get("source_caption_ids", []) for bid in row.get("beat_ids", [])):
            add("failed", "coverage_beat_mismatch", "coverage 指向的 beat 不包含本条原字幕。", caption_id=cid)
    dom = CompositionDOM()
    dom.feed(html)
    if dom.duplicates:
        add("failed", "duplicate_dom_id", "实际 HTML 出现重复 ID。", ids=dom.duplicates)
    if not dom.roots:
        add("failed", "composition_root_missing", "缺少 data-composition-id 根节点。")
    else:
        try:
            if abs(millis(dom.roots[0]["attrs"]["data-duration"]) - (end - start)) > 1:
                add("failed", "composition_duration_mismatch", "成片时长与接入有效范围不一致。")
        except (KeyError, ValueError):
            add("failed", "composition_duration_invalid", "根节点缺少有效时长。")
    scenes = plan.get("render_spec", {}).get("scenes", [])
    scene_index = {scene.get("id"): scene for scene in scenes}
    if len(scene_index) != len(scenes):
        add("failed", "duplicate_scene_id", "计划场景 ID 重复。")
    for scene in scenes:
        sid = scene.get("id")
        node = dom.ids.get(sid)
        if not node or not node["is_scene"]:
            add("failed", "scene_not_rendered", "计划场景未在实际 HTML 中生成。", scene_id=sid)
            continue
        try:
            ds = millis(node["attrs"]["data-start"]) + offset
            de = ds + millis(node["attrs"]["data-duration"])
            if abs(ds - scene["start_ms"]) > 1 or abs(de - scene["end_ms"]) > 1:
                add("failed", "scene_timing_mismatch", "计划和 HTML 场景时间不一致。", scene_id=sid, plan=[scene.get("start_ms"), scene.get("end_ms")], actual=[ds, de])
        except (KeyError, ValueError, TypeError):
            add("failed", "scene_timing_invalid", "场景缺少有效开始/结束时间。", scene_id=sid)
    bindings = plan.get("render_bindings")
    if not isinstance(bindings, list) or not bindings:
        add("pending", "render_bindings_missing", "尚未提供逐条原字幕到实际场景/对象的接线。")
        bindings = []
    binding_index = {row.get("caption_id"): row for row in bindings}
    if len(binding_index) != len(bindings):
        add("failed", "duplicate_binding", "同一字幕只能有一个绑定条目；跨场景使用多个 segments。")
    for cid in binding_index:
        if cid not in caption_index:
            add("failed", "binding_outside_scope", "接线引用范围之外的字幕。", caption_id=cid)
    for cid, cue in caption_index.items():
        before_count = len(findings)
        binding = binding_index.get(cid)
        if not binding:
            add("failed" if bindings else "pending", "caption_binding_missing", "没有对应的画面接线。", caption_id=cid)
            caption_results.append({"caption_id": cid, "status": findings[-1]["status"]})
            continue
        segments = binding.get("segments", [])
        left, right = max(start, cue["start_ms"]), min(end, cue["end_ms"])
        intervals = []
        if not segments:
            add("failed", "segments_empty", "segments 不能为空。", caption_id=cid)
        for segment in segments:
            sid, objects = segment.get("scene_id"), segment.get("object_ids")
            seg_start, seg_end = segment.get("start_ms"), segment.get("end_ms")
            if not integer(seg_start) or not integer(seg_end) or seg_end <= seg_start:
                add("failed", "binding_time_invalid", "绑定时间必须为递增的绝对整数毫秒。", caption_id=cid)
                continue
            intervals.append((seg_start, seg_end))
            if seg_start < left or seg_end > right:
                add("failed", "binding_outside_caption", "绑定片段超出目标字幕显示区间。", caption_id=cid, segment=[seg_start, seg_end], required=[left, right])
            scene = scene_index.get(sid)
            if not scene:
                add("failed", "binding_scene_unknown", "绑定场景不存在。", caption_id=cid, scene_id=sid)
            elif not (scene.get("start_ms", end + 1) <= seg_start < seg_end <= scene.get("end_ms", -1)):
                add("failed", "binding_outside_scene", "绑定时间不在目标场景存续区间。", caption_id=cid, scene_id=sid)
            if not isinstance(objects, list) or not objects:
                add("failed", "binding_objects_empty", "每个片段必须至少指向一个真实主体对象。", caption_id=cid)
                continue
            for oid in objects:
                node = dom.ids.get(oid)
                if node is None:
                    add("failed", "binding_object_missing", "绑定对象未出现在实际 HTML。", caption_id=cid, object_id=oid)
                elif node["scene_id"] != sid or node["is_scene"] or "caption" in node["attrs"].get("class", "").split():
                    add("failed", "binding_object_wrong_scene", "对象必须属于该场景的正文元素，不能用场景根或字幕本身代替。", caption_id=cid, object_id=oid, scene_id=sid)
            # Do not read user-authored passed/status/verified flags.
        cursor = left
        for a, b in sorted(intervals):
            if a > cursor:
                add("failed", "binding_time_gap", "绑定片段未连续承接本条字幕。", caption_id=cid, missing=[cursor, a])
            cursor = max(cursor, b)
        if cursor < right:
            add("failed", "binding_time_gap", "绑定片段未覆盖字幕末尾。", caption_id=cid, missing=[cursor, right])
        local_issues = findings[before_count:]
        state = "failed" if any(row["status"] == "failed" for row in local_issues) else "pending" if any(row["status"] == "pending" for row in local_issues) else "passed"
        caption_results.append({"caption_id": cid, "status": state, "source_text": cue["text"], "required_interval_ms": [left, right], "segments": segments})
    # Verify generated cue_sheet really matches the current plan and embedded code data.
    if cue_sheet.get("plan_sha256") != evidence["plan_sha256"]:
        add("failed", "cue_plan_hash_mismatch", "cue_sheet 并非由当前计划生成。")
    cues = cue_sheet.get("cues", [])
    if not isinstance(cues, list):
        add("failed", "cue_schema_invalid", "cue_sheet.cues 必须为数组。")
        cues = []
    marker = re.search(r"\b(?:const|let|var)\s+cues\s*=\s*", html)
    if marker:
        try:
            embedded, _ = json.JSONDecoder().raw_decode(html[marker.end():])
            if embedded != cues:
                add("failed", "embedded_cues_mismatch", "HTML 使用的 cues 与 cue_sheet 不一致。")
        except ValueError:
            add("pending", "embedded_cues_unreadable", "实际脚本 cues 不是可直接读取的 JSON；需适配器给出接线证据。")
    else:
        add("pending", "embedded_cues_unavailable", "未找到可读取的 const cues；无法证明实际脚本消费 cue_sheet。")
    expected_cues = []
    for scene in scenes:
        for action in scene.get("actions", []):
            full_id = action.get("target")
            if full_id not in dom.ids or dom.ids[full_id]["scene_id"] != scene.get("id"):
                full_id = str(scene.get("id")) + "-" + str(full_id)
            expected = {**action, "target": full_id, "scene_id": scene.get("id")}
            if integer(expected.get("at_ms")):
                expected["at_ms"] -= offset
            expected_cues.append(expected)
    unmatched = list(cues)
    for expected in expected_cues:
        keys = [key for key in ("target", "scene_id", "op", "at_ms", "duration_ms", "initial", "values", "ease", "beat_id") if key in expected]
        candidate = next((row for row in unmatched if all(row.get(key) == expected.get(key) for key in keys)), None)
        if candidate is None:
            add("failed", "plan_action_not_compiled", "计划动作在 cue_sheet 中缺失或已改变。", target=expected.get("target"), at_ms=expected.get("at_ms"))
        else:
            unmatched.remove(candidate)
    if unmatched:
        add("failed", "unplanned_compiled_cues", "cue_sheet 含当前计划未定义的正文动作。", count=len(unmatched))
    for action in cues:
        target = action.get("target")
        node = dom.ids.get(target)
        if node is None:
            add("failed", "cue_target_missing", "实际动作引用不存在的 DOM。", object_id=target)
        if not integer(action.get("at_ms")) or not integer(action.get("duration_ms")) or action.get("duration_ms", -1) < 0:
            add("failed", "cue_time_invalid", "实际动作时间必须为毫秒整数，时长不能为负。", object_id=target)
        else:
            absolute_start = action["at_ms"] + offset
            scene = scene_index.get(action.get("scene_id"))
            if scene and (absolute_start < scene.get("start_ms", 0) or absolute_start + action["duration_ms"] > scene.get("end_ms", end) + 1):
                add("failed", "cue_outside_scene", "动作跨出场景存续时间，需要检查退场。", object_id=target, at_ms=absolute_start)
    provenance_path = composition_dir / "provenance.json"
    if not provenance_path.exists():
        add("pending", "provenance_missing", "缺少生成 provenance。")
    else:
        try:
            provenance = load(provenance_path)
            for key, expected in (("plan_sha256", evidence["plan_sha256"]), ("html_sha256", evidence["html_sha256"]), ("source_captions_sha256", report["input_srt"]["sha256"])):
                if provenance.get(key) != expected:
                    add("failed", "provenance_hash_mismatch", "生成记录哈希不匹配。", field=key)
        except (OSError, ValueError):
            add("failed", "provenance_invalid", "provenance 无法读取。")
    local_images = []
    for media in dom.media:
        parsed = urlparse(media["src"])
        if parsed.scheme == "data":
            continue
        if parsed.scheme or parsed.netloc:
            add("pending", "external_media_not_frozen", "媒体还未冻结为本地文件。", src=media["src"])
            continue
        asset_path = (composition_dir / unquote(parsed.path)).resolve()
        if not asset_path.is_file():
            add("failed", "local_media_missing", "实际 HTML 引用的本地文件不存在。", src=media["src"])
        elif media["tag"] == "img":
            local_images.append(asset_path)
    for entity in plan.get("entities", []):
        asset_status = entity.get("asset_status")
        entry = {"entity_id": entity.get("id"), "asset_id": entity.get("asset_id"), "declared_status": asset_status, "representation": entity.get("representation")}
        if asset_status != "ready":
            entry["status"] = "pending"
            add("pending", "asset_unresolved", "实体素材尚未 ready，必须显示在缺口清单。", entity_id=entity.get("id"), asset_id=entity.get("asset_id"), declared_status=asset_status)
        elif entity.get("representation") == "icon":
            asset_id = entity.get("asset_id")
            matches = [str(path) for path in local_images if path.stem == asset_id]
            entry["local_matches"] = sorted(set(matches))
            if not asset_id or not matches:
                entry["status"] = "pending"
                add("pending", "asset_identity_not_resolved", "ready/icon 仍需 asset_id 与实际本地图片文件同名对应，不能只靠自填 ready。", entity_id=entity.get("id"), asset_id=asset_id)
            else:
                entry["status"] = "passed"
        else:
            entry["status"] = "passed"
        assets.append(entry)
    if not any(row["status"] in {"failed", "pending"} for row in findings):
        add("passed", "mechanical_handoff_verified", "全部目标字幕已绑定实际场景/对象，原文、时间、动作、文件和生成哈希一致。", caption_count=len(expected_ids))
    return result(evidence)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--intake", required=True, type=Path)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--composition", required=True, type=Path)
    parser.add_argument("--composition-timebase", choices=("local", "source"), default="local")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    if args.out.exists():
        parser.error("output already exists; use a new --out path to preserve history")
    try:
        report = validate(args.intake, args.plan, args.composition, composition_timebase=args.composition_timebase)
    except (KeyError, ValueError, TypeError, AttributeError) as exc:
        report = {"schema_version": 1, "status": "failed", "scope": "mechanical_handoff_only", "review_layers": UNVERIFIED.copy(), "findings": [{"status": "failed", "code": "invalid_schema", "message": str(exc)}]}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "out": str(args.out.resolve()), "counts": report.get("counts"), "review_layers": report["review_layers"]}, ensure_ascii=False))
    return {"passed": 0, "pending": 3, "failed": 2}[report["status"]]


if __name__ == "__main__":
    raise SystemExit(main())

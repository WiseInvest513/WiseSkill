#!/usr/bin/env python3
"""Read-only design risk scan. Findings request review; they do not grade beauty.

Exit 0 means scanning completed, including when review is required. Exit 2 means
the input/output could not be processed. No SRT text or source beat text is scanned
for production-language leakage; only rendered object text is inspected.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
import sys


PRODUCTION_LANGUAGE = (
    "口播称", "据讲述资料", "本次尚未提供", "尚未核实", "尚待补充",
    "原声测试", "本次测试", "原始字幕末尾",
)


def _text(value):
    return re.sub(r"\s+", " ", value).strip() if isinstance(value, str) else ""


def _number(value, default=0):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else default


def _audit_sentence_states(plan, scenes, add, required=False):
    """Check bindings, not the meaning of reasons or the rendered focus."""
    states = plan.get("sentence_states")
    if states is None:
        if required:
            add("sentence_states_missing", [], {}, "新计划补充实际句间状态及其对象引用，再审阅对应画面。")
        return 0
    if not isinstance(states, list) or not states:
        add("sentence_states_invalid", [], {}, "sentence_states 需要非空状态数组；旧计划可省略，不能以空记录声称已审句间焦点。")
        return 0

    scene_map = defaultdict(list)
    all_object_ids = set()
    for scene in scenes:
        sid = str(scene.get("id", ""))
        scene_map[sid].append(scene)
        all_object_ids.update(str(o["id"]) for o in scene.get("objects", [])
                              if isinstance(o, dict) and o.get("id") is not None)
    reviewed_scenes = set()
    for index, state in enumerate(states):
        if not isinstance(state, dict):
            add("sentence_state_invalid", [], {"state_index": index}, "每个状态应为对象记录。")
            continue
        sid = str(state.get("scene_id", ""))
        base = dict(state_index=index, scene_id=sid)

        def issue(code, detail, recommendation):
            add(code, [sid] if sid else [], dict(base, **detail), recommendation)

        matches = scene_map.get(sid, [])
        if len(matches) != 1:
            issue("sentence_state_scene_reference", {"matching_scenes": len(matches)},
                  "scene_id 应明确引用一个已有场景；缺失或重名时先修复接线。")
            continue
        reviewed_scenes.add(sid)
        objects = [o for o in matches[0].get("objects", []) if isinstance(o, dict)]
        ids = [str(o["id"]) for o in objects if o.get("id") is not None]
        known = set(ids)
        duplicate_ids = sorted({oid for oid in ids if ids.count(oid) > 1})
        if duplicate_ids:
            issue("sentence_state_ambiguous_object_ids", {"object_ids": duplicate_ids},
                  "场景内对象 ID 必须唯一，焦点与保留理由才能绑定到具体对象。")

        def references(field, values, allowed):
            if not isinstance(values, list) or any(not isinstance(v, str) or not v for v in values):
                issue("sentence_state_invalid_references", {"field": field}, "对象引用使用非空字符串 ID 数组。")
                return []
            unknown = sorted(set(values) - allowed)
            duplicates = sorted({v for v in values if values.count(v) > 1})
            if unknown or duplicates:
                issue("sentence_state_object_reference", dict(field=field, unknown_ids=unknown,
                       duplicate_ids=duplicates), "核对对象 ID 与所属场景，删除重复引用；退出对象可引用计划中的前场对象。")
            return values

        focus = references("focus_object_ids", state.get("focus_object_ids", []), known)
        if not focus:
            issue("sentence_state_empty_focus", {}, "指出当前一句的可见焦点；有意停留也应引用继续承担理解的对象。")
        # Exclude explicitly declared background/decoration, but do not infer
        # roles from an asset name, visual size, or arbitrary text contents.
        foreground = {str(o["id"]) for o in objects if o.get("id") is not None and
                      o.get("role") not in ("background", "decoration", "subtitle", "signature")}
        focused = set(focus) & foreground
        if len(focused) >= 3 and len(focused) / max(1, len(foreground)) >= .8 and not _text(state.get("focus_reason")):
            issue("sentence_state_near_all_focus", dict(focus_object_ids=focus,
                  foreground_count=len(foreground), focused_count=len(focused), threshold=.8),
                  "检查是否把几乎全部对象都当重点；若共同组成比较或关系焦点，用 focus_reason 说明同一理解任务，再看实际主次。")

        retained = state.get("retain", [])
        if not isinstance(retained, list) or any(not isinstance(r, dict) for r in retained):
            issue("sentence_state_invalid_retain", {}, "retain 使用逐项 object_id / reason 记录。")
        else:
            references("retain", [r.get("object_id") for r in retained], known)
            for r in retained:
                if not _text(r.get("reason")):
                    issue("sentence_state_empty_retain_reason", {"object_id": r.get("object_id")},
                          "说明该对象在当前句中的具体任务；脚本不判断理由是否与对象含义匹配，仍须看图核对。")
        references("retire_object_ids", state.get("retire_object_ids", []), all_object_ids)
        if required:
            captions = state.get("caption_ids", [])
            target = state.get("target_caption_id")
            if not isinstance(captions, list) or not captions or target is None or target not in captions:
                issue("sentence_state_target_caption", {"target_caption_id": target},
                      "caption_ids 只列当前承接句；target_caption_id 应属于它。上文另放 context_caption_ids，不冒充当前覆盖。")
            time = state.get("time_ms")
            if not isinstance(time, (int, float)) or isinstance(time, bool) or not 0 <= time < float("inf"):
                issue("sentence_state_review_time", {"time_ms": time}, "为实际审阅帧提供非负有限 time_ms；数值存在不证明与原字幕同步。")
    if required:
        missing = sorted(set(scene_map) - reviewed_scenes)
        if missing:
            add("sentence_states_unreviewed_scenes", missing, {}, "为本次交付场景关联句间状态；不必每句新建画面。")
    return len(states)


def audit(plan, require_sentence_states=False):
    """Return evidence-backed review candidates for an existing v1 plan."""
    if not isinstance(plan, dict) or not isinstance(plan.get("render_spec"), dict):
        raise ValueError("Expected a semantic plan with render_spec")
    spec = plan["render_spec"]
    scenes = spec.get("scenes")
    if not isinstance(scenes, list) or any(not isinstance(s, dict) for s in scenes):
        raise ValueError("render_spec.scenes must be an array of objects")
    findings = []
    width, height = _number(spec.get("width"), 1920), _number(spec.get("height"), 1080)
    scene_ids = [str(s.get("id", i)) for i, s in enumerate(scenes)]
    known_ids = set(scene_ids)
    beats = [b for b in plan.get("beats", []) if isinstance(b, dict)]
    beat_scenes = {}
    for b in beats:
        bid = str(b.get("id", ""))
        explicit = b.get("scene_ids", [b.get("scene_id", bid)])
        beat_scenes[bid] = [str(x) for x in explicit if str(x) in known_ids]
    for binding in plan.get("render_bindings", []):
        if not isinstance(binding, dict):
            continue
        cid = binding.get("caption_id")
        matching = [str(x.get("scene_id")) for x in binding.get("segments", [])
                    if isinstance(x, dict) and str(x.get("scene_id")) in known_ids]
        for b in beats:
            if cid in b.get("caption_ids", b.get("source_caption_ids", [])):
                bid = str(b.get("id", ""))
                beat_scenes[bid] = sorted(set(beat_scenes.get(bid, []) + matching))

    def add(code, ids, evidence, recommendation):
        findings.append(dict(code=code, severity="review", scene_ids=sorted(set(ids)),
                             evidence=evidence, recommendation=recommendation))

    state_count = _audit_sentence_states(plan, scenes, add, require_sentence_states)

    # Repetition is a review signal, never a ban: comparison and long holds can
    # legitimately repeat. The report preserves exact values and affected beats.
    for field in ("action", "acceptance", "before", "after"):
        groups = defaultdict(list)
        for b in beats:
            val = _text(b.get(field))
            if val:
                groups[val].append(str(b.get("id", "")))
        for val, ids in groups.items():
            ratio = len(ids) / max(1, len(beats))
            if len(ids) >= 3 and ratio >= .6:
                add("repeated_beat_" + field,
                    [s for bid in ids for s in beat_scenes.get(bid, [])],
                    dict(field=field, value=val, beat_ids=ids, repeated_count=len(ids),
                         total_beats=len(beats), ratio=round(ratio, 4), threshold=.6),
                    "检查是否以通用句代替具体对象状态与动作；合理重复可保留，并记录叙事理由。")

    coverage = [c for c in plan.get("coverage", []) if isinstance(c, dict)]
    holds = defaultdict(list)
    for c in coverage:
        reason = _text(c.get("hold_reason"))
        if reason:
            holds[reason].append(c)
    for reason, items in holds.items():
        ids = [s for c in items for bid in c.get("beat_ids", [])
               for s in beat_scenes.get(str(bid), [])]
        ratio = len(items) / max(1, len(coverage))
        if len(items) >= 6 and ratio >= .7 and len(set(ids)) >= 3:
            add("repeated_coverage_reason", ids,
                dict(value=reason, caption_ids=[c.get("caption_id") for c in items],
                     repeated_count=len(items), total_coverage=len(coverage),
                     ratio=round(ratio, 4), threshold=.7),
                "逐意群检查当前对象如何承接这一句；批量绑定和同一句 hold_reason 不能证明语义承接。")

    all_actions, entrances = [], defaultdict(list)
    note_scenes, note_objects = [], []
    for sid, scene in zip(scene_ids, scenes):
        objects = [o for o in scene.get("objects", []) if isinstance(o, dict)]
        for action in scene.get("actions", []):
            if not isinstance(action, dict):
                continue
            all_actions.append(action)
            initial, values = action.get("initial", {}), action.get("values", {})
            if not isinstance(initial, dict) or not isinstance(values, dict):
                continue
            if initial.get("opacity") == 0 and _number(values.get("opacity")) > 0:
                # Target/time vary naturally across objects. The remaining
                # properties define an identical entrance treatment.
                signature = {k: action.get(k) for k in
                             ("op", "duration_ms", "initial", "values", "ease")}
                key = json.dumps(signature, ensure_ascii=False, sort_keys=True)
                entrances[key].append(dict(scene_id=sid, object_id=action.get("target")))
        for o in objects:
            text = o.get("text", "")
            if isinstance(text, str):
                phrases = [p for p in PRODUCTION_LANGUAGE if p in text]
                if phrases:
                    add("production_language_in_render_text", [sid],
                        dict(object_id=o.get("id"), text=text, matched_phrases=phrases),
                        "复核观众文案与内部审稿记录；把制作过程说明移入 review，必要观众信息单独设计。")
            if (o.get("kind") in ("note", "footnote") or o.get("id") in ("note", "footnote")):
                if (_number(o.get("w")) >= .6 * width and
                        0 < _number(o.get("h")) <= .18 * height):
                    note_scenes.append(sid)
                    note_objects.append(dict(scene_id=sid, object_id=o.get("id"),
                                             width=o.get("w"), height=o.get("h")))

        def main_size(o):
            return (_number(o.get("w")) >= .08 * width and
                    _number(o.get("h")) >= .12 * height and
                    o.get("role") not in ("decoration", "relation", "connector"))
        assets = [o for o in objects if main_size(o) and
                  (o.get("entity_id") or o.get("asset_id")) and
                  o.get("kind") not in ("brand", "brandwide", "mark", "logo")]
        papers = [o for o in objects if main_size(o) and o.get("kind") == "paper" and o.get("svg")]
        if assets and papers:
            add("mixed_main_asset_and_svg_paper", [sid],
                dict(asset_object_ids=[o.get("id") for o in assets],
                     svg_paper_object_ids=[o.get("id") for o in papers]),
                "并排查看实际尺寸素材，检查主角完成度、材质与视角是否一致；混用本身不判失败，关系线条可保留。")

    for signature, items in entrances.items():
        ratio = len(items) / max(1, len(all_actions))
        if len(items) >= 8 and ratio >= .75 and len({i["scene_id"] for i in items}) >= 3:
            add("dominant_identical_entrance", [i["scene_id"] for i in items],
                dict(signature=json.loads(signature), matching_count=len(items),
                     total_actions=len(all_actions), ratio=round(ratio, 4), threshold=.75,
                     objects=items),
                "检查主要语义动作是否只是统一入场；保留简洁入场，但给关键关系安排可观察的状态变化。")
    ratio = len(set(note_scenes)) / max(1, len(scenes))
    if len(set(note_scenes)) >= 4 and ratio >= .7:
        add("near_per_scene_note_bar", note_scenes,
            dict(note_scene_count=len(set(note_scenes)), total_scenes=len(scenes),
                 ratio=round(ratio, 4), threshold=.7, objects=note_objects),
            "检查是否形成与原字幕并行的第二条说明轨；正常条件标签不在此禁用，逐条判断底栏的观众价值。")
    return dict(schema_version=1, status="review_required" if findings else "no_automatic_findings",
                scan_completed=True, aesthetic_approval=False,
                sentence_state_scan=dict(present="sentence_states" in plan, checked=state_count,
                                         required=require_sentence_states),
                limits="只查结构绑定和启发式候选；不验证焦点/保留理由的语义，不观察实际大小、对比度或动效。无发现不等于语义、审美或动态通过。未扫描原始 SRT/beat 原文。",
                summary=dict(scenes=len(scenes), beats=len(beats), actions=len(all_actions),
                             findings=len(findings)), findings=findings)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path, help="Existing semantic_plan.json (read only)")
    parser.add_argument("--out", type=Path, help="Optional JSON report; must differ from input")
    parser.add_argument("--require-sentence-states", action="store_true",
                        help="For new plans: require state bindings and a target caption/time for review")
    args = parser.parse_args(argv)
    try:
        if args.out and args.out.resolve() == args.plan.resolve():
            raise ValueError("--out must not overwrite the input plan")
        report = audit(json.loads(args.plan.read_text(encoding="utf-8")),
                       require_sentence_states=args.require_sentence_states)
        report["source_plan"] = str(args.plan.resolve())
        data = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(data, encoding="utf-8")
        print(data, end="")
        return 0
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps(dict(status="scan_error", scan_completed=False, error=str(exc)),
                         ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

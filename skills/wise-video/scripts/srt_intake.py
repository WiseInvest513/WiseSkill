#!/usr/bin/env python3
"""Preserve source SRT while preparing an auditable, range-specific video intake."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

STAMP = r"\d+:\d{2}:\d{2}[,.]\d{1,3}"
TIMING = re.compile(rf"^\s*(?P<start>{STAMP})\s*-->\s*(?P<end>{STAMP})(?P<settings>\s+.*)?\s*$")
OUTPUT_NAMES = (
    "captions.parsed.json", "captions.scope.json", "coverage.checklist.json",
    "coverage.checklist.md", "intake-report.json",
)


def issue(code, message, severity="warning", **details):
    return {"code": code, "severity": severity, "message": message, **details}


def seconds_ms(value: str, *, signed=False) -> int:
    """Read seconds or H:MM:SS[.mmm] without floating-point rounding."""
    value = str(value).strip().replace(",", ".")
    try:
        if ":" in value:
            parts = value.split(":")
            if len(parts) != 3 or not parts[0].isdigit() or not re.fullmatch(r"\d{2}", parts[1]):
                raise ValueError("time must be seconds or H:MM:SS[.mmm]")
            hours, minutes, seconds = int(parts[0]), int(parts[1]), Decimal(parts[2])
            if not (0 <= minutes < 60 and 0 <= seconds < 60):
                raise ValueError("minutes and seconds must be below 60")
            number = Decimal(hours * 3600 + minutes * 60) + seconds
        else:
            number = Decimal(value)
        if not number.is_finite() or (number < 0 and not signed):
            raise ValueError("time must be finite and non-negative")
        millis = number * 1000
        if millis != millis.to_integral_value():
            raise ValueError("time precision must be at most one millisecond")
        return int(millis)
    except InvalidOperation as exc:
        raise ValueError(f"invalid time: {value}") from exc


def format_ms(value):
    sign = "-" if value < 0 else ""
    hours, rest = divmod(abs(value), 3600000)
    minutes, rest = divmod(rest, 60000)
    seconds, millis = divmod(rest, 1000)
    return f"{sign}{hours:02}:{minutes:02}:{seconds:02}.{millis:03}"


def parse_srt(source: str):
    """Keep order, cue wording, line breaks, source indices and line locations.

    caption_id is a stable 1-based block ordinal, NOT the possibly duplicated
    source index. Malformed blocks produce errors; they are never silently fixed.
    """
    source = source.removeprefix("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    lines = source.split("\n")
    blocks, current, start_line = [], [], 1
    for number, line in enumerate(lines, 1):
        if not line.strip():
            if current:
                blocks.append((start_line, current))
                current = []
        else:
            if not current:
                start_line = number
            current.append(line)
    if current:
        blocks.append((start_line, current))
    captions, issues = [], []
    for ordinal, (line_number, block) in enumerate(blocks, 1):
        timing_index = 1 if block[0].strip().isdigit() else 0
        source_index = block[0].strip() if timing_index else None
        if timing_index >= len(block):
            issues.append(issue("invalid_block", "字幕块缺少时间和文字。", "error", block=ordinal, source_line=line_number))
            continue
        match = TIMING.fullmatch(block[timing_index])
        if not match:
            issues.append(issue("invalid_timing", "无法解析时间行；不猜测或修正。", "error", block=ordinal, source_line=line_number + timing_index))
            continue
        try:
            start, end = seconds_ms(match["start"]), seconds_ms(match["end"])
        except ValueError as exc:
            issues.append(issue("invalid_timestamp", str(exc), "error", block=ordinal, source_line=line_number + timing_index))
            continue
        text = "\n".join(block[timing_index + 1:])
        if not text.strip():
            issues.append(issue("empty_caption", "字幕没有正文。", "error", block=ordinal, source_line=line_number))
            continue
        if end <= start:
            issues.append(issue("invalid_duration", "字幕结束时间必须大于开始时间。", "error", block=ordinal, start_ms=start, end_ms=end))
            continue
        if source_index is None:
            issues.append(issue("missing_source_index", "字幕块没有原始编号；使用稳定的块顺序 ID。", caption_id=ordinal))
        caption = {"caption_id": ordinal, "start_ms": start, "end_ms": end, "text": text,
                   "source_index": source_index, "source_line": line_number}
        if match["settings"]:
            caption["source_timing_settings"] = match["settings"].strip()
        captions.append(caption)
    if not blocks:
        issues.append(issue("empty_srt", "SRT 中没有字幕块。", "error"))
    return captions, issues


def audit_captions(captions, gap_threshold_ms=1500):
    issues, seen_indices, seen_times = [], {}, {}
    previous = None
    for cue in captions:
        cid = cue["caption_id"]
        index = cue["source_index"]
        timing = (cue["start_ms"], cue["end_ms"])
        if index is not None and index in seen_indices:
            issues.append(issue("duplicate_source_index", "原始字幕编号重复；保留两个条目，不去重。", caption_ids=[seen_indices[index], cid], source_index=index))
        seen_indices[index] = cid
        if timing in seen_times:
            issues.append(issue("duplicate_timing", "两个条目具有完全相同的时间；保留原始内容。", caption_ids=[seen_times[timing], cid]))
        seen_times[timing] = cid
        if previous is not None:
            if cue["start_ms"] < previous["start_ms"]:
                issues.append(issue("out_of_order", "字幕时间倒序；输出仍保留原文件顺序。", caption_ids=[previous["caption_id"], cid]))
            if cue["text"] == previous["text"]:
                issues.append(issue("consecutive_duplicate_text", "相邻字幕正文重复；可能是转写重复，也可能是原声重复，不自动删除。", caption_ids=[previous["caption_id"], cid]))
        previous = cue
    ordered = sorted(captions, key=lambda cue: (cue["start_ms"], cue["end_ms"], cue["caption_id"]))
    previous_end, owner = None, None
    for cue in ordered:
        if previous_end is not None:
            if cue["start_ms"] < previous_end:
                issues.append(issue("overlapping_timing", "字幕显示区间相互重叠；需要确认是否为双人对话或转写问题。", caption_ids=[owner, cue["caption_id"]], overlap_ms=min(cue["end_ms"], previous_end) - cue["start_ms"]))
            elif cue["start_ms"] - previous_end >= gap_threshold_ms:
                issues.append(issue("caption_gap", "此区间没有字幕；需由语义计划说明保留主体或过渡，不能据此推断音频静音。", start_ms=previous_end, end_ms=cue["start_ms"], duration_ms=cue["start_ms"] - previous_end))
        if previous_end is None or cue["end_ms"] > previous_end:
            previous_end, owner = cue["end_ms"], cue["caption_id"]
    return issues


def select_range(captions, start_ms=0, end_ms=None, boundary_policy="whole-cues"):
    if boundary_policy not in {"whole-cues", "exact"}:
        raise ValueError("unsupported boundary policy")
    if start_ms < 0:
        raise ValueError("range start must be non-negative")
    source_end_ms = max((cue["end_ms"] for cue in captions), default=0)
    if end_ms is None:
        end_ms = source_end_ms
    if end_ms <= start_ms:
        raise ValueError("range end must be greater than range start")
    selected = [cue for cue in captions if cue["end_ms"] > start_ms and cue["start_ms"] < end_ms]
    issues = []
    crossing = [cue for cue in selected if cue["start_ms"] < start_ms or cue["end_ms"] > end_ms]
    effective_start, effective_end = start_ms, end_ms
    missing_content_intervals = []
    if end_ms > source_end_ms:
        missing_content_intervals.append({"start_ms": max(start_ms, source_end_ms), "end_ms": end_ms,
                                          "reason": "not_provided_in_srt"})
        issues.append(issue("content_shorter_than_request", "已提供的 SRT 正文早于请求范围结束；剩余内容尚未提供，不能延长背景或补造正文来冒充完整交付。whole-cues 先制作已有内容；exact 保留请求时间轴但待补内容。",
                            source_end_ms=source_end_ms, requested_end_ms=end_ms,
                            missing_start_ms=max(start_ms, source_end_ms), missing_end_ms=end_ms,
                            policy=boundary_policy))
        if boundary_policy == "whole-cues":
            # Never turn a short supplied script into minutes of blank video.
            # An entirely out-of-source request has an empty effective range.
            effective_end = max(start_ms, source_end_ms)
    if start_ms >= source_end_ms and captions:
        issues.append(issue("range_starts_after_source", "请求起点已在所提供正文末尾或之后；没有可用于本范围的内容。", "error",
                            requested_start_ms=start_ms, source_end_ms=source_end_ms))
    if boundary_policy == "whole-cues" and crossing:
        effective_start = min(start_ms, min(cue["start_ms"] for cue in crossing))
        effective_end = max(effective_end, max(cue["end_ms"] for cue in crossing))
        # Expansion can reach other overlapping cues; include them and expand
        # until every included cue is complete rather than silently cutting one.
        while True:
            expanded = [cue for cue in captions if cue["end_ms"] > effective_start and cue["start_ms"] < effective_end]
            new_start = min([effective_start] + [cue["start_ms"] for cue in expanded])
            new_end = max([effective_end] + [cue["end_ms"] for cue in expanded])
            selected = expanded
            if (new_start, new_end) == (effective_start, effective_end):
                break
            effective_start, effective_end = new_start, new_end
    if crossing:
        issues.append(issue("range_crosses_cues", "请求范围切入字幕条目；whole-cues 会扩展到完整条目，exact 仅裁显示时间且不改原文。", caption_ids=[cue["caption_id"] for cue in crossing], policy=boundary_policy))
    if not selected:
        issues.append(issue("empty_scope", "所选范围没有字幕，不能自动推断正文画面。", "error"))
    if selected:
        issues.append(issue("sentence_boundary_unverified", "字幕条目不等于完整语义句。已保留条目原文；跨条目的句意和范围首尾是否完整，必须在语义分镜阶段检查。", "info"))
        intervals = sorted((max(cue["start_ms"], effective_start), min(cue["end_ms"], effective_end)) for cue in selected)
        cursor = effective_start
        for left, right in intervals:
            if left > cursor:
                issues.append(issue("scope_uncovered_interval", "目标范围内此区间无字幕，需安排可见主体；不代表无旁白。", "info", start_ms=cursor, end_ms=left, duration_ms=left - cursor))
            cursor = max(cursor, right)
        if cursor < effective_end:
            issues.append(issue("scope_uncovered_interval", "此区间超出已提供正文；未获准将其补成无字背景，不能当作已有内容。", "info", start_ms=cursor, end_ms=effective_end, duration_ms=effective_end - cursor))
    target = {"requested_start_ms": start_ms, "requested_end_ms": end_ms,
              "effective_start_ms": effective_start, "effective_end_ms": effective_end,
              "duration_ms": effective_end - effective_start, "boundary_policy": boundary_policy,
              "source_end_ms": source_end_ms,
              "requested_content_fully_supplied": end_ms <= source_end_ms and bool(selected),
              "effective_range_content_complete": effective_end <= source_end_ms and bool(selected),
              "content_status": ("no_content" if not selected else "pending_content" if boundary_policy == "exact" and missing_content_intervals else "partial_content_available" if missing_content_intervals else "supplied"),
              "missing_content_intervals": missing_content_intervals,
              "scope_caption_ids": [cue["caption_id"] for cue in selected]}
    return selected, target, issues


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def probe_audio(path, ffprobe=None):
    executable = ffprobe or shutil.which("ffprobe")
    if not executable:
        raise ValueError("ffprobe is unavailable; pass --ffprobe /absolute/path/to/ffprobe")
    try:
        result = subprocess.run([executable, "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)], check=False, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError(f"ffprobe failed: {exc}") from exc
    if result.returncode:
        raise ValueError(f"ffprobe exited {result.returncode}: {result.stderr.strip()[:1000]}")
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError("ffprobe did not return valid JSON") from exc
    streams = [stream for stream in data.get("streams", []) if stream.get("codec_type") == "audio"]
    if not streams:
        raise ValueError("provided file has no audio stream")
    duration = None
    duration_source = None
    # Rendering uses the first audio stream. A longer video/container or other
    # audio stream must not make a shorter primary audio track appear sufficient.
    candidates = [("first_audio_stream", streams[0].get("duration")), ("container_fallback", data.get("format", {}).get("duration"))]
    for source, value in candidates:
        try:
            val = Decimal(str(value))
            if val.is_finite() and val >= 0:
                duration, duration_source = int(val * 1000), source
                break
        except (InvalidOperation, ValueError):
            pass
    return {"duration_ms": duration, "duration_source": duration_source,
            "selected_audio_stream_index": streams[0].get("index"),
            "format_name": data.get("format", {}).get("format_name"),
            "audio_streams": [{key: stream[key] for key in ("index", "codec_name", "sample_rate", "channels", "channel_layout", "duration", "start_time") if key in stream} for stream in streams],
            "ffprobe": str(executable), "raw_probe": data}


def audio_alignment(audio, target, offset_ms=None):
    """Only map an explicitly supplied offset; duration never establishes sync."""
    if audio is None:
        return {"status": "silent_preview_only", "audio_render_allowed": False,
                "message": "未提供音频：可制作无声预览，不生成或伪造旁白。"}, []
    if offset_ms is None:
        return {"status": "offset_required", "audio_render_allowed": False,
                "message": "音频与字幕的时间映射未明确；即使时长相同也不推断同步。"}, [issue("audio_offset_unknown", "先确认同源零点或明确偏移；不能根据时长猜测。")]
    left, right = target["effective_start_ms"] + offset_ms, target["effective_end_ms"] + offset_ms
    duration = audio.get("duration_ms")
    result = {"status": "mapping_declared_content_unverified", "audio_render_allowed": True,
              "offset_ms": offset_ms, "mapping": "audio_time_ms = srt_time_ms + offset_ms",
              "audio_start_ms": left, "audio_end_ms": right,
              "source": "explicit_cli_argument", "content_sync_verified": False,
              "message": "偏移已明确，仍需在至少开头、中间和结尾核对原声与字幕；本工具没有听辨内容。"}
    issues = []
    if left < 0:
        issues.append(issue("audio_range_before_zero", "指定偏移使目标音频从负时间开始，不能渲染。", "error", audio_start_ms=left))
    if duration is None:
        issues.append(issue("audio_duration_unknown", "音频时长不可读取，无法验证范围覆盖。", "error"))
    elif right > duration + 50:
        issues.append(issue("audio_too_short", "音频不足以覆盖指定映射范围，不能自动拉伸或补声。", "error", required_end_ms=right, duration_ms=duration))
    if issues:
        result["status"] = "invalid_audio_range"
        result["audio_render_allowed"] = False
    return result, issues


def build_checklist(captions, target):
    return {"version": 1, "status": "awaiting_semantic_plan",
            "unit": "original_srt_cue_not_inferred_sentence",
            "note": "每条原字幕均需指向可见主体和语义 beat；一语义句可跨多条字幕，复用主体有效，不必每句新增元素。",
            "items": [{"caption_id": cue["caption_id"], "source_index": cue["source_index"],
                       "source_start_ms": cue["start_ms"], "source_end_ms": cue["end_ms"],
                       "display_start_ms": max(cue["start_ms"], target["effective_start_ms"]) - target["effective_start_ms"],
                       "display_end_ms": min(cue["end_ms"], target["effective_end_ms"]) - target["effective_start_ms"],
                       "source_text": cue["text"], "boundary_clipped": cue["start_ms"] < target["effective_start_ms"] or cue["end_ms"] > target["effective_end_ms"],
                       "semantic_sentence_id": None, "beat_ids": [], "visible_subject_ids": [],
                       "handling": None, "acceptance": None, "review_status": "pending"} for cue in captions]}


def checklist_markdown(checklist, target):
    lines = ["# 逐句视觉承接清单（待语义分析）", "", checklist["note"], "",
             f"请求范围：{format_ms(target['requested_start_ms'])}—{format_ms(target['requested_end_ms'])}；实际范围：{format_ms(target['effective_start_ms'])}—{format_ms(target['effective_end_ms'])}。", "",
             "SRT 只给出字幕条目时间；下面不是自动断句结果，也不是已通过的视觉覆盖验收。", ""]
    for missing in target.get("missing_content_intervals", []):
        lines += [f"**尚未提供的正文：{format_ms(missing['start_ms'])}—{format_ms(missing['end_ms'])}。不能延长背景来冒充该段内容。**", ""]
    for cue in checklist["items"]:
        lines += [f"## 字幕 {cue['caption_id']} · {format_ms(cue['source_start_ms'])}—{format_ms(cue['source_end_ms'])}", "", cue["source_text"], "",
                  "- [ ] 与相邻字幕组成完整语义句并记录限定、否定和条件。",
                  "- [ ] 指向实际可见主体与 beat；说明出现、复用、聚焦、变化或有意停留。",
                  "- [ ] 写清前状态 → 动作 → 后状态和观察时间点。", ""]
    return "\n".join(lines)


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("srt", type=Path)
    parser.add_argument("--audio", type=Path)
    parser.add_argument("--start", default="0", help="seconds or H:MM:SS.mmm")
    stop = parser.add_mutually_exclusive_group()
    stop.add_argument("--end", help="absolute SRT end time")
    stop.add_argument("--duration", help="duration from requested start")
    parser.add_argument("--boundary-policy", choices=("whole-cues", "exact"), default="whole-cues")
    parser.add_argument("--audio-offset", help="explicit seconds: audio_time = SRT_time + offset (zero must also be explicit)")
    parser.add_argument("--ffprobe", help="path to ffprobe; otherwise searches PATH")
    parser.add_argument("--gap-threshold", default="1.5", help="seconds, audit gaps at least this long")
    parser.add_argument("--out", required=True, type=Path, help="new output directory; does not overwrite intake artifacts")
    args = parser.parse_args(argv)
    try:
        srt_path = args.srt.resolve(strict=True)
        raw = srt_path.read_bytes()
        source = raw.decode("utf-8-sig")
        start = seconds_ms(args.start)
        duration = seconds_ms(args.duration) if args.duration is not None else None
        end = seconds_ms(args.end) if args.end is not None else (start + duration if duration is not None else None)
        threshold = seconds_ms(args.gap_threshold)
        if threshold <= 0:
            raise ValueError("--gap-threshold must be positive")
        if args.audio_offset is not None and args.audio is None:
            raise ValueError("--audio-offset requires --audio")
        offset = seconds_ms(args.audio_offset, signed=True) if args.audio_offset is not None else None
        out = args.out.resolve()
        if any((out / name).exists() for name in OUTPUT_NAMES):
            raise ValueError("output artifacts already exist; use a new --out directory to preserve history")
        captions, issues = parse_srt(source)
        issues.extend(audit_captions(captions, threshold))
        scoped, target, range_issues = select_range(captions, start, end, args.boundary_policy)
        issues.extend(range_issues)
        audio, audio_input = None, None
        if args.audio is not None:
            audio_path = args.audio.resolve(strict=True)
            audio_input = {"path": str(audio_path), "sha256": sha256(audio_path), "size_bytes": audio_path.stat().st_size}
            try:
                audio = probe_audio(audio_path, args.ffprobe)
            except ValueError as exc:
                issues.append(issue("audio_probe_failed", str(exc), "error"))
                audio = {"duration_ms": None, "probe_failed": True}
        alignment, audio_issues = audio_alignment(audio, target, offset)
        issues.extend(audio_issues)
        if audio and audio.get("probe_failed"):
            alignment["audio_render_allowed"] = False
            alignment["status"] = "audio_probe_failed"
        errors = [item for item in issues if item["severity"] == "error"]
        checklist = build_checklist(scoped, target)
        content_pending = target["content_status"] == "pending_content"
        report = {"schema_version": 1, "created_at": datetime.now(timezone.utc).isoformat(),
                  "input_srt": {"path": str(srt_path), "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw), "encoding": "utf-8-sig" if raw.startswith(b"\xef\xbb\xbf") else "utf-8", "source_modified": False},
                  "input_audio": audio_input, "audio_probe": audio,
                  "source_caption_count": len(captions), "scope_caption_count": len(scoped),
                  "range": target, "audio_alignment": alignment,
                  "status": "failed" if errors else "pending" if content_pending else "ready_for_available_content",
                  "readiness": {"intake_valid": not errors, "semantic_plan_required": True,
                                "available_content_analysis_allowed": not errors and bool(scoped),
                                "requested_content_fully_supplied": not errors and target["requested_content_fully_supplied"],
                                "silent_preview_allowed": not errors and target["effective_range_content_complete"],
                                "audio_render_allowed": not errors and target["effective_range_content_complete"] and alignment["audio_render_allowed"],
                                "semantic_quality_verified": False, "content_audio_sync_verified": False},
                  "issues": issues,
                  "limitations": ["不改写、不去重、不重新排序原字幕。", "原文 line breaks 保留；原始输入字节由 SHA256 锁定。", "连续覆盖只表示每个字幕条目已列入待办，不表示已经设计画面或理解完整语义句。", "音频时长与显式偏移只能验证时间范围，不能证明内容同步。", "不生成旁白；不拉伸、裁改或自动补齐原音频。"]}
        out.mkdir(parents=True, exist_ok=True)
        write_json(out / "captions.parsed.json", captions)
        write_json(out / "captions.scope.json", scoped)
        write_json(out / "coverage.checklist.json", checklist)
        (out / "coverage.checklist.md").write_text(checklist_markdown(checklist, target), encoding="utf-8")
        write_json(out / "intake-report.json", report)
        print(json.dumps({"out": str(out), "captions": len(captions), "selected": len(scoped), "duration_ms": target["duration_ms"], "errors": len(errors), "warnings": sum(item["severity"] == "warning" for item in issues), "audio_status": alignment["status"], "content_status": target["content_status"], "requested_content_fully_supplied": target["requested_content_fully_supplied"]}, ensure_ascii=False))
        return 2 if errors else 3 if content_pending else 0
    except (OSError, UnicodeError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())

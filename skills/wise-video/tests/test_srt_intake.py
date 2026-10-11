import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "srt_intake.py"
spec = importlib.util.spec_from_file_location("srt_intake", MODULE_PATH)
intake = importlib.util.module_from_spec(spec)
spec.loader.exec_module(intake)


def cue(index, start, end, text):
    return f"{index}\n{start} --> {end}\n{text}\n"


def sample():
    return "\n".join([
        cue(1, "00:00:00,000", "00:00:02,000", "第一行\n第二行"),
        cue(2, "00:00:02,000", "00:00:04,000", "后续内容"),
        cue(3, "00:00:06,000", "00:00:08,000", "第三条"),
    ])


class ParsingTests(unittest.TestCase):
    def test_bom_crlf_dots_and_multiline_preserved(self):
        text = "\ufeff17\r\n00:01:02.125 --> 00:01:04,050\r\n 第一行 \r\n第二行\r\n"
        captions, issues = intake.parse_srt(text)
        self.assertEqual(captions[0]["text"], " 第一行 \n第二行")
        self.assertEqual(captions[0]["source_index"], "17")
        self.assertEqual(captions[0]["caption_id"], 1)
        self.assertEqual((captions[0]["start_ms"], captions[0]["end_ms"]), (62125, 64050))
        self.assertFalse(issues)

    def test_time_parser_is_exact_and_not_hardcoded_to_two_minutes(self):
        self.assertEqual(intake.seconds_ms("600.125"), 600125)
        self.assertEqual(intake.seconds_ms("01:02:03,007"), 3723007)
        self.assertEqual(intake.seconds_ms("-2.5", signed=True), -2500)
        for invalid in ("nan", "inf", "-1", "00:60:01", "1.0001"):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                intake.seconds_ms(invalid)

    def test_duplicate_source_ids_timing_and_text_are_not_deleted(self):
        source = "\n".join([cue(9, "00:00:00,000", "00:00:02,000", "重复"), cue(9, "00:00:00,000", "00:00:02,000", "重复")])
        captions, _ = intake.parse_srt(source)
        issues = intake.audit_captions(captions)
        self.assertEqual([item["caption_id"] for item in captions], [1, 2])
        self.assertTrue({"duplicate_source_index", "duplicate_timing", "consecutive_duplicate_text", "overlapping_timing"}.issubset({item["code"] for item in issues}))

    def test_out_of_order_does_not_reorder_source(self):
        source = "\n".join([cue(1, "00:00:06,000", "00:00:07,000", "later"), cue(2, "00:00:01,000", "00:00:03,000", "earlier")])
        captions, _ = intake.parse_srt(source)
        self.assertEqual([cue["text"] for cue in captions], ["later", "earlier"])
        self.assertIn("out_of_order", [item["code"] for item in intake.audit_captions(captions)])

    def test_invalid_blocks_are_errors_not_silent_repairs(self):
        source = "1\n00:00:04,000 --> 00:00:02,000\nbackwards\n\n2\nbad timing\ntext\n\n3\n00:00:61,000 --> 00:02:00,000\ninvalid\n"
        captions, issues = intake.parse_srt(source)
        self.assertFalse(captions)
        self.assertEqual({i["code"] for i in issues}, {"invalid_duration", "invalid_timing", "invalid_timestamp"})
        self.assertTrue(all(i["severity"] == "error" for i in issues))

    def test_missing_index_and_srt_position_settings_retained(self):
        captions, issues = intake.parse_srt("00:00:00,000 --> 00:00:01,000 X1:40 X2:600\nText\n")
        self.assertIsNone(captions[0]["source_index"])
        self.assertEqual(captions[0]["source_timing_settings"], "X1:40 X2:600")
        self.assertEqual(issues[0]["code"], "missing_source_index")


class RangeTests(unittest.TestCase):
    def setUp(self):
        self.captions, _ = intake.parse_srt(sample())

    def test_mid_range_expands_to_complete_cues(self):
        selected, target, issues = intake.select_range(self.captions, 1000, 3000)
        self.assertEqual(target["scope_caption_ids"], [1, 2])
        self.assertEqual((target["effective_start_ms"], target["effective_end_ms"]), (0, 4000))
        self.assertEqual([cue["text"] for cue in selected], ["第一行\n第二行", "后续内容"])
        self.assertIn("sentence_boundary_unverified", [i["code"] for i in issues])

    def test_half_open_boundary_does_not_include_next_cue(self):
        selected, target, _ = intake.select_range(self.captions, 0, 2000)
        self.assertEqual(target["scope_caption_ids"], [1])

    def test_exact_range_clips_display_time_without_rewriting_text(self):
        selected, target, _ = intake.select_range(self.captions, 1000, 3000, "exact")
        checklist = intake.build_checklist(selected, target)
        self.assertEqual(target["duration_ms"], 2000)
        self.assertEqual(checklist["items"][0]["source_text"], "第一行\n第二行")
        self.assertEqual(checklist["items"][0]["display_start_ms"], 0)
        self.assertEqual(checklist["items"][1]["display_end_ms"], 2000)
        self.assertTrue(all(item["boundary_clipped"] for item in checklist["items"]))

    def test_overlapping_expansion_includes_entire_newly_reached_cue(self):
        source = "\n".join([cue(1, "00:00:00,000", "00:00:03,000", "one"), cue(2, "00:00:02,000", "00:00:05,000", "two"), cue(3, "00:00:04,000", "00:00:06,000", "three")])
        captions, _ = intake.parse_srt(source)
        _, target, _ = intake.select_range(captions, 1000, 1500)
        self.assertEqual(target["scope_caption_ids"], [1, 2, 3])
        self.assertEqual(target["effective_end_ms"], 6000)

    def test_missing_content_interval_is_reported_not_filled(self):
        _, _, issues = intake.select_range(self.captions, 0, 8000)
        gaps = [(item["start_ms"], item["end_ms"]) for item in issues if item["code"] == "scope_uncovered_interval"]
        self.assertEqual(gaps, [(4000, 6000)])
        self.assertIn("caption_gap", [item["code"] for item in intake.audit_captions(self.captions)])

    def test_empty_range_is_an_error(self):
        _, _, issues = intake.select_range(self.captions, 9000, 10000)
        self.assertTrue(any(item["code"] == "empty_scope" and item["severity"] == "error" for item in issues))


    def test_short_source_does_not_expand_to_requested_five_or_ten_minutes(self):
        captions, _ = intake.parse_srt(cue(1, "00:00:00,000", "00:00:24,000", "只有这段已提供内容"))
        for requested_end in (300000, 600000):
            with self.subTest(requested_end=requested_end):
                selected, target, issues = intake.select_range(captions, 0, requested_end)
                self.assertEqual(target["requested_end_ms"], requested_end)
                self.assertEqual(target["effective_end_ms"], 24000)
                self.assertEqual(target["duration_ms"], 24000)
                self.assertEqual(target["content_status"], "partial_content_available")
                self.assertFalse(target["requested_content_fully_supplied"])
                self.assertTrue(target["effective_range_content_complete"])
                self.assertEqual(target["missing_content_intervals"], [{"start_ms": 24000, "end_ms": requested_end, "reason": "not_provided_in_srt"}])
                self.assertIn("content_shorter_than_request", [item["code"] for item in issues])
                self.assertFalse(any(item["severity"] == "error" for item in issues))
                self.assertEqual(selected[0]["text"], "只有这段已提供内容")

    def test_short_source_exact_range_is_pending_with_unprovided_tail(self):
        captions, _ = intake.parse_srt(cue(1, "00:00:00,000", "00:00:24,000", "已提供内容"))
        _, target, issues = intake.select_range(captions, 0, 300000, "exact")
        self.assertEqual(target["effective_end_ms"], 300000)
        self.assertEqual(target["content_status"], "pending_content")
        self.assertFalse(target["effective_range_content_complete"])
        gaps = [(item["start_ms"], item["end_ms"]) for item in issues if item["code"] == "scope_uncovered_interval"]
        self.assertEqual(gaps, [(24000, 300000)])

    def test_start_after_source_is_empty_error_without_negative_duration(self):
        captions, _ = intake.parse_srt(cue(1, "00:00:00,000", "00:00:24,000", "已提供内容"))
        selected, target, issues = intake.select_range(captions, 30000, 330000)
        self.assertFalse(selected)
        self.assertEqual(target["duration_ms"], 0)
        self.assertEqual(target["content_status"], "no_content")
        self.assertFalse(target["effective_range_content_complete"])
        self.assertTrue(any(item["code"] == "range_starts_after_source" and item["severity"] == "error" for item in issues))


class AudioTests(unittest.TestCase):
    def setUp(self):
        self.target = {"effective_start_ms": 1000, "effective_end_ms": 5000}

    def test_no_audio_means_silent_preview_only(self):
        result, issues = intake.audio_alignment(None, self.target)
        self.assertEqual(result["status"], "silent_preview_only")
        self.assertFalse(result["audio_render_allowed"])
        self.assertFalse(issues)

    def test_matching_duration_does_not_infer_sync(self):
        result, issues = intake.audio_alignment({"duration_ms": 5000}, self.target)
        self.assertEqual(result["status"], "offset_required")
        self.assertFalse(result["audio_render_allowed"])

    def test_explicit_zero_offset_is_not_claimed_content_verified(self):
        result, issues = intake.audio_alignment({"duration_ms": 6000}, self.target, 0)
        self.assertTrue(result["audio_render_allowed"])
        self.assertFalse(result["content_sync_verified"])
        self.assertEqual(result["audio_start_ms"], 1000)
        self.assertFalse(issues)

    def test_negative_mapping_and_short_audio_are_blocked(self):
        result, issues = intake.audio_alignment({"duration_ms": 2000}, self.target, -1500)
        self.assertFalse(result["audio_render_allowed"])
        self.assertEqual({item["code"] for item in issues}, {"audio_range_before_zero", "audio_too_short"})

    def test_probe_uses_argument_list_and_no_shell(self):
        response = type("Result", (), {"returncode": 0, "stdout": json.dumps({"format": {"duration": "10.123"}, "streams": [{"index": 0, "codec_type": "audio", "codec_name": "aac", "sample_rate": "48000"}]}), "stderr": ""})()
        with mock.patch.object(intake.subprocess, "run", return_value=response) as run:
            result = intake.probe_audio(Path("a file;$(touch bad).mp3"), "/test/ffprobe")
        self.assertEqual(result["duration_ms"], 10123)
        self.assertNotIn("shell", run.call_args.kwargs)
        self.assertEqual(run.call_args.args[0][-1], "a file;$(touch bad).mp3")


    def test_longer_container_does_not_hide_short_primary_audio(self):
        response = type("Result", (), {"returncode": 0, "stdout": json.dumps({"format": {"duration": "60"}, "streams": [{"index": 0, "codec_type": "audio", "duration": "3"}, {"index": 1, "codec_type": "audio", "duration": "60"}]}), "stderr": ""})()
        with mock.patch.object(intake.subprocess, "run", return_value=response):
            result = intake.probe_audio(Path("clip.mkv"), "/test/ffprobe")
        self.assertEqual(result["duration_ms"], 3000)
        self.assertEqual(result["duration_source"], "first_audio_stream")
        mapping, issues = intake.audio_alignment(result, self.target, 0)
        self.assertFalse(mapping["audio_render_allowed"])
        self.assertEqual(issues[0]["code"], "audio_too_short")


class CLITests(unittest.TestCase):
    def test_end_to_end_keeps_input_bytes_hash_and_pending_coverage(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = root / "input.srt"
            raw = ("\ufeff" + sample()).encode("utf-8")
            src.write_bytes(raw)
            with contextlib.redirect_stdout(io.StringIO()):
                result = intake.main([str(src), "--duration", "3", "--out", str(root / "out")])
            self.assertEqual(result, 0)
            self.assertEqual(src.read_bytes(), raw)
            report = json.loads((root / "out/intake-report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["input_srt"]["sha256"], hashlib.sha256(raw).hexdigest())
            self.assertEqual(report["scope_caption_count"], 2)
            self.assertFalse(report["readiness"]["semantic_quality_verified"])
            coverage = json.loads((root / "out/coverage.checklist.json").read_text(encoding="utf-8"))
            self.assertTrue(all(item["review_status"] == "pending" for item in coverage["items"]))
            self.assertEqual(len(list((root / "out").iterdir())), 5)
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as exc:
                intake.main([str(src), "--out", str(root / "out")])
            self.assertEqual(exc.exception.code, 2)

    def test_malformed_block_keeps_error_report_and_nonzero_exit(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = root / "input.srt"
            src.write_text(sample() + "\n4\nBROKEN\nnot silently skipped\n", encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                result = intake.main([str(src), "--duration", "8", "--out", str(root / "out")])
            self.assertEqual(result, 2)
            report = json.loads((root / "out/intake-report.json").read_text(encoding="utf-8"))
            self.assertFalse(report["readiness"]["intake_valid"])
            self.assertFalse(report["readiness"]["silent_preview_allowed"])


    def test_short_source_cli_can_proceed_only_with_available_content(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = root / "short.srt"
            src.write_text(cue(1, "00:00:00,000", "00:00:24,000", "这份内容只有二十四秒"), encoding="utf-8")
            for duration in ("300", "600"):
                with self.subTest(duration=duration), contextlib.redirect_stdout(io.StringIO()):
                    out = root / duration
                    code = intake.main([str(src), "--duration", duration, "--out", str(out)])
                    report = json.loads((out / "intake-report.json").read_text(encoding="utf-8"))
                    self.assertEqual(code, 0)
                    self.assertEqual(report["range"]["duration_ms"], 24000)
                    self.assertTrue(report["readiness"]["silent_preview_allowed"])
                    self.assertFalse(report["readiness"]["requested_content_fully_supplied"])
                    self.assertEqual(report["status"], "ready_for_available_content")

    def test_exact_cli_cannot_claim_five_minutes_of_provided_content(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = root / "short.srt"
            src.write_text(cue(1, "00:00:00,000", "00:00:24,000", "只有二十四秒"), encoding="utf-8")
            out = root / "out"
            with contextlib.redirect_stdout(io.StringIO()):
                code = intake.main([str(src), "--duration", "300", "--boundary-policy", "exact", "--out", str(out)])
            report = json.loads((out / "intake-report.json").read_text(encoding="utf-8"))
            self.assertEqual(code, 3)
            self.assertEqual(report["status"], "pending")
            self.assertFalse(report["readiness"]["silent_preview_allowed"])
            self.assertFalse(report["readiness"]["audio_render_allowed"])
            self.assertTrue(report["readiness"]["available_content_analysis_allowed"])
            self.assertEqual(report["range"]["duration_ms"], 300000)

    def test_cli_start_after_source_is_hard_failure(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = root / "short.srt"
            src.write_text(cue(1, "00:00:00,000", "00:00:24,000", "只有二十四秒"), encoding="utf-8")
            out = root / "out"
            with contextlib.redirect_stdout(io.StringIO()):
                code = intake.main([str(src), "--start", "30", "--duration", "300", "--out", str(out)])
            report = json.loads((out / "intake-report.json").read_text(encoding="utf-8"))
            self.assertEqual(code, 2)
            self.assertFalse(report["readiness"]["intake_valid"])
            self.assertFalse(report["readiness"]["silent_preview_allowed"])
            self.assertEqual(report["range"]["duration_ms"], 0)


if __name__ == "__main__":
    unittest.main()

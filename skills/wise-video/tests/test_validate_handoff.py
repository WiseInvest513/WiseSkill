import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

TOOLING = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(TOOLING))
import srt_intake
import validate_handoff as handoff


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = self.root / "source.srt"
        self.source.write_text("1\n00:00:10,000 --> 00:00:12,000\n原文一\n\n2\n00:00:12,000 --> 00:00:15,000\n原文二\n", encoding="utf-8")
        self.intake = self.root / "intake"
        with contextlib.redirect_stdout(io.StringIO()):
            srt_intake.main([str(self.source), "--start", "10", "--end", "15", "--out", str(self.intake)])
        self.comp = self.root / "composition"
        self.comp.mkdir()
        self.plan_path = self.root / "plan.json"
        self.plan = {"version": 1, "scope_caption_ids": [1, 2], "entities": [],
                     "beats": [{"id": "b1", "source_caption_ids": [1], "text": "原文一"}, {"id": "b2", "source_caption_ids": [2], "text": "原文二"}],
                     "coverage": [{"caption_id": 1, "beat_ids": ["b1"]}, {"caption_id": 2, "beat_ids": ["b2"]}],
                     "sentence_coverage": [{"caption_id": 1, "start_ms": 10000, "end_ms": 12000, "text": "原文一"}, {"caption_id": 2, "start_ms": 12000, "end_ms": 15000, "text": "原文二"}],
                     "render_spec": {"scenes": [
                         {"id": "a", "start_ms": 10000, "end_ms": 12000, "objects": [{"id": "subject"}], "actions": [{"target": "subject", "op": "fromTo", "at_ms": 10000, "duration_ms": 300, "initial": {"opacity": 0}, "values": {"opacity": 1}}]},
                         {"id": "b", "start_ms": 12000, "end_ms": 15000, "objects": [{"id": "subject"}], "actions": [{"target": "subject", "op": "fromTo", "at_ms": 12000, "duration_ms": 300, "initial": {"opacity": 0}, "values": {"opacity": 1}}]},
                     ]},
                     "render_bindings": [{"caption_id": 1, "segments": [{"scene_id": "a", "object_ids": ["a-subject"], "start_ms": 10000, "end_ms": 12000}]}, {"caption_id": 2, "segments": [{"scene_id": "b", "object_ids": ["b-subject"], "start_ms": 12000, "end_ms": 15000}]}]}
        self.media_markup = ""
        self.write_all()

    def tearDown(self):
        self.tmp.cleanup()

    def write_json(self, path, value):
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")

    def write_all(self):
        self.write_json(self.plan_path, self.plan)
        cues = []
        markup = []
        for scene in self.plan["render_spec"]["scenes"]:
            markup.append(f'<section class="clip scene" id="{scene["id"]}" data-start="{(scene["start_ms"] - 10000)/1000}" data-duration="{(scene["end_ms"] - scene["start_ms"])/1000}"><div id="{scene["id"]}-subject">图解{self.media_markup}</div></section>')
            cues += [{**action, "target": scene["id"] + "-" + action["target"], "scene_id": scene["id"], "at_ms": action["at_ms"] - 10000} for action in scene["actions"]]
        self.write_json(self.comp / "cue_sheet.json", {"plan_sha256": handoff.sha(self.plan_path), "cues": cues})
        html = '<div data-composition-id="test" data-duration="5">' + "".join(markup) + '</div><script>const cues=' + json.dumps(cues) + ';</script>'
        (self.comp / "index.html").write_text(html, encoding="utf-8")
        self.write_provenance()

    def write_provenance(self):
        self.write_json(self.comp / "provenance.json", {"plan_sha256": handoff.sha(self.plan_path), "html_sha256": handoff.sha(self.comp / "index.html"), "source_captions_sha256": handoff.sha(self.source)})

    def check(self):
        return handoff.validate(self.intake, self.plan_path, self.comp)

    def codes(self, result):
        return {row["code"] for row in result["findings"]}

    def test_valid_mid_file_local_composition_passes_mechanical_only(self):
        result = self.check()
        self.assertEqual(result["status"], "passed", result["findings"])
        self.assertTrue(all(v == "not_verified" for v in result["review_layers"].values()))
        self.assertEqual([row["status"] for row in result["caption_bindings"]], ["passed", "passed"])

    def test_missing_all_bindings_is_pending_not_false_pass(self):
        self.plan.pop("render_bindings")
        self.plan["review"] = "passed"
        self.plan["status"] = "passed"
        self.write_all()
        result = self.check()
        self.assertEqual(result["status"], "pending")
        self.assertIn("render_bindings_missing", self.codes(result))

    def test_missing_one_caption_is_failed(self):
        self.plan["render_bindings"].pop()
        self.write_all()
        self.assertIn("caption_binding_missing", self.codes(self.check()))
        self.assertEqual(self.check()["status"], "failed")

    def test_nonexistent_or_wrong_scene_objects_fail(self):
        for object_id, code in (("not-a-real-object", "binding_object_missing"), ("b-subject", "binding_object_wrong_scene"), ("a", "binding_object_wrong_scene")):
            with self.subTest(object_id=object_id):
                self.plan["render_bindings"][0]["segments"][0]["object_ids"] = [object_id]
                self.write_all()
                self.assertIn(code, self.codes(self.check()))

    def test_time_gap_cannot_be_overridden_by_self_declared_pass(self):
        segment = self.plan["render_bindings"][0]["segments"][0]
        segment["end_ms"] = 11000
        segment["status"] = "passed"
        segment["verified"] = True
        self.write_all()
        self.assertIn("binding_time_gap", self.codes(self.check()))

    def test_cross_scene_caption_uses_segments(self):
        self.plan["render_spec"]["scenes"][0]["end_ms"] = 11000
        self.plan["render_spec"]["scenes"][1]["start_ms"] = 11000
        self.plan["render_spec"]["scenes"][1]["actions"][0]["at_ms"] = 11000
        self.plan["render_bindings"][0]["segments"] = [
            {"scene_id": "a", "object_ids": ["a-subject"], "start_ms": 10000, "end_ms": 11000},
            {"scene_id": "b", "object_ids": ["b-subject"], "start_ms": 11000, "end_ms": 12000}]
        self.write_all()
        self.assertEqual(self.check()["status"], "passed", self.check()["findings"])

    def test_binding_cannot_extend_past_own_caption_or_scene(self):
        self.plan["render_bindings"][0]["segments"][0]["end_ms"] = 13000
        self.write_all()
        self.assertTrue({"binding_outside_caption", "binding_outside_scene"}.issubset(self.codes(self.check())))

    def test_source_text_tamper_detected_in_plan_and_intake(self):
        self.plan["beats"][0]["text"] = "改写"
        self.write_all()
        self.assertIn("beat_text_changed", self.codes(self.check()))
        rows = json.loads((self.intake / "captions.scope.json").read_text(encoding="utf-8"))
        rows[0]["text"] = "篡改"
        self.write_json(self.intake / "captions.scope.json", rows)
        self.assertIn("scope_source_changed", self.codes(self.check()))

    def test_source_file_change_detected_even_if_intake_says_valid(self):
        self.source.write_text(self.source.read_text(encoding="utf-8").replace("原文一", "另一个版本"), encoding="utf-8")
        self.assertIn("source_hash_mismatch", self.codes(self.check()))

    def test_plan_change_without_recompiling_is_failed(self):
        self.plan["render_spec"]["scenes"][0]["actions"][0]["duration_ms"] = 650
        self.write_json(self.plan_path, self.plan)
        self.assertTrue({"cue_plan_hash_mismatch", "plan_action_not_compiled", "provenance_hash_mismatch"}.issubset(self.codes(self.check())))

    def test_changed_html_cues_are_detected_even_if_html_hash_updated(self):
        html = (self.comp / "index.html").read_text(encoding="utf-8").replace('"duration_ms": 300', '"duration_ms": 301', 1)
        (self.comp / "index.html").write_text(html, encoding="utf-8")
        self.write_provenance()
        self.assertIn("embedded_cues_mismatch", self.codes(self.check()))

    def test_missing_asset_is_pending_and_listed(self):
        self.plan["entities"] = [{"id": "nvidia", "asset_id": "nvidia-logo", "representation": "icon", "asset_status": "missing"}]
        self.write_all()
        result = self.check()
        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["assets"][0]["declared_status"], "missing")
        self.assertIn("asset_unresolved", self.codes(result))

    def test_ready_flag_without_real_asset_is_not_accepted(self):
        self.plan["entities"] = [{"id": "item", "asset_id": "item-logo", "representation": "icon", "asset_status": "ready"}]
        self.write_all()
        self.assertEqual(self.check()["status"], "pending")
        self.assertIn("asset_identity_not_resolved", self.codes(self.check()))

    def test_local_media_missing_is_failed(self):
        self.media_markup = '<img src="assets/item-logo.png">'
        self.write_all()
        self.assertIn("local_media_missing", self.codes(self.check()))
        self.assertEqual(self.check()["status"], "failed")

    def test_ready_asset_with_actual_file_is_mechanically_resolved(self):
        self.plan["entities"] = [{"id": "item", "asset_id": "item-logo", "representation": "icon", "asset_status": "ready"}]
        self.media_markup = '<img src="assets/item-logo.png">'
        (self.comp / "assets").mkdir()
        (self.comp / "assets/item-logo.png").write_bytes(b"test asset; decoding belongs to media QA")
        self.write_all()
        result = self.check()
        self.assertEqual(result["status"], "passed", result["findings"])
        self.assertEqual(result["assets"][0]["status"], "passed")
        self.assertEqual(result["review_layers"]["runtime_visibility"], "not_verified")

    def test_scene_time_drift_and_duplicate_dom_id_fail(self):
        html = (self.comp / "index.html").read_text(encoding="utf-8").replace('data-duration="2.0"', 'data-duration="1.0"').replace('id="b-subject"', 'id="a-subject"')
        (self.comp / "index.html").write_text(html, encoding="utf-8")
        self.write_provenance()
        self.assertTrue({"scene_timing_mismatch", "duplicate_dom_id"}.issubset(self.codes(self.check())))

    def test_coverage_beat_must_contain_the_caption(self):
        self.plan["coverage"][0]["beat_ids"] = ["b2"]
        self.write_all()
        self.assertIn("coverage_beat_mismatch", self.codes(self.check()))


    def test_exact_source_shortfall_stays_pending_after_all_bindings_pass(self):
        self.intake = self.root / "intake-exact"
        with contextlib.redirect_stdout(io.StringIO()):
            intake_code = srt_intake.main([str(self.source), "--start", "10", "--end", "20", "--boundary-policy", "exact", "--out", str(self.intake)])
        self.assertEqual(intake_code, 3)
        html = (self.comp / "index.html").read_text(encoding="utf-8").replace('data-duration="5"', 'data-duration="10"')
        (self.comp / "index.html").write_text(html, encoding="utf-8")
        self.write_provenance()
        result = self.check()
        self.assertEqual(result["status"], "pending", result["findings"])
        self.assertEqual(result["counts"]["failed"], 0)
        self.assertTrue(all(row["status"] == "passed" for row in result["caption_bindings"]))
        self.assertIn("effective_source_content_pending", self.codes(result))

    def test_self_edited_intake_ready_cannot_hide_unprovided_exact_tail(self):
        self.intake = self.root / "intake-exact"
        with contextlib.redirect_stdout(io.StringIO()):
            srt_intake.main([str(self.source), "--start", "10", "--end", "20", "--boundary-policy", "exact", "--out", str(self.intake)])
        report = json.loads((self.intake / "intake-report.json").read_text(encoding="utf-8"))
        report["status"] = "ready_for_available_content"
        report["range"]["effective_range_content_complete"] = True
        report["readiness"]["intake_valid"] = True
        self.write_json(self.intake / "intake-report.json", report)
        html = (self.comp / "index.html").read_text(encoding="utf-8").replace('data-duration="5"', 'data-duration="10"')
        (self.comp / "index.html").write_text(html, encoding="utf-8")
        self.write_provenance()
        self.assertEqual(self.check()["status"], "pending")
        self.assertIn("effective_source_content_pending", self.codes(self.check()))

    def test_intake_hard_error_status_cannot_be_mechanically_passed(self):
        report = json.loads((self.intake / "intake-report.json").read_text(encoding="utf-8"))
        report["status"] = "failed"
        self.write_json(self.intake / "intake-report.json", report)
        result = self.check()
        self.assertEqual(result["status"], "failed")
        self.assertIn("intake_not_valid", self.codes(result))

    def test_default_short_source_can_pass_for_its_actual_available_range(self):
        self.intake = self.root / "intake-whole-short"
        with contextlib.redirect_stdout(io.StringIO()):
            code = srt_intake.main([str(self.source), "--start", "10", "--end", "600", "--out", str(self.intake)])
        self.assertEqual(code, 0)
        report = json.loads((self.intake / "intake-report.json").read_text(encoding="utf-8"))
        self.assertFalse(report["range"]["requested_content_fully_supplied"])
        self.assertTrue(report["range"]["effective_range_content_complete"])
        self.assertEqual(self.check()["status"], "passed", self.check()["findings"])

    def test_cli_output_cannot_overwrite_prior_evidence(self):
        out = self.root / "qa.json"
        with contextlib.redirect_stdout(io.StringIO()):
            code = handoff.main(["--intake", str(self.intake), "--plan", str(self.plan_path), "--composition", str(self.comp), "--out", str(out)])
        self.assertEqual(code, 0)
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as exc:
            handoff.main(["--intake", str(self.intake), "--plan", str(self.plan_path), "--composition", str(self.comp), "--out", str(out)])
        self.assertEqual(exc.exception.code, 2)


if __name__ == "__main__":
    unittest.main()

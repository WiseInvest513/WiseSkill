"""Behavioral checks for the read-only visual plan review scanner."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_visual_plan.py"
SPEC = importlib.util.spec_from_file_location("audit_visual_plan", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def plan(count=4):
    return {"version": 1, "render_spec": {"width": 1920, "height": 1080,
            "scenes": [{"id": "s" + str(i), "objects": [], "actions": []}
                       for i in range(count)]}, "beats": [], "coverage": []}


def codes(result):
    return {f["code"] for f in result["findings"]}


def state_plan():
    p = plan(1)
    p["render_spec"]["scenes"][0]["objects"] = [
        {"id": oid} for oid in ("heading", "total-limit", "total-amount", "cash", "cash-amount")]
    p["sentence_states"] = [{"scene_id": "s0", "caption_ids": [87],
        "target_caption_id": 87, "time_ms": 163000,
        "focus_object_ids": ["cash", "cash-amount"],
        "focus_reason": "金额与现金物件一起表达当前现金子限额",
        "retain": [{"object_id": "total-limit", "reason": "外层仍显示现金属于总额以内"}],
        "retire_object_ids": []}]
    return p


class VisualAuditTests(unittest.TestCase):
    def test_safe_labels_and_source_script_are_not_flagged(self):
        p = plan(1)
        p["beats"] = [{"id": "s0", "text": "口播称尚未核实，原始字幕末尾"}]
        p["srt"] = "据讲述资料"
        p["render_spec"]["scenes"][0]["objects"] = [
            {"id": "terms", "kind": "label", "text": "SIPC 现金子限额 $250,000；税率 20%；账户资格"}]
        report = MODULE.audit(p)
        self.assertEqual(report["status"], "no_automatic_findings")
        self.assertFalse(report["aesthetic_approval"])

    def test_only_rendered_object_work_language_is_reported(self):
        p = plan(1)
        p["render_spec"]["scenes"][0]["objects"] = [
            {"id": "address", "kind": "paper", "text": "地址证明\n口播称无需"}]
        f = MODULE.audit(p)["findings"][0]
        self.assertEqual(f["code"], "production_language_in_render_text")
        self.assertEqual(f["scene_ids"], ["s0"])
        self.assertEqual(f["evidence"]["object_id"], "address")

    def test_repeated_placeholder_semantics_and_coverage(self):
        p = plan()
        for i in range(4):
            p["beats"].append(dict(id="s" + str(i), action="依据口播展开",
                                   before="关系尚未展开", after="对象可辨认", acceptance="有主体"))
            for c in range(2):
                p["coverage"].append(dict(caption_id=i * 2 + c, beat_ids=["s" + str(i)], hold_reason="持续承接"))
        result = MODULE.audit(p)
        self.assertTrue({"repeated_beat_action", "repeated_beat_acceptance",
                         "repeated_beat_before", "repeated_beat_after",
                         "repeated_coverage_reason"}.issubset(codes(result)))
        self.assertEqual(result["status"], "review_required")

    def test_one_scene_hold_is_not_treated_as_cross_scene_repetition(self):
        p = plan(1)
        p["beats"] = [{"id": "s0"}]
        p["coverage"] = [dict(caption_id=i, beat_ids=["s0"], hold_reason="观察同一张图") for i in range(10)]
        self.assertNotIn("repeated_coverage_reason", codes(MODULE.audit(p)))

    def test_identical_entrances_ignore_start_and_target_but_keep_duration(self):
        p = plan()
        for i, scene in enumerate(p["render_spec"]["scenes"]):
            for j in range(3):
                scene["actions"].append(dict(target=str(j), op="fromTo", at_ms=i*1000+j*150,
                    duration_ms=450, initial={"opacity": 0, "y": 16},
                    values={"opacity": 1, "y": 0}, ease="power2.out"))
        self.assertIn("dominant_identical_entrance", codes(MODULE.audit(p)))
        for i, scene in enumerate(p["render_spec"]["scenes"]):
            for j, a in enumerate(scene["actions"]):
                a["duration_ms"] += i*100+j
        self.assertNotIn("dominant_identical_entrance", codes(MODULE.audit(p)))

    def test_repeated_note_bars_review_frequency_not_financial_terms(self):
        p = plan()
        for s in p["render_spec"]["scenes"]:
            s["objects"] = [dict(id="note", kind="footnote", w=1560, h=55, text="账户条件")]
        self.assertIn("near_per_scene_note_bar", codes(MODULE.audit(p)))
        self.assertNotIn("production_language_in_render_text", codes(MODULE.audit(p)))
        for s in p["render_spec"]["scenes"]:
            s["objects"][0]["w"] = 300
        self.assertNotIn("near_per_scene_note_bar", codes(MODULE.audit(p)))

    def test_mixed_main_materials_review_but_small_relation_svg_allowed(self):
        p = plan(1)
        objects = p["render_spec"]["scenes"][0]["objects"]
        objects.extend([dict(id="stock", kind="illustration", entity_id="certificate", w=330, h=350),
                        dict(id="fund", kind="paper", svg="<svg/>", w=330, h=350)])
        self.assertIn("mixed_main_asset_and_svg_paper", codes(MODULE.audit(p)))
        objects[1].update(w=60, h=60, role="connector")
        self.assertNotIn("mixed_main_asset_and_svg_paper", codes(MODULE.audit(p)))

    def test_input_not_mutated(self):
        p = plan()
        before = copy.deepcopy(p)
        MODULE.audit(p)
        self.assertEqual(p, before)

    def test_cli_reports_review_with_exit_zero_and_preserves_source(self):
        with tempfile.TemporaryDirectory() as d:
            source, out = Path(d)/"plan.json", Path(d)/"report.json"
            p = plan(1)
            p["render_spec"]["scenes"][0]["objects"] = [{"text": "本次尚未提供来源"}]
            source.write_text(json.dumps(p), encoding="utf-8")
            original = source.read_bytes()
            result = subprocess.run([sys.executable, str(SCRIPT), str(source), "--out", str(out)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(out.read_text())["status"], "review_required")
            self.assertEqual(source.read_bytes(), original)
            blocked = subprocess.run([sys.executable, str(SCRIPT), str(source), "--out", str(source)], capture_output=True, text=True)
            self.assertEqual(blocked.returncode, 2)
            self.assertEqual(source.read_bytes(), original)

    def test_invalid_input_errors_instead_of_claiming_no_findings(self):
        with self.assertRaises(ValueError):
            MODULE.audit({"version": 1})

    def test_legacy_without_states_remains_supported_but_strict_requires_them(self):
        p = plan(1)
        self.assertEqual(MODULE.audit(p)["status"], "no_automatic_findings")
        report = MODULE.audit(p, require_sentence_states=True)
        self.assertIn("sentence_states_missing", codes(report))
        self.assertEqual(report["status"], "review_required")

    def test_old_everything_is_focus_failure_requires_review(self):
        p = state_plan()
        state = p["sentence_states"][0]
        state["focus_object_ids"] = [o["id"] for o in p["render_spec"]["scenes"][0]["objects"]]
        del state["focus_reason"]
        report = MODULE.audit(p)
        self.assertIn("sentence_state_near_all_focus", codes(report))
        self.assertEqual(report["status"], "review_required")

    def test_valid_multi_object_comparison_is_allowed_with_shared_task(self):
        p = state_plan()
        p["render_spec"]["scenes"][0]["objects"] = [
            {"id": "old"}, {"id": "new"}, {"id": "difference"},
            {"id": "globe", "role": "background"}]
        p["sentence_states"][0].update(focus_object_ids=["old", "new", "difference"],
            focus_reason="同一尺度比较旧值、新值及两者差距，三者共同表达变化", retain=[])
        report = MODULE.audit(p, require_sentence_states=True)
        self.assertEqual(report["status"], "no_automatic_findings")
        self.assertFalse(report["aesthetic_approval"])

    def test_bad_references_are_reported_instead_of_silently_accepted(self):
        p = state_plan()
        s = p["sentence_states"][0]
        s["focus_object_ids"] = ["wrong"]
        s["retain"] = [{"object_id": "missing", "reason": "参照"},
                       {"object_id": "missing", "reason": ""}]
        report = MODULE.audit(p)
        f = [f for f in report["findings"] if f["code"] == "sentence_state_object_reference"]
        self.assertEqual(len(f), 2)
        self.assertEqual(f[1]["evidence"]["unknown_ids"], ["missing"])
        self.assertEqual(f[1]["evidence"]["duplicate_ids"], ["missing"])
        self.assertIn("sentence_state_empty_retain_reason", codes(report))

    def test_missing_scene_and_empty_focus_are_review_findings(self):
        p = state_plan()
        p["sentence_states"][0]["focus_object_ids"] = []
        self.assertIn("sentence_state_empty_focus", codes(MODULE.audit(p)))
        p["sentence_states"][0]["scene_id"] = "no-scene"
        self.assertIn("sentence_state_scene_reference", codes(MODULE.audit(p)))

    def test_strict_target_must_be_current_caption_and_frame_time_present(self):
        p = state_plan()
        s = p["sentence_states"][0]
        s.update(context_caption_ids=[86], target_caption_id=86)
        del s["time_ms"]
        report = MODULE.audit(p, require_sentence_states=True)
        self.assertIn("sentence_state_target_caption", codes(report))
        self.assertIn("sentence_state_review_time", codes(report))

    def test_retirement_can_reference_an_object_in_a_previous_scene(self):
        p = state_plan()
        p["render_spec"]["scenes"].insert(0, {"id": "prior", "objects": [{"id": "phone"}]})
        p["sentence_states"][0]["retire_object_ids"] = ["phone"]
        self.assertNotIn("sentence_state_object_reference", codes(MODULE.audit(p)))

    def test_cross_scene_focus_is_not_accepted_as_a_local_object(self):
        p = state_plan()
        p["render_spec"]["scenes"].insert(0, {"id": "prior", "objects": [{"id": "phone"}]})
        p["sentence_states"][0]["focus_object_ids"] = ["phone"]
        self.assertIn("sentence_state_object_reference", codes(MODULE.audit(p)))

    def test_strict_empty_caption_reference_is_not_a_valid_target(self):
        p = state_plan()
        s = p["sentence_states"][0]
        s["caption_ids"] = [None]
        del s["target_caption_id"]
        self.assertIn("sentence_state_target_caption", codes(MODULE.audit(p, require_sentence_states=True)))

    def test_reason_text_is_not_misrepresented_as_semantic_validation(self):
        p = state_plan()
        # Syntactically bound but semantically wrong: the scanner must not claim
        # it has understood this mapping merely because a nonempty reason exists.
        p["sentence_states"][0]["retain"] = [{"object_id": "cash-amount", "reason": "外层总限额框"}]
        report = MODULE.audit(p, require_sentence_states=True)
        self.assertEqual(report["status"], "no_automatic_findings")
        self.assertFalse(report["aesthetic_approval"])
        self.assertEqual(report["sentence_state_scan"]["checked"], 1)

    def test_cli_strict_flag_is_wired_and_preserves_source(self):
        with tempfile.TemporaryDirectory() as d:
            source = Path(d) / "legacy.json"
            source.write_text(json.dumps(plan(1)), encoding="utf-8")
            original = source.read_bytes()
            result = subprocess.run([sys.executable, str(SCRIPT), str(source),
                                     "--require-sentence-states"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("sentence_states_missing", codes(json.loads(result.stdout)))
            self.assertEqual(source.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()

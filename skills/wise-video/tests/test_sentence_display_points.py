#!/usr/bin/env python3
"""Prove sentence-display / outro gates FAIL on full-v1 boxy ending and preview-60s-v1."""
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_sentence_display_points.py"
SPEC = importlib.util.spec_from_file_location("audit_sentence_display_points", SCRIPT)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)

PARITY = Path(os.environ.get("WISE_PARITY_PROJECT", ""))
HTML = PARITY / "composition/full-v1/index.html"
PLAN = PARITY / "plan/semantic_plan.full-v1.json"
INV = PARITY / "planning/concept-inventory.json"

PREVIEW = Path(os.environ.get("WISE_PREVIEW_PROJECT", ""))
V1_HTML = PREVIEW / "composition/preview-60s-v1/index.html"
V1_PLAN = PREVIEW / "plan/semantic_plan.preview-60s-v1.json"
V1_INV = PREVIEW / "planning/concept-inventory.preview-60s-v1.json"


class SentenceDisplayGates(unittest.TestCase):
    @unittest.skipUnless(HTML.exists() and PLAN.exists(), "parity full-v1 missing")
    def test_full_v1_fails_outro_and_box_coverage(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "report.json"
            ns = SimpleNamespace(
                html=str(HTML),
                plan=str(PLAN),
                inventory=str(INV) if INV.exists() else None,
                out=str(out),
                check_outro=True,
                require_tg=False,
                legacy_soft=False,
                expect_fail=False,
                cues=None,
                captions=None,
            )
            report = MOD.audit(ns)
            self.assertEqual(report["status"], "fail")
            codes = {f["code"] for f in report["findings"]}
            self.assertTrue(
                {
                    "outro_template_missing",
                    "outro_box_stack_farewell",
                    "outro_missing_portrait",
                    "outro_missing_red_subscribe",
                }
                & codes,
                codes,
            )

    def test_lone_box_sentence_detection(self):
        html = (
            '<div id="q1" class="claim" style="left:100px">三个问题</div>'
            '<div id="q2" class="claim">01 回应什么</div>'
        )
        plan = {
            "sentence_states": [
                {
                    "scene_id": "three-q",
                    "meaning_delta": "把三个问题放在一起",
                    "focus_object_ids": ["q1", "q2"],
                    "caption_ids": [1],
                }
            ],
            "beats": [],
        }
        findings = MOD.audit_sentence_states(plan, html, None, strict=True)
        codes = {f["code"] for f in findings}
        self.assertIn("sentence_covered_by_lone_box", codes)


class StaleIdentityAndUnlabeledFixtures(unittest.TestCase):
    def test_leftover_nasdaq_badge_fails(self):
        html = (
            '<div id="qNasdaq" class="prop" style="left:430px;top:280px;width:180px">'
            '<img src="nasdaq.png" alt="纳指100"><div class="label">纳指100</div></div>'
        )
        plan = {
            "sentence_states": [{
                "scene_id": "seriesQ",
                "meaning_delta": "买之前纠结进场，买完又纠结另一个问题",
                "focus_object_ids": ["qNasdaq", "qPlus20", "qSellPath"],
                "caption_ids": [11, 12],
            }],
            "beats": [],
        }
        cues = [
            {"target": "qNasdaq", "scene_id": "seriesQ", "op": "fromTo", "at_ms": 14100, "duration_ms": 420,
             "initial": {"opacity": 0}, "values": {"opacity": 1}},
            {"target": "qNasdaq", "scene_id": "seriesQ", "op": "fromTo", "at_ms": 25980, "duration_ms": 350,
             "initial": {"opacity": 1}, "values": {"opacity": 0}},
        ]
        captions = [
            {"caption_id": 11, "start_ms": 16933, "end_ms": 19266, "text": "买之前我们纠结什么时候进场"},
            {"caption_id": 12, "start_ms": 19366, "end_ms": 21933, "text": "买完开始赚钱又会纠结另一个问题"},
        ]
        findings = MOD.audit_stale_identity(plan, html, cues, captions)
        self.assertTrue(any(f["code"] == "sentence_covered_by_stale_identity" for f in findings), findings)
        caps = {f["evidence"]["caption_id"] for f in findings if f["code"] == "sentence_covered_by_stale_identity"}
        self.assertTrue({11, 12} <= caps, caps)

    def test_unlabeled_sell_wait_buyback_paths_fail(self):
        html = (
            '<div id="acc2" class="acct-tile" style="left:880px;top:360px;width:440px;height:300px">账户2赚20%就卖</div>'
            '<path id="accSellPath" class="exit" d="M1100 680 C 1100 730, 1100 760, 1240 790"></path>'
            '<path id="accTrigger" class="trigger" d="M900 820 L 1280 820"></path>'
            '<path id="accBuyPath" d="M1240 820 C 1180 800, 1120 760, 1100 700"></path>'
        )
        plan = {"sentence_states": [], "beats": []}
        cues = [
            {"target": "accSellPath", "scene_id": "accounts", "op": "fromTo", "at_ms": 39466, "duration_ms": 650,
             "initial": {"opacity": 1}, "values": {"opacity": 1}},
            {"target": "accTrigger", "scene_id": "accounts", "op": "fromTo", "at_ms": 43366, "duration_ms": 500,
             "initial": {"opacity": 1}, "values": {"opacity": 1}},
            {"target": "accBuyPath", "scene_id": "accounts", "op": "fromTo", "at_ms": 46300, "duration_ms": 650,
             "initial": {"opacity": 1}, "values": {"opacity": 1}},
        ]
        captions = [
            {"caption_id": 22, "start_ms": 39466, "end_ms": 41533, "text": "赚到20%就全部卖出"},
            {"caption_id": 24, "start_ms": 43366, "end_ms": 46300, "text": "价值比自己实际卖出时低10%"},
            {"caption_id": 25, "start_ms": 46300, "end_ms": 47866, "text": "把钱全部买回来"},
        ]
        findings = MOD.audit_unlabeled_strokes(html, plan, cues, captions)
        paths = {f["evidence"]["path_id"] for f in findings if f["code"] == "unlabeled_stroke"}
        self.assertTrue({"accSellPath", "accTrigger", "accBuyPath"} <= paths, paths)


class Preview60sV1SentenceGates(unittest.TestCase):
    @unittest.skipUnless(V1_HTML.exists() and V1_PLAN.exists(), "preview-60s-v1 missing")
    def test_v1_fails_stale_badge_and_unlabeled_strokes(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "report.json"
            ns = SimpleNamespace(
                html=str(V1_HTML),
                plan=str(V1_PLAN),
                inventory=str(V1_INV) if V1_INV.exists() else None,
                out=str(out),
                check_outro=False,
                require_tg=False,
                legacy_soft=False,
                expect_fail=False,
                cues=None,
                captions=None,
            )
            report = MOD.audit(ns)
            self.assertEqual(report["status"], "fail")
            codes = {f["code"] for f in report["findings"]}
            self.assertIn("sentence_covered_by_stale_identity", codes)
            self.assertIn("unlabeled_stroke", codes)
            stale_caps = {
                f["evidence"]["caption_id"]
                for f in report["findings"]
                if f["code"] == "sentence_covered_by_stale_identity"
            }
            self.assertTrue({11, 12} & stale_caps, stale_caps)
            paths = {
                f["evidence"]["path_id"]
                for f in report["findings"]
                if f["code"] == "unlabeled_stroke"
            }
            self.assertTrue({"accSellPath", "accTrigger", "accBuyPath"} <= paths, paths)


if __name__ == "__main__":
    unittest.main()

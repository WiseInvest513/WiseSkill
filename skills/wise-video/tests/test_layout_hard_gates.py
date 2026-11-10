#!/usr/bin/env python3
"""Prove layout hard gates FAIL on known-bad semantic-v2 HTML and preview-60s-v1."""
import importlib.util
import os
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_layout_hard_gates.py"
SPEC = importlib.util.spec_from_file_location("audit_layout_hard_gates", SCRIPT)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)

PARITY = Path(os.environ.get("WISE_PARITY_PROJECT", ""))
HTML = PARITY / "composition/v2/index.html"
INV = PARITY / "planning/concept-inventory.json"

PREVIEW = Path(os.environ.get("WISE_PREVIEW_PROJECT", ""))
V1_HTML = PREVIEW / "composition/preview-60s-v1/index.html"
V1_CONTRACT = PREVIEW / "layout_contract.preview-60s-v1.json"


class LayoutHardGatesBaseline(unittest.TestCase):
    @unittest.skipUnless(HTML.exists(), "parity project HTML missing")
    def test_static_html_flags_wallet_metaphors(self):
        html = HTML.read_text(encoding="utf-8")
        findings = MOD.scan_html_metaphor(html)
        details = {f.get("detail") for f in findings}
        self.assertIn("sell_as_wallet", details)
        self.assertIn("drawdown_as_wallet", details)

    @unittest.skipUnless(INV.exists(), "inventory missing")
    def test_inventory_flags_wallet_support_for_drawdown(self):
        inv = json.loads(INV.read_text(encoding="utf-8"))
        concepts = inv.get("concepts") or []
        if not any(c.get("id") == "wallet-support" for c in concepts):
            self.skipTest("parity inventory no longer has wallet-support")
        findings = MOD.scan_plan_metaphor(None, inv)
        self.assertTrue(any(f.get("code") == "metaphor_mismatch" for f in findings))

    @unittest.skipUnless(HTML.exists(), "parity project HTML missing")
    def test_require_contract_fails_without_file(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "report.json"
            ns = SimpleNamespace(
                html=str(HTML),
                url=None,
                times="4.8",
                contract=None,
                plan=None,
                inventory=str(INV) if INV.exists() else None,
                dom_json=None,
                measure_js=str(SCRIPT.parent / "measure_layout_dom.cjs"),
                measure_out=None,
                chrome="",
                puppeteer="",
                cues=None,
                require_contract=True,
                out=str(out),
                expect_fail=False,
            )
            report = MOD.audit(ns)
            self.assertEqual(report["status"], "fail")
            codes = {f["code"] for f in report["findings"]}
            self.assertIn("missing_layout_contract", codes)
            self.assertIn("metaphor_mismatch", codes)


class CanvasGateFixtures(unittest.TestCase):
    def test_earth_reserved_column_and_loose_contract_fail(self):
        html = (
            '<div id="earth"></div>'
            '<div id="acc1" class="acct-tile" style="left:400px;top:360px;width:440px;height:300px">账户1</div>'
            '<div id="acc2" class="acct-tile" style="left:880px;top:360px;width:440px;height:300px">账户2</div>'
        )
        contract = {
            "layout_mode": "center",
            "earth_is_background": True,
            "center_x_min": 0.40,
            "center_x_max": 0.58,
            "safe_frame_x_ratio": [0.12, 0.70],
            "sibling_sets": [{"id": "two-accounts", "ids": ["acc1", "acc2"]}],
        }
        findings = MOD.scan_contract_layout_floors(contract) + MOD.scan_html_scene_centers(html, contract)
        codes = {f["code"] for f in findings}
        self.assertIn("contract_reserves_earth_column", codes)
        self.assertIn("contract_loosens_center_band", codes)
        self.assertIn("earth_reserved_column", codes)

    def test_hook_path_over_label_fails(self):
        html = (
            '<div id="hookNasdaq" class="prop" style="left:760px;top:220px;width:200px">'
            '<img src="nasdaq.png" alt="纳指100"><div class="label">纳指100</div></div>'
            '<svg class="rel"><path id="hookSellPath" class="exit" d="M850 430 C 780 520, 680 590, 560 650"></path>'
            '<path id="hookHoldPath" d="M860 430 C 940 500, 1040 560, 1160 620"></path></svg>'
        )
        findings = MOD.scan_path_text_collisions(html)
        paths = {f["evidence"]["path_id"] for f in findings if f["code"] == "path_covers_text"}
        self.assertTrue({"hookSellPath", "hookHoldPath"} <= paths, paths)


class Preview60sV1LayoutGates(unittest.TestCase):
    @unittest.skipUnless(V1_HTML.exists(), "preview-60s-v1 missing")
    def test_v1_fails_centering_and_hook_paths(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "report.json"
            ns = SimpleNamespace(
                html=str(V1_HTML),
                url=None,
                times="4.2,42,64",
                contract=str(V1_CONTRACT) if V1_CONTRACT.exists() else None,
                plan=None,
                inventory=None,
                dom_json=None,
                measure_js=str(SCRIPT.parent / "measure_layout_dom.cjs"),
                measure_out=None,
                chrome="",
                puppeteer="",
                cues=None,
                require_contract=False,
                out=str(out),
                expect_fail=False,
            )
            report = MOD.audit(ns)
            self.assertEqual(report["status"], "fail")
            codes = {f["code"] for f in report["findings"]}
            self.assertIn("path_covers_text", codes)
            self.assertTrue(
                {"earth_reserved_column", "content_center_outside_band", "left_bias_against_earth_bg"} & codes,
                codes,
            )
            self.assertTrue(
                {"contract_reserves_earth_column", "contract_loosens_center_band"} <= codes,
                codes,
            )
            group_names = {
                (f.get("evidence") or {}).get("group")
                for f in report["findings"]
                if f["code"] in {"earth_reserved_column", "content_center_outside_band", "left_bias_against_earth_bg"}
            }
            self.assertTrue(
                any("account" in str(g) or g == "two-accounts" or str(g).endswith("accounts") for g in group_names),
                group_names,
            )
            self.assertTrue(
                any("chart" in str(g) or "result" in str(g) for g in group_names),
                group_names,
            )
            path_ids = {
                (f.get("evidence") or {}).get("path_id")
                for f in report["findings"]
                if f["code"] == "path_covers_text"
            }
            self.assertTrue({"hookSellPath", "hookHoldPath"} & path_ids, path_ids)


if __name__ == "__main__":
    unittest.main()

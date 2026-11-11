"""Portable positive and mutation regressions for observed DOM chrome/outro gates."""
import copy
import contextlib
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("audit_chrome_outro", ROOT / "scripts/audit_chrome_outro.py")
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)
TOPIC = "加息买入，降息卖出？"


def node(role, text="", x=100, y=200, width=200, height=60, **kwargs):
    return {"role": role, "id": role, "text": text, "visible": True, "opacity": 1,
            "visible_area_ratio": 1, "background_color": "rgba(0, 0, 0, 0)", "color": "rgb(23, 39, 53)",
            "rect": {"x": x, "y": y, "width": width, "height": height, "right": x+width, "bottom": y+height}, **kwargs}


def evidence():
    nodes = [node("series-card"), node("signature", x=1634, y=32, image_loaded=True),
             node("episode-number", "10", background_color="rgb(235, 113, 105)"),
             node("series-name", "纳斯达克投资 · 第10期"), node("episode-topic", TOPIC),
             node("outro-root"), node("portrait", image_loaded=True), node("brand", "WiseInvest"),
             node("topics", "美股 · 宏观 · 科技 · AI"), node("slogan", "用大白话，讲清楚市场"),
             node("subscribe", "关注 · 订阅", background_color="rgb(227, 49, 45)"),
             node("bookmark", "收藏", svg_shapes=[{"tag": "path", "d": "M2 2H38V52L20 40L2 52Z", "fill": "rgb(183, 154, 96)"}]),
             node("support", "你的支持，是持续更新的动力"), node("bye", "我们下期再见")]
    return {"frames": [{"t": t, "canvas": {"width": 1920, "height": 1080},
                        "chrome_outro": {"capture_version": 1, "source": "browser_computed_dom", "nodes": copy.deepcopy(nodes)}}
                       for t in (0, 4, 12)]}


def audit(data, **kwargs):
    return MOD.audit_evidence(data, check_series=True, check_outro=True, episode=10, topic=TOPIC,
                              outro_times=[12], **kwargs)


def omit_policy(*roles):
    return {"schema_version": 1, "optional_objects": {
        role: {"expected": False, "reason": f"本期原声未包含 {role} 对应句，按录音省略"} for role in roles}}


def remove_roles(data, *roles):
    for frame in data["frames"]:
        frame["chrome_outro"]["nodes"] = [n for n in frame["chrome_outro"]["nodes"] if n["role"] not in roles]
    return data


class ChromeOutroEvidenceTests(unittest.TestCase):
    def test_positive_is_only_sampled_dom_not_visual_certification(self):
        report = audit(evidence())
        self.assertEqual(report["status"], "pass", report)
        self.assertEqual(report["visual_review"], "not_checked")

    def test_no_browser_evidence_or_marker_only_is_not_checked(self):
        for source in (None, {"frames": [{"t": 0, "nodes": [{"id": "seriesCard"}]}]}):
            report = audit(source)
            self.assertEqual(report["status"], "not_checked")
            self.assertFalse(report["encode_allowed"])

    def test_no_outro_sample_is_not_checked_even_if_intro_objects_exist(self):
        data = evidence()
        data["frames"].pop()
        self.assertEqual(audit(data)["status"], "not_checked")

    def test_series_only_preview_does_not_require_an_ending(self):
        data = evidence()
        data["frames"][-1]["t"] = 44.5
        for frame in data["frames"]:
            frame["chrome_outro"]["nodes"] = [n for n in frame["chrome_outro"]["nodes"]
                                                 if n["role"] in {"series-card", "signature", "episode-number", "series-name", "episode-topic"}]
        report = MOD.audit_evidence(data, check_series=True, episode=10, topic=TOPIC)
        self.assertEqual(report["status"], "pass", report)
        self.assertEqual(report["requested_checks"], {"series": True, "outro": False})
        self.assertIsNone(report["outro_object_policy"])
        self.assertIsNone(report["outro_variant"])
        data["frames"][-1]["chrome_outro"]["nodes"][0].update(visible=False, opacity=0)
        negative = MOD.audit_evidence(data, check_series=True, episode=10, topic=TOPIC)
        self.assertIn("series_chrome_missing_during_sample", {f["code"] for f in negative["findings"]})

    def test_full_film_checks_still_require_ending_times(self):
        report = MOD.audit_evidence(evidence(), check_series=True, check_outro=True, episode=10, topic=TOPIC)
        self.assertEqual(report["status"], "not_checked", report)
        self.assertIn("outro_times_missing", {n["code"] for n in report["not_checked"]})
        self.assertFalse(report["encode_allowed"])

    def test_optional_copy_defaults_to_required_and_each_exception_is_explicit(self):
        data = remove_roles(evidence(), "slogan", "support")
        negative = audit(data)
        self.assertTrue({"outro_missing_slogan", "outro_missing_support"} <= {f["code"] for f in negative["findings"]})
        slogan_only = audit(data, outro_policy=omit_policy("slogan"))
        self.assertEqual({f["code"] for f in slogan_only["findings"]}, {"outro_missing_support"})
        positive = audit(data, outro_policy=omit_policy("slogan", "support"))
        self.assertEqual(positive["status"], "pass", positive)
        self.assertEqual(positive["outro_object_policy"]["expected_objects"], ["portrait", "brand", "topics", "subscribe", "bookmark", "bye"])
        self.assertEqual(set(positive["outro_object_policy"]["not_required"]), {"slogan", "support"})
        # "expected:false" is an exemption, not a new prohibition on brand copy.
        self.assertEqual(audit(evidence(), outro_policy=omit_policy("slogan"))["status"], "pass")

    def test_optional_policy_cannot_waive_core_objects_or_dom_evidence(self):
        for role, code in {"portrait": "outro_missing_portrait", "brand": "outro_missing_brand",
                           "topics": "outro_missing_topics_line", "subscribe": "outro_missing_red_subscribe",
                           "bookmark": "outro_bell_instead_of_bookmark", "bye": "outro_missing_bye"}.items():
            with self.subTest(role=role):
                report = audit(remove_roles(evidence(), role), outro_policy=omit_policy("slogan", "support"))
                self.assertEqual(report["status"], "fail", report)
                self.assertIn(code, {f["code"] for f in report["findings"]})
        self.assertEqual(audit(None, outro_policy=omit_policy("slogan", "support"))["status"], "not_checked")

    def test_invalid_or_mis_scoped_optional_policies_are_input_errors(self):
        bad = [omit_policy("portrait"), {"schema_version": 2, "optional_objects": {}},
               {"schema_version": 1, "optional_objects": {"slogan": {"expected": "false", "reason": "VO"}}},
               {"schema_version": 1, "optional_objects": {"support": {"expected": False, "reason": " "}}},
               {"schema_version": 1, "optional_objects": {}, "bypass": True}]
        for policy in bad:
            with self.subTest(policy=policy), self.assertRaises(ValueError):
                audit(evidence(), outro_policy=policy)
        for options in ({"check_series": True}, {"check_outro": True, "require_tg": True}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                MOD.audit_evidence(evidence(), outro_policy=omit_policy("slogan"), **options)

    def test_missing_zero_cannot_be_bypassed_with_custom_intro_times(self):
        data = evidence()
        data["frames"].pop(0)
        self.assertEqual(audit(data, intro_times=[4])["status"], "not_checked")

    def test_promised_mutations_fail(self):
        mutations = [
            ("signature", {"rect": node("x", x=76, y=32)["rect"]}, "series_chrome_logo_left", 0),
            ("episode-number", {"background_color": "rgb(31, 59, 87)"}, "series_chrome_num_navy", 0),
            ("episode-number", {"color": "rgb(255, 255, 255)"}, "series_chrome_num_text_wrong", 0),
            ("series-name", {"text": "纳指 · 标普投资系列"}, "series_chrome_copy_wrong", 0),
            ("series-card", {"visible": False, "opacity": 0}, "series_chrome_missing_t0", 0),
            ("series-card", {"visible": False, "opacity": 0}, "series_chrome_missing_in_outro", 2),
            ("topics", {"visible": False, "opacity": 0}, "outro_missing_topics_line", 2),
            ("bookmark", {"role": "bell", "text": "提醒"}, "outro_bell_instead_of_bookmark", 2),
            ("subscribe", {"background_color": "rgb(31, 59, 87)"}, "outro_missing_red_subscribe", 2),
            ("portrait", {"image_loaded": False}, "outro_missing_portrait", 2),
        ]
        for role, changes, code, frame in mutations:
            with self.subTest(code=code):
                data = evidence()
                next(n for n in data["frames"][frame]["chrome_outro"]["nodes"] if n["role"] == role).update(changes)
                report = audit(data)
                self.assertEqual(report["status"], "fail", report)
                self.assertIn(code, {f["code"] for f in report["findings"]})

    def test_portrait_overlap_fails_only_when_chip_is_visible(self):
        data = evidence()
        chip = node("interest-chip")
        data["frames"][2]["chrome_outro"]["nodes"].append(chip)
        self.assertIn("outro_interest_chips_on_portrait", {f["code"] for f in audit(data)["findings"]})
        chip.update(visible=False, opacity=0)
        self.assertEqual(audit(data)["status"], "pass")

    def test_icon_label_cannot_prove_bookmark_geometry(self):
        data = evidence()
        next(n for n in data["frames"][2]["chrome_outro"]["nodes"] if n["role"] == "bookmark")["svg_shapes"][0]["d"] = "M1 1L8 8"
        report = audit(data)
        self.assertEqual(report["status"], "not_checked")
        self.assertIn("bookmark_geometry_unverified", {n["code"] for n in report["not_checked"]})

    def test_malformed_node_is_input_error(self):
        data = evidence()
        del data["frames"][0]["chrome_outro"]["nodes"][0]["rect"]
        with self.assertRaises(ValueError):
            audit(data)

    def test_community_signature_has_distinct_requirements_and_missing_image_fails(self):
        data = evidence()
        for f in data["frames"]:
            f["chrome_outro"]["nodes"] = [n for n in f["chrome_outro"]["nodes"] if n["role"] not in {"topics", "slogan", "support", "bookmark"}]
        community_nodes = data["frames"][1]["chrome_outro"]["nodes"]
        community_nodes += [node("community-label", "电报群组 · 重新开启"), node("community-image", image_loaded=True)]
        options = {"check_outro": True, "require_tg": True, "community_times": [4], "outro_times": [12]}
        self.assertEqual(MOD.audit_evidence(data, **options)["status"], "pass")
        community_nodes[-1]["image_loaded"] = False
        self.assertIn("outro_missing_tg_community", {f["code"] for f in MOD.audit_evidence(data, **options)["findings"]})

    def test_cli_missing_evidence_does_not_exit_successfully(self):
        result = subprocess.run([sys.executable, str(ROOT / "scripts/audit_chrome_outro.py"), "--check-outro"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["status"], "not_checked")

    def test_combined_cli_requires_matching_html_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            html, measured = Path(tmp) / "index.html", Path(tmp) / "dom.json"
            html.write_text('<html><body></body></html>', encoding='utf-8')
            data = evidence()
            data['document_sha256'] = hashlib.sha256(html.read_bytes()).hexdigest()
            measured.write_text(json.dumps(data), encoding='utf-8')
            command = [sys.executable, str(ROOT / 'scripts/audit_sentence_display_points.py'), '--html', str(html),
                       '--check-outro', '--dom-evidence', str(measured), '--outro-times', '12']
            positive = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(positive.returncode, 0, positive.stderr + positive.stdout)
            html.write_text('<html><body>changed</body></html>', encoding='utf-8')
            negative = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(negative.returncode, 1)
            self.assertIn('dom_source_hash_mismatch', {f['code'] for f in json.loads(negative.stdout)['findings']})

    def test_policy_cli_and_combined_cli_preserve_effective_objects_and_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            html, measured, policy = (Path(tmp) / name for name in ("index.html", "dom.json", "outro-policy.json"))
            html.write_text('<html><body></body></html>', encoding='utf-8')
            data = remove_roles(evidence(), "slogan", "support")
            data['document_sha256'] = hashlib.sha256(html.read_bytes()).hexdigest()
            measured.write_text(json.dumps(data), encoding='utf-8')
            policy.write_text(json.dumps(omit_policy("slogan", "support"), ensure_ascii=False), encoding='utf-8')
            for script in ('audit_chrome_outro.py', 'audit_sentence_display_points.py'):
                with self.subTest(script=script):
                    command = [sys.executable, str(ROOT / 'scripts' / script), '--check-outro', '--dom-evidence', str(measured), '--outro-times', '12']
                    if script == 'audit_sentence_display_points.py':
                        command += ['--html', str(html)]
                    missing_policy = subprocess.run(command, capture_output=True, text=True)
                    self.assertEqual(missing_policy.returncode, 1, missing_policy.stderr)
                    explicit = subprocess.run(command + ['--outro-policy', str(policy)], capture_output=True, text=True)
                    self.assertEqual(explicit.returncode, 0, explicit.stderr + explicit.stdout)
                    result = json.loads(explicit.stdout)
                    report = result['chrome_outro'] if script == 'audit_sentence_display_points.py' else result
                    resolved = report['outro_object_policy']
                    self.assertEqual(resolved['source'], {'path': str(policy), 'sha256': hashlib.sha256(policy.read_bytes()).hexdigest()})
                    self.assertEqual(resolved['expected_objects'], ['portrait', 'brand', 'topics', 'subscribe', 'bookmark', 'bye'])


@unittest.skipUnless(os.environ.get("WISE_CHROME") and os.environ.get("WISE_PUPPETEER"), "set WISE_CHROME + WISE_PUPPETEER for real browser regression")
class BrowserChromeOutroTests(unittest.TestCase):
    @contextlib.contextmanager
    def serve(self, source=None, gsap=None):
        class Handler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(ROOT / "assets"), **kwargs)

            def log_message(self, *args):
                pass

            def do_GET(self):
                if self.path == '/__test.html' and source is not None:
                    body, content_type = source.encode('utf-8'), 'text/html; charset=utf-8'
                elif self.path == '/__gsap.js' and gsap:
                    body, content_type = Path(gsap).read_bytes(), 'text/javascript'
                else:
                    return super().do_GET()
                self.send_response(200)
                self.send_header('Content-Type', content_type)
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield f'http://127.0.0.1:{server.server_port}'
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def measure(self, url, times="0,4,6,10,13.8"):
        result = subprocess.run(["node", str(ROOT / "scripts/measure_layout_dom.cjs"), "--url", url,
                                 "--times", times], capture_output=True, text=True, timeout=100)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_series_preview_and_configured_slogan_have_explicit_scopes(self):
        with self.serve() as url:
            sample = self.measure(url + '/series-chrome/index.html', '0,4,44.5')
        preview = MOD.audit_evidence(sample, check_series=True, episode=10, topic=TOPIC)
        self.assertEqual(preview['status'], 'pass', preview)
        self.assertEqual(preview['requested_checks'], {'series': True, 'outro': False})
        template = ROOT / 'assets/signature-outro/index.html'
        source = template.read_text(encoding='utf-8').replace('<head>', '<head><base href="/signature-outro/">')
        source += '<script>configureSignature({sloganEnabled:false});</script>'
        with self.serve(source) as url:
            data = self.measure(url + '/__test.html')
        options = {'check_outro': True, 'outro_times': [6, 10, 13.8]}
        default = MOD.audit_evidence(data, **options)
        self.assertEqual({f['code'] for f in default['findings']}, {'outro_missing_slogan'})
        adapted = MOD.audit_evidence(data, outro_policy=omit_policy('slogan'), **options)
        self.assertEqual(adapted['status'], 'pass', adapted)
        self.assertIn('support', adapted['outro_object_policy']['expected_objects'])

    def test_approved_community_template_can_pass_with_separate_phase_samples(self):
        gsap = os.environ.get("WISE_GSAP")
        if not gsap:
            self.skipTest("legacy host template needs WISE_GSAP for the explicit test runtime adapter")
        template = ROOT / "assets/outro/index.html"
        source = template.read_text(encoding="utf-8").replace("<head>", '<head><base href="/outro/">')
        source = source.replace('src="../background/assets/gsap.min.js"', 'src="/__gsap.js"')
        # Original fragment is hosted by HyperFrames; this explicit adapter
        # supplies its deterministic timeline seeking and clip visibility.
        source += '''<script>window.renderAt=t=>{
          window.__timelines['srt-video'].time(t,false);
          for(const el of document.querySelectorAll('.clip[data-start][data-duration]')){
            const start=Number(el.dataset.start),end=start+Number(el.dataset.duration);
            el.style.visibility=t>=start&&t<end?'visible':'hidden';
          }
        };</script>'''
        with self.serve(source, gsap) as url:
            data = self.measure(url + '/__test.html', "4,10,17,25.7,34.5")
        report = MOD.audit_evidence(data, check_outro=True, require_tg=True,
                                    community_times=[4, 10], outro_times=[17, 25.7, 34.5])
        self.assertEqual(report["status"], "pass", report)

    def test_portable_template_computed_styles_and_parent_visibility(self):
        template = ROOT / "assets/signature-outro/index.html"
        if not template.exists():
            self.skipTest("signature template not installed")
        with self.serve() as url:
            data = self.measure(url + '/signature-outro/index.html')
        report = MOD.audit_evidence(data, check_series=True, check_outro=True, episode=10,
                                    topic=TOPIC, outro_times=[6, 10, 13.8])
        self.assertEqual(report["status"], "pass", report)
        with contextlib.nullcontext():
            # Absolute base preserves the packaged assets, but CSS and actual
            # runtime mutations defeat otherwise-correct IDs/data roles.
            source = template.read_text(encoding="utf-8").replace("<head>", '<head><base href="/signature-outro/">')
            source += '''<style>#wise-brand-logo{left:76px!important}.num{background:#1f3b57!important}
                #topics{display:none!important}</style><script>
                const originalRender=window.renderAt;window.renderAt=(t)=>{originalRender(t);
                document.querySelector('#seriesCard').style.opacity=(t===0||t>12)?0:1;};
                document.querySelector('[data-outro-object="bookmark"]').setAttribute('data-outro-object','bell');
                document.querySelector('[data-series-name]').textContent='纳指 · 标普投资系列';
                const chip=document.createElement('div');chip.className='chip';chip.textContent='科技';
                chip.style.cssText='position:absolute;left:600px;top:350px;width:180px;height:70px;background:gold;border-radius:20px';
                document.querySelector('[data-outro-variant]').append(chip);
                </script>'''
            with self.serve(source) as url:
                data = self.measure(url + '/__test.html')
            report = MOD.audit_evidence(data, check_series=True, check_outro=True,
                                        episode=10, topic=TOPIC, outro_times=[6, 10, 13.8])
            self.assertTrue({"series_chrome_logo_left", "series_chrome_num_navy", "series_chrome_missing_t0",
                             "series_chrome_missing_in_outro", "series_chrome_copy_wrong", "outro_missing_topics_line",
                             "outro_bell_instead_of_bookmark", "outro_interest_chips_on_portrait"}
                            <= {f["code"] for f in report["findings"]}, report)


if __name__ == "__main__":
    unittest.main()

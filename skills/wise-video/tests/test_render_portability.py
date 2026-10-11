"""Portable packaging checks; these compile HTML and do not render video."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

TOOLING = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(TOOLING))
import render_plan as renderer
import srt_intake


class PortableCompilerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "工作区 with spaces"
        self.root.mkdir()
        self.plan = self.root / "plan.json"
        self.captions = self.root / "captions.json"
        self.index = self.root / "asset-index.json"
        self.gsap = self.root / "gsap.min.js"
        self.gsap.write_text("/* packaging fixture, not a JavaScript runtime */", encoding="utf-8")
        self.write_json(self.captions, [{"caption_id": 1, "start_ms": 1000, "end_ms": 3000, "text": "原字幕完整保留"}])
        self.write_json(self.index, [])
        self.write_json(self.plan, {"scope_caption_ids": [1], "entities": [], "render_spec": {"scenes": [{
            "id": "scene", "start_ms": 1000, "end_ms": 3000,
            "objects": [{"id": "subject", "kind": "text", "text": "主体", "x": 200, "y": 200, "w": 400, "h": 200}],
            "actions": [{"target": "subject", "op": "fromTo", "at_ms": 1000, "duration_ms": 200, "initial": {"opacity": 0}, "values": {"opacity": 1}}]
        }]}})

    def write_json(self, path, value):
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")

    def args(self, *extra, gsap=True):
        argv = ["--plan", str(self.plan), "--captions", str(self.captions), "--asset-index", str(self.index),
                "--asset-root", str(self.root), "--source-start-ms", "1000", "--duration-ms", "2000",
                "--out", str(self.root / "output")]
        if gsap:
            argv += ["--gsap", str(self.gsap)]
        return renderer.parser().parse_args(argv + list(extra))

    def compile(self, *extra, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            renderer.compile_plan(self.args(*extra, **kwargs))

    def test_standalone_unicode_workspace_compiles_without_historical_project(self):
        self.compile()
        out = self.root / "output"
        html = (out / "index.html").read_text(encoding="utf-8")
        self.assertIn("原字幕完整保留", html)
        self.assertIn('id="scene-subject"', html)
        provenance = json.loads((out / "provenance.json").read_text(encoding="utf-8"))
        self.assertEqual(provenance["html_sha256"], renderer.sha(out / "index.html"))
        self.assertEqual((out / "assets/gsap.min.js").read_bytes(), self.gsap.read_bytes())
        self.assertEqual(provenance["audio"]["status"], "silent_srt_only")

    def test_missing_explicit_gsap_does_not_search_ancestor_samples(self):
        old = self.root / "sample-old/assets/gsap.min.js"
        old.parent.mkdir(parents=True)
        old.write_bytes(self.gsap.read_bytes())
        with self.assertRaisesRegex(ValueError, "pass --gsap"):
            self.compile(gsap=False)

    def test_explicit_ffprobe_is_used_with_confirmed_audio_offset(self):
        voice = self.root / "voice.wav"
        voice.write_bytes(b"audio packaging fixture")
        executable = str(self.root / "tools/ffprobe")
        with mock.patch.object(renderer, "probe_audio", return_value={"duration_ms": 4000}) as probe:
            self.compile("--audio", str(voice), "--audio-offset-ms", "0", "--ffprobe", executable)
        probe.assert_called_once_with(voice, executable)
        html = (self.root / "output/index.html").read_text(encoding="utf-8")
        self.assertIn('data-media-start="1.0"', html)

    def test_missing_ffprobe_reports_dependency_without_machine_specific_fallback(self):
        voice = self.root / "voice.wav"
        voice.write_bytes(b"audio packaging fixture")
        with mock.patch.object(srt_intake.shutil, "which", return_value=None):
            with self.assertRaisesRegex(ValueError, "ffprobe is unavailable"):
                self.compile("--audio", str(voice), "--audio-offset-ms", "0")

    def test_unknown_primary_audio_duration_cannot_pass_range_check(self):
        voice = self.root / "voice.wav"
        voice.write_bytes(b"audio packaging fixture")
        with mock.patch.object(renderer, "probe_audio", return_value={"duration_ms": None}):
            with self.assertRaisesRegex(ValueError, "duration unavailable"):
                self.compile("--audio", str(voice), "--audio-offset-ms", "0")

    def test_css_font_and_image_are_frozen_as_local_output_assets(self):
        out = self.root / "css-output"
        (out / "assets").mkdir(parents=True)
        font = self.root / "font.woff2"
        icon = self.root / "icon.png"
        font.write_bytes(b"font packaging fixture")
        icon.write_bytes(b"image packaging fixture")
        ledger = []
        css = renderer.rewrite_css("@font-face{src:url('font.woff2')} .x{background:url(icon.png);filter:url(#mask)}", self.root, out, "style", ledger)
        self.assertEqual(len(ledger), 2)
        for item in ledger:
            self.assertIn(item["path"], css)
            self.assertEqual(renderer.sha(out / item["path"]), item["sha256"])
        self.assertIn("url(#mask)", css)

    def test_remote_css_resource_requires_local_resolution(self):
        with self.assertRaises(renderer.Unsupported):
            renderer.rewrite_css('.x{background:url("https://example.invalid/image.png")}', self.root, self.root, "style", [])

    def test_intro_without_font_face_has_balanced_extracted_container(self):
        template = self.root / "intro.html"
        template.write_text('<html><style>.intro-copy{color:navy}</style><body><div data-duration="2"><div class="intro-copy"><div id="hello">你好</div><div class="clip caption">source caption</div></div></div><script>const introCues=[];for(const c of introCues){}</script></body></html>', encoding="utf-8")
        markup, css, actions, duration = renderer.intro(template, 1000, self.root, [])
        self.assertEqual(markup.count("<div"), markup.count("</div>"))
        self.assertNotIn("source caption", markup)
        self.assertIn(".intro-copy", css)
        self.assertEqual((actions, duration), ([], 2000))


if __name__ == "__main__":
    unittest.main()

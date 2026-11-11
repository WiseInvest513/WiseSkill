import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('package_check',ROOT/'scripts/check-package.py')
checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)
doctor_spec=importlib.util.spec_from_file_location('doctor',ROOT/'scripts/doctor.py')
doctor=importlib.util.module_from_spec(doctor_spec);doctor_spec.loader.exec_module(doctor)

class PackageRegression(unittest.TestCase):
    def test_node_minimum_matches_locked_browser_dependencies(self):
        for version in ('v20.19.0','v22.0.0','v22.11.9','unknown'):
            self.assertFalse(doctor.supported_node(version),version)
        for version in ('v22.12.0','v22.19.0','v24.0.0'):
            self.assertTrue(doctor.supported_node(version),version)
    def fixture(self,tmp):
        root=Path(tmp)
        for name in checker.SKILLS:
            p=root/'skills'/name;p.mkdir(parents=True)
            (p/'SKILL.md').write_text('---\nname: '+name+'\n---\n',encoding='utf-8')
        (root/'video-package.json').write_text(json.dumps({'required_files':['skills/wise-video/SKILL.md']}))
        return root
    def test_missing_declared_reference_is_detected_without_markdown_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=self.fixture(tmp)
            (root/'video-package.json').write_text(json.dumps({'required_files':['skills/wise-video/references/needed.md']}))
            self.assertTrue(any('Missing required' in x for x in checker.check(root)[1]))
    def test_unshipped_backtick_method_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=self.fixture(tmp);(root/'rules.md').write_text('Read `.agents/skills/_external/missing.md` before production.')
            self.assertTrue(any('Unshipped external' in x for x in checker.check(root)[1]))
    def test_changed_asset_cannot_pass_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=self.fixture(tmp);p=root/'skills/wise-video/assets/test';p.mkdir(parents=True)
            (p/'a.png').write_bytes(b'changed');(p/'manifest.json').write_text(json.dumps({'files':{'a.png':'0'*64}}))
            self.assertTrue(any('modified template' in x for x in checker.check(root)[1]))
    def test_installer_pairs_video_skills_and_preserves_existing_work(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest=Path(tmp)/'安装 skills'
            result=subprocess.run([sys.executable,str(ROOT/'scripts/install.py'),'--skill','wise-thumbnail','--dest',str(dest)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertTrue((dest/'wise-video/SKILL.md').is_file())
            self.assertTrue((dest/'wise-thumbnail/SKILL.md').is_file())
            marker=dest/'wise-video/user-work.txt';marker.write_text('keep')
            result=subprocess.run([sys.executable,str(ROOT/'scripts/install.py'),'--video','--dest',str(dest)],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertEqual(marker.read_text(),'keep')
    def test_doctor_reports_missing_runtime_without_installing(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'missing'
            result=subprocess.run([sys.executable,str(ROOT/'scripts/doctor.py'),'--skill-root',str(p)],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            report=json.loads(result.stdout)
            self.assertIn('skill',report['missing']);self.assertFalse(report['visual_approval']);self.assertFalse(p.exists())

if __name__=='__main__':unittest.main()

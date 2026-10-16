import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'validate_concepts.py'
if not SCRIPT.exists():
    SCRIPT = Path(__file__).with_name('validate_concepts.py')
spec = importlib.util.spec_from_file_location('validate_concepts', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ConceptInventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'logo.png').write_bytes(b'file-existence-only')
        self.captions = [{'caption_id': 1, 'text': '品牌'}, {'caption_id': 2, 'text': '这就是接下来的章节'}]
        self.inventory = {'schema_version': 1, 'scope_caption_ids': [1, 2], 'concepts': [{
            'id': 'brand', 'name': '品牌', 'aliases': [], 'category': '身份', 'caption_ids': [1],
            'decision': 'exact_identity', 'reason': '准确辨认主体', 'visual_role': '主体',
            'representation_hint': '使用提供的原图', 'available_asset': ['logo.png'], 'missing': False}],
            'source_coverage': [{'caption_id': 1, 'concept_ids': ['brand']},
                                {'caption_id': 2, 'concept_ids': [], 'context_concept_ids': ['brand']}]}

    def check(self, stage='planning'):
        return module.validate(self.inventory, self.captions, self.root, stage)

    def test_valid_identity_and_context(self):
        self.assertTrue(self.check('assets')['ok'])

    def test_missing_source_sentence_fails(self):
        self.inventory['source_coverage'].pop()
        self.assertFalse(self.check()['ok'])

    def test_out_of_scope_occurrence_fails(self):
        self.inventory['concepts'][0]['caption_ids'].append(99)
        self.assertFalse(self.check()['ok'])

    def test_trimming_scope_cannot_hide_unplanned_source(self):
        self.inventory['scope_caption_ids'] = [1]
        self.inventory['source_coverage'].pop()
        self.assertFalse(self.check()['ok'])

    def test_claimed_occurrence_must_wire_back(self):
        self.inventory['concepts'][0]['caption_ids'].append(2)
        self.assertFalse(self.check()['ok'])

    def test_gap_allows_planning_but_blocks_asset_gate(self):
        concept = self.inventory['concepts'][0]
        concept.update(available_asset=[], missing=True, missing_detail='等待原图')
        self.assertTrue(self.check()['ok'])
        self.assertFalse(self.check('assets')['ok'])

    def test_setting_ready_does_not_hide_missing_identity(self):
        self.inventory['concepts'][0].update(available_asset=[], missing=False)
        self.assertFalse(self.check('assets')['ok'])

    def test_existing_but_wrong_path_fails(self):
        self.inventory['concepts'][0]['available_asset'] = ['not-there.png']
        self.assertFalse(self.check()['ok'])

    def test_text_and_code_relationship_need_no_image(self):
        concept = self.inventory['concepts'][0]
        for decision in ('text', 'data_chart', 'relationship'):
            concept.update(decision=decision, available_asset=[])
            self.assertTrue(self.check('assets')['ok'], decision)

    def test_code_concept_has_explicit_basis(self):
        concept = self.inventory['concepts'][0]
        concept.update(decision='concept_asset', available_asset=[], implementation_basis='SVG可编辑日历组件')
        self.assertTrue(self.check('assets')['ok'])
        concept.pop('implementation_basis')
        self.assertFalse(self.check('assets')['ok'])

    def test_unknown_reference_and_duplicate_id_fail(self):
        self.inventory['source_coverage'][1]['context_concept_ids'] = ['nonexistent']
        self.assertFalse(self.check()['ok'])
        self.inventory['source_coverage'][1]['context_concept_ids'] = ['brand']
        self.inventory['concepts'].append(copy.deepcopy(self.inventory['concepts'][0]))
        self.assertFalse(self.check()['ok'])


if __name__ == '__main__':
    unittest.main()

import unittest,sys,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from validate_plan import validate
class Preflight(unittest.TestCase):
 def setUp(self):
  self.c=[{'caption_id':1,'text':'可供选择的产品逐渐增多'},{'caption_id':2,'text':'另一家公司加入'}]
  self.p={'version':1,'scope_caption_ids':[1],'entities':[{'id':'products','name':'产品','identity_required':False,'representation':'icon','asset_status':'ready','asset_id':'generic-product'}],'beats':[{'id':'b1','source_caption_ids':[1],'text':self.c[0]['text'],'entity_ids':['products'],'meaning':'选择增多','kind':'quantity_change','before':'少量成员','after':'新增成员','action':'分批加入','changes':['membership'],'acceptance':'比较前后可见成员数'}],'coverage':[{'caption_id':1,'beat_ids':['b1']}]}
 def test_complete_plan(self):self.assertEqual(validate(self.p,self.c),[])
 def test_new_scope_must_be_covered(self):
  self.p['scope_caption_ids'].append(2);self.assertIn('coverage does not match full scope',validate(self.p,self.c))
 def test_missing_brand_rejected(self):
  e=self.p['entities'][0];e.update(identity_required=True,asset_status='missing');self.assertTrue(any('unresolved visual asset' in x for x in validate(self.p,self.c)))
 def test_silent_text_substitution_rejected(self):
  self.p['entities'][0].update(identity_required=True,representation='text',reason='没有图');self.assertTrue(any('not authorized' in x for x in validate(self.p,self.c)))
 def test_explicit_text_choice_allowed(self):
  self.p['entities'][0].update(identity_required=True,representation='text',reason='用户选择文字',fallback_approved=True,fallback_evidence='这项用文字即可');self.assertEqual(validate(self.p,self.c),[])
 def test_cosmetic_growth_rejected(self):
  self.p['beats'][0]['changes']=['opacity','scale'];self.assertTrue(any('cosmetic' in x for x in validate(self.p,self.c)))
 def test_label_change_not_growth(self):
  self.p['beats'][0]['changes']=['labels'];self.assertTrue(any('member/count' in x for x in validate(self.p,self.c)))
 def test_unknown_entity(self):
  self.p['beats'][0]['entity_ids']=['unknown'];self.assertTrue(any('unknown entity' in x for x in validate(self.p,self.c)))
 def test_source_text_cannot_silently_change(self):
  self.p['beats'][0]['text']='产品数量翻倍';self.assertTrue(any('text mismatch' in x for x in validate(self.p,self.c)))
 def test_meaningful_hold_allowed(self):
  b=self.p['beats'][0];b.update(kind='hold',before='数据图',after='数据图',changes=[],hold_reason='观众需要阅读');self.assertEqual(validate(self.p,self.c),[])
if __name__=='__main__':unittest.main()

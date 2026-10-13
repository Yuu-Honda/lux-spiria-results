"""Verify public numerical consistency, generated parity and publication boundaries."""
import importlib.util
import json
from pathlib import Path
import re
import unittest
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote

ROOT=Path(__file__).resolve().parents[1]
D=json.loads((ROOT/'data/shiori-pilot-2026-10-13.json').read_text())
PAGES=[ROOT/x for x in ('index.html','en.html','studies/2026-10-13-shiori-pilot/index.html','studies/2026-10-13-shiori-pilot/en.html')]
class Markup(HTMLParser):
 def __init__(self,text):
  super().__init__(); self.ids=[]; self.refs=[]; self.lang=None; self.feed(text)
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if 'id' in a:self.ids.append(a['id'])
  if tag=='html':self.lang=a.get('lang')
  for k in ('href','src'):
   if k in a:self.refs.append(a[k])
class Results(unittest.TestCase):
 def test_aggregate_recalculation(self):
  self.assertEqual(len(D['per_query']),24)
  self.assertEqual([q['id'] for q in D['per_query']],[f'Q{i:02}' for i in range(1,25)])
  answerable=[q for q in D['per_query'] if q['category']!='no_answer_control']
  self.assertEqual(len(answerable),22)
  for c in D['conditions']:
   ranks=[q['conditions'][c['id']]['target_rank_at_5'] for q in answerable]
   for k in (1,3,5):self.assertEqual(c['target_hits'][f'at_{k}'],sum(r is not None and r<=k for r in ranks))
   self.assertAlmostEqual(c['mrr_at_5'],sum(1/r if r else 0 for r in ranks)/22)
   self.assertEqual(c['no_answer_controls_with_candidates'],sum(q['conditions'][c['id']]['candidate_count']>0 for q in D['per_query'] if q['category']=='no_answer_control'))
 def test_zero_cue_failure_and_timing(self):
  for q in D['per_query'][8:16]:
   for c in q['conditions'].values():self.assertEqual((c['cue_count'],c['candidate_count']),(0,0))
  self.assertEqual(len(D['timing']['samples']),12)
  for r in D['timing']['samples']:
   self.assertEqual(r['n'],24*21); self.assertGreaterEqual(r['p95_ms'],r['median_ms'])
  self.assertFalse(D['verification']['timing_values_reproduction_claimed'])
 def test_public_schema_allowlist(self):
  self.assertEqual(set(D),{'schema_version','study_id','date','provenance','sample','indexing','conditions','per_query','timing','verification','findings','boundaries','retrieval_config'})
  for q in D['per_query']:
   self.assertEqual(set(q),{'id','category','conditions'})
   for c in q['conditions'].values():self.assertEqual(set(c),{'target_rank_at_5','candidate_count','cue_count','has_ties_at_5'})
  for p in ROOT.rglob('*'):
   if not p.is_file() or '.git' in p.parts or '__pycache__' in p.parts:continue
   self.assertNotIn(p.suffix.lower(),{'.db','.sqlite','.sqlite3','.zip','.jsonl'})
   if p.suffix.lower() in {'.html','.json','.js','.css','.md','.py','.webmanifest'}:
    s=p.read_text()
    self.assertNotRegex(s,r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')
    self.assertNotRegex(s,r'/' + r'Users/[^/\s]+/')
 def test_local_links_ids_and_language(self):
  for p in PAGES:
   m=Markup(p.read_text());self.assertEqual(len(m.ids),len(set(m.ids)))
   self.assertEqual(m.lang,'en' if p.name=='en.html' else 'ja')
   for ref in m.refs:
    u=urlsplit(ref)
    if u.scheme or u.netloc:continue
    target=(p.parent/unquote(u.path)).resolve() if u.path else p
    if target.is_dir():target=target/'index.html'
    self.assertTrue(target.is_file(),f'{p}: {ref}')
    if u.fragment and target.suffix=='.html':self.assertIn(u.fragment,Markup(target.read_text()).ids)
  self.assertEqual(set(Markup(PAGES[0].read_text()).ids),set(Markup(PAGES[1].read_text()).ids))
  self.assertEqual(set(Markup(PAGES[2].read_text()).ids),set(Markup(PAGES[3].read_text()).ids))
 def test_generated_pages_current(self):
  spec=importlib.util.spec_from_file_location('pages',ROOT/'tools/build_pages.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
  for lang,name in [('ja','index.html'),('en','en.html')]:
   self.assertEqual((ROOT/name).read_text(),mod.landing(lang)+'\n')
   self.assertEqual((ROOT/'studies/2026-10-13-shiori-pilot'/name).read_text(),mod.study(lang)+'\n')
 def test_home_screen_icons(self):
  for name,lang in [('site.webmanifest','ja'),('site.en.webmanifest','en')]:
   m=json.loads((ROOT/name).read_text());self.assertEqual(m['lang'],lang)
   for i in m['icons']:self.assertTrue((ROOT/i['src']).is_file())
if __name__=='__main__':unittest.main()

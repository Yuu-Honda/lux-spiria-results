"""Verify the additive study using public summaries only, never private inputs."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import copy
import hashlib
import importlib.util
import json
import re
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/shiori-retrieval-hypotheses-2026-10-21.json'
STUDY = ROOT / 'studies/2026-10-21-retrieval-hypotheses'
spec = importlib.util.spec_from_file_location('retrieval_hypotheses_site', ROOT / 'tools/build_retrieval_hypotheses.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

PRIOR_STUDY_HASHES = {
    'studies/2026-10-13-shiori-pilot/en.html': '1a4aef0f75524e73200641f59826d3cdabb88a001f6fcccb8f61599313044b77',
    'studies/2026-10-13-shiori-pilot/index.html': '64ae9b3dadc4eb659031c3d43622920e111acddcd9588d4de92d55e838c1eb09',
    'studies/2026-10-21-cross-session/en.html': 'dec228d307488278563ae25ff8f049e6507bd110bf1282698b24ef2842935862',
    'studies/2026-10-21-cross-session/index.html': 'ee8b03d898021d4eaf99617e583003473f3d56a1e20fd71086e8e035beb2540e',
    'data/shiori-pilot-2026-10-13.json': '5f1a09df554ac6a57b0ead347ae4f3bbd4ec9ed4866fc44e96f82926194f21c7',
    'data/shiori-cross-session-2026-10-21.json': '09f075d9f84bfb336912946b6f268056e2c0b1b8fd6ca8e58eb28d3d1ab34c99',
}


class Page(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.ids, self.refs, self.text, self.links, self.arms = [], [], [], [], []
        self.lang = None
        self.scripts = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if 'id' in a:
            self.ids.append(a['id'])
        if tag == 'html':
            self.lang = a.get('lang')
        if tag == 'link':
            self.links.append(a)
        if tag == 'script':
            self.scripts.append(a)
        if a.get('data-arm'):
            self.arms.append(a['data-arm'])
        self.refs.extend(a[key] for key in ('href', 'src') if a.get(key))

    def handle_data(self, data):
        self.text.append(data)


class RetrievalPreparation(unittest.TestCase):
    def test_prior_study_bytes_unchanged(self):
        for name, digest in PRIOR_STUDY_HASHES.items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), digest, name)

    def test_missing_summary_never_renders_pending_numbers(self):
        with TemporaryDirectory() as missing_root:
            with patch.object(mod, 'ROOT', Path(missing_root)):
                with self.assertRaisesRegex(FileNotFoundError, 'no study pages were written'):
                    mod.build()
                self.assertFalse((mod.ROOT / mod.STUDY).exists())

    def test_incomplete_summary_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'public fields'):
            mod.validate_summary({})


@unittest.skipUnless(DATA.exists(), 'Awaiting actual audited public study data')
class RetrievalResults(unittest.TestCase):
    def setUp(self):
        self.d = json.loads(DATA.read_text())

    def test_recursive_allowlist_and_aggregate_recalculation(self):
        self.assertIs(mod.validate_summary(self.d), self.d)
        self.assertEqual([c['id'] for c in self.d['conditions']], list(mod.ARMS))
        self.assertEqual([self.d['sample'][k + '_queries'] for k in mod.CATEGORIES], [4, 12, 8, 8])
        for condition in self.d['conditions']:
            arm = condition['id']
            wrong = sum(q['category'] in ('literal', 'paraphrase') and q['conditions'][arm]['returned_candidate'] and not q['conditions'][arm]['target_hit'] for q in self.d['per_query'])
            self.assertEqual(condition['positive_wrong_scene_returns'], wrong)
        for q in self.d['per_query']:
            raw, gated = q['conditions']['recovery_raw'], q['conditions']['recovery_gated']
            self.assertEqual(raw['search_executed'], gated['search_executed'])
            if gated['returned_candidate']:
                self.assertTrue(raw['returned_candidate'])

    def test_corrupt_aggregate_and_private_fields_are_rejected(self):
        corrupt = copy.deepcopy(self.d)
        corrupt['conditions'][0]['positive_hits'] += 1
        with self.assertRaisesRegex(ValueError, 'disagrees'):
            mod.validate_summary(corrupt)
        corrupt = copy.deepcopy(self.d)
        corrupt['conditions'][0]['positive_wrong_scene_returns'] += 1
        with self.assertRaisesRegex(ValueError, 'disagrees'):
            mod.validate_summary(corrupt)
        corrupt = copy.deepcopy(self.d)
        corrupt['per_query'][0]['query_text'] = 'must never be imported'
        with self.assertRaisesRegex(ValueError, 'public fields'):
            mod.validate_summary(corrupt)
        corrupt = copy.deepcopy(self.d)
        corrupt['per_query'][0]['conditions']['baseline']['target_hit'] = 1
        with self.assertRaisesRegex(ValueError, 'booleans'):
            mod.validate_summary(corrupt)

    def test_known_regression_is_separate_and_retains_recorded_values(self):
        r = self.d['known_regression']
        self.assertEqual([c['positive_hits'] for c in r['conditions']], [7, 5, 6, 8, 13, 11])
        self.assertEqual([c['confusable_false_returns'] for c in r['conditions']], [6, 0, 0, 0, 8, 0])

    def test_privacy_and_verification_boundaries(self):
        raw = DATA.read_text()
        self.assertNotRegex(raw, r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')
        self.assertNotRegex(raw, r'/' + r'Users/[^/\s]+/')
        self.assertNotRegex(raw, r'"(?:query_text|source_text|evidence|source_id|scene_id|case_id|feature_key)"\s*:')
        v = self.d['verification']
        for key in ('source_event_identity_verified', 'model_regeneration_tested', 'timing_measured', 'daily_brain_verified', 'emotion_verified', 'full_wake_verified', 'external_source_audit_possible_from_public_data', 'model_identity_recorded'):
            self.assertFalse(v[key], key)
        for key in ('saved_actual_ai_outputs_replayed', 'pre_body_selection_locked', 'mechanical_metadata_repair_preserved', 'query_author_read_full_protocol', 'role_isolation_instruction_only'):
            self.assertTrue(v[key], key)
        self.assertEqual(v['synthetic_engineering_tests'], 58)
        self.assertEqual(v['synthetic_engineering_passed'], 58)
        self.assertEqual(v['semantic_review_repairs'], 1)
        self.assertEqual(v['pre_score_literal_requirements_removed'], 5)

    def test_prior_results_listing_retains_public_conditions(self):
        c = {x['id']:x for x in self.d['conditions']}
        legacy, recovery = c['legacy_gated'], c['recovery_gated']
        for home, listing, detail in [('index.html', 'results.html', 'index.html'), ('index.en.html', 'results.en.html', 'en.html')]:
            html = (ROOT / home).read_text()
            text = re.sub(r'\s+', '', ''.join(Page((ROOT / listing).read_text()).text))
            for key, denominator in [('positive_hits',16), ('confusable_false_returns',8)]:
                self.assertIn(f'{legacy[key]}/{denominator}→{recovery[key]}/{denominator}', text)
            self.assertIn(f'{recovery["positive_wrong_scene_returns"]}/16', text)
            self.assertIn(f'studies/2026-10-21-retrieval-hypotheses/{detail}', (ROOT / listing).read_text())
            self.assertEqual(html.count('data-mechanism '), 4)

    def test_bilingual_pages_routes_and_static_chart_accessibility(self):
        ids = []
        for lang, name in [('ja', 'index.html'), ('en', 'en.html')]:
            p = STUDY / name
            html = mod.retrieval_hypotheses(lang, self.d) + '\n'
            self.assertEqual(p.read_text(), html)
            self.assertEqual(html, mod.retrieval_hypotheses(lang, self.d) + '\n')
            page = Page(html)
            self.assertEqual(page.lang, lang)
            self.assertEqual(len(page.ids), len(set(page.ids)))
            self.assertEqual(page.arms, list(mod.ARMS) * 2)
            self.assertEqual(page.scripts, [])
            self.assertNotIn('data-chart-cutoff', html)
            self.assertEqual(html.count('class="chart-track" aria-hidden="true"'), 12)
            self.assertIn('scope="col"', html)
            self.assertIn('scope="row"', html)
            links = {link.get('hreflang'): link['href'] for link in page.links if link.get('rel') == 'alternate'}
            self.assertIn('2026-10-21-retrieval-hypotheses/', links['ja'])
            self.assertEqual(links['en'], links['ja'] + 'en.html')
            self.assertIn('not blind to algorithm design' if lang == 'en' else 'アルゴリズム設計には盲検ではありません', ''.join(page.text))
            self.assertIn('Wrong-scene returns on positive queries' if lang == 'en' else '対象ありで別場面を誤返却', ''.join(page.text))
            self.assertIn('After mechanical counting, selection was durably fixed before semantic reading of selected bodies.' if lang == 'en' else '件数を機械的に確認した後、原文の意味を読む前に選定をファイルへ固定', ''.join(page.text))
            self.assertIn('No contribution of the graph or convergence' if lang == 'en' else '網や合流による最終1候補の選択への寄与は確認できません', ''.join(page.text))
            for statement in self.d['boundaries']:
                self.assertIn(statement, ''.join(page.text))
            for ref in page.refs:
                url = urlsplit(ref)
                if url.scheme or url.netloc:
                    continue
                target = (p.parent / unquote(url.path)).resolve() if url.path else p
                if target.is_dir():
                    target /= 'index.html'
                self.assertTrue(target.is_file(), ref)
                if url.fragment and target.suffix == '.html':
                    self.assertIn(url.fragment, Page(target.read_text()).ids, ref)
            ids.append(set(page.ids))
        self.assertEqual(ids[0], ids[1])


if __name__ == '__main__':
    unittest.main()

"""Recalculate the new public study without access to private research inputs."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import importlib.util
import json
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/shiori-cross-session-2026-10-21.json'
D = json.loads(DATA.read_text())
ARMS = ['baseline', 'raw_semantic', 'gated_semantic']
STUDY = ROOT / 'studies/2026-10-21-cross-session'


class Page(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.ids, self.refs, self.text = [], [], []
        self.lang = None
        self.canonical = None
        self.feed(path.read_text())

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if 'id' in a:
            self.ids.append(a['id'])
        if tag == 'html':
            self.lang = a.get('lang')
        if tag == 'link' and a.get('rel') == 'canonical':
            self.canonical = a.get('href')
        self.refs.extend(a[k] for k in ('href', 'src') if a.get(k))

    def handle_data(self, data):
        self.text.append(data)


class CrossSessionResults(unittest.TestCase):
    def test_public_field_allowlist(self):
        self.assertEqual(set(D), {
            'schema_version', 'study_id', 'date', 'endpoint', 'provenance',
            'sample', 'conditions', 'per_query', 'failure_analysis',
            'verification', 'implementation', 'boundaries',
        })
        self.assertEqual(D['endpoint'], 'relevant_original_source_scene_at_1')
        self.assertEqual(len(D['per_query']), 32)
        self.assertEqual([q['id'] for q in D['per_query']], [f'Q{i:02}' for i in range(1, 33)])
        for q in D['per_query']:
            self.assertEqual(set(q), {'id', 'category', 'conditions'})
            self.assertEqual(set(q['conditions']), set(ARMS))
            for c in q['conditions'].values():
                self.assertEqual(set(c), {'target_hit', 'returned_candidate', 'search_executed'})
                self.assertTrue(all(type(v) is bool for v in c.values()))
        text = DATA.read_text()
        self.assertNotRegex(text, r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')
        self.assertNotRegex(text, r'/' + r'Users/[^/\s]+/')
        self.assertNotRegex(text, r'"(?:query_text|source_text|evidence|source_id|scene_id|case_id)"\s*:')
        for value in D['provenance'].values():
            self.assertTrue(value == 'canonical-evidence-01' or re.fullmatch('[a-f0-9]{64}', value))

    def test_recalculate_all_conditions_and_denominators(self):
        sizes = {'literal': 4, 'paraphrase': 12, 'confusable': 8, 'absent': 8}
        self.assertEqual(sum(sizes.values()), D['sample']['queries'])
        self.assertEqual(D['sample']['source_messages'], D['sample']['sessions'] * D['sample']['messages_per_session'])
        self.assertEqual([c['id'] for c in D['conditions']], ARMS)
        for kind, count in sizes.items():
            self.assertEqual(sum(q['category'] == kind for q in D['per_query']), count)
        for arm in D['conditions']:
            aid = arm['id']
            for kind in ('literal', 'paraphrase'):
                self.assertEqual(arm[kind + '_hits'], sum(q['conditions'][aid]['target_hit'] for q in D['per_query'] if q['category'] == kind))
            self.assertEqual(arm['positive_hits'], arm['literal_hits'] + arm['paraphrase_hits'])
            for kind in ('confusable', 'absent'):
                self.assertEqual(arm[kind + '_false_returns'], sum(q['conditions'][aid]['returned_candidate'] for q in D['per_query'] if q['category'] == kind))
            self.assertEqual(arm['native_searches'], sum(q['conditions'][aid]['search_executed'] for q in D['per_query']))
            self.assertEqual(arm['pre_search_abstentions'], 32 - arm['native_searches'])
            for q in D['per_query']:
                c = q['conditions'][aid]
                if c['target_hit']:
                    self.assertIn(q['category'], {'literal', 'paraphrase'})
                    self.assertTrue(c['returned_candidate'])
                if not c['search_executed']:
                    self.assertFalse(c['returned_candidate'])
            for metric in ('graph_expansions', 'graph_edges', 'associated_hits'):
                self.assertEqual(arm[metric], 0)
        self.assertEqual([c['positive_hits'] for c in D['conditions']], [7, 6, 5])
        self.assertEqual([c['confusable_false_returns'] for c in D['conditions']], [6, 3, 0])

    def test_failure_and_execution_boundaries(self):
        f, v, i = D['failure_analysis'], D['verification'], D['implementation']
        actual = sum(q['category'] in {'literal', 'paraphrase'} and not q['conditions']['raw_semantic']['search_executed'] for q in D['per_query'])
        self.assertEqual(actual, f['positive_abstentions'])
        self.assertEqual(actual, sum(f['positive_abstention_reasons'].values()))
        changes = [(q['category'], q['conditions']['raw_semantic']['target_hit']) for q in D['per_query'] if q['conditions']['raw_semantic']['returned_candidate'] and not q['conditions']['gated_semantic']['returned_candidate']]
        self.assertEqual(len(changes), f['gate_candidates_rejected'])
        self.assertEqual(sum(hit for _, hit in changes), f['correct_candidates_removed'])
        self.assertEqual(sum(kind == 'confusable' for kind, _ in changes), f['false_candidates_removed'])
        self.assertTrue(v['initial_condition_failed'])
        self.assertFalse(v['initial_scored_results_observed'])
        for name in ('model_regeneration_tested', 'timing_measured', 'native_lre_state_written', 'external_source_audit_possible_from_public_data', 'source_event_identity_verified'):
            self.assertFalse(v[name])
        for name in ('shiori_merged_into_lre_main', 'operational_shiori_store_updated', 'operational_shiori_store_location_confirmed', 'full_wake_completed_in_smoke'):
            self.assertFalse(i[name])
        self.assertEqual(i['maintenance_tests'], i['maintenance_passed'] + i['maintenance_preexisting_failures'])

    def test_generated_new_study_and_routes(self):
        spec = importlib.util.spec_from_file_location('cross_session_site_pages', ROOT / 'tools/build_pages.py')
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        pages = []
        for lang, name in [('ja', 'index.html'), ('en', 'en.html')]:
            p = STUDY / name
            self.assertEqual(p.read_text(), mod.cross_session(lang) + '\n')
            page = Page(p)
            self.assertEqual(page.lang, lang)
            self.assertEqual(len(page.ids), len(set(page.ids)))
            self.assertIn('/studies/2026-10-21-cross-session/', page.canonical)
            pages.append(page)
            for ref in page.refs:
                u = urlsplit(ref)
                if u.scheme or u.netloc:
                    continue
                dest = (p.parent / unquote(u.path)).resolve() if u.path else p
                if dest.is_dir():
                    dest /= 'index.html'
                self.assertTrue(dest.is_file(), ref)
                if u.fragment and dest.suffix == '.html':
                    self.assertIn(u.fragment, Page(dest).ids, ref)
        self.assertEqual(set(pages[0].ids), set(pages[1].ids))

    def test_listings_retain_prior_study_and_home_walkthroughs(self):
        for home, listing, detail in [('index.html', 'results.html', 'index.html'), ('index.en.html', 'results.en.html', 'en.html')]:
            self.assertIn(f'studies/2026-10-21-cross-session/{detail}', (ROOT / listing).read_text())
            html = (ROOT / home).read_text()
            self.assertEqual(html.count('data-mechanism '), 4)
            text = re.sub(r'\s+', '', ''.join(Page(ROOT / listing).text))
            for count in ('7/16', '5/16', '6/8', '0/8'):
                self.assertIn(count, text)


if __name__ == '__main__':
    unittest.main()

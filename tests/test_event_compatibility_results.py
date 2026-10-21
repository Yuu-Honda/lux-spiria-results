"""Public-only validation; synthetic contract fixtures are never study results.

Actual-data checks activate only after the audited public JSON is supplied.
Preparation checks never create an HTML page or a placeholder result file.
"""
import copy
import hashlib
from html.parser import HTMLParser
import importlib.util
import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/shiori-event-compatibility-2026-10-22.json'
STUDY = ROOT / 'studies/2026-10-22-event-compatibility'
spec = importlib.util.spec_from_file_location('event_compatibility_site', ROOT / 'tools/build_event_compatibility.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

PRIOR_HASHES = {
    'data/shiori-cross-session-2026-10-21.json': '09f075d9f84bfb336912946b6f268056e2c0b1b8fd6ca8e58eb28d3d1ab34c99',
    'data/shiori-pilot-2026-10-13.json': '5f1a09df554ac6a57b0ead347ae4f3bbd4ec9ed4866fc44e96f82926194f21c7',
    'data/shiori-retrieval-hypotheses-2026-10-21.json': '54c09696c06e5ddcc0031d73663fc4d46e82d3b79e8aa4223d15449d4edd7680',
    'studies/2026-10-13-shiori-pilot/en.html': '1a4aef0f75524e73200641f59826d3cdabb88a001f6fcccb8f61599313044b77',
    'studies/2026-10-13-shiori-pilot/index.html': '64ae9b3dadc4eb659031c3d43622920e111acddcd9588d4de92d55e838c1eb09',
    'studies/2026-10-21-cross-session/en.html': 'dec228d307488278563ae25ff8f049e6507bd110bf1282698b24ef2842935862',
    'studies/2026-10-21-cross-session/index.html': 'ee8b03d898021d4eaf99617e583003473f3d56a1e20fd71086e8e035beb2540e',
    'studies/2026-10-21-retrieval-hypotheses/en.html': 'bd816448fb20b690c8e390bcd9eebb34b5a70afe62fde68230d4aec31a6643dd',
    'studies/2026-10-21-retrieval-hypotheses/index.html': '5b3aa38dcf92ba6506700fb78d078a31f15dabbef890f9febdc49da8d856ac93',
}


def contract_fixture():
    """Clearly synthetic input for validator tests only; never serialized/written."""
    queries = []
    categories = ['paraphrase', 'absent', 'confusable', 'literal'] * 4 + ['paraphrase', 'absent', 'confusable', 'paraphrase'] * 4
    for i, category in enumerate(categories, 1):
        positive = category in ('literal', 'paraphrase')
        # Different outcomes across arms exercise all independently derived columns.
        conditions = {}
        for j, arm in enumerate(mod.ARMS):
            returned = j == 0 or (i + j) % 3 != 0
            conditions[arm] = {'target_hit': positive and returned and (i + j) % 2 == 0,
                               'returned_candidate': returned, 'search_executed': True}
        retrieval = {key: 0 for key in mod.RETRIEVAL_FIELDS - mod.TARGET_FIELDS}
        retrieval.update({key: positive for key in mod.TARGET_FIELDS})
        retrieval.update(original_native_candidates=20, semantic_native_candidates=20,
                         unique_union_candidates=30, native_route_count=2,
                         graph_expansions=i, graph_edges=i % 3, associated_hits=i % 2)
        ablations = {ablation: {arm: dict(result, same_selection_as_normal=True)
                               for arm, result in conditions.items()} for ablation in mod.ABLATIONS}
        queries.append({'id': f'Q{i:02}', 'category': category,
                        'retrieval': retrieval, 'conditions': conditions, 'ablations': ablations})
    known = [{'id': f'K{i:02}', 'category': q['category'], 'conditions': copy.deepcopy(q['conditions']),
              'ablations': copy.deepcopy(q['ablations'])}
             for i, q in enumerate(queries, 1)]
    return {
        'schema_version': 1, 'study_id': 'shiori-event-compatibility-2026-10-22',
        'date': '2026-10-22', 'endpoint': 'relevant_original_source_scene_at_1',
        'provenance': {key: '0' * 64 for key in mod.PROVENANCE_FIELDS},
        'sample': dict(mod.SAMPLE_VALUES),
        'method': dict({key: True for key in mod.METHOD_TRUE}, **{key: False for key in mod.METHOD_FALSE}, event_review_prescore_repairs=0),
        'per_query': queries, 'conditions': mod.recalculate_conditions(queries),
        'known_regression': dict({key: mod.SAMPLE_VALUES[key] for key in ('queries', 'positive_queries', 'literal_queries', 'paraphrase_queries', 'confusable_queries', 'absent_queries')}, per_query=known, conditions=mod.recalculate_conditions(known)),
        'verification': dict({key: True for key in mod.VERIFICATION_TRUE}, **{key: False for key in mod.VERIFICATION_FALSE},
                             code_engineering_tests=1, code_engineering_passed=1,
                             synthetic_engineering_tests=1, synthetic_engineering_passed=1,
                             failed_index_artifacts_retained=3, native_primary_search_calls=192,
                             preparation_replay_native_search_calls=192,
                             independent_replay_native_search_calls=192, known_regression_native_search_calls=64,
                             known_regression_preparation_replay_native_search_calls=64,
                             known_regression_independent_replay_native_search_calls=64,
                             final_audit_additional_native_search_calls=192,
                             known_regression_final_audit_additional_native_search_calls=64),
    }


class Page(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.ids, self.refs, self.text, self.links, self.scripts = [], [], [], [], []
        self.lang = None
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
        self.refs.extend(a[key] for key in ('href', 'src') if a.get(key))

    def handle_data(self, data):
        self.text.append(data)


class EventPreparation(unittest.TestCase):
    def setUp(self):
        self.d = contract_fixture()

    def test_existing_three_dated_pairs_and_json_are_byte_preserved(self):
        for name, expected in PRIOR_HASHES.items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), expected, name)

    def test_missing_data_fails_before_writing_anything(self):
        with TemporaryDirectory() as temporary:
            with patch.object(mod, 'ROOT', Path(temporary)):
                with self.assertRaisesRegex(FileNotFoundError, 'no study pages were written'):
                    mod.build()
                self.assertEqual(list(Path(temporary).iterdir()), [])

    def test_invalid_data_fails_before_output_creation(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / mod.DATA_FILE
            path.parent.mkdir()
            path.write_text('{}')
            with patch.object(mod, 'ROOT', root):
                with self.assertRaisesRegex(ValueError, 'public fields'):
                    mod.build()
                self.assertFalse((root / mod.STUDY).exists())

    def test_contract_and_all_aggregate_columns_recalculate(self):
        self.assertIs(mod.validate_summary(self.d), self.d)
        for dataset in (self.d, self.d['known_regression']):
            self.assertEqual(dataset['conditions'], mod.recalculate_conditions(dataset['per_query']))
            for i, row in enumerate(dataset['conditions']):
                for metric in mod.METRICS:
                    corrupt = copy.deepcopy(self.d)
                    rows = corrupt['conditions'] if dataset is self.d else corrupt['known_regression']['conditions']
                    rows[i][metric] += 1
                    with self.subTest(arm=row['id'], metric=metric), self.assertRaisesRegex(ValueError, 'disagrees'):
                        mod.validate_summary(corrupt)

    def test_recursive_allowlist_rejects_extra_fields_at_every_object_depth(self):
        paths = [(), ('provenance',), ('sample',), ('method',), ('verification',),
                 ('conditions', 0), ('per_query', 0), ('per_query', 0, 'retrieval'),
                 ('per_query', 0, 'conditions'), ('per_query', 0, 'conditions', mod.ARMS[0]),
                 ('per_query', 0, 'ablations'), ('per_query', 0, 'ablations', mod.ABLATIONS[0]),
                 ('per_query', 0, 'ablations', mod.ABLATIONS[0], mod.ARMS[0]),
                 ('known_regression',), ('known_regression', 'conditions', 0),
                 ('known_regression', 'per_query', 0),
                 ('known_regression', 'per_query', 0, 'conditions'),
                 ('known_regression', 'per_query', 0, 'conditions', mod.ARMS[0]),
                 ('known_regression', 'per_query', 0, 'ablations'),
                 ('known_regression', 'per_query', 0, 'ablations', mod.ABLATIONS[0]),
                 ('known_regression', 'per_query', 0, 'ablations', mod.ABLATIONS[0], mod.ARMS[0])]
        for path in paths:
            corrupt = copy.deepcopy(self.d)
            node = corrupt
            for key in path:
                node = node[key]
            node['source_text'] = 'forbidden contract field'
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, 'public fields'):
                mod.validate_summary(corrupt)

    def test_no_source_tokens_or_native_artifacts_can_enter_string_fields(self):
        for path, value in [(('per_query', 0, 'id'), 'native-source-identifier'),
                            (('per_query', 0, 'category'), 'private query text'),
                            (('provenance', 'protocol_sha256'), '/private/source/path'),
                            (('per_query', 0, 'conditions', mod.ARMS[0], 'target_hit'), 'source body')]:
            corrupt = copy.deepcopy(self.d)
            node = corrupt
            for key in path[:-1]:
                node = node[key]
            node[path[-1]] = value
            with self.subTest(path=path), self.assertRaises(ValueError):
                mod.validate_summary(corrupt)

    def test_native_route_counts_and_full_union_are_distinct(self):
        self.assertTrue(all(q['retrieval']['unique_union_candidates'] > 20 for q in self.d['per_query']))
        for key, value in [('original_native_candidates', 21), ('unique_union_candidates', 19),
                           ('native_route_count', 3), ('union_target_present', False)]:
            corrupt = copy.deepcopy(self.d)
            corrupt['per_query'][0]['retrieval'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                mod.validate_summary(corrupt)
        corrupt = copy.deepcopy(self.d)
        corrupt['verification']['native_primary_search_calls'] -= 1
        with self.assertRaisesRegex(ValueError, 'Primary native calls'):
            mod.validate_summary(corrupt)

    def test_negative_target_coverage_and_numeric_booleans_are_rejected(self):
        corrupt = copy.deepcopy(self.d)
        corrupt['per_query'][1]['retrieval']['union_target_present'] = True
        with self.assertRaisesRegex(ValueError, 'positive query'):
            mod.validate_summary(corrupt)
        corrupt = copy.deepcopy(self.d)
        corrupt['per_query'][0]['conditions'][mod.ARMS[0]]['returned_candidate'] = 1
        with self.assertRaisesRegex(ValueError, 'booleans'):
            mod.validate_summary(corrupt)
        corrupt = copy.deepcopy(self.d)
        corrupt['sample']['sessions'] = True
        with self.assertRaisesRegex(ValueError, 'integer'):
            mod.validate_summary(corrupt)

    def test_ablation_equality_is_validated_without_scene_ids(self):
        corrupt = copy.deepcopy(self.d)
        result = corrupt['per_query'][0]['ablations']['hops0'][mod.ARMS[0]]
        result['target_hit'] = not result['target_hit']
        with self.assertRaisesRegex(ValueError, 'Equal selections'):
            mod.validate_summary(corrupt)
        result['same_selection_as_normal'] = False
        self.assertIs(mod.validate_summary(corrupt), corrupt)

    def test_known_ablation_blocks_are_required_validated_and_recalculated_separately(self):
        known = self.d['known_regression']['per_query']
        self.assertEqual(len(mod.recalculate_ablations(known)), 8)
        expected = mod.recalculate_ablations(known)
        # Alter a known-set outcome only; the fresh set must remain independent.
        known[0]['ablations']['hops0']['event_review_only']['target_hit'] = True
        known[0]['ablations']['hops0']['event_review_only']['returned_candidate'] = True
        known[0]['ablations']['hops0']['event_review_only']['same_selection_as_normal'] = False
        self.assertIs(mod.validate_summary(self.d), self.d)
        actual = mod.recalculate_ablations(known)
        for before, after in zip(expected, actual):
            if after['ablation'] == 'hops0' and after['id'] == 'event_review_only':
                self.assertEqual(after['positive_hits'], before['positive_hits'] + 1)
                self.assertEqual(after['changed_selections'], before['changed_selections'] + 1)
            else:
                self.assertEqual(after, before)
        self.assertEqual(mod.recalculate_ablations(self.d['per_query']), expected)
        corrupt = copy.deepcopy(self.d)
        del corrupt['known_regression']['per_query'][0]['ablations']
        with self.assertRaisesRegex(ValueError, 'public fields'):
            mod.validate_summary(corrupt)
        corrupt = copy.deepcopy(self.d)
        corrupt['known_regression']['per_query'][0]['ablations']['hops0']['event_review_only']['same_selection_as_normal'] = True
        with self.assertRaisesRegex(ValueError, 'Equal selections'):
            mod.validate_summary(corrupt)

    def test_review_repair_cap_and_world_truth_boundaries_fail_closed(self):
        corrupt = copy.deepcopy(self.d)
        corrupt['method']['event_review_prescore_repairs'] = 3
        with self.assertRaisesRegex(ValueError, 'At most two'):
            mod.validate_summary(corrupt)
        for key in mod.VERIFICATION_FALSE:
            corrupt = copy.deepcopy(self.d)
            corrupt['verification'][key] = True
            with self.subTest(key=key), self.assertRaises(ValueError):
                mod.validate_summary(corrupt)

    def test_css_is_entirely_scoped_to_the_new_study(self):
        text = (STUDY / 'event-compatibility.css').read_text()
        self.assertIn('.event-study', text)
        self.assertNotIn('.retrieval-study', text)
        self.assertNotIn('data-mechanism', text)


@unittest.skipUnless(DATA.is_file(), 'Actual audited public summary has not been supplied')
class EventActualResults(unittest.TestCase):
    def setUp(self):
        self.d = json.loads(DATA.read_text())

    def test_actual_allowlist_recalculation_and_no_private_identifiers(self):
        self.assertEqual(hashlib.sha256(DATA.read_bytes()).hexdigest(), 'da314ce28940785dac7b097f07ab028b378757f1af6efbfe32d7867be3c3c2bd')
        self.assertIs(mod.validate_summary(self.d), self.d)
        self.assertEqual(self.d['conditions'], mod.recalculate_conditions(self.d['per_query']))
        self.assertEqual(self.d['known_regression']['conditions'], mod.recalculate_conditions(self.d['known_regression']['per_query']))
        text = DATA.read_text()
        self.assertNotRegex(text, r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')
        self.assertNotRegex(text, r'/(?:Users|home)/')
        self.assertNotRegex(text, r'"(?:query_text|source_text|source_id|scene_id|selected_scene_id|evidence|rank|score|path)"\s*:')

    def test_latest_home_and_listing_match_the_actual_public_conditions(self):
        arms = {row['id']: row for row in self.d['conditions']}
        strict, reviewed = arms['strict_source_gate'], arms['strict_and_event_review']
        for home, listing, detail in [('index.html', 'results.html', 'index.html'), ('index.en.html', 'results.en.html', 'en.html')]:
            home_html = (ROOT / home).read_text()
            module = re.search(r'<section class="latest-study".*?</section>', home_html, re.S).group()
            text = re.sub(r'\s+', '', ''.join(Page(module).text))
            for arm in ('strict_source_gate', 'strict_and_event_review'):
                self.assertIn(arm, text)
            for metric, denominator in [('positive_hits', 16), ('confusable_false_returns', 8), ('absent_false_returns', 8)]:
                pair = f'{strict[metric]}/{denominator}→{reviewed[metric]}/{denominator}'
                self.assertIn(pair, text)
                self.assertIn(pair, re.sub(r'\s+', '', ''.join(Page((ROOT / listing).read_text()).text)))
            for path in (home, listing):
                self.assertIn(f'studies/2026-10-22-event-compatibility/{detail}', (ROOT / path).read_text())
            self.assertEqual(home_html.count('data-mechanism '), 4)

    def test_bilingual_generated_pages_are_data_derived_and_static(self):
        ids = []
        for lang, name in [('ja', 'index.html'), ('en', 'en.html')]:
            path = STUDY / name
            self.assertTrue(path.is_file(), 'Generate only after actual allowlisted data is supplied')
            self.assertEqual(path.read_text(), mod.event_compatibility(lang, self.d) + '\n')
            page = Page(path.read_text())
            self.assertEqual(page.lang, lang)
            self.assertEqual(len(page.ids), len(set(page.ids)))
            self.assertEqual(page.scripts, [])
            self.assertEqual(set(page.ids), {'main', 'results', 'results-title', 'coverage', 'coverage-title', 'mechanism', 'mechanism-title', 'diagnostics', 'diagnostics-title', 'known-regression', 'known-regression-title', 'method', 'method-title', 'per-query', 'per-query-title', 'verification', 'verification-title'})
            links = {link.get('hreflang'): link['href'] for link in page.links if link.get('rel') == 'alternate'}
            self.assertIn('/2026-10-22-event-compatibility/', links['ja'])
            self.assertEqual(links['en'], links['ja'] + 'en.html')
            for ref in page.refs:
                url = urlsplit(ref)
                if url.scheme or url.netloc:
                    continue
                target = (path.parent / unquote(url.path)).resolve() if url.path else path
                if target.is_dir():
                    target /= 'index.html'
                self.assertTrue(target.is_file(), ref)
                if url.fragment and target.suffix == '.html':
                    self.assertIn(url.fragment, Page(target.read_text()).ids, ref)
            ids.append(set(page.ids))
        self.assertEqual(ids[0], ids[1])


if __name__ == '__main__':
    unittest.main()

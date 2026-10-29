"""Public builder engineering tests; the fixture is artificial, never a study.

Synthetic objects are created in memory and never written to public data/HTML.
Actual-data checks are skipped until the audited public export is supplied.
"""
import copy
import hashlib
from html.parser import HTMLParser
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('event_adoption_public', ROOT / 'tools/build_event_adoption.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
publication_spec = importlib.util.spec_from_file_location('adoption_publication_test', ROOT / 'tools/event_adoption_publication.py')
publication = importlib.util.module_from_spec(publication_spec)
publication_spec.loader.exec_module(publication)

PRESERVED = {
    'data/shiori-cross-session-2026-10-21.json': '09f075d9f84bfb336912946b6f268056e2c0b1b8fd6ca8e58eb28d3d1ab34c99',
    'data/shiori-event-compatibility-2026-10-22.json': 'da314ce28940785dac7b097f07ab028b378757f1af6efbfe32d7867be3c3c2bd',
    'data/shiori-pilot-2026-10-13.json': '5f1a09df554ac6a57b0ead347ae4f3bbd4ec9ed4866fc44e96f82926194f21c7',
    'data/shiori-retrieval-hypotheses-2026-10-21.json': '54c09696c06e5ddcc0031d73663fc4d46e82d3b79e8aa4223d15449d4edd7680',
    'studies/2026-10-13-shiori-pilot/index.html': '64ae9b3dadc4eb659031c3d43622920e111acddcd9588d4de92d55e838c1eb09',
    'studies/2026-10-13-shiori-pilot/en.html': '1a4aef0f75524e73200641f59826d3cdabb88a001f6fcccb8f61599313044b77',
    'studies/2026-10-21-retrieval-hypotheses/index.html': '5b3aa38dcf92ba6506700fb78d078a31f15dabbef890f9febdc49da8d856ac93',
    'studies/2026-10-21-retrieval-hypotheses/en.html': 'bd816448fb20b690c8e390bcd9eebb34b5a70afe62fde68230d4aec31a6643dd',
    'studies/2026-10-21-cross-session/index.html': 'ee8b03d898021d4eaf99617e583003473f3d56a1e20fd71086e8e035beb2540e',
    'studies/2026-10-21-cross-session/en.html': 'dec228d307488278563ae25ff8f049e6507bd110bf1282698b24ef2842935862',
    'studies/2026-10-22-event-compatibility/index.html': 'a2e312d96b2127e635a9460d03b691afe137c8b9813999081270921810339e63',
    'studies/2026-10-22-event-compatibility/en.html': '4dcda4b37cd051e35c44f7fd0707421b416a179fc696ba2b1d3259417f75844a',
    'mechanism.js': 'c04ad2c229961dd41b8c28f42a703eb7deb3eeebafab3ff95fe5c0630e912541',
    'mechanism.css': '596d8eb74a61053ed88095aea263fb726fd84f76bc5bcb03d3799ee9da887700',
    'hero-visual.js': '697889dca2f6b280db7488726c9af1b817e1c33e6c993f9aa2cb4fdda733eb17',
    'recorded-trial.js': 'ac31b45b0ac6fe94f6388f8b2269fed89eb8e2e2c9ca6c5673b953c4274730d1',
    'shiori-network.css': '83cbbec13e5f628e4a1571eb828489d739bda213d57bbbacefb001242bde1f48',
}


def synthetic_contract_fixture():
    """Deliberately artificial engineering input; never serialized as results."""
    conditions = []
    kinds = [kind for kind, count in mod.KINDS.items() for _ in range(count)]
    def counts(items):
        return {key: sum(item[key] for item in items) for key in mod.METRICS}
    for j, cid in enumerate(mod.CONDITIONS):
        items = []
        for i, kind in enumerate(kinds):
            positive = kind in ('literal', 'paraphrase')
            available = positive and (i + j) % 3 != 0
            if positive:
                outcome = ('correct_supported', 'partial_supported', 'missed_answer', 'wrong_or_unsupported')[(i + j) % 4]
            else:
                outcome = 'correct_abstention' if (i + j) % 3 else 'wrong_or_unsupported'
            item = {key: 0 for key in mod.METRICS}
            item.update(queries=1, **{outcome: 1})
            item.update(binding_errors=int((i + j) % 8 == 0),
                        proposal_completion_errors=int((i + j) % 9 == 0),
                        unsupported_claim_items=int((i + j) % 6 == 0),
                        reader_unsupported_assertions=int((i + j) % 6 == 0),
                        mechanical_evidence_error_items=int((i + j) % 7 == 0),
                        retrieval_failures_for_supported_queries=int(positive and not available),
                        reader_answer_use_failures_when_support_available=int(available and outcome != 'correct_supported'))
            items.append(dict(item, kind=kind, cluster=mod.CLUSTERS[i % 4], available=available))
        conditions.append(dict(counts(items), id=cid,
            primary_denominators={'all_frozen_queries': 32, 'supported_queries': 16,
                'corpus_unsupported_queries': 16, 'fully_supporting_supported_queries': sum(item['available'] for item in items),
                'independent_source_clusters': 4},
            query_kind_strata={kind: counts([item for item in items if item['kind'] == kind]) for kind in mod.KINDS},
            source_cluster_strata={cluster: counts([item for item in items if item['cluster'] == cluster]) for cluster in mod.CLUSTERS}))
    native = {cid: dict(positive_scene_at_1_hits=10, positive_wrong_scene_returns=3,
        positive_no_return=3, confusable_false_returns=1, confusable_no_return=7,
        absent_false_returns=1, absent_no_return=7) for cid in mod.CONDITIONS[:-1]}
    return {
        'schema_version': 1, 'study_id': 'shiori-event-adoption-2026-10-24', 'date': '2026-10-24',
        'sample': dict(mod.SAMPLE), 'source_index': dict(mod.SOURCE_INDEX),
        'provenance': {key: '0' * 64 for key in mod.PROVENANCE},
        'method': dict({key: True for key in mod.METHOD_TRUE}, **{key: False for key in mod.METHOD_FALSE}),
        'limits': {key: False for key in mod.LIMITS_FALSE},
        'calls': {'successful_reader_contexts': 4, 'failed_collection_attempts': 1,
            'actual_distinct_reader_calls_including_retained_attempts': 5,
            'failed_output_call_metadata_unavailable': False,
            'primary_assessor_calls': 1, 'final_audit_assessor_calls': 2},
        'answer_reuse': {'unique_query_source_answer_pool_items': 72,
            'unique_answer_items_used_in_condition_lookups': 64,
            'condition_answer_lookups': 416, 'reused_condition_answer_lookups': 352,
            'unique_mechanical_evidence_error_items': 35},
        'conditions': conditions, 'native_scene_diagnostics': native,
        'secondary': {'native_preparation': None, 'graph': None, 'timing': None},
        'verification': {'independent_audit_verified': True, 'code_engineering_checks': 3,
            'code_engineering_passed': 3, 'synthetic_procedure_checks': 2, 'synthetic_procedure_passed': 2},
    }


class Page(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.ids, self.anchors, self.tables, self.captions, self.regions = [], [], 0, 0, 0
        self.lang = None
        self.text, self.scripts = [], []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'html':
            self.lang = attrs.get('lang')
        if attrs.get('id'):
            self.ids.append(attrs['id'])
        if tag == 'a':
            self.anchors.append(attrs.get('href', ''))
        if tag == 'table':
            self.tables += 1
        if tag == 'caption':
            self.captions += 1
        if tag == 'th' and attrs.get('scope') not in ('col', 'row'):
            raise AssertionError('Every table header requires a scope')
        if tag == 'div' and attrs.get('role') == 'region':
            if attrs.get('tabindex') != '0' or not attrs.get('aria-label'):
                raise AssertionError('Overflow table must have a keyboard-focusable labeled region')
            self.regions += 1
        if tag == 'script':
            self.scripts.append(attrs)

    def handle_data(self, text):
        self.text.append(text)


class EventAdoptionPreparation(unittest.TestCase):
    def setUp(self):
        self.d = synthetic_contract_fixture()

    def test_existing_four_studies_overview_and_scroll_assets_unchanged(self):
        for name, expected in PRESERVED.items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), expected, name)

    def test_absent_data_fails_before_any_output_directory_or_page(self):
        with TemporaryDirectory() as temporary:
            with patch.object(mod, 'ROOT', Path(temporary)):
                with self.assertRaisesRegex(FileNotFoundError, 'no study pages were written'):
                    mod.build()
                self.assertEqual(list(Path(temporary).iterdir()), [])

    def test_invalid_data_fails_before_page_or_directory_creation(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            data = root / mod.DATA_FILE
            data.parent.mkdir()
            data.write_text('{}', encoding='utf-8')
            with patch.object(mod, 'ROOT', root):
                with self.assertRaisesRegex(ValueError, 'public fields'):
                    mod.build()
            self.assertFalse((root / mod.STUDY).exists())

    def test_full_synthetic_contract_validates_in_memory_only(self):
        self.assertIs(mod.validate_summary(self.d), self.d)
        self.assertEqual(len(self.d['conditions']), 13)

    def test_recursive_allowlist_rejects_injected_source_fields_everywhere(self):
        paths = []
        def visit(value, path=()):
            if isinstance(value, dict):
                paths.append(path)
                for key, child in value.items():
                    visit(child, path + (key,))
            elif isinstance(value, list):
                for index, child in enumerate(value):
                    visit(child, path + (index,))
        visit(self.d)
        for path in paths:
            corrupt = copy.deepcopy(self.d)
            node = corrupt
            for key in path:
                node = node[key]
            node['source_text'] = 'forbidden engineering sentinel'
            with self.subTest(path=path), self.assertRaises(ValueError):
                mod.validate_summary(corrupt)

    def test_both_strata_partitions_recalculate_all_condition_metrics(self):
        for field in ('query_kind_strata', 'source_cluster_strata'):
            for metric in mod.METRICS:
                corrupt = copy.deepcopy(self.d)
                first = next(iter(corrupt['conditions'][0][field].values()))
                first[metric] += 1
                with self.subTest(field=field, metric=metric), self.assertRaises(ValueError):
                    mod.validate_summary(corrupt)

    def test_frozen_denominators_and_support_available_failure_denominator(self):
        for key in mod.DENOMINATORS:
            corrupt = copy.deepcopy(self.d)
            corrupt['conditions'][0]['primary_denominators'][key] = 33
            with self.subTest(key=key), self.assertRaises(ValueError):
                mod.validate_summary(corrupt)
        corrupt = copy.deepcopy(self.d)
        corrupt['conditions'][0]['primary_denominators']['fully_supporting_supported_queries'] = 0
        with self.assertRaisesRegex(ValueError, 'support-available'):
            mod.validate_summary(corrupt)

    def test_cluster_totals_cannot_hide_a_missing_frozen_source_cluster(self):
        corrupt = copy.deepcopy(self.d)
        strata = corrupt['conditions'][0]['source_cluster_strata']
        # Preserve every aggregate metric while moving all C02 rows into C01.
        for metric in mod.METRICS:
            strata['C01'][metric] += strata['C02'][metric]
            strata['C02'][metric] = 0
        with self.assertRaisesRegex(ValueError, 'eight queries'):
            mod.validate_summary(corrupt)

    def test_condition_errors_are_flagged_items_but_unique_global_count_can_exceed32(self):
        self.assertGreater(self.d['answer_reuse']['unique_mechanical_evidence_error_items'], 32)
        self.assertIs(mod.validate_summary(self.d), self.d)
        for metric in mod.ERRORS:
            corrupt = copy.deepcopy(self.d)
            corrupt['conditions'][0][metric] = 33
            with self.subTest(metric=metric), self.assertRaises(ValueError):
                mod.validate_summary(corrupt)

    def test_calls_retain_failures_unknown_metadata_and_separate_audits(self):
        self.assertIs(mod.validate_summary(self.d), self.d)
        self.d['calls']['actual_distinct_reader_calls_including_retained_attempts'] = None
        self.d['calls']['failed_output_call_metadata_unavailable'] = True
        self.assertIs(mod.validate_summary(self.d), self.d)
        self.d['calls']['failed_collection_attempts'] = 0
        with self.assertRaises(ValueError):
            mod.validate_summary(self.d)

    def test_zero_collection_failures_is_supported_but_not_assumed(self):
        self.d['calls'].update(failed_collection_attempts=0,
            actual_distinct_reader_calls_including_retained_attempts=4)
        self.assertIs(mod.validate_summary(self.d), self.d)

    def test_reuse_is_lookups_minus_unique_items_used_not_whole_pool(self):
        self.assertNotEqual(self.d['answer_reuse']['unique_query_source_answer_pool_items'],
                            self.d['answer_reuse']['unique_answer_items_used_in_condition_lookups'])
        corrupt = copy.deepcopy(self.d)
        corrupt['answer_reuse']['reused_condition_answer_lookups'] -= 1
        with self.assertRaisesRegex(ValueError, 'reused lookups'):
            mod.validate_summary(corrupt)

    def test_scene_diagnostics_are_distinct_and_ceiling_is_never_retrieval(self):
        self.assertNotIn('designated_source_ceiling', self.d['native_scene_diagnostics'])
        corrupt = copy.deepcopy(self.d)
        corrupt['native_scene_diagnostics']['designated_source_ceiling'] = {}
        with self.assertRaisesRegex(ValueError, 'public fields'):
            mod.validate_summary(corrupt)
        for cid in mod.CONDITIONS[:-1]:
            corrupt = copy.deepcopy(self.d)
            corrupt['native_scene_diagnostics'][cid]['confusable_false_returns'] += 1
            with self.subTest(cid=cid), self.assertRaisesRegex(ValueError, 'sum to 8'):
                mod.validate_summary(corrupt)

    def test_nonpublic_strings_and_numeric_booleans_are_rejected(self):
        paths = [(('conditions', 0, 'id'), 'source-identifier'),
                 (('provenance', 'protocol_sha256'), '/private/path'),
                 (('calls', 'failed_collection_attempts'), 'private source text'),
                 (('sample', 'queries'), True),
                 (('method', 'saved_actual_ai_outputs_replayed'), 1)]
        for path, value in paths:
            corrupt = copy.deepcopy(self.d)
            node = corrupt
            for key in path[:-1]:
                node = node[key]
            node[path[-1]] = value
            with self.subTest(path=path), self.assertRaises(ValueError):
                mod.validate_summary(corrupt)

    def test_non_audited_export_is_rejected(self):
        self.d['verification']['independent_audit_verified'] = False
        with self.assertRaisesRegex(ValueError, 'independently audited'):
            mod.validate_summary(self.d)

    def test_optional_actual_native_and_timing_types_reconcile(self):
        # Artificial engineering values, deliberately different from the run.
        self.d['secondary']['native_preparation'] = {
            'primary_native_calls': 190, 'independent_verification_native_calls': 190,
            'fresh_process_replay_equal': False, 'unique_query_candidate_pairs': 64,
            'candidate_count_distribution': {'2': 32}}
        self.d['secondary']['timing'] = {
            'measurement_scope': 'native_wrapper_excludes_ai_orchestration_index_build',
            'primary_native_wrapper_seconds': 1.5, 'verification_native_wrapper_seconds': 2.5}
        self.assertIs(mod.validate_summary(self.d), self.d)
        self.d['secondary']['native_preparation']['unique_query_candidate_pairs'] = 63
        with self.assertRaisesRegex(ValueError, 'reconcile'):
            mod.validate_summary(self.d)

    def test_graph_contract_counts_normal_returned_paths_and_hit_records_only(self):
        # Artificial engineering input, never written as public study data.
        graph = {
            'counting_unit': 'normal_unique_native_route_executions',
            'native_calls': 64, 'graph_expansions': 140,
            'returned_path_segments': 99, 'associated_hits': 12,
            'ablation_selection_changes': {
                f'{arm}:{variant}': 1 for arm in mod.ARMS for variant in mod.VARIANTS[1:]},
        }
        self.d['secondary']['graph'] = graph
        self.assertIs(mod.validate_summary(self.d), self.d)
        html = mod.render('en', self.d)
        self.assertIn('64 normal route executions shared across all arms', html)
        self.assertIn('Returned path segments', html)
        self.assertIn('sum len(hit.path) over normal route outputs', html)
        self.assertIn('Associated hit records', html)
        self.assertIn('these are not unique memories', html)
        self.assertIn('Graph and convergence contributions require the ablation comparisons', html)
        self.assertNotIn('Graph edges', html)
        for unsupported in ('unique_native_route_executions',
                            'all_ablation_unique_native_route_executions', True):
            corrupt = copy.deepcopy(self.d)
            corrupt['secondary']['graph']['counting_unit'] = unsupported
            with self.subTest(counting_unit=unsupported), self.assertRaisesRegex(ValueError, 'normal routes only'):
                mod.validate_summary(corrupt)
        corrupt = copy.deepcopy(self.d)
        corrupt['secondary']['graph']['graph_edges'] = 99
        with self.assertRaisesRegex(ValueError, 'public fields'):
            mod.validate_summary(corrupt)

    def test_in_memory_bilingual_markup_has_accessible_tables_and_all_conditions(self):
        for lang in ('ja', 'en'):
            html = mod.render(lang, self.d)
            page = Page(html)
            self.assertEqual(page.lang, lang)
            self.assertEqual(len(page.ids), len(set(page.ids)))
            self.assertEqual(page.tables, page.captions)
            self.assertEqual(page.tables, page.regions)
            self.assertFalse(page.scripts)
            for link in page.anchors:
                if link.startswith('#'):
                    self.assertIn(link[1:], page.ids)
            for cid in mod.CONDITIONS:
                self.assertIn(mod.label(cid, lang), ''.join(page.text))
            self.assertIn('95', ''.join(page.text))
            self.assertIn('344', ''.join(page.text))
            self.assertIn('284', ''.join(page.text))
            self.assertIn('230', ''.join(page.text))
            self.assertNotIn('forbidden engineering sentinel', html)

    def test_no_new_study_page_is_created_by_preparation_tests(self):
        if not (ROOT / mod.DATA_FILE).exists():
            self.assertFalse((ROOT / mod.STUDY / 'index.html').exists())
            self.assertFalse((ROOT / mod.STUDY / 'en.html').exists())

    def test_reader_source_identity_and_instruction_isolation_limits_are_disclosed(self):
        en = mod.render('en', self.d)
        ja = mod.render('ja', self.d)
        for sentence in (
                'original-message trace retained internal source-case IDs and archive provenance',
                'no direct query-kind, expected-source, arm, rank, score or condition mapping fields',
                'Source-case identities were therefore not fully anonymous',
                'instruction-separated on a shared host, without technical isolation',
                'Frozen inputs were retained as used, without a retrospective retry',
                'Original messages and internal IDs are absent from public JSON and pages'):
            self.assertIn(sentence, en)
        for phrase in ('内部の出典ケースIDとアーカイブの来歴',
                       '質問種別・期待する出典・方式・順位・点数・条件への直接の対応表',
                       '出典ケースの同一性は完全には匿名化されていません',
                       '技術的な隔離ではありません',
                       '固定入力は実際に使った状態で保持',
                       '原文や内部IDは公開JSON・ページに含めません'):
            self.assertIn(phrase, ja)


class EventAdoptionPublicationPreparation(unittest.TestCase):
    def setUp(self):
        self.d = synthetic_contract_fixture()

    def test_missing_optional_export_means_empty_plan_without_any_writes(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.assertIsNone(publication.optional_summary(root))
            self.assertEqual(publication.prepare_updates(root), {})
            self.assertEqual(list(root.iterdir()), [])
        for integrate in (publication.integrate_listing, publication.integrate_home):
            self.assertEqual(integrate('existing bytes', 'en', None), 'existing bytes')
        for integrate in (publication.integrate_readme, publication.integrate_sitemap):
            self.assertEqual(integrate('existing bytes', None), 'existing bytes')

    def test_existing_invalid_optional_export_fails_before_any_output(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            data = root / mod.DATA_FILE
            data.parent.mkdir()
            data.write_text('{}', encoding='utf-8')
            with self.assertRaises(ValueError):
                publication.prepare_updates(root)
            self.assertEqual({str(path.relative_to(root)) for path in root.rglob('*') if path.is_file()}, {mod.DATA_FILE})

    def test_synthetic_plan_stays_in_memory_and_home_change_is_exactly_latest_panel(self):
        originals = {name: (ROOT / name).read_bytes() for name in ('index.html', 'index.en.html', 'README.md', 'sitemap.xml')}
        # Synthetic rendering is in memory only, never written to a public file.
        plan = publication.prepare_updates(ROOT, self.d)
        self.assertEqual(set(plan), {mod.STUDY + 'index.html', mod.STUDY + 'en.html', *originals})
        for name in ('index.html', 'index.en.html'):
            before = originals[name].decode('utf-8')
            after = plan[name]
            self.assertEqual(publication.LATEST_SECTION.sub('', before), publication.LATEST_SECTION.sub('', after))
            self.assertEqual(before.count('data-mechanism '), 4)
            self.assertEqual(after.count('data-mechanism '), 4)
            self.assertIn(mod.DATA_FILE, after)
            self.assertEqual((ROOT / name).read_bytes(), originals[name])
        self.assertEqual(publication.integrate_readme(plan['README.md'], self.d), plan['README.md'])
        self.assertEqual(publication.integrate_sitemap(plan['sitemap.xml'], self.d), plan['sitemap.xml'])
        for name in ('README.md', 'sitemap.xml'):
            self.assertEqual((ROOT / name).read_bytes(), originals[name])
        for url in (mod.BASE + mod.STUDY, mod.BASE + mod.STUDY + 'en.html'):
            self.assertEqual(plan['sitemap.xml'].count('<loc>' + url + '</loc>'), 1)

    def test_listing_uses_actual_input_metrics_and_retains_all_four_previous_cards(self):
        pages_spec = importlib.util.spec_from_file_location('adoption_listing_test', ROOT / 'tools/build_pages.py')
        pages = importlib.util.module_from_spec(pages_spec)
        pages_spec.loader.exec_module(pages)
        before, after = publication._comparison(self.d)
        for lang in ('ja', 'en'):
            with patch.object(pages, 'ADOPTION_D', None), patch.object(pages, 'WORKING_D', None), patch.object(pages, 'ACTION_D', None), patch.object(pages, 'CONDITIONAL_D', None), patch.object(pages, 'EXPERIENCE_D', None), patch.object(pages, 'TOOL_D', None), patch.object(pages, 'DELAYED_D', None):
                original = pages.landing(lang)
            updated = publication.integrate_listing(original, lang, self.d)
            parsed = Page(updated)
            text = ''.join(parsed.text)
            self.assertEqual(updated.count('class="study-card"'), 5)
            self.assertIn(mod.STUDY, updated)
            for dated in ('2026-10-13-shiori-pilot', '2026-10-21-cross-session',
                          '2026-10-21-retrieval-hypotheses', '2026-10-22-event-compatibility'):
                self.assertIn('studies/' + dated, updated)
            for metric, denominator in [('correct_supported', 16), ('correct_abstention', 16), ('wrong_or_unsupported', 32)]:
                self.assertIn(f'{before[metric]}/{denominator} → {after[metric]}/{denominator}', text)
            self.assertIn('95', text)
            self.assertEqual(len(parsed.ids), len(set(parsed.ids)))


@unittest.skipUnless((ROOT / mod.DATA_FILE).is_file(), 'Audited public export has not been supplied')
class EventAdoptionActualData(unittest.TestCase):
    def test_actual_data_validates_and_both_committed_pages_match_the_builder(self):
        data = mod.load_summary()
        for lang, name in [('ja', 'index.html'), ('en', 'en.html')]:
            expected = mod.render(lang, data)
            self.assertEqual((ROOT / mod.STUDY / name).read_text(encoding='utf-8'), expected)

    def test_actual_publication_home_readme_sitemap_and_latest_listing_match(self):
        data = mod.load_summary()
        if not (ROOT / 'data/working-memory-source-fixed-2026-10-24.json').is_file():
            expected = publication.prepare_updates(ROOT, data)
            for name in ('index.html', 'index.en.html', 'README.md', 'sitemap.xml'):
                self.assertEqual((ROOT / name).read_text(encoding='utf-8'), expected[name])
        else:
            # A later study owns latest metadata; retain this historical block
            # and both dated URLs while its own tests verify current metadata.
            readme = (ROOT / 'README.md').read_text(encoding='utf-8')
            expected = publication.integrate_readme(readme, data)
            for text in (readme, expected):
                self.assertIn(publication.README_START, text)
                self.assertIn(publication.README_END, text)
            self.assertEqual(readme.split(publication.README_START)[1].split(publication.README_END)[0],
                             expected.split(publication.README_START)[1].split(publication.README_END)[0])
            sitemap = (ROOT / 'sitemap.xml').read_text(encoding='utf-8')
            for url in (mod.BASE + mod.STUDY, mod.BASE + mod.STUDY + 'en.html'):
                self.assertEqual(sitemap.count('<loc>' + url + '</loc>'), 1)
        for name in ('results.html', 'results.en.html'):
            self.assertIn(mod.STUDY, (ROOT / name).read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()

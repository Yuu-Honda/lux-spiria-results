"""Public-site engineering fixtures are artificial and never public results.

Fixtures stay in memory or temporary directories. Actual publication checks are
skipped until the independently audited public export and replay are supplied.
"""
import copy
import hashlib
from html.parser import HTMLParser
import importlib.util
import io
import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


mod = module('action_feedback_engineering', 'tools/build_action_feedback.py')
pub = module('action_feedback_publication_engineering', 'tools/action_feedback_publication.py')
PRESERVED_SIXTH = {
    'data/working-memory-source-fixed-2026-10-24.json': 'a7ce1a4553cd7b85f0780bf9f178c6940c2300461caaa90ade6025736f80a8b6',
    'studies/2026-10-24-working-memory/index.html': '48fbaf0aed7efc98c857155d3a7a960729e386f5539d3b41d52004ab51d0e01c',
    'studies/2026-10-24-working-memory/en.html': '9151e978e328e92fd1841d6d89997f27b13c1674998a81f302d29e647fdca2f0',
}


def replay_fixture_bytes():
    readme = b'Artificial engineering replay fixture. Not a study.\n'
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w') as archive:
        archive.writestr('README.md', readme)
    return readme, output.getvalue()


def refresh_aggregates(d):
    d.update(mod.recalculate(d['items']))
    for arm, row in d.get('costs', {}).items():
        items = [item for item in d['items'] if item['arm'] == arm]
        row.update(actions=len(items), contexts=1,
                   canonical_output_characters=sum(item['canonical_output_characters'] for item in items),
                   maximum_output_characters=max(item['canonical_output_characters'] for item in items),
                   output_cap_violations=sum(item['canonical_output_characters'] > 6000 for item in items))
    return d


def artificial_fixture():
    d = {'schema_version': 1, 'study_id': 'action-feedback-2026-10-27', 'date': '2026-10-27',
         'sample': dict(mod.SAMPLE),
         'design': {**mod.DESIGN_COUNTS, 'practice_task_order': list(mod.PRACTICE),
                    'later_task_order': list(mod.LATER_ORDER), 'arm_dispatch_order': list(mod.DISPATCH_ORDER),
                    'repeat_mapping': {'R01': 'P01', 'R02': 'P03', 'R03': 'P05'}},
         'sources': copy.deepcopy(mod.SOURCE_FILES),
         'provenance': {key: 'a' * 64 for key in mod.PROVENANCE},
         'method': {**{key: True for key in mod.METHOD_TRUE}, **{key: False for key in mod.METHOD_FALSE}},
         'limits': {key: False for key in mod.LIMITS_FALSE},
         'provider': {key: None for key in mod.PROVIDER_FIELDS}, 'items': [], 'costs': {},
         'memory': {'entries': 6, 'confirmations': 2, 'revisions': 2, 'deferred': 2,
                    'canonical_characters': 1000, 'cap_violations': 0, 'sha256': 'a' * 64},
         'verification': {**{key: True for key in mod.VERIFICATION_FLAGS}, **mod.VERIFICATION_COUNTS,
                          'controller_code_checks': 20, 'controller_code_passed': 20},
         'replay': {}}
    for arm_index, arm in enumerate(('practice', *mod.ARMS)):
        tasks = mod.PRACTICE if arm == 'practice' else mod.LATER_ORDER
        for index, task in enumerate(tasks):
            number = int(task[1:])
            repeated = task.startswith('R')
            supported = repeated or number % 2 == 1
            source = f'D{number if repeated else (number + 1) // 2:02d}'
            schema = (index + arm_index) % 13 == 12
            execution = not schema and (index + arm_index) % 11 == 10
            written = not (schema or execution)
            accepted = written and (index + arm_index) % 4 != 0
            artifact_status = 'none' if not written else 'artifact' if supported or not accepted else 'source_unavailable'
            token = f'artificial-engineering-{arm}-{task}'.encode()
            d['items'].append({'arm': arm, 'task_id': task, 'source': source, 'supported': supported,
                'artifact_status': artifact_status, 'validator_accepted': accepted,
                'execution_failure': execution, 'schema_error': schema, 'artifact_written': written,
                'prediction': ('accepted', 'rejected', 'uncertain')[(index + arm_index) % 3],
                'canonical_output_characters': 100 + 10 * index + arm_index,
                'action_sha256': hashlib.sha256(token).hexdigest(),
                'artifact_sha256': hashlib.sha256(token + b'artifact').hexdigest() if written else None})
        d['costs'][arm] = {**{key: 0 for key in mod.COST_FIELDS},
                           'input_packet_characters': 1000 * (arm_index + 1),
                           'raw_output_characters': 3000 + arm_index}
    readme, archive = replay_fixture_bytes()
    d['replay'] = {'readme_sha256': hashlib.sha256(readme).hexdigest(), 'zip_sha256': hashlib.sha256(archive).hexdigest()}
    # Preserve exact bytes for temporary replay setup rather than reserializing
    # a ZIP whose embedded timestamp can differ. This is never a public export.
    return refresh_aggregates(d), readme, archive


def temporary_inputs(root, d, readme, archive):
    for source in d['sources'].values():
        path = root / source['public_path']
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / source['public_path']).read_bytes())
    (root / mod.REPLAY).mkdir(parents=True)
    (root / mod.REPLAY / 'README.md').write_bytes(readme)
    (root / mod.ZIP_FILE).parent.mkdir(parents=True, exist_ok=True)
    (root / mod.ZIP_FILE).write_bytes(archive)


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__(); self.ids = []; self.refs = []; self.lang = None; self.captions = 0
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        if tag == 'html':
            self.lang = attrs.get('lang')
        if tag == 'caption':
            self.captions += 1
        for key in ('href', 'src'):
            if attrs.get(key):
                self.refs.append(attrs[key])


class ActionFeedbackEngineering(unittest.TestCase):
    def setUp(self):
        self.d, self.readme, self.archive = artificial_fixture()

    def test_artificial_full_contract_and_all_recalculations_only_in_memory(self):
        self.assertIs(mod.validate_summary(self.d), self.d)
        self.assertEqual(len(self.d['items']), 33)
        self.assertEqual(self.d['practice']['actions'], 6)
        for arm in mod.ARMS:
            self.assertEqual(self.d['arms'][arm]['all']['actions'], 9)
            self.assertEqual(self.d['arms'][arm]['transfer']['supported'], 3)
            self.assertEqual(self.d['arms'][arm]['repeat']['supported'], 3)

    def test_absent_export_never_writes_or_requires_replay(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.assertEqual(pub.prepare_updates(root), {})
            with patch.object(mod, 'ROOT', root), self.assertRaises(FileNotFoundError):
                mod.build()
            self.assertEqual(list(root.iterdir()), [])
        for function, args in [(pub.integrate_home, ('same', 'ja', None)),
                               (pub.integrate_listing, ('same', 'en', None)),
                               (pub.integrate_readme, ('same', None)),
                               (pub.integrate_sitemap, ('same', None))]:
            self.assertEqual(function(*args), 'same')

    def test_invalid_and_duplicate_json_refuse_writes(self):
        for text in ('{}', json.dumps(self.d).replace('"schema_version": 1', '"schema_version":"PRIVATE_SENTINEL","schema_version":1', 1)):
            with self.subTest(text=text[:30]), TemporaryDirectory() as temporary:
                root = Path(temporary); export = root / mod.DATA_FILE; export.parent.mkdir()
                export.write_text(text, encoding='utf-8')
                before = export.read_bytes()
                with patch.object(mod, 'ROOT', root), self.assertRaises(ValueError):
                    mod.build()
                with self.assertRaises(ValueError):
                    pub.prepare_updates(root)
                self.assertEqual(export.read_bytes(), before)
                self.assertFalse((root / mod.STUDY).exists())

    def test_recursive_unknown_fields_rejected_at_every_dictionary(self):
        paths = []
        def visit(value, path=()):
            if isinstance(value, dict):
                paths.append(path)
                for key, child in value.items(): visit(child, path + (key,))
            elif isinstance(value, list):
                for index, child in enumerate(value): visit(child, path + (index,))
        visit(self.d)
        for path in paths:
            corrupt = copy.deepcopy(self.d); node = corrupt
            for key in path: node = node[key]
            node['private_source_text'] = 'PRIVATE_SENTINEL'
            with self.subTest(path=path), self.assertRaises(ValueError): mod.validate_summary(corrupt)

    def test_nonallowlisted_strings_rejected_at_every_leaf(self):
        paths = []
        def visit(value, path=()):
            if isinstance(value, dict):
                for key, child in value.items(): visit(child, path + (key,))
            elif isinstance(value, list):
                for index, child in enumerate(value): visit(child, path + (index,))
            else: paths.append(path)
        visit(self.d)
        for path in paths:
            corrupt = copy.deepcopy(self.d); node = corrupt
            for key in path[:-1]: node = node[key]
            node[path[-1]] = 'PRIVATE_SENTINEL'
            with self.subTest(path=path), self.assertRaises(ValueError): mod.validate_summary(corrupt)

    def test_source_alias_path_and_raw_sha_freeze(self):
        for change in ('swap', 'substitute', 'hash'):
            corrupt = copy.deepcopy(self.d)
            if change == 'swap':
                corrupt['sources']['D01'], corrupt['sources']['D02'] = corrupt['sources']['D02'], corrupt['sources']['D01']
            elif change == 'substitute':
                corrupt['sources']['D03']['public_path'] = 'data/shiori-retrieval-hypotheses-2026-10-21.json'
            else:
                corrupt['sources']['D03']['sha256'] = '0' * 64
            with self.subTest(change=change), self.assertRaises(ValueError): mod.validate_summary(corrupt)

    def test_real_runner_failure_and_write_branches_are_exclusive(self):
        corruptions = [dict(validator_accepted=False, schema_error=True, execution_failure=True),
                       dict(validator_accepted=False, schema_error=True, execution_failure=False),
                       dict(validator_accepted=False, artifact_status='none'),
                       dict(validator_accepted=False, artifact_written=False, artifact_sha256=None)]
        for changes in corruptions:
            corrupt = copy.deepcopy(self.d); corrupt['items'][1].update(changes); refresh_aggregates(corrupt)
            with self.subTest(changes=changes), self.assertRaises(ValueError): mod.validate_summary(corrupt)
        for error in ('schema_error', 'execution_failure'):
            valid = copy.deepcopy(self.d)
            valid['items'][1].update(validator_accepted=False, artifact_status='none', artifact_written=False,
                                    artifact_sha256=None, schema_error=error == 'schema_error',
                                    execution_failure=error == 'execution_failure')
            self.assertIs(mod.validate_summary(refresh_aggregates(valid)), valid)

    def test_accepted_artifact_must_match_support_and_have_no_errors(self):
        for changes in (dict(artifact_status='artifact'), dict(artifact_written=False, artifact_sha256=None), dict(schema_error=True)):
            corrupt = copy.deepcopy(self.d)
            item = next(item for item in corrupt['items'] if not item['supported'] and item['validator_accepted'])
            item.update(changes); refresh_aggregates(corrupt)
            with self.subTest(changes=changes), self.assertRaises(ValueError): mod.validate_summary(corrupt)

    def test_all33_bindings_and_fixed_orders_are_required(self):
        for field in ('practice_task_order', 'later_task_order', 'arm_dispatch_order'):
            corrupt = copy.deepcopy(self.d); corrupt['design'][field].reverse()
            with self.subTest(field=field), self.assertRaises(ValueError): mod.validate_summary(corrupt)
        corrupt = copy.deepcopy(self.d); corrupt['items'][-1] = copy.deepcopy(corrupt['items'][-2])
        with self.assertRaises(ValueError): mod.validate_summary(corrupt)
        corrupt = copy.deepcopy(self.d); corrupt['items'].pop()
        with self.assertRaises(ValueError): mod.validate_summary(corrupt)

    def test_source_support_and_repeat_objectives_remain_bound_between_arms(self):
        for field, value in [('source', 'D03'), ('supported', False)]:
            corrupt = copy.deepcopy(self.d); corrupt['items'][6][field] = value; refresh_aggregates(corrupt)
            with self.subTest(field=field), self.assertRaises(ValueError): mod.validate_summary(corrupt)
        corrupt = copy.deepcopy(self.d); corrupt['design']['repeat_mapping']['R01'] = 'P02'
        with self.assertRaises(ValueError): mod.validate_summary(corrupt)

    def test_every_aggregate_and_paired_count_is_recalculated_from_items(self):
        for section in ('practice', 'arms', 'paired'):
            paths = []
            def visit(value, path):
                for key, child in value.items():
                    if isinstance(child, dict): visit(child, path + (key,))
                    else: paths.append(path + (key,))
            visit(self.d[section], (section,))
            for path in paths:
                corrupt = copy.deepcopy(self.d); node = corrupt
                for key in path[:-1]: node = node[key]
                node[path[-1]] += 1
                with self.subTest(path=path), self.assertRaises(ValueError): mod.validate_summary(corrupt)

    def test_costs_match_actual_peritem_characters_without_equal_input_assumption(self):
        for field in ('canonical_output_characters', 'maximum_output_characters', 'output_cap_violations', 'actions', 'contexts'):
            corrupt = copy.deepcopy(self.d); corrupt['costs']['raw_feedback'][field] += 1
            with self.subTest(field=field), self.assertRaises(ValueError): mod.validate_summary(corrupt)
        self.assertNotEqual(self.d['costs']['raw_feedback']['input_packet_characters'], self.d['costs']['raw_feedback_and_review']['input_packet_characters'])
        for key in mod.PROVIDER_FIELDS:
            corrupt = copy.deepcopy(self.d); corrupt['provider'][key] = 0
            with self.subTest(key=key), self.assertRaises(ValueError): mod.validate_summary(corrupt)

    def test_action_overrun_is_reported_without_changing_artifact_correctness(self):
        item = next(item for item in self.d['items'] if item['validator_accepted'])
        accepted = item['validator_accepted']; item['canonical_output_characters'] = 6001
        refresh_aggregates(self.d)
        self.assertIs(mod.validate_summary(self.d), self.d)
        self.assertEqual(item['validator_accepted'], accepted)
        self.assertEqual(self.d['costs'][item['arm']]['output_cap_violations'], 1)

    def test_review_partition_cap_digest_and_final_audits_fail_closed(self):
        for field, value in [('entries', 7), ('confirmations', 7), ('cap_violations', 1), ('sha256', 'b' * 64)]:
            corrupt = copy.deepcopy(self.d); corrupt['memory'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): mod.validate_summary(corrupt)
        self.d['memory'].update(canonical_characters=6001, cap_violations=1)
        self.assertIs(mod.validate_summary(self.d), self.d)
        for field in mod.VERIFICATION_FLAGS:
            corrupt = copy.deepcopy(self.d); corrupt['verification'][field] = False
            with self.subTest(field=field), self.assertRaises(ValueError): mod.validate_summary(corrupt)

    def test_missing_changed_replay_or_source_refuses_before_any_publication_write(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary); temporary_inputs(root, self.d, self.readme, self.archive)
            mod.require_public_inputs(root, self.d)
            for relative in (mod.REPLAY + 'README.md', mod.ZIP_FILE, self.d['sources']['D01']['public_path']):
                path = root / relative; original = path.read_bytes(); path.write_bytes(original + b'changed')
                with self.subTest(relative=relative), self.assertRaises(ValueError): pub.prepare_updates(root, self.d)
                self.assertFalse((root / mod.STUDY).exists()); path.write_bytes(original)

    def test_valid_artificial_build_writes_only_in_temporary_directory(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary); temporary_inputs(root, self.d, self.readme, self.archive)
            (root / mod.DATA_FILE).write_text(json.dumps(self.d), encoding='utf-8')
            with patch.object(mod, 'ROOT', root): pages = mod.build()
            self.assertEqual(set(pages), {'index.html', 'en.html'})
            self.assertEqual(set(path.name for path in (root / mod.STUDY).iterdir()), {'index.html', 'en.html'})

    def test_artificial_bilingual_render_has_semantic_flow_all_rows_and_limits(self):
        for lang in ('ja', 'en'):
            text = mod.render(lang, self.d); page = Page(text)
            self.assertEqual(page.lang, lang); self.assertEqual(len(page.ids), len(set(page.ids)))
            self.assertIn('../../assets/lux-symbol.png', page.refs)
            self.assertIn('../../' + mod.REPLAY + 'README.md', page.refs)
            self.assertIn('../../' + mod.ZIP_FILE, page.refs)
            self.assertGreater(page.captions, 8); self.assertNotIn('<script', text)
            self.assertNotIn('PRIVATE_SENTINEL', text)
            self.assertNotIn('重なりうる', text)
            self.assertNotIn('potentially overlapping', text)
            self.assertNotIn('may overlap', text)
        text = mod.render('en', self.d)
        for expected in ('All 33 retained actual rows', 'no counterbalancing', 'do not mean unseen files',
                         'not 33 provider requests', 'fresh AI generation', 'parameter update', 'remain null'):
            self.assertTrue(expected in text, expected)

    def test_findings_are_conditional_and_do_not_invent_a_practice_failure(self):
        self.assertNotIn('adding the review did not change', mod.finding(self.d, 'en'))
        for item in self.d['items']:
            item.update(validator_accepted=True, schema_error=False, execution_failure=False,
                        artifact_written=True, artifact_sha256='c' * 64,
                        artifact_status='artifact' if item['supported'] else 'source_unavailable')
        refresh_aggregates(self.d); mod.validate_summary(self.d)
        finding = mod.finding(self.d, 'en')
        self.assertIn('adding the review did not change', finding)
        self.assertIn('correction of practice errors could not be tested', finding)
        self.assertIn('ceiling on these engineered tasks', finding)

    def test_home_plan_changes_only_latest_panel_and_preserves_four_stories(self):
        for name, lang in [('index.html', 'ja'), ('index.en.html', 'en')]:
            before = (ROOT / name).read_text(encoding='utf-8'); after = pub.integrate_home(before, lang, self.d)
            self.assertEqual(pub.LATEST.sub('', before), pub.LATEST.sub('', after))
            self.assertEqual(after.count('data-mechanism '), 4)
            self.assertEqual(pub.integrate_home(after, lang, self.d), after)

    def test_listing_keeps_all_six_prior_cards_and_adds_public_scope_exception(self):
        for name, lang in [('results.html', 'ja'), ('results.en.html', 'en')]:
            before = pub.CARD.sub('', (ROOT / name).read_text(encoding='utf-8'))
            cards = re.findall(r'<article class="study-card".*?</article>', before, re.S)
            self.assertEqual(len(cards), 6)
            after = pub.integrate_listing(before, lang, self.d)
            self.assertEqual(after.count('<article class="study-card"'), 7)
            for card in cards: self.assertIn(card, after)
            self.assertEqual(pub.integrate_listing(after, lang, self.d), after)
            self.assertIn(mod.REPLAY + 'README.md', after)
            expected = '公開データ作業台は例外' if lang == 'ja' else 'public-data workbench is an exception'
            self.assertIn(expected, after)

    def test_readme_sitemap_are_idempotent_and_historical_blocks_unchanged(self):
        before = (ROOT / 'README.md').read_text(encoding='utf-8'); after = pub.integrate_readme(before, self.d)
        self.assertEqual(pub.integrate_readme(after, self.d), after)
        for start, end in [('<!-- WORKING_MEMORY_STUDY_START -->', '<!-- WORKING_MEMORY_STUDY_END -->'),
                           ('<!-- EVENT_ADOPTION_STUDY_START -->', '<!-- EVENT_ADOPTION_STUDY_END -->')]:
            self.assertIn(before.split(start)[1].split(end)[0], after)
        before = (ROOT / 'sitemap.xml').read_text(encoding='utf-8'); after = pub.integrate_sitemap(before, self.d)
        self.assertEqual(pub.integrate_sitemap(after, self.d), after)
        for line in before.splitlines():
            if '<loc>' in line: self.assertIn(line, after)

    def test_complete_publication_plan_is_side_effect_free(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary); temporary_inputs(root, self.d, self.readme, self.archive)
            for name in ('index.html', 'index.en.html', 'README.md', 'sitemap.xml'):
                (root / name).write_bytes((ROOT / name).read_bytes())
            before = {str(path.relative_to(root)): path.read_bytes() for path in root.rglob('*') if path.is_file()}
            plan = pub.prepare_updates(root, self.d)
            self.assertEqual(set(plan), {mod.STUDY + 'index.html', mod.STUDY + 'en.html', 'index.html', 'index.en.html', 'README.md', 'sitemap.xml'})
            self.assertEqual(before, {str(path.relative_to(root)): path.read_bytes() for path in root.rglob('*') if path.is_file()})

    def test_download_zip_is_outside_the_manifest_covered_replay_directory(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary); temporary_inputs(root, self.d, self.readme, self.archive)
            mod.require_public_inputs(root, self.d)
            bundle = (root / mod.REPLAY).resolve(); archive = (root / mod.ZIP_FILE).resolve()
            self.assertNotIn(bundle, archive.parents)
            self.assertEqual({path.name for path in bundle.iterdir()}, {'README.md'})
            self.assertFalse((bundle / 'replay.zip').exists())
            self.assertTrue(archive.is_file())
        for lang in ('ja', 'en'):
            page = Page(mod.render(lang, self.d))
            self.assertIn('../../' + mod.ZIP_FILE, page.refs)
            self.assertNotIn('../../' + mod.REPLAY + 'replay.zip', page.refs)

    def test_sixth_study_and_data_preserved_with_earlier_five_guarded_by_prior_tests(self):
        for name, digest in PRESERVED_SIXTH.items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), digest, name)

    def test_actual_export_and_publication_when_supplied(self):
        if not (ROOT / mod.DATA_FILE).is_file():
            self.skipTest('Actual audited export and public replay are not supplied')
        d = mod.load_summary(); mod.require_public_inputs(ROOT, d)
        for name, expected in pub.prepare_updates(ROOT, d).items():
            self.assertEqual((ROOT / name).read_text(encoding='utf-8'), expected)
        pages = module('action_actual_main', 'tools/build_pages.py')
        for name, lang in [('results.html', 'ja'), ('results.en.html', 'en')]:
            self.assertEqual((ROOT / name).read_text(encoding='utf-8'), pages.landing(lang) + '\n')


if __name__ == '__main__':
    unittest.main()

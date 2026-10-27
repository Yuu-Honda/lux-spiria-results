"""Engineering tests use artificial in-memory fixtures, never public outcomes.

Only temporary directories may receive synthetic HTML/JSON. Actual result checks
run only after a real independently audited public export exists.
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

ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


mod = module('working_memory_engineering', 'tools/build_working_memory.py')
pub = module('working_memory_publication_engineering', 'tools/working_memory_publication.py')
PRESERVED = {
    'data/shiori-cross-session-2026-10-21.json': '09f075d9f84bfb336912946b6f268056e2c0b1b8fd6ca8e58eb28d3d1ab34c99',
    'data/shiori-event-adoption-2026-10-24.json': 'fc7bfaed1b721a8d6fb95609b8edaa74c8cce1a9d10a238cf4b85083fededffe',
    'data/shiori-event-compatibility-2026-10-22.json': 'da314ce28940785dac7b097f07ab028b378757f1af6efbfe32d7867be3c3c2bd',
    'data/shiori-pilot-2026-10-13.json': '5f1a09df554ac6a57b0ead347ae4f3bbd4ec9ed4866fc44e96f82926194f21c7',
    'data/shiori-retrieval-hypotheses-2026-10-21.json': '54c09696c06e5ddcc0031d73663fc4d46e82d3b79e8aa4223d15449d4edd7680',
    'studies/2026-10-13-shiori-pilot/en.html': '1a4aef0f75524e73200641f59826d3cdabb88a001f6fcccb8f61599313044b77',
    'studies/2026-10-13-shiori-pilot/index.html': '64ae9b3dadc4eb659031c3d43622920e111acddcd9588d4de92d55e838c1eb09',
    'studies/2026-10-21-cross-session/en.html': 'dec228d307488278563ae25ff8f049e6507bd110bf1282698b24ef2842935862',
    'studies/2026-10-21-cross-session/index.html': 'ee8b03d898021d4eaf99617e583003473f3d56a1e20fd71086e8e035beb2540e',
    'studies/2026-10-21-retrieval-hypotheses/en.html': 'bd816448fb20b690c8e390bcd9eebb34b5a70afe62fde68230d4aec31a6643dd',
    'studies/2026-10-21-retrieval-hypotheses/index.html': '5b3aa38dcf92ba6506700fb78d078a31f15dabbef890f9febdc49da8d856ac93',
    'studies/2026-10-22-event-compatibility/en.html': '4dcda4b37cd051e35c44f7fd0707421b416a179fc696ba2b1d3259417f75844a',
    'studies/2026-10-22-event-compatibility/index.html': 'a2e312d96b2127e635a9460d03b691afe137c8b9813999081270921810339e63',
    'studies/2026-10-24-event-adoption/en.html': '243395d7daf6674dcf42e0c8e4251409853b5d84d7344417302b0703bbac6cdb',
    'studies/2026-10-24-event-adoption/index.html': '7ffe5931d04348da413a8087d8b25d34e73d00d51e884b2abc00d1d9552d4103',
}


def artificial_fixture():
    """Artificial outcomes are assembled only for validator/rendering checks."""
    d = {'schema_version': 1, 'study_id': 'working-memory-source-fixed-2026-10-24',
         'date': '2026-10-24', 'sample': dict(mod.SAMPLE), 'design': dict(mod.DESIGN),
         'provenance': {key: 'a' * 64 for key in mod.PROVENANCE},
         'method': {**{key: True for key in mod.METHOD_TRUE}, **{key: False for key in mod.METHOD_FALSE}},
         'limits': {key: False for key in mod.LIMITS_FALSE}, 'cohorts': {}, 'costs': {},
         'verification': {'independent_audit_verified': True, 'code_engineering_checks': 7,
                          'code_engineering_passed': 7, 'synthetic_procedure_checks': 0,
                          'synthetic_procedure_passed': 0}}

    def counts(items):
        return {key: sum(item[key] for item in items) for key in mod.METRICS}

    for cohort, (total, positive, _) in mod.COHORTS.items():
        part = {'conditions': {}, 'paired': {}}
        items_by_condition = {}
        for condition_index, condition in enumerate(mod.CONDITIONS):
            items = []
            for index in range(total):
                supported = index < positive
                if supported:
                    outcome = ('correct_supported', 'partial_supported', 'missed_answer', 'wrong_or_unsupported')[(index + condition_index) % 4]
                else:
                    outcome = 'correct_abstention' if (index + condition_index) % 3 else 'wrong_or_unsupported'
                item = {key: 0 for key in mod.METRICS}
                item.update(queries=1, **{outcome: 1})
                wrong = outcome == 'wrong_or_unsupported'
                item.update(binding_errors=int(wrong and index % 2 == 0),
                            proposal_completion_errors=int(wrong and index % 3 == 0),
                            unsupported_claim_items=int(wrong),
                            mechanical_evidence_error_items=int(supported and outcome != 'correct_supported' and index % 2 == 0))
                items.append(item)
            items_by_condition[condition] = items
            part['conditions'][condition] = {'metrics': counts(items),
                'support_strata': {'supported': counts(items[:positive]), 'unsupported': counts(items[positive:])}}
        complete = {'correct_supported', 'correct_abstention'}
        for pair, (before, after) in mod.PAIRS.items():
            matrix = {a: {b: 0 for b in mod.OUTCOMES} for a in mod.OUTCOMES}
            for first, final in zip(items_by_condition[before], items_by_condition[after]):
                a = next(key for key in mod.OUTCOMES if first[key])
                b = next(key for key in mod.OUTCOMES if final[key])
                matrix[a][b] += 1
            part['paired'][pair] = {'matrix': matrix,
                'corrected': sum(matrix[a][b] for a in mod.OUTCOMES for b in mod.OUTCOMES if a not in complete and b in complete),
                'regressed': sum(matrix[a][b] for a in mod.OUTCOMES for b in mod.OUTCOMES if a in complete and b not in complete)}
        d['cohorts'][cohort] = part
    for key, (records, contexts, _) in mod.COST_DESIGN.items():
        row = {field: 0 for field in mod.COST_FIELDS}
        row.update(records=records, contexts=contexts,
                   emitted_payload_characters=records * 100, maximum_payload_characters=100)
        if key.endswith(':final'):
            row.update(answer_characters=records * 40, maximum_answer_characters=40)
        d['costs'][key] = row
    return d


def artificial_cohort_from_triples(triples, supported):
    """Create three consistent margins from artificial paired item outcomes."""
    result = {'conditions': {}, 'paired': {}}
    def counts(values):
        row = {key: 0 for key in mod.METRICS}
        row['queries'] = len(values)
        for outcome in values:
            row[outcome] += 1
        return row
    for index, condition in enumerate(mod.CONDITIONS):
        values = [triple[index] for triple in triples]
        result['conditions'][condition] = {'metrics': counts(values), 'support_strata': {
            'supported': counts(values[:supported]), 'unsupported': counts(values[supported:])}}
    complete = {'correct_supported', 'correct_abstention'}
    for pair, (before, after) in mod.PAIRS.items():
        first, second = mod.CONDITIONS.index(before), mod.CONDITIONS.index(after)
        matrix = {a: {b: 0 for b in mod.OUTCOMES} for a in mod.OUTCOMES}
        for triple in triples:
            matrix[triple[first]][triple[second]] += 1
        result['paired'][pair] = {'matrix': matrix,
            'corrected': sum(matrix[a][b] for a in mod.OUTCOMES for b in mod.OUTCOMES if a not in complete and b in complete),
            'regressed': sum(matrix[a][b] for a in mod.OUTCOMES for b in mod.OUTCOMES if a in complete and b not in complete)}
    return result


class Page(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.ids, self.links, self.canonicals, self.languages, self.captions = [], [], [], [], 0
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if 'id' in a:
            self.ids.append(a['id'])
        if tag == 'html':
            self.languages.append(a.get('lang'))
        if tag == 'link' and a.get('rel') == 'canonical':
            self.canonicals.append(a.get('href'))
        for key in ('href', 'src'):
            if key in a:
                self.links.append(a[key])
        if tag == 'caption':
            self.captions += 1


class WorkingMemoryEngineering(unittest.TestCase):
    def setUp(self):
        self.d = artificial_fixture()

    def test_full_artificial_contract_validates_only_in_memory(self):
        self.assertIs(mod.validate_summary(self.d), self.d)
        self.assertEqual(sum(row['records'] for row in self.d['costs'].values()), 140)
        self.assertEqual(sum(row['contexts'] for row in self.d['costs'].values()), 12)

    def test_missing_export_refuses_all_writes(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(mod, 'ROOT', root):
                with self.assertRaises(FileNotFoundError):
                    mod.build()
            self.assertEqual(pub.prepare_updates(root), {})
            self.assertEqual(list(root.iterdir()), [])

    def test_existing_invalid_export_refuses_standalone_and_publication_writes(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            export = root / mod.DATA_FILE
            export.parent.mkdir()
            export.write_text('{}', encoding='utf-8')
            snapshot = {path.relative_to(root): path.read_bytes() for path in root.rglob('*') if path.is_file()}
            with patch.object(mod, 'ROOT', root):
                with self.assertRaises(ValueError):
                    mod.build()
            with self.assertRaises(ValueError):
                pub.prepare_updates(root)
            self.assertEqual(snapshot, {path.relative_to(root): path.read_bytes() for path in root.rglob('*') if path.is_file()})
            self.assertFalse((root / mod.STUDY).exists())

    def test_duplicate_json_fields_cannot_hide_a_private_string(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            export = root / mod.DATA_FILE
            export.parent.mkdir()
            text = json.dumps(self.d).replace('"schema_version": 1', '"schema_version": "PRIVATE_SENTINEL", "schema_version": 1', 1)
            export.write_text(text, encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Duplicate public JSON'):
                mod.load_summary(root)
            with self.assertRaises(ValueError):
                pub.prepare_updates(root)
            self.assertFalse((root / mod.STUDY).exists())

    def test_recursive_unknown_fields_rejected_at_every_dictionary(self):
        paths = []
        def visit(value, path=()):
            if isinstance(value, dict):
                paths.append(path)
                for key, child in value.items():
                    visit(child, path + (key,))
        visit(self.d)
        for path in paths:
            corrupt = copy.deepcopy(self.d)
            node = corrupt
            for key in path:
                node = node[key]
            node['source_text'] = 'PRIVATE_SENTINEL'
            with self.subTest(path=path), self.assertRaises(ValueError):
                mod.validate_summary(corrupt)

    def test_nonallowlisted_string_and_boolean_substitution_rejected_at_every_leaf(self):
        paths = []
        def visit(value, path=()):
            if isinstance(value, dict):
                for key, child in value.items():
                    visit(child, path + (key,))
            else:
                paths.append(path)
        visit(self.d)
        for path in paths:
            corrupt = copy.deepcopy(self.d)
            node = corrupt
            for key in path[:-1]:
                node = node[key]
            node[path[-1]] = 'PRIVATE_SENTINEL'
            with self.subTest(path=path), self.assertRaises(ValueError):
                mod.validate_summary(corrupt)
        for field in mod.SAMPLE:
            corrupt = copy.deepcopy(self.d)
            corrupt['sample'][field] = True
            with self.subTest(field=field), self.assertRaises(ValueError):
                mod.validate_summary(corrupt)

    def test_frozen_denominators_and_actual_role_design_cannot_change(self):
        for category in ('sample', 'design'):
            for field in self.d[category]:
                corrupt = copy.deepcopy(self.d)
                corrupt[category][field] += 1
                with self.subTest(category=category, field=field), self.assertRaises(ValueError):
                    mod.validate_summary(corrupt)

    def test_every_support_partition_metric_recalculates_condition(self):
        for cohort in mod.COHORTS:
            for condition in mod.CONDITIONS:
                for metric in mod.METRICS:
                    corrupt = copy.deepcopy(self.d)
                    corrupt['cohorts'][cohort]['conditions'][condition]['support_strata']['supported'][metric] += 1
                    with self.subTest(cohort=cohort, condition=condition, metric=metric), self.assertRaises(ValueError):
                        mod.validate_summary(corrupt)

    def test_every_paired_cell_and_corrected_regressed_count_reconciles(self):
        for cohort in mod.COHORTS:
            for pair in mod.PAIRS:
                for source in mod.OUTCOMES:
                    for target in mod.OUTCOMES:
                        corrupt = copy.deepcopy(self.d)
                        corrupt['cohorts'][cohort]['paired'][pair]['matrix'][source][target] += 1
                        with self.subTest(cohort=cohort, pair=pair, source=source, target=target), self.assertRaises(ValueError):
                            mod.validate_summary(corrupt)
                for field in ('corrected', 'regressed'):
                    corrupt = copy.deepcopy(self.d)
                    corrupt['cohorts'][cohort]['paired'][pair][field] += 1
                    with self.subTest(cohort=cohort, pair=pair, field=field), self.assertRaises(ValueError):
                        mod.validate_summary(corrupt)

    def test_three_pair_tables_must_be_simultaneously_integer_realizable(self):
        correct, partial, abstain = 'correct_supported', 'partial_supported', 'correct_abstention'
        part = artificial_cohort_from_triples([(correct,) * 3] * 3 + [(partial,) * 3] * 3 + [(abstain,) * 3] * 6, 6)
        # Both adjacent comparisons say every outcome is unchanged. The third
        # comparison nevertheless exchanges one complete and one partial answer.
        pair = part['paired']['first_to_structured']
        pair['matrix'][correct][correct] -= 1
        pair['matrix'][partial][partial] -= 1
        pair['matrix'][correct][partial] += 1
        pair['matrix'][partial][correct] += 1
        pair.update(corrected=1, regressed=1)
        for key, (before, after) in mod.PAIRS.items():
            mod._pair(part['paired'][key], part['conditions'][before]['metrics'],
                      part['conditions'][after]['metrics'], key)
        self.d['cohorts']['fresh'] = part
        with self.assertRaisesRegex(ValueError, 'jointly realizable integer three-condition'):
            mod.validate_summary(self.d)

    def test_nontrivial_valid_three_way_pair_margins_are_accepted(self):
        correct, partial, missed, wrong, abstain = mod.OUTCOMES[0], mod.OUTCOMES[2], mod.OUTCOMES[3], mod.OUTCOMES[4], mod.OUTCOMES[1]
        triples = [(correct, partial, correct), (correct, correct, partial),
                   (partial, correct, correct), (partial, missed, partial),
                   (missed, partial, wrong), (wrong, wrong, missed),
                   (abstain, abstain, abstain), (abstain, wrong, abstain),
                   (wrong, abstain, abstain), (abstain, abstain, wrong),
                   (wrong, wrong, abstain), (abstain, wrong, wrong)]
        self.d['cohorts']['fresh'] = artificial_cohort_from_triples(triples, 6)
        self.assertIs(mod.validate_summary(self.d), self.d)
        for pair in self.d['cohorts']['fresh']['paired'].values():
            self.assertGreater(sum(pair['matrix'][a][b] for a in mod.OUTCOMES for b in mod.OUTCOMES if a != b), 0)

    def test_finding_requires_matching_counts_and_unchanged_paired_items(self):
        correct, partial, abstain = 'correct_supported', 'partial_supported', 'correct_abstention'
        self.d['cohorts']['fresh'] = artificial_cohort_from_triples([(correct,) * 3] * 6 + [(abstain,) * 3] * 6, 6)
        self.d['cohorts']['known'] = artificial_cohort_from_triples([(correct,) * 3] * 3 + [(partial,) * 3] * 3 + [(abstain,) * 3] * 2, 6)
        mod.validate_summary(self.d)
        finding = mod._finding(self.d, 'en')
        self.assertIn('No additional improvement', finding)
        self.assertIn('already correct at the shared first answer', finding)
        self.assertIn('3 partial supported answers remained', finding)
        self.assertIn('do not establish general inferiority', finding)
        self.assertIn('追加の改善は確認できませんでした', mod._finding(self.d, 'ja'))
        # Equal aggregates with offsetting item changes are not an unchanged
        # result: every pair comes from these consistent artificial triples.
        self.d['cohorts']['known'] = artificial_cohort_from_triples(
            [(correct, partial, correct), (partial, correct, partial),
             (correct,) * 3, (correct,) * 3, (partial,) * 3, (partial,) * 3,
             (abstain,) * 3, (abstain,) * 3], 6)
        mod.validate_summary(self.d)
        self.assertNotIn('No additional improvement', mod._finding(self.d, 'en'))
        self.assertNotIn('No additional improvement', mod._finding(artificial_fixture(), 'en'))

    def test_joint_pair_realization_preserves_the_six_supported_query_identities(self):
        correct, wrong = 'correct_supported', 'wrong_or_unsupported'
        part = artificial_cohort_from_triples([(correct,) * 3] * 6 + [(wrong,) * 3] * 6, 6)
        for key in ('first_to_plain', 'plain_to_structured'):
            pair = part['paired'][key]
            pair['matrix'][correct][correct] = pair['matrix'][wrong][wrong] = 0
            pair['matrix'][correct][wrong] = pair['matrix'][wrong][correct] = 6
            pair.update(corrected=6, regressed=6)
        # As outcome tables these permit twelve triples, but every triple would
        # need to be supported, contradicting the fixed six supported queries.
        self.d['cohorts']['fresh'] = part
        with self.assertRaisesRegex(ValueError, 'jointly realizable integer three-condition'):
            mod.validate_summary(self.d)

    def test_unsupported_queries_cannot_be_supported_answers(self):
        row = self.d['cohorts']['fresh']['conditions']['first_pass']['support_strata']['unsupported']
        row['correct_supported'] += 1
        row['correct_abstention'] -= 1
        with self.assertRaisesRegex(ValueError, 'unsupported queries'):
            mod.validate_summary(self.d)

    def test_invalid_grounding_prevents_complete_source_bound_correctness(self):
        row = self.d['cohorts']['fresh']['conditions']['first_pass']['support_strata']['supported']
        row['mechanical_evidence_error_items'] = row['queries']
        with self.assertRaisesRegex(ValueError, 'source evidence'):
            mod.validate_summary(self.d)

    def test_production_records_are_not_context_or_provider_request_counts(self):
        for field in ('records', 'contexts'):
            corrupt = copy.deepcopy(self.d)
            corrupt['costs']['plain_reread:plan'][field] += 1
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'records and contexts'):
                mod.validate_summary(corrupt)
        corrupt = copy.deepcopy(self.d)
        corrupt['costs']['plain_reread:plan']['provider_requests'] = 20
        with self.assertRaises(ValueError):
            mod.validate_summary(corrupt)

    def test_payload_budget_overrun_does_not_reclassify_semantic_outcomes(self):
        row = self.d['costs']['plain_reread:plan']
        row.update(emitted_payload_characters=24020, maximum_payload_characters=1201,
                   payload_cap_violation_records=20)
        before = copy.deepcopy(self.d['cohorts'])
        self.assertIs(mod.validate_summary(self.d), self.d)
        self.assertEqual(self.d['cohorts'], before)
        row['payload_cap_violation_records'] = 0
        with self.assertRaisesRegex(ValueError, 'caps and violation'):
            mod.validate_summary(self.d)

    def test_character_total_maximum_and_overrun_count_are_jointly_possible(self):
        row = self.d['costs']['plain_reread:plan']
        # With one 1,201-character overrun, the other 19 payloads are 1..1,200.
        # Exact feasible totals are therefore 1,220..24,001, not up to 24,020.
        row.update(maximum_payload_characters=1201, payload_cap_violation_records=1)
        for total in (1219, 24020):
            row['emitted_payload_characters'] = total
            with self.subTest(total=total), self.assertRaisesRegex(ValueError, 'not jointly realizable'):
                mod.validate_summary(self.d)
        for total in (1220, 24001):
            row['emitted_payload_characters'] = total
            self.assertIs(mod.validate_summary(self.d), self.d)
        answer = self.d['costs']['plain_reread:final']
        answer.update(emitted_payload_characters=120000, maximum_payload_characters=6000,
                      answer_characters=40020, maximum_answer_characters=2001,
                      answer_cap_violation_records=1)
        with self.assertRaisesRegex(ValueError, 'not jointly realizable'):
            mod.validate_summary(self.d)

    def test_answer_and_payload_totals_share_the_same_twenty_records(self):
        row = self.d['costs']['plain_reread:final']
        row.update(emitted_payload_characters=7900, maximum_payload_characters=6000,
                   answer_characters=6000, maximum_answer_characters=2000)
        # Individually both summaries fit their caps. The 6,000-character
        # payload can hold at most one 2,000-character answer; all other
        # payloads total only 1,900, so answers can total no more than 3,900.
        with self.assertRaisesRegex(ValueError, 'answer and payload character totals'):
            mod.validate_summary(self.d)
        row['answer_characters'] = 3900
        self.assertIs(mod.validate_summary(self.d), self.d)
        row.update(answer_characters=0, maximum_answer_characters=0)
        self.assertIs(mod.validate_summary(self.d), self.d)
        # Every non-answer row retains zero answer characters and remains
        # valid under the same cross-record check.
        for key in mod.COST_DESIGN:
            if not key.endswith(':final'):
                self.assertEqual(self.d['costs'][key]['answer_characters'], 0)

    def test_cost_bounds_answer_stage_and_audit_fail_closed(self):
        for field, value in [('maximum_payload_characters', 0),
                             ('payload_cap_violation_records', 21),
                             ('answer_characters', 1), ('slot_cap_violation_records', 21)]:
            corrupt = copy.deepcopy(self.d)
            corrupt['costs']['plain_reread:plan'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                mod.validate_summary(corrupt)
        corrupt = copy.deepcopy(self.d)
        corrupt['verification']['independent_audit_verified'] = False
        with self.assertRaisesRegex(ValueError, 'independently audited'):
            mod.validate_summary(corrupt)

    def test_artificial_rendering_only_in_memory_has_accessible_bilingual_structure(self):
        for lang in ('ja', 'en'):
            html = mod.render(lang, self.d)
            page = Page(html)
            self.assertEqual(page.languages, [lang])
            self.assertEqual(len(page.ids), len(set(page.ids)))
            self.assertEqual(len(page.canonicals), 1)
            self.assertTrue(page.canonicals[0].startswith(mod.BASE + mod.STUDY))
            self.assertIn('../../assets/lux-symbol.png', page.links)
            self.assertIn('../../theme-dark.css', page.links)
            self.assertIn('working-memory.css', page.links)
            self.assertGreater(page.captions, 12)
            self.assertNotIn('<script', html)
            self.assertNotIn('PRIVATE_SENTINEL', html)
        en = mod.render('en', self.d)
        for text in ('ordinary reread → structured working state', 'lower-stage diagnostic',
                     'does not mean 140 provider requests', 'equal provider tokens or compute were not verified',
                     'PROPOSED / NOT EXECUTED', 'not full anonymity', 'Fresh 12 queries', 'Known 8 queries'):
            self.assertTrue(text in en, text)

    def test_absent_export_publication_functions_are_identity_operations(self):
        for function, args in ((pub.integrate_home, ('unchanged', 'ja', None)),
                               (pub.integrate_listing, ('unchanged', 'en', None)),
                               (pub.integrate_readme, ('unchanged', None)),
                               (pub.integrate_sitemap, ('unchanged', None))):
            self.assertEqual(function(*args), 'unchanged')

    def test_home_integration_changes_exactly_latest_panel_and_preserves_four_stories(self):
        for name, lang in [('index.html', 'ja'), ('index.en.html', 'en')]:
            html = (ROOT / name).read_text(encoding='utf-8')
            result = pub.integrate_home(html, lang, self.d)
            self.assertEqual(pub.LATEST.sub('', result), pub.LATEST.sub('', html))
            self.assertEqual(result.count('data-mechanism '), 4)
            self.assertEqual(pub.integrate_home(result, lang, self.d), result)

    def test_all_five_older_study_pairs_and_data_retain_original_bytes(self):
        for name, digest in PRESERVED.items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), digest, name)

    def test_listing_integration_preserves_each_previous_card_and_is_idempotent(self):
        for name, lang in [('results.html', 'ja'), ('results.en.html', 'en')]:
            html = (ROOT / name).read_text(encoding='utf-8')
            html = re.sub(r'<article class="study-card" data-study="action-feedback">.*?</article>', '', html, flags=re.S)
            html = re.sub(r'<article class="study-card" data-study="conditional-revision">.*?</article>', '', html, flags=re.S)
            html = re.sub(r'<article class="study-card" data-study="experience-retention">.*?</article>', '', html, flags=re.S)
            # If actual publication exists, its sixth card is replaced as intended.
            old_cards = [card for card in re.findall(r'<article class="study-card".*?</article>', html, re.S) if 'data-study="working-memory-source-fixed"' not in card]
            self.assertEqual(len(old_cards), 5)
            result = pub.integrate_listing(html, lang, self.d)
            self.assertEqual(result.count('<article class="study-card"'), 6)
            for card in old_cards:
                self.assertIn(card, result)
            self.assertEqual(pub.integrate_listing(result, lang, self.d), result)

    def test_readme_and_sitemap_integration_are_idempotent_and_keep_older_records(self):
        readme = (ROOT / 'README.md').read_text(encoding='utf-8')
        result = pub.integrate_readme(readme, self.d)
        self.assertEqual(pub.integrate_readme(result, self.d), result)
        adoption_start, adoption_end = '<!-- EVENT_ADOPTION_STUDY_START -->', '<!-- EVENT_ADOPTION_STUDY_END -->'
        block = readme.split(adoption_start)[1].split(adoption_end)[0]
        self.assertIn(block, result)
        sitemap = (ROOT / 'sitemap.xml').read_text(encoding='utf-8')
        result = pub.integrate_sitemap(sitemap, self.d)
        self.assertEqual(pub.integrate_sitemap(result, self.d), result)
        for line in sitemap.splitlines():
            if '<loc>' in line:
                self.assertIn(line, result)

    def test_publication_plan_only_targets_sixth_pages_and_latest_metadata_without_writes(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in ('index.html', 'index.en.html', 'README.md', 'sitemap.xml'):
                (root / name).write_bytes((ROOT / name).read_bytes())
            before = {path.name: path.read_bytes() for path in root.iterdir()}
            plan = pub.prepare_updates(root, self.d)
            self.assertEqual(set(plan), {mod.STUDY + 'index.html', mod.STUDY + 'en.html',
                                         'index.html', 'index.en.html', 'README.md', 'sitemap.xml'})
            self.assertEqual(before, {path.name: path.read_bytes() for path in root.iterdir()})
            self.assertFalse((root / mod.STUDY).exists())

    def test_artificial_standalone_outputs_can_only_be_written_in_temporary_directory(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            export = root / mod.DATA_FILE
            export.parent.mkdir()
            export.write_text(json.dumps(self.d), encoding='utf-8')
            with patch.object(mod, 'ROOT', root):
                pages = mod.build()
            self.assertEqual(set(pages), {'index.html', 'en.html'})
            self.assertEqual(set(path.name for path in (root / mod.STUDY).iterdir()), {'index.html', 'en.html'})

    def test_actual_data_is_valid_if_supplied_without_inventing_a_fixture_export(self):
        if not (ROOT / mod.DATA_FILE).is_file():
            self.skipTest('Actual independently audited public export has not been supplied')
        d = mod.load_summary()
        self.assertIs(mod.validate_summary(d), d)
        for name, lang in [('index.html', 'ja'), ('en.html', 'en')]:
            page = ROOT / mod.STUDY / name
            if page.is_file():
                self.assertEqual(page.read_text(encoding='utf-8'), mod.render(lang, d))

    def test_actual_publication_matches_audited_data_if_supplied(self):
        if not (ROOT / mod.DATA_FILE).is_file():
            self.skipTest('Actual independently audited public export has not been supplied')
        d = mod.load_summary()
        if not (ROOT / 'data/action-feedback-2026-10-27.json').is_file():
            for name, expected in pub.prepare_updates(ROOT, d).items():
                self.assertEqual((ROOT / name).read_text(encoding='utf-8'), expected)
        else:
            # Later publication owns the latest panel/build instructions; this
            # study's dated pages and historical README block remain exact.
            readme = (ROOT / 'README.md').read_text(encoding='utf-8')
            updated = pub.integrate_readme(readme, d)
            self.assertEqual(readme.split(pub.README_START)[1].split(pub.README_END)[0],
                             updated.split(pub.README_START)[1].split(pub.README_END)[0])
        pages = module('working_actual_listing', 'tools/build_pages.py')
        for name, lang in [('results.html', 'ja'), ('results.en.html', 'en')]:
            self.assertEqual((ROOT / name).read_text(encoding='utf-8'), pages.landing(lang) + '\n')


if __name__ == '__main__':
    unittest.main()

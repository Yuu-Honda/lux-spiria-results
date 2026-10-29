"""Artificial engineering fixtures stay in memory/tmp, never study exports."""
import copy
from datetime import datetime, timedelta, timezone
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


def module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


mod = module('experience_engineering', 'tools/build_experience_retention.py')
pub = module('experience_publication_engineering', 'tools/experience_retention_publication.py')
SOURCE_PATHS = {
    'X01': 'data/shiori-event-adoption-2026-10-24.json',
    'X02': 'data/shiori-event-compatibility-2026-10-22.json',
    'X03': 'data/shiori-retrieval-hypotheses-2026-10-21.json',
}
METRICS = ('attempts', 'accepted', 'rejected', 'artifacts_written', 'execution_errors',
           'invalid_actions', 'abstentions', 'budget_exceeded', 'predicted_accepted_failures',
           'uncertain_predictions', 'inspections', 'source_bytes_read',
           'returned_canonical_characters', 'action_canonical_characters')


def digest(label):
    return hashlib.sha256(('artificial-engineering-' + label).encode()).hexdigest()


def action(label, status='ok', accepted=True, prediction='accepted', characters=101):
    validation = 'accepted' if accepted else 'rejected'
    failed = status in ('execution_error', 'invalid_action')
    return {'execution_status': status,
            'error': {'type': 'ActionError', 'sha256': digest(label + '-error')} if failed else None,
            'validation_status': validation,
            'artifact_sha256': None if failed else digest(label + '-artifact'),
            'prediction': prediction,
            'prediction_agreement': None if prediction == 'uncertain' else prediction == validation,
            'canonical_characters': characters, 'action_sha256': digest(label),
            'budget_exceeded': characters > 6000}


def inspection(d, family, fmt, label):
    return {'raw_sha256': d['sources'][family][fmt + '_sha256'],
            'raw_bytes_read': 250 + len(label), 'returned_canonical_characters': 150 + len(label),
            'observation_sha256': digest(label + '-observation'), 'record_sha256': digest(label + '-inspection')}


def expected_aggregate(attempts):
    """Independent, transparent expected arithmetic rather than builder output."""
    results = [result for result, _ in attempts]
    inspections = [value for _, value in attempts if value is not None]
    return {
        'attempts': len(results),
        'accepted': sum(row['validation_status'] == 'accepted' for row in results),
        'rejected': sum(row['validation_status'] == 'rejected' for row in results),
        'artifacts_written': sum(row['artifact_sha256'] is not None for row in results),
        'execution_errors': sum(row['execution_status'] == 'execution_error' for row in results),
        'invalid_actions': sum(row['execution_status'] == 'invalid_action' for row in results),
        'abstentions': sum(row['execution_status'] == 'unavailable' for row in results),
        'budget_exceeded': sum(row['budget_exceeded'] for row in results),
        'predicted_accepted_failures': sum(row['prediction'] == 'accepted' and row['validation_status'] == 'rejected' for row in results),
        'uncertain_predictions': sum(row['prediction'] == 'uncertain' for row in results),
        'inspections': len(inspections),
        'source_bytes_read': sum(row['raw_bytes_read'] for row in inspections),
        'returned_canonical_characters': sum(row['returned_canonical_characters'] for row in inspections),
        'action_canonical_characters': sum(row['canonical_characters'] for row in results),
    }


def refresh(d):
    training = {}
    for fmt in ('original', 'changed'):
        training[fmt] = {}
        for phase in ('initial', 'repair'):
            attempts = [(row[phase], row[phase + '_inspection']) for row in d['training']
                        if row['format'] == fmt and row[phase] is not None]
            training[fmt][phase] = expected_aggregate(attempts)
    immediate = {}
    for arm in ('no_experience', 'experience_record'):
        immediate[arm] = {}
        for fmt in ('all', 'original', 'changed'):
            rows = [row for row in d['immediate'] if row['arm'] == arm and (fmt == 'all' or row['format'] == fmt)]
            immediate[arm][fmt] = expected_aggregate([(row['result'], row['inspection']) for row in rows])
    d['counts'] = {'training': training, 'immediate': immediate}
    bound = {(row['arm'], row['id']): row for row in d['immediate']}
    d['paired'] = []
    for number in range(1, 7):
        task = f'P{number:02d}'
        before, after = (bound[arm, task]['result']['validation_status'] == 'accepted'
                         for arm in ('no_experience', 'experience_record'))
        category = 'both_correct' if before and after else 'corrected' if after else 'regressed' if before else 'both_wrong'
        d['paired'].append({'id': task, 'format': bound['no_experience', task]['format'], 'classification': category})
    return d


def fixture():
    start = datetime(2026, 10, 28, tzinfo=timezone.utc)
    later = start + timedelta(seconds=86400)
    d = {'schema_version': 1, 'study_id': 'experience-retention-2026-10-28', 'date': '2026-10-28',
         'sample': dict(mod.SAMPLE),
         'sources': {family: {'public_path': path, 'original_sha256': hashlib.sha256((ROOT / path).read_bytes()).hexdigest(),
                             'changed_sha256': digest(family + '-changed')} for family, path in SOURCE_PATHS.items()},
         'training': [], 'immediate': [],
         'memory': {'change_types': ['conditional_update', 'confirmation', 'deferred'],
                    'grounded': [True, False, True], 'legacy_scope_preserved': [False, True, True],
                    'canonical_characters': 1000, 'sha256': digest('memory')},
         'delay': {'status': 'uncollected_pending', 'minimum_elapsed_seconds': 86400,
                   'clock_start_utc': start.isoformat().replace('+00:00', 'Z'),
                   'clock_start_unix_seconds': start.timestamp(),
                   'not_before_utc': later.isoformat().replace('+00:00', 'Z'),
                   'not_before_unix_seconds': later.timestamp(),
                   'planned_unique_objectives': 3, 'planned_items_per_arm': 6},
         'scope': {**{key: True for key in mod.SCOPE_TRUE}, **{key: False for key in mod.SCOPE_FALSE}, 'provider_metadata': None},
         'provenance': {key: digest(key) for key in mod.PROVENANCE},
         'replay': {key: digest(key) for key in ('manifest_sha256', 'readme_sha256', 'zip_sha256')}}
    d['provenance'].update(action_loop_sha256='61495538507742ab5c3d55721a4115bf9fb24542b605525c63edc6b8f4cb7297',
                           protocol_sha256='8d675c231d358b5412839fccd4829785920b867e48eab915f02cec141d37434a',
                           memory_sha256=d['memory']['sha256'])
    training_specs = [
        ('T01', 'X01', 'original', 'ok', True, None),
        ('T02', 'X02', 'original', 'execution_error', False, ('ok', True)),
        ('T03', 'X03', 'original', 'ok', False, None),
        ('C01', 'X01', 'changed', 'invalid_action', False, ('ok', True)),
        ('C02', 'X02', 'changed', 'unavailable', False, ('ok', False)),
        ('C03', 'X03', 'changed', 'ok', True, None),
    ]
    for i, (task, family, fmt, status, accepted, repair) in enumerate(training_specs):
        row = {'id': task, 'source': family, 'family': family, 'format': fmt,
               'initial': action(task, status, accepted, ('accepted', 'rejected', 'uncertain')[i % 3]),
               'initial_inspection': inspection(d, family, fmt, task), 'repair': None, 'repair_inspection': None}
        if repair is not None:
            row['repair'] = action(task + '-repair', *repair, prediction='uncertain' if i == 1 else 'accepted', characters=6001 if i == 3 else 102)
            if i != 4: row['repair_inspection'] = inspection(d, family, fmt, task + '-repair')
        d['training'].append(row)
    outcomes = {
        'no_experience': [('ok', True), ('execution_error', False), ('ok', True), ('invalid_action', False), ('unavailable', False), ('ok', False)],
        'experience_record': [('ok', True), ('ok', True), ('ok', False), ('invalid_action', False), ('ok', True), ('execution_error', False)],
    }
    for arm in ('no_experience', 'experience_record'):
        for i, (source, (family, fmt)) in enumerate(mod.CATALOG.items()):
            task = f'P{i + 1:02d}'; inspect = i % 2 == 0 if arm == 'no_experience' else i in (1, 3)
            d['immediate'].append({'arm': arm, 'id': task, 'source': source, 'family': family, 'format': fmt,
                'policy_decision': 'inspect' if inspect else 'submit',
                'inspection': inspection(d, family, fmt, arm + task) if inspect else None,
                'result': action(arm + task, *outcomes[arm][i], prediction=('accepted', 'uncertain', 'rejected')[i % 3])})
    return refresh(d)


def temporary_inputs(root, d):
    for relative in SOURCE_PATHS.values():
        path = root / relative; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / relative).read_bytes())
    for relative, key, data in [(mod.REPLAY + 'README.md', 'readme_sha256', b'artificial instructions\n'),
                                (mod.REPLAY + 'MANIFEST.json', 'manifest_sha256', b'{"artificial":true}\n'),
                                (mod.ZIP_FILE, 'zip_sha256', b'artificial engineering archive')]:
        path = root / relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
        d['replay'][key] = hashlib.sha256(data).hexdigest()


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__(); self.ids = []; self.refs = []; self.lang = None
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs: self.ids.append(attrs['id'])
        if tag == 'html': self.lang = attrs.get('lang')
        self.refs.extend(attrs[key] for key in ('href', 'src') if attrs.get(key))


class ExperienceRetentionEngineering(unittest.TestCase):
    def setUp(self): self.d = fixture()

    def test_complete_fixture_independent_aggregates_and_all_pair_categories(self):
        self.assertIs(mod.validate_summary(self.d), self.d)
        self.assertEqual(len(self.d['training']), 6); self.assertEqual(len(self.d['immediate']), 12)
        self.assertEqual(set(row['classification'] for row in self.d['paired']), {'both_correct', 'corrected', 'regressed', 'both_wrong'})
        self.assertEqual(mod.recalculate(self.d['training'], self.d['immediate']), {key: self.d[key] for key in ('counts', 'paired')})
        self.assertEqual(mod.aggregate_attempts([(row['initial'], row['initial_inspection']) for row in self.d['training']]),
                         expected_aggregate([(row['initial'], row['initial_inspection']) for row in self.d['training']]))
        self.assertEqual(mod.paired_counts(self.d), {'both_correct': 1, 'corrected': 2, 'regressed': 1, 'both_wrong': 2})
        for arm in mod.ARMS:
            self.assertEqual(len(mod.selected_probe(self.d, arm)), 6)
            for fmt in mod.FORMATS: self.assertEqual(len(mod.selected_probe(self.d, arm, fmt)), 3)

    def test_optional_absence_is_identity_and_standalone_refuses_before_writes(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertIsNone(mod.optional_summary(root)); self.assertEqual(pub.prepare_updates(root), {})
            with patch.object(mod, 'ROOT', root), self.assertRaises(FileNotFoundError): mod.build()
            self.assertEqual(list(root.iterdir()), [])
        for fn, args in [(pub.integrate_home, ('same', 'ja', None)), (pub.integrate_listing, ('same', 'en', None)),
                         (pub.integrate_readme, ('same', None)), (pub.integrate_sitemap, ('same', None))]:
            self.assertEqual(fn(*args), 'same')

    def test_recursive_unknown_fields_and_strings_fail_closed(self):
        dictionaries = []; strings = []
        def visit(node, path=()):
            if isinstance(node, dict):
                dictionaries.append(path)
                for key, child in node.items(): visit(child, path + (key,))
            elif isinstance(node, list):
                for i, child in enumerate(node): visit(child, path + (i,))
            elif isinstance(node, str): strings.append(path)
        visit(self.d)
        for paths, add_key in [(dictionaries, True), (strings, False)]:
            for path in paths:
                bad = copy.deepcopy(self.d); node = bad
                for key in (path if add_key else path[:-1]): node = node[key]
                if add_key: node['private_source'] = 'PRIVATE_SENTINEL'
                else: node[path[-1]] = 'PRIVATE_SENTINEL'
                with self.subTest(path=path, add_key=add_key), self.assertRaises(ValueError): mod.validate_summary(bad)

    def test_duplicate_json_fields_nonfinite_and_invalid_exports_fail_before_writes(self):
        texts = ['{}', json.dumps(self.d).replace('"schema_version": 1', '"schema_version":1,"schema_version":1', 1)]
        for token in ('NaN', 'Infinity', '-Infinity'):
            texts.append(json.dumps(self.d).replace('"canonical_characters": 1000', '"canonical_characters":' + token, 1))
            texts.append(json.dumps(self.d).replace('"clock_start_unix_seconds": ' + str(self.d['delay']['clock_start_unix_seconds']),
                                                   '"clock_start_unix_seconds":' + token, 1))
        for text in texts:
            with self.subTest(prefix=text[:30]), TemporaryDirectory() as tmp:
                root = Path(tmp); path = root / mod.DATA_FILE; path.parent.mkdir(); path.write_text(text)
                with patch.object(mod, 'ROOT', root), self.assertRaises(ValueError): mod.build()
                with self.assertRaises(ValueError): pub.prepare_updates(root)
                self.assertFalse((root / mod.STUDY).exists()); self.assertEqual(path.read_text(), text)

    def test_all_frozen_training_and_probe_bindings_complete_and_unique(self):
        for collection, values in [('training', [('id', 'T99'), ('source', 'X03'), ('family', 'X03'), ('format', 'changed')]),
                                   ('immediate', [('arm', 'other'), ('id', 'P99'), ('source', 'A06'), ('family', 'X03'), ('format', 'original')])]:
            for field, value in values:
                bad = copy.deepcopy(self.d); bad[collection][0][field] = value
                with self.subTest(collection=collection, field=field), self.assertRaises(ValueError): mod.validate_summary(bad)
            for edit in ('missing', 'duplicate'):
                bad = copy.deepcopy(self.d)
                if edit == 'missing': bad[collection].pop()
                else: bad[collection][-1] = copy.deepcopy(bad[collection][-2])
                with self.subTest(collection=collection, edit=edit), self.assertRaises(ValueError): mod.validate_summary(bad)

    def test_training_repairs_are_optional_failed_only_and_at_most_one(self):
        bad = copy.deepcopy(self.d); row = bad['training'][0]
        row['repair'] = action('forbidden-repair'); refresh(bad)
        with self.assertRaises(ValueError): mod.validate_summary(bad)
        bad = copy.deepcopy(self.d); bad['training'][0]['repair_inspection'] = copy.deepcopy(bad['training'][0]['initial_inspection'])
        with self.assertRaises(ValueError): mod.validate_summary(bad)
        for value in ([action('extra-one'), action('extra-two')], {}, True):
            bad = copy.deepcopy(self.d); bad['training'][1]['repair'] = value
            with self.subTest(value=value), self.assertRaises(ValueError): mod.validate_summary(bad)
        # Rejected initial rows may stop rather than being silently dropped or repaired.
        changed = copy.deepcopy(self.d); changed['training'][1].update(repair=None, repair_inspection=None)
        refresh(changed); mod.validate_summary(changed)
        self.assertEqual(changed['counts']['training']['original']['repair']['attempts'], 0)
        self.assertEqual(changed['counts']['training']['original']['initial']['rejected'], 2)

    def test_all_probe_policies_bind_one_optional_inspection_and_no_retry_fields(self):
        for i, row in enumerate(self.d['immediate']):
            bad = copy.deepcopy(self.d)
            bad['immediate'][i]['policy_decision'] = 'submit' if row['policy_decision'] == 'inspect' else 'inspect'
            with self.subTest(index=i), self.assertRaises(ValueError): mod.validate_summary(bad)
        for field, value in [('repair', None), ('repair_inspection', None), ('retry', action('probe-retry'))]:
            bad = copy.deepcopy(self.d); bad['immediate'][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): mod.validate_summary(bad)
        for value in ([self.d['immediate'][0]['inspection']], {}, 'inspect again'):
            bad = copy.deepcopy(self.d); bad['immediate'][0]['inspection'] = value
            with self.subTest(value=value), self.assertRaises(ValueError): mod.validate_summary(bad)

    def test_inspections_bind_exact_source_format_digest_and_positive_actual_costs(self):
        containers = [(row, phase + '_inspection') for row in self.d['training'] for phase in ('initial', 'repair')
                      if row[phase + '_inspection'] is not None]
        containers += [(row, 'inspection') for row in self.d['immediate'] if row['inspection'] is not None]
        for row, field in containers:
            old = row[field]['raw_sha256']; row[field]['raw_sha256'] = digest('wrong-source')
            with self.subTest(id=row['id'], inspection=field), self.assertRaises(ValueError): mod.validate_summary(self.d)
            row[field]['raw_sha256'] = old
        for field in ('raw_bytes_read', 'returned_canonical_characters'):
            for value in (True, 1.5, 0, -1, float('nan'), float('inf')):
                bad = copy.deepcopy(self.d); bad['immediate'][0]['inspection'][field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ValueError): mod.validate_summary(bad)
        for family in SOURCE_PATHS:
            for field, value in [('public_path', '../../private.json'), ('original_sha256', digest('wrong-original'))]:
                bad = copy.deepcopy(self.d); bad['sources'][family][field] = value
                with self.subTest(family=family, field=field), self.assertRaises(ValueError): mod.validate_summary(bad)

    def test_error_artifact_prediction_and_budget_branches_recalculate(self):
        for changes in [{'artifact_sha256': digest('forbidden')}, {'validation_status': 'accepted'}, {'error': None}]:
            bad = copy.deepcopy(self.d); bad['training'][1]['initial'].update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError): mod.validate_summary(bad)
        for changes in [{'error': {'type': 'ActionError', 'sha256': digest('unneeded')}}, {'artifact_sha256': None},
                        {'execution_status': 'unavailable'}, {'prediction_agreement': False}, {'prediction_agreement': 1},
                        {'budget_exceeded': True}, {'canonical_characters': True}]:
            bad = copy.deepcopy(self.d); bad['training'][0]['initial'].update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError): mod.validate_summary(bad)
        for changes in [{'prediction': 'uncertain', 'prediction_agreement': True}, {'prediction': 'accepted', 'prediction_agreement': None}]:
            bad = copy.deepcopy(self.d); bad['training'][0]['initial'].update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError): mod.validate_summary(bad)
        for collection in ('action', 'memory'):
            for value in (True, 1.5, 0, -1, float('nan'), float('inf')):
                bad = copy.deepcopy(self.d)
                row = bad['training'][0]['initial'] if collection == 'action' else bad['memory']
                row['canonical_characters'] = value
                with self.subTest(collection=collection, value=value), self.assertRaises(ValueError): mod.validate_summary(bad)
        # Actual accepted work above the cap remains an accepted, flagged attempt.
        self.assertEqual(self.d['training'][3]['repair']['validation_status'], 'accepted')
        self.assertEqual(self.d['counts']['training']['changed']['repair']['budget_exceeded'], 1)
        self.d['memory']['canonical_characters'] = 6001; mod.validate_summary(self.d)
        self.assertIn('6001', mod.render('en', self.d))
        self.assertEqual(mod.validate_summary(self.d)['training'][1]['initial']['error']['type'], 'ActionError')

    def test_every_nested_metric_and_paired_category_must_recalculate(self):
        for group in ('training', 'immediate'):
            for stratum, phases in self.d['counts'][group].items():
                for phase, values in phases.items():
                    self.assertEqual(set(values), set(METRICS))
                    for field in METRICS:
                        bad = copy.deepcopy(self.d); bad['counts'][group][stratum][phase][field] += 1
                        with self.subTest(group=group, stratum=stratum, phase=phase, field=field), self.assertRaises(ValueError): mod.validate_summary(bad)
        for field, value in [('id', 'P99'), ('format', 'original'), ('classification', 'regressed')]:
            bad = copy.deepcopy(self.d); bad['paired'][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): mod.validate_summary(bad)
        bad = copy.deepcopy(self.d); bad['counts']['immediate']['no_experience']['all']['attempts'] = True
        with self.assertRaises(ValueError): mod.validate_summary(bad)
        bad = copy.deepcopy(self.d); bad['paired'][-1] = copy.deepcopy(bad['paired'][0])
        with self.assertRaises(ValueError): mod.validate_summary(bad)

    def test_pending_delay_has_finite_matching_real_clock_commitments_and_no_outcomes(self):
        for field in ('clock_start_unix_seconds', 'not_before_unix_seconds'):
            for value in (True, float('nan'), float('inf'), float('-inf'), 0, -1, '1793145600'):
                bad = copy.deepcopy(self.d); bad['delay'][field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ValueError): mod.validate_summary(bad)
        for field, value in [('status', 'collected'), ('minimum_elapsed_seconds', 86399), ('planned_unique_objectives', 6),
                             ('planned_items_per_arm', True), ('clock_start_utc', '2026-10-28'),
                             ('clock_start_utc', '2026-10-28T00:00:00+09:00'), ('not_before_unix_seconds', self.d['delay']['not_before_unix_seconds'] + 1)]:
            bad = copy.deepcopy(self.d); bad['delay'][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError): mod.validate_summary(bad)
        for field, value in [('elapsed_seconds', 86400), ('accepted', 6), ('results', []), ('execution_started', True)]:
            bad = copy.deepcopy(self.d); bad['delay'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): mod.validate_summary(bad)
        bad = copy.deepcopy(self.d)
        bad['delay']['not_before_unix_seconds'] += 1
        bad['delay']['not_before_utc'] = '2026-10-29T00:00:01Z'
        with self.assertRaises(ValueError): mod.validate_summary(bad)
        # Fractional clocks and UTC offsets are actual valid observations, not rounded estimates.
        for field in ('clock_start', 'not_before'):
            self.d['delay'][field + '_unix_seconds'] += .25
            self.d['delay'][field + '_utc'] = self.d['delay'][field + '_utc'].replace('00Z', '00.250000+00:00')
        mod.validate_summary(self.d)

    def test_scope_memory_and_provenance_are_strict_without_forcing_success(self):
        for field in mod.SCOPE_TRUE | mod.SCOPE_FALSE:
            bad = copy.deepcopy(self.d); bad['scope'][field] = not bad['scope'][field]
            with self.subTest(field=field), self.assertRaises(ValueError): mod.validate_summary(bad)
        for field in ('action_loop_sha256', 'protocol_sha256', 'memory_sha256'):
            bad = copy.deepcopy(self.d); bad['provenance'][field] = digest('wrong')
            with self.subTest(field=field), self.assertRaises(ValueError): mod.validate_summary(bad)
        for field in ('delayed_task_commitment_sha256', 'delayed_gold_commitment_sha256'):
            bad = copy.deepcopy(self.d); bad['provenance'].pop(field)
            with self.subTest(field=field), self.assertRaises(ValueError): mod.validate_summary(bad)
        bad = copy.deepcopy(self.d); bad['scope']['provider_metadata'] = {}
        with self.assertRaises(ValueError): mod.validate_summary(bad)
        for field in ('grounded', 'legacy_scope_preserved'):
            bad = copy.deepcopy(self.d); bad['memory'][field][0] = 1
            with self.subTest(field=field), self.assertRaises(ValueError): mod.validate_summary(bad)
        self.d['memory'].update(change_types=['confirmation'] * 3, grounded=[False] * 3, legacy_scope_preserved=[False] * 3)
        mod.validate_summary(self.d)

    def test_efficiency_finding_requires_every_predeclared_condition_and_is_not_total_io(self):
        for row in self.d['immediate']:
            row['result'] = action(row['arm'] + row['id'] + '-controlled')
            row['policy_decision'] = 'inspect' if row['arm'] == 'no_experience' else 'submit'
            row['inspection'] = inspection(self.d, row['family'], row['format'], row['arm'] + row['id']) if row['policy_decision'] == 'inspect' else None
        refresh(self.d); mod.validate_summary(self.d)
        self.assertTrue(mod.efficient_record_use(self.d))
        self.assertIn('bounded benefit', mod.finding(self.d, 'en'))
        self.assertIn('6 fewer optional structural inspections', mod.finding(self.d, 'en'))
        self.assertIn('shows no accuracy gain', mod.finding(self.d, 'en'))
        for i, row in enumerate(row for row in self.d['immediate'] if row['arm'] == 'experience_record'):
            if i:
                row.update(policy_decision='inspect', inspection=inspection(self.d, row['family'], row['format'], row['id']))
        refresh(self.d); mod.validate_summary(self.d)
        self.assertIn('1 fewer optional structural inspections', mod.finding(self.d, 'en'))
        for case in ('unequal_acceptance', 'equal_inspections', 'execution_error', 'invalid_action', 'unavailable'):
            bad = copy.deepcopy(self.d)
            before = next(row for row in bad['immediate'] if row['arm'] == 'no_experience')
            after = next(row for row in bad['immediate'] if row['arm'] == 'experience_record')
            if case == 'equal_inspections':
                for row in bad['immediate']:
                    if row['arm'] == 'experience_record':
                        row.update(policy_decision='inspect', inspection=inspection(bad, row['family'], row['format'], row['id']))
            elif case == 'unequal_acceptance': after['result'] = action('controlled-rejected', accepted=False)
            else:
                before['result'] = action('controlled-before-rejected', accepted=False)
                after['result'] = action('controlled-added-' + case, case, False)
            refresh(bad); mod.validate_summary(bad)
            with self.subTest(case=case):
                self.assertFalse(mod.efficient_record_use(bad))
                self.assertIn('criterion was not met', mod.finding(bad, 'en'))
                self.assertNotIn('bounded benefit', mod.finding(bad, 'en'))
        for d in (self.d, bad):
            text = mod.finding(d, 'en')
            self.assertIn('Zero additional inspections does not mean zero total source I/O', text)
            self.assertIn('Speed, token and compute savings were not measured', text)
            html = mod.render('en', d)
            for phrase in ('Inspection raw bytes', 'Projection chars', 'equal compute, latency or spend are unverified'):
                self.assertIn(phrase, html)

    def test_no_initial_failure_does_not_create_own_error_correction_evidence(self):
        for row in self.d['training']:
            row.update(initial=action(row['id'] + '-all-correct'), repair=None, repair_inspection=None)
        refresh(self.d); mod.validate_summary(self.d)
        html = mod.render('en', self.d)
        self.assertIn('There were 0 failed own initials, and 0 became accepted through actual repairs', html)
        self.assertIn('no evidence of own-error correction', html)
        self.assertIn('An uncertain prediction is distinct from', html)

    def test_original_sources_replay_and_external_zip_verified_before_writes(self):
        for relative in (*SOURCE_PATHS.values(), mod.REPLAY + 'MANIFEST.json', mod.REPLAY + 'README.md', mod.ZIP_FILE):
            for edit in ('changed', 'missing'):
                with self.subTest(relative=relative, edit=edit), TemporaryDirectory() as tmp:
                    root = Path(tmp); temporary_inputs(root, self.d)
                    if edit == 'changed': (root / relative).write_bytes(b'changed')
                    else: (root / relative).unlink()
                    with self.assertRaises(ValueError): pub.prepare_updates(root, self.d)
                    self.assertFalse((root / mod.STUDY).exists())
        with TemporaryDirectory() as tmp:
            root = Path(tmp); temporary_inputs(root, self.d); mod.require_public_inputs(root, self.d)
            self.assertNotIn((root / mod.REPLAY).resolve(), (root / mod.ZIP_FILE).resolve().parents)
            self.assertEqual({path.name for path in (root / mod.REPLAY).iterdir()}, {'README.md', 'MANIFEST.json'})
            # Matching bytes at a lowercase legacy name do not satisfy this bundle.
            (root / mod.REPLAY / 'MANIFEST.json').rename(root / mod.REPLAY / 'manifest.json')
            with self.assertRaises(ValueError): mod.require_public_inputs(root, self.d)

    def test_bilingual_render_and_publication_preserve_prior_stories_and_cards(self):
        for lang in ('ja', 'en'):
            html = mod.render(lang, self.d); page = Page(html)
            self.assertEqual(page.lang, lang); self.assertEqual(len(page.ids), len(set(page.ids)))
            for ref in ('../../assets/lux-symbol.png', '../../theme-dark.css', 'experience-retention.css',
                        '../../' + mod.ZIP_FILE, '../../' + mod.REPLAY + 'README.md'):
                self.assertIn(ref, page.refs)
            self.assertNotIn('PRIVATE_SENTINEL', html); self.assertNotIn('<script', html)
            self.assertIn('プローブ共通指示には旧形式維持の直接指示がありません' if lang == 'ja' else 'common probe instructions contain no direct legacy-preservation instruction', html)
            self.assertIn('経験記録のテンプレートは旧条件の適用範囲を尋ね' if lang == 'ja' else 'experience-record template does ask for the applicability of earlier conditions', html)
        for name, lang in [('index.html', 'ja'), ('index.en.html', 'en')]:
            before = (ROOT / name).read_text(); after = pub.integrate_home(before, lang, self.d)
            self.assertEqual(pub.LATEST.sub('', before), pub.LATEST.sub('', after))
            self.assertEqual(after.count('data-mechanism '), 4)
            self.assertEqual(pub.integrate_home(after, lang, self.d), after)
        for name, lang in [('results.html', 'ja'), ('results.en.html', 'en')]:
            before = pub.CARD.sub('', (ROOT / name).read_text())
            before = re.sub(r'<article class="study-card" data-study="tool-observation-loop">.*?</article>', '', before, flags=re.S)
            before = re.sub(r'<article class="study-card" data-study="experience-retention-delayed">.*?</article>', '', before, flags=re.S)
            cards = re.findall(r'<article class="study-card".*?</article>', before, re.S)
            self.assertEqual(len(cards), 8)
            after = pub.integrate_listing(before, lang, self.d)
            self.assertEqual(after.count('<article class="study-card"'), 9)
            for card in cards: self.assertIn(card, after)
            self.assertEqual(pub.integrate_listing(after, lang, self.d), after)

    def test_readme_history_sitemap_and_publication_plan_are_side_effect_free(self):
        before = (ROOT / 'README.md').read_text(); after = pub.integrate_readme(before, self.d)
        for name in ('CONDITIONAL_REVISION', 'ACTION_FEEDBACK', 'WORKING_MEMORY', 'EVENT_ADOPTION'):
            start, end = f'<!-- {name}_STUDY_START -->', f'<!-- {name}_STUDY_END -->'
            self.assertIn(before.split(start)[1].split(end)[0], after)
        self.assertEqual(pub.integrate_readme(after, self.d), after)
        before = (ROOT / 'sitemap.xml').read_text(); after = pub.integrate_sitemap(before, self.d)
        self.assertEqual(pub.integrate_sitemap(after, self.d), after)
        for line in before.splitlines():
            if '<loc>' in line: self.assertIn(line, after)
        for suffix in ('', 'en.html'): self.assertEqual(after.count('<loc>' + mod.BASE + mod.STUDY + suffix + '</loc>'), 1)
        with TemporaryDirectory() as tmp:
            root = Path(tmp); temporary_inputs(root, self.d)
            for name in ('index.html', 'index.en.html', 'README.md', 'sitemap.xml'):
                (root / name).write_bytes((ROOT / name).read_bytes())
            snapshot = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}
            plan = pub.prepare_updates(root, self.d)
            self.assertEqual(set(plan), {mod.STUDY + 'index.html', mod.STUDY + 'en.html', 'index.html', 'index.en.html', 'README.md', 'sitemap.xml'})
            self.assertEqual(snapshot, {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()})

    def test_actual_audited_export_and_generated_pages_when_supplied(self):
        if not (ROOT / mod.DATA_FILE).is_file(): self.skipTest('Actual audited export not supplied')
        data = mod.load_summary(); mod.require_public_inputs(ROOT, data)
        for name, expected in pub.prepare_updates(ROOT, data).items():
            if (ROOT / 'data/tool-observation-loop-2026-10-28.json').is_file() and not name.startswith(mod.STUDY):
                continue  # The tenth study owns shared latest metadata; dated bytes stay exact.
            self.assertEqual((ROOT / name).read_text(encoding='utf-8'), expected, name)
        pages = module('experience_actual_main', 'tools/build_pages.py')
        for name, lang in [('results.html', 'ja'), ('results.en.html', 'en')]:
            self.assertEqual((ROOT / name).read_text(encoding='utf-8'), pages.landing(lang) + '\n')


if __name__ == '__main__': unittest.main()

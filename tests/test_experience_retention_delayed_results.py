"""Synthetic engineering fixtures stay in memory/tmp, outside real study exports.

No delayed task, gold, actor, private record or actual new public export is read
or written by this test module.
"""
import copy
from contextlib import ExitStack, contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
from html.parser import HTMLParser
import importlib.util
from io import BytesIO
import json
from pathlib import Path
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


mod = module('delayed_experience_engineering', 'tools/build_experience_retention_delayed.py')
pub = module('delayed_experience_publication_engineering', 'tools/experience_retention_delayed_publication.py')


def digest(label):
    return hashlib.sha256(('synthetic-delayed-engineering-' + label).encode()).hexdigest()


def paths(value, predicate, path=()):
    result = [path] if predicate(value) else []
    if isinstance(value, dict):
        for key, child in value.items():
            result.extend(paths(child, predicate, path + (key,)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            result.extend(paths(child, predicate, path + (index,)))
    return result


def at(value, path):
    for key in path:
        value = value[key]
    return value


def replaced(value, path, replacement):
    result = copy.deepcopy(value)
    at(result, path[:-1])[path[-1]] = replacement
    return result


def duplicate_json(value, target, path=()):
    if isinstance(value, dict):
        items = [json.dumps(key) + ':' + duplicate_json(child, target, path + (key,))
                 for key, child in value.items()]
        if path == target:
            items.insert(0, json.dumps(next(iter(value))) + ':"PRIVATE_SENTINEL"')
        return '{' + ','.join(items) + '}'
    if isinstance(value, list):
        return '[' + ','.join(duplicate_json(child, target, path + (index,))
                              for index, child in enumerate(value)) + ']'
    return json.dumps(value)


def snapshot(root):
    return {path.relative_to(root).as_posix(): path.read_bytes()
            for path in root.rglob('*') if path.is_file()}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False) + '\n').encode()
    path.write_bytes(raw)
    return raw


def point(seconds):
    return {'utc': datetime.fromtimestamp(seconds, timezone.utc).isoformat().replace('+00:00', 'Z'),
            'unix_seconds': seconds}


def action(label, status='ok', accepted=True, prediction='accepted', characters=101):
    validation = 'accepted' if accepted else 'rejected'
    failed = status in ('execution_error', 'invalid_action')
    return {'execution_status': status,
        'error': {'type': 'ActionError', 'sha256': digest(label + '-error')} if failed else None,
        'validation_status': validation, 'artifact_sha256': None if failed else digest(label + '-artifact'),
        'prediction': prediction, 'prediction_agreement': None if prediction == 'uncertain' else prediction == validation,
        'canonical_characters': characters, 'action_sha256': digest(label), 'budget_exceeded': characters > 6000}


def expected_aggregate(rows):
    results = [row['result'] for row in rows]
    inspections = [row['inspection'] for row in rows if row['inspection'] is not None]
    return {'attempts': len(rows),
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
        'action_canonical_characters': sum(row['canonical_characters'] for row in results)}


def refresh(d):
    d['counts'] = {arm: {fmt: expected_aggregate([row for row in d['delayed']
        if row['arm'] == arm and (fmt == 'all' or row['format'] == fmt)])
        for fmt in ('all', 'original', 'changed')} for arm in mod.ARMS}
    bound = {(row['arm'], row['id']): row for row in d['delayed']}
    d['paired'] = []
    for number in range(1, 7):
        identity = f'Q{number:02d}'
        before, after = (bound[arm, identity]['result']['validation_status'] == 'accepted' for arm in mod.ARMS)
        classification = 'both_correct' if before and after else 'corrected' if after else 'regressed' if before else 'both_wrong'
        d['paired'].append({'id': identity, 'format': bound[mod.ARMS[0], identity]['format'],
                            'classification': classification})
    return d


def fixture():
    freeze = mod.MEMORY_FREEZE_UNIX
    prepared = freeze + 86460
    policies, inspections, actions = prepared + 10, prepared + 20, prepared + 30
    d = {'schema_version': 1, 'study_id': 'experience-retention-delayed-2026-10-29',
        'date': '2026-10-29', 'status': 'collected', 'sample': dict(mod.SAMPLE),
        'sources': copy.deepcopy(mod.SOURCE_FILES),
        'memory': {'sha256': mod.MEMORY_SHA256, 'canonical_characters': 5627,
                   'unchanged_from_phase_one': True},
        'clocks': {'minimum_elapsed_seconds': 86400, 'stage_freeze_clock_basis': 'local_filesystem_mtime',
            'memory_freeze': point(freeze),
            'not_before': point(freeze + 86400), 'collection_prepared': point(prepared),
            'policy_phase_authorization': point(prepared + .5),
            'policies_frozen': point(policies), 'inspection_phase_authorization': point(policies + .5),
            'inspections_frozen': point(inspections),
            'action_phase_authorization': point(inspections + .5),
            'actions_frozen': point(actions)}, 'delayed': [],
        'engineering': {'evidence_kind': 'synthetic_transport_preparation', 'tests_run': 17,
            'failures': 0, 'errors': 0, 'report_sha256': digest('engineering')},
        'scope': {**{key: True for key in mod.SCOPE_TRUE},
                  **{key: False for key in mod.SCOPE_FALSE}, 'provider_metadata': None},
        'provenance': {key: digest(key) for key in mod.PROVENANCE},
        'replay': {key: digest(key) for key in ('manifest_sha256', 'readme_sha256', 'zip_sha256')}}
    d['provenance'].update(action_loop_sha256=mod.ACTION_LOOP_SHA256,
        experience_io_sha256=mod.EXPERIENCE_IO_SHA256, protocol_sha256=mod.PROTOCOL_SHA256,
        phase_one_public_summary_sha256=mod.PHASE_ONE_SUMMARY_SHA256,
        memory_freeze_sha256=mod.MEMORY_FREEZE_SHA256,
        delayed_task_commitment_sha256=mod.DELAYED_TASK_SHA256,
        delayed_gold_commitment_sha256=mod.DELAYED_GOLD_SHA256)
    outcomes = {
        'no_experience': [('ok', True), ('execution_error', False), ('ok', True),
                          ('invalid_action', False), ('unavailable', False), ('ok', True)],
        'experience_record': [('ok', True), ('ok', True), ('ok', False),
                              ('invalid_action', False), ('ok', True), ('execution_error', False)]}
    for arm_index, arm in enumerate(mod.ARMS):
        for index, (source, (family, fmt)) in enumerate(mod.CATALOG.items()):
            identity = f'Q{index + 1:02d}'
            ordinal = arm_index * 6 + index
            inspect = index % 2 == 0 if arm_index == 0 else index in (1, 3)
            inspection = {'raw_sha256': d['sources'][family][fmt + '_sha256'],
                'raw_bytes_read': 250 + ordinal, 'returned_canonical_characters': 150 + ordinal,
                'observation_sha256': digest(arm + identity + '-observation'),
                'record_sha256': digest(arm + identity + '-inspection')} if inspect else None
            d['delayed'].append({'arm': arm, 'id': identity, 'source': source, 'family': family,
                'format': fmt, 'policy_decision': 'inspect' if inspect else 'submit',
                'inspection': inspection,
                'result': action(arm + identity, *outcomes[arm][index],
                    prediction=('accepted', 'uncertain', 'rejected')[index % 3],
                    characters=6001 if ordinal == 0 else 101 + ordinal),
                'clocks': {'initial_authoring': point(prepared + 1 + ordinal / 2),
                    'inspection': point(policies + 1 + ordinal / 2) if inspect else None,
                    'final_authoring': point(inspections + 1 + ordinal / 2) if inspect else None,
                    'execution': point(actions + 1 + ordinal)}})
    return refresh(d)


def json_bytes(value):
    return (mod.canonical(value) + '\n').encode()


def archive_bytes(files):
    output = BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, raw in sorted(files.items()):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, raw)
    return output.getvalue()


def seal_replay(bundle, archive, d, files):
    files['MANIFEST.json'] = json_bytes({'schema_version': 1, 'files': {
        name: {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
        for name, raw in sorted(files.items()) if name != 'MANIFEST.json'}})
    for name, raw in files.items():
        path = bundle / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    archive.parent.mkdir(parents=True, exist_ok=True)
    archive.write_bytes(archive_bytes(files))
    d['replay'] = {'manifest_sha256': hashlib.sha256(files['MANIFEST.json']).hexdigest(),
        'readme_sha256': hashlib.sha256(files['README.md']).hexdigest(),
        'zip_sha256': hashlib.sha256(archive.read_bytes()).hexdigest()}


def synthetic_inputs(root, d, external=False):
    """Create a coherent synthetic replay, never copying actual replay material."""
    files = {'README.md': b'# Synthetic saved-action fixture\n',
        'action_loop.py': b'# synthetic public action executor fixture\n',
        'experience_io.py': b'# synthetic public transport fixture\n',
        'replay.py': b'# synthetic saved-action replay fixture\n',
        'collection_metadata.json': json_bytes({'synthetic_collection': True}),
        'input/ACTION_CONTRACT.txt': b'Synthetic action contract fixture.\n',
        'input/SOURCE_PROVENANCE.json': json_bytes({'synthetic_provenance': True}),
        'input/DELAYED_TASKS.json': json_bytes({'synthetic_fixture': 'no real study task'}),
        'input/DELAYED_GOLD.json': json_bytes({'synthetic_fixture': 'no real study gold'})}
    empty = mod.canonical({'synthetic': ''})
    files['memory/experience_record.json'] = json_bytes({'synthetic': 'x' * (5627 - len(empty))})
    sources = {}
    for index, (family, source) in enumerate(mod.SOURCE_FILES.items(), 1):
        original = json_bytes({'synthetic_family': family, 'value': index})
        changed = json_bytes({'payload': {'synthetic_family': family, 'value': index}})
        public = root / source['public_path']
        public.parent.mkdir(parents=True, exist_ok=True)
        public.write_bytes(original)
        files['input/originals/' + family + '.json'] = original
        files['input/environment/migrated/' + family + '.json'] = changed
        sources[family] = {'public_path': source['public_path'],
            'original_sha256': hashlib.sha256(original).hexdigest(),
            'changed_sha256': hashlib.sha256(changed).hexdigest()}
    d['sources'] = copy.deepcopy(sources)
    original_map = {family: '../originals/' + family + '.json' for family in sources}
    changed_map = {family: 'migrated/' + family + '.json' for family in sources}
    files['input/environment/source_map_original.json'] = json_bytes(original_map)
    files['input/environment/source_map_changed.json'] = json_bytes(changed_map)
    files['input/environment/source_map_probes.json'] = json_bytes({source:
        (original_map if fmt == 'original' else changed_map)[family]
        for source, (family, fmt) in mod.CATALOG.items()})
    entries = []
    for index, row in enumerate(d['delayed']):
        key = row['arm'] + '-' + row['id']
        suffix = row['arm'] + '/' + row['id'] + '.json'
        result = row['result']
        saved_action = {'id': row['id'], 'prediction': result['prediction'],
                        'operation': 'synthetic_fixture', 'value': index}
        result['action_sha256'] = hashlib.sha256(mod.canonical(saved_action).encode()).hexdigest()
        result['canonical_characters'] = len(mod.canonical(saved_action))
        result['budget_exceeded'] = False
        action_file = 'actions/' + suffix
        selector = None
        files[action_file] = json_bytes(saved_action)
        saved_policy = {'id': row['id'], 'decision': row['policy_decision']}
        if row['inspection'] is None:
            saved_policy['action'] = saved_action
        else:
            saved_policy['rationale'] = 'synthetic optional structural inspection'
        policy_file = 'policies/' + suffix
        files[policy_file] = json_bytes(saved_policy)
        error = None
        if result['error'] is not None:
            error = {'type': result['error']['type'], 'message': 'synthetic recorded failure ' + key}
            result['error']['sha256'] = hashlib.sha256(mod.canonical(error).encode()).hexdigest()
        if result['artifact_sha256'] is not None:
            artifact = json_bytes({'id': row['id'], 'synthetic_value': index})
            files['artifacts/' + suffix] = artifact
            result['artifact_sha256'] = hashlib.sha256(artifact).hexdigest()
        inspection_file = None
        if row['inspection'] is not None:
            inspection_file = 'observations/' + suffix
            inspection = row['inspection']
            inspection['raw_sha256'] = sources[row['family']][row['format'] + '_sha256']
            observation = {'synthetic_structure': ['value'], 'synthetic_family': row['family']}
            record = {'source': row['source'], 'raw_sha256': inspection['raw_sha256'],
                'raw_bytes_read': inspection['raw_bytes_read'],
                'returned_canonical_characters': inspection['returned_canonical_characters'],
                'observation': observation}
            files[inspection_file] = json_bytes(record)
            inspection['record_sha256'] = hashlib.sha256(files[inspection_file]).hexdigest()
            inspection['observation_sha256'] = hashlib.sha256(mod.canonical(observation).encode()).hexdigest()
        entries.append({'key': 'delayed_' + key, 'task_id': row['id'], 'source': row['source'],
            'map': 'probes', 'action_file': action_file, 'action_selector': selector,
            'policy_file': policy_file, 'policy_selector': None,
            'expected_file': 'input/DELAYED_GOLD.json',
            'expected_result': {'id': row['id'], 'execution_status': result['execution_status'],
                'validation_status': result['validation_status'], 'artifact_sha256': result['artifact_sha256'],
                'error': error}, 'inspection_file': inspection_file})
    files['replay_plan.json'] = json_bytes({'schema_version': 1, 'entries': entries})
    phase_one_raw = json_bytes({'synthetic_phase_one': True, 'delay': {'status': 'uncollected_pending'}})
    old_summary = root / mod.phase_one.DATA_FILE
    old_summary.parent.mkdir(parents=True, exist_ok=True)
    old_summary.write_bytes(phase_one_raw)
    bindings = {'SOURCE_FILES': sources, 'PHASE_ONE_SUMMARY_SHA256': hashlib.sha256(phase_one_raw).hexdigest()}
    for name, constant, provenance in [('action_loop.py', 'ACTION_LOOP_SHA256', 'action_loop_sha256'),
            ('experience_io.py', 'EXPERIENCE_IO_SHA256', 'experience_io_sha256'),
            ('memory/experience_record.json', 'MEMORY_SHA256', None),
            ('input/DELAYED_TASKS.json', 'DELAYED_TASK_SHA256', 'delayed_task_commitment_sha256'),
            ('input/DELAYED_GOLD.json', 'DELAYED_GOLD_SHA256', 'delayed_gold_commitment_sha256')]:
        value = hashlib.sha256(files[name]).hexdigest()
        bindings[constant] = value
        if provenance is not None:
            d['provenance'][provenance] = value
    d['provenance']['phase_one_public_summary_sha256'] = bindings['PHASE_ONE_SUMMARY_SHA256']
    d['memory']['sha256'] = bindings['MEMORY_SHA256']
    refresh(d)
    bundle = root / ('external-replay' if external else mod.REPLAY)
    archive = root / ('external-replay.zip' if external else mod.ZIP_FILE)
    seal_replay(bundle, archive, d, files)
    return bundle, archive, files, bindings


@contextmanager
def synthetic_bindings(bindings, *modules):
    with ExitStack() as stack:
        for target in modules or (mod,):
            for name, value in bindings.items():
                stack.enter_context(patch.object(target, name, value))
        yield


def temporary_site(root):
    stories = ['<section class="story" data-mechanism="synthetic-' + str(index)
               + '"><p>synthetic story ' + str(index) + '</p><script>syntheticAnimation('
               + str(index) + ')</script></section>' for index in range(1, 5)]
    identities = [f'synthetic-older-{index:02d}' for index in range(1, 9)]
    identities += ['experience-retention', 'tool-observation-loop']
    cards = ['<article class="study-card" data-study="' + identity + '"><h3>' + identity
             + '</h3><p>at-publication uncollected_pending preserved</p></article>' for identity in identities]
    old_blocks = ['<!-- EXPERIENCE_RETENTION_STUDY_START -->\nImmediate study: uncollected_pending.\n'
                  '<!-- EXPERIENCE_RETENTION_STUDY_END -->\n\n',
                  '<!-- TOOL_OBSERVATION_LOOP_STUDY_START -->\nEarlier typed pilot.\n'
                  '<!-- TOOL_OBSERVATION_LOOP_STUDY_END -->\n\n']
    files = {}
    for lang, name in [('ja', 'index.html'), ('en', 'index.en.html')]:
        files[name] = ('<html lang="' + lang + '"><body><section class="latest-study" '
            + 'data-source="data/tool-observation-loop-2026-10-28.json"><p>previous latest</p></section>'
            + ''.join(stories) + '</body></html>').encode()
    for lang, name in [('ja', 'results.html'), ('en', 'results.en.html')]:
        files[name] = ('<html lang="' + lang + '"><body><div class="status-strip">old status</div>\n'
            + '<div class="hero-metrics"><div class="metric">old metrics</div></div>'
            + '<section class="section" id="studies"><div class="section-heading"><h2>Studies</h2></div>'
            + ''.join(cards) + '</section></body></html>').encode()
    files['README.md'] = ('# Synthetic site\n\n' + ''.join(old_blocks)
        + '## Public and private scope\nExisting scope.\n\n'
        + '## Build and verify the website\nExisting ten-study build instructions.\n\n'
        + '## Preservation\nPreserve ten dated studies and four stories.\n').encode()
    files['sitemap.xml'] = b'<urlset><url><loc>https://example.invalid/older/</loc></url></urlset>'
    for index, identity in enumerate(identities):
        study = ('studies/synthetic-older-' + str(index) + '/') if index < 8 else (
            mod.phase_one.STUDY if index == 8 else 'studies/2026-10-28-tool-observation-loop/')
        for name in ('index.html', 'en.html'):
            files[study + name] = b'<html><p>immutable old study: uncollected_pending</p></html>\n'
        files['data/synthetic-older-' + str(index) + '.json'] = b'{"old":"uncollected_pending"}\n'
        files['experiments/synthetic-older-' + str(index) + '/MANIFEST.json'] = b'{"synthetic_old":true}\n'
        files['downloads/synthetic-older-' + str(index) + '.zip'] = b'synthetic old archive bytes\n'
    for index in range(1, 5):
        files['assets/synthetic-story-' + str(index) + '.js'] = ('syntheticAnimation(' + str(index) + ');\n').encode()
    for name, raw in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    return stories, cards, old_blocks


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.ids, self.refs, self.languages = [], [], []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        if tag == 'html':
            self.languages.append(attrs.get('lang'))
        self.refs.extend(attrs[key] for key in ('href', 'src') if attrs.get(key))


class DelayedExperienceSchemaEngineering(unittest.TestCase):
    def setUp(self):
        self.d = fixture()

    def test_complete_synthetic_fixture_recalculates_strata_pairs_and_costs(self):
        self.assertIs(mod.validate_summary(self.d), self.d)
        self.assertEqual(mod.recalculate(self.d['delayed']), {key: self.d[key] for key in ('counts', 'paired')})
        self.assertEqual(set(row['classification'] for row in self.d['paired']), set(mod.CLASSIFICATIONS))
        self.assertEqual(mod.paired_counts(self.d), {'both_correct': 1, 'corrected': 2, 'regressed': 2, 'both_wrong': 1})
        self.assertEqual(len(self.d['delayed']), 12)
        for arm in mod.ARMS:
            rows = [row for row in self.d['delayed'] if row['arm'] == arm]
            self.assertEqual(len(rows), 6)
            self.assertEqual({family: sum(row['family'] == family for row in rows) for family in self.d['sources']},
                             {'X01': 2, 'X02': 2, 'X03': 2})
            for fmt in mod.FORMATS:
                self.assertEqual(sum(row['format'] == fmt for row in rows), 3)
                self.assertEqual(sum(mod.paired_counts(self.d, fmt).values()), 3)
            self.assertEqual(self.d['counts'][arm]['all'], expected_aggregate(rows))
            self.assertEqual(mod.phase_one.aggregate_attempts([(row['result'], row['inspection']) for row in rows]),
                             expected_aggregate(rows))
        self.assertTrue(mod.efficient_record_use(self.d))
        ranges = mod.clock_ranges(self.d)
        for stage, (first, last) in ranges.items():
            values = [row['clocks'][stage]['unix_seconds'] for row in self.d['delayed']
                      if row['clocks'][stage] is not None]
            self.assertEqual((first, last), (min(values), max(values)))

    def test_every_nested_dictionary_rejects_unknown_private_fields(self):
        for path in paths(self.d, lambda value: isinstance(value, dict)):
            bad = copy.deepcopy(self.d)
            at(bad, path)['private_source'] = 'PRIVATE_SENTINEL'
            with self.subTest(path=path), self.assertRaises(ValueError):
                mod.validate_summary(bad)

    def test_every_leaf_rejects_unallowlisted_free_text(self):
        for path in paths(self.d, lambda value: not isinstance(value, (dict, list))):
            with self.subTest(path=path), self.assertRaises(ValueError):
                mod.validate_summary(replaced(self.d, path, 'PRIVATE_SENTINEL'))

    def test_boolean_integer_and_flag_types_are_never_interchangeable(self):
        for path in paths(self.d, lambda value: type(value) is int):
            for value in (True, False, 1.0):
                with self.subTest(path=path, value=value), self.assertRaises(ValueError):
                    mod.validate_summary(replaced(self.d, path, value))
        for path in paths(self.d, lambda value: type(value) is bool):
            with self.subTest(path=path), self.assertRaises(ValueError):
                mod.validate_summary(replaced(self.d, path, int(at(self.d, path))))

    def test_frozen_memory_sources_code_and_commitments_cannot_be_replaced(self):
        for field, value in [('sha256', digest('changed-memory')), ('canonical_characters', 5626),
                             ('unchanged_from_phase_one', False)]:
            bad = copy.deepcopy(self.d)
            bad['memory'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                mod.validate_summary(bad)
        for field in ('action_loop_sha256', 'experience_io_sha256', 'protocol_sha256',
                      'phase_one_public_summary_sha256', 'memory_freeze_sha256',
                      'delayed_task_commitment_sha256', 'delayed_gold_commitment_sha256'):
            bad = copy.deepcopy(self.d)
            bad['provenance'][field] = digest('substitution-' + field)
            with self.subTest(field=field), self.assertRaises(ValueError):
                mod.validate_summary(bad)
        for family in self.d['sources']:
            for field in self.d['sources'][family]:
                bad = copy.deepcopy(self.d)
                bad['sources'][family][field] = 'data/synthetic-other.json' if field == 'public_path' else digest('different-source')
                with self.subTest(family=family, field=field), self.assertRaises(ValueError):
                    mod.validate_summary(bad)
        for field in self.d['sample']:
            bad = copy.deepcopy(self.d)
            bad['sample'][field] += 1
            with self.subTest(field=field), self.assertRaises(ValueError):
                mod.validate_summary(bad)

    def test_every_count_pair_and_engineering_denominator_is_checked(self):
        for path in paths(self.d['counts'], lambda value: type(value) is int):
            bad = copy.deepcopy(self.d)
            target = ('counts',) + path
            at(bad, target[:-1])[target[-1]] += 1
            with self.subTest(path=target), self.assertRaises(ValueError):
                mod.validate_summary(bad)
        for index in range(6):
            bad = copy.deepcopy(self.d)
            row = bad['paired'][index]
            row['classification'] = next(value for value in mod.CLASSIFICATIONS if value != row['classification'])
            with self.subTest(index=index), self.assertRaises(ValueError):
                mod.validate_summary(bad)
        for field, value in [('tests_run', 18), ('failures', 18), ('errors', 18),
                             ('evidence_kind', 'actual_functional_pilot')]:
            bad = copy.deepcopy(self.d)
            bad['engineering'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                mod.validate_summary(bad)

    def test_fixed_arm_item_source_family_format_bindings_are_complete_and_unique(self):
        for field, value in [('arm', 'other'), ('id', 'Q99'), ('source', 'A06'),
                             ('family', 'X03'), ('format', 'original')]:
            bad = copy.deepcopy(self.d)
            bad['delayed'][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                mod.validate_summary(bad)
        for collection in ('delayed', 'paired'):
            for mutation in ('missing', 'duplicate', 'extra'):
                bad = copy.deepcopy(self.d)
                if mutation == 'missing':
                    bad[collection].pop()
                elif mutation == 'duplicate':
                    bad[collection][-1] = copy.deepcopy(bad[collection][-2])
                else:
                    bad[collection].append(copy.deepcopy(bad[collection][-1]))
                with self.subTest(collection=collection, mutation=mutation), self.assertRaises(ValueError):
                    mod.validate_summary(bad)

    def test_actual_minimum_elapsed_time_and_all_global_clock_orderings_are_guarded(self):
        seconds = {key: self.d['clocks'][key]['unix_seconds'] for key in mod.TOP_CLOCKS}
        changes = [('memory_freeze', seconds['memory_freeze'] + 1),
                   ('not_before', seconds['not_before'] - 1),
                   ('collection_prepared', seconds['not_before'] - .01),
                   ('policy_phase_authorization', seconds['collection_prepared'] - .01),
                   ('policies_frozen', seconds['policy_phase_authorization'] - .01),
                   ('inspection_phase_authorization', seconds['policies_frozen'] - .01),
                   ('inspections_frozen', seconds['inspection_phase_authorization'] - .01),
                   ('action_phase_authorization', seconds['inspections_frozen'] - .01),
                   ('actions_frozen', seconds['action_phase_authorization'] - .01)]
        for field, value in changes:
            bad = copy.deepcopy(self.d)
            bad['clocks'][field] = point(value)
            with self.subTest(field=field), self.assertRaises(ValueError):
                mod.validate_summary(bad)
        bad = copy.deepcopy(self.d)
        bad['clocks']['minimum_elapsed_seconds'] = 86399
        with self.assertRaises(ValueError):
            mod.validate_summary(bad)

    def test_item_initial_inspection_final_and_execution_clocks_follow_all_freezes(self):
        times = {key: self.d['clocks'][key]['unix_seconds'] for key in mod.TOP_CLOCKS}
        changes = [('initial_authoring', times['collection_prepared'] - .01),
                   ('initial_authoring', times['policies_frozen'] + .01),
                   ('inspection', times['inspection_phase_authorization'] - .01),
                   ('inspection', times['inspections_frozen'] + .01),
                   ('final_authoring', times['inspections_frozen'] - .01),
                   ('final_authoring', times['actions_frozen'] + .01),
                   ('execution', times['actions_frozen'] - .01)]
        for field, value in changes:
            bad = copy.deepcopy(self.d)
            bad['delayed'][0]['clocks'][field] = point(value)
            with self.subTest(field=field, seconds=value), self.assertRaises(ValueError):
                mod.validate_summary(bad)
        bad = copy.deepcopy(self.d)
        bad['delayed'][1]['clocks']['inspection'] = point(times['policies_frozen'])
        with self.assertRaises(ValueError):
            mod.validate_summary(bad)
        bad = copy.deepcopy(self.d)
        bad['delayed'][0]['clocks']['inspection'] = None
        with self.assertRaises(ValueError):
            mod.validate_summary(bad)
        for index, value in ((0, None), (1, point(times['actions_frozen']))):
            bad = copy.deepcopy(self.d)
            bad['delayed'][index]['clocks']['final_authoring'] = value
            with self.subTest(index=index, final=value), self.assertRaises(ValueError):
                mod.validate_summary(bad)
        good = copy.deepcopy(self.d)
        for row in good['delayed']:
            row['clocks'].update(initial_authoring=point(times['policies_frozen']),
                execution=point(times['actions_frozen']))
            if row['inspection'] is not None:
                row['clocks']['inspection'] = point(times['inspections_frozen'])
                row['clocks']['final_authoring'] = point(times['actions_frozen'])
        self.assertIs(mod.validate_summary(good), good)

    def test_every_clock_requires_matching_finite_positive_utc_and_unix_values(self):
        clock_paths = paths(self.d, lambda value: isinstance(value, dict) and set(value) == {'utc', 'unix_seconds'})
        for path in clock_paths:
            for value in (True, False, 0, -1, float('nan'), float('inf'), float('-inf'), 10 ** 1000):
                bad = copy.deepcopy(self.d)
                at(bad, path)['unix_seconds'] = value
                with self.subTest(path=path, value=str(value)[:20]), self.assertRaises(ValueError):
                    mod.validate_summary(bad)
            bad = copy.deepcopy(self.d)
            at(bad, path)['unix_seconds'] += 1
            with self.subTest(path=path, mismatch=True), self.assertRaises(ValueError):
                mod.validate_summary(bad)
        for utc in ('2026-10-29', '2026-10-29T00:00:00', '2026-10-29T09:00:00+09:00',
                    '2026-02-30T00:00:00Z', '2026-10-29T00:00:00.1234567Z'):
            bad = copy.deepcopy(self.d)
            bad['clocks']['collection_prepared']['utc'] = utc
            with self.subTest(utc=utc), self.assertRaises(ValueError):
                mod.validate_summary(bad)

    def test_optional_inspection_policy_source_cost_and_failed_action_invariants(self):
        changes = [(0, 'policy_decision', 'submit'), (1, 'policy_decision', 'inspect'),
                   (0, 'inspection', None), (1, 'inspection', copy.deepcopy(self.d['delayed'][0]['inspection']))]
        for index, field, value in changes:
            bad = copy.deepcopy(self.d)
            bad['delayed'][index][field] = value
            with self.subTest(index=index, field=field), self.assertRaises(ValueError):
                mod.validate_summary(bad)
        for field, value in [('raw_sha256', digest('wrong-inspection-source')),
                             ('raw_bytes_read', 0), ('returned_canonical_characters', 0)]:
            bad = copy.deepcopy(self.d)
            bad['delayed'][0]['inspection'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                mod.validate_summary(bad)
        changes = [(1, 'error', None), (1, 'artifact_sha256', digest('impossible-failed-artifact')),
                   (1, 'validation_status', 'accepted'), (0, 'execution_status', 'unavailable'),
                   (0, 'error', {'type': 'ActionError', 'sha256': digest('spurious-error')}),
                   (0, 'prediction_agreement', False), (1, 'prediction_agreement', True),
                   (0, 'budget_exceeded', False), (0, 'canonical_characters', 0)]
        for index, field, value in changes:
            bad = copy.deepcopy(self.d)
            bad['delayed'][index]['result'][field] = value
            with self.subTest(index=index, field=field), self.assertRaises(ValueError):
                mod.validate_summary(bad)

    def test_duplicate_nested_json_and_nonfinite_numbers_fail_before_publication(self):
        for path in paths(self.d, lambda value: isinstance(value, dict)):
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, 'Duplicate'):
                mod.parse_json(duplicate_json(self.d, path).encode())
        for token in ('NaN', 'Infinity', '-Infinity'):
            text = json.dumps(self.d).replace('"canonical_characters": 5627', '"canonical_characters":' + token, 1)
            with self.subTest(token=token), self.assertRaisesRegex(ValueError, 'Nonfinite'):
                mod.parse_json(text.encode())

    def test_efficient_use_requires_all_predeclared_outcome_and_inspection_conditions(self):
        self.assertTrue(mod.efficient_record_use(self.d))
        for field, value in [('accepted', 4), ('inspections', 3), ('execution_errors', 2),
                             ('invalid_actions', 2), ('abstentions', 2)]:
            bad = copy.deepcopy(self.d)
            bad['counts']['experience_record']['all'][field] = value
            with self.subTest(field=field):
                self.assertFalse(mod.efficient_record_use(bad))


class DelayedReplayEngineering(unittest.TestCase):
    def test_coherent_synthetic_saved_actions_sources_and_replay_bytes_validate(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            d = fixture()
            bundle, archive, files, bindings = synthetic_inputs(root, d)
            before = snapshot(root)
            with synthetic_bindings(bindings):
                self.assertIs(mod.validate_summary(d), d)
                verified, raw = mod.require_public_inputs(root, d)
                self.assertEqual(verified, files)
                self.assertEqual(raw, archive.read_bytes())
                self.assertIsNone(mod._bind_saved_records(d, files))
                self.assertEqual(len(mod.REPLAY_FIXED_FILES), 21)
                expected = set(mod.REPLAY_FIXED_FILES)
                for row in d['delayed']:
                    suffix = row['arm'] + '/' + row['id'] + '.json'
                    expected.update({'actions/' + suffix, 'policies/' + suffix})
                    if row['inspection'] is not None:
                        expected.add('observations/' + suffix)
                    if row['result']['artifact_sha256'] is not None:
                        expected.add('artifacts/' + suffix)
                self.assertEqual(set(files), expected)
            self.assertEqual(snapshot(root), before)
            self.assertEqual(archive.read_bytes(), archive_bytes(files))
            with zipfile.ZipFile(archive) as zipped:
                self.assertEqual(zipped.namelist(), sorted(files))
                self.assertEqual({name: zipped.read(name) for name in zipped.namelist()}, files)

    def test_known_public_sources_and_immutable_phase_one_bytes_are_required(self):
        for target in ('source', 'phase_one'):
            for mutation in ('missing', 'changed'):
                with self.subTest(target=target, mutation=mutation), TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    d = fixture()
                    _, _, _, bindings = synthetic_inputs(root, d)
                    path = root / (next(iter(d['sources'].values()))['public_path']
                                   if target == 'source' else mod.phase_one.DATA_FILE)
                    if mutation == 'missing':
                        path.unlink()
                    else:
                        path.write_bytes(b'changed synthetic public bytes\n')
                    before = snapshot(root)
                    with synthetic_bindings(bindings), self.assertRaises(ValueError):
                        mod.require_public_inputs(root, d)
                    self.assertEqual(snapshot(root), before)

    def test_manifest_exact_case_inventory_hash_sizes_and_separate_zip_are_guarded(self):
        for mutation in ('lowercase_manifest', 'missing_readme', 'tampered_file', 'tampered_archive',
                         'extra_file', 'manifest_boolean_size', 'manifest_unknown_field'):
            with self.subTest(mutation=mutation), TemporaryDirectory() as temporary:
                root = Path(temporary)
                d = fixture()
                bundle, archive, files, bindings = synthetic_inputs(root, d)
                if mutation == 'lowercase_manifest':
                    (bundle / 'MANIFEST.json').rename(bundle / 'manifest.json')
                elif mutation == 'missing_readme':
                    (bundle / 'README.md').unlink()
                elif mutation == 'tampered_file':
                    (bundle / 'replay.py').write_bytes(b'changed synthetic replay\n')
                elif mutation == 'tampered_archive':
                    archive.write_bytes(b'changed synthetic archive\n')
                elif mutation == 'extra_file':
                    (bundle / 'unlisted.txt').write_bytes(b'unlisted synthetic bytes\n')
                else:
                    manifest = json.loads(files['MANIFEST.json'])
                    if mutation == 'manifest_boolean_size':
                        manifest['files']['README.md']['bytes'] = True
                    else:
                        manifest['files']['README.md']['private_source'] = 'PRIVATE_SENTINEL'
                    files['MANIFEST.json'] = json_bytes(manifest)
                    (bundle / 'MANIFEST.json').write_bytes(files['MANIFEST.json'])
                    d['replay']['manifest_sha256'] = hashlib.sha256(files['MANIFEST.json']).hexdigest()
                    archive.write_bytes(archive_bytes(files))
                    d['replay']['zip_sha256'] = hashlib.sha256(archive.read_bytes()).hexdigest()
                with synthetic_bindings(bindings), self.assertRaises((ValueError, zipfile.BadZipFile)):
                    mod.require_public_inputs(root, d)

    def test_rehashed_missing_frozen_code_memory_tasks_gold_maps_and_sources_fail(self):
        names = ['action_loop.py', 'experience_io.py', 'memory/experience_record.json',
                 'input/DELAYED_TASKS.json', 'input/DELAYED_GOLD.json', 'replay.py', 'replay_plan.json',
                 'collection_metadata.json', 'input/ACTION_CONTRACT.txt', 'input/SOURCE_PROVENANCE.json',
                 'input/environment/source_map_original.json', 'input/environment/source_map_changed.json',
                 'input/environment/source_map_probes.json']
        names += ['input/' + prefix + '/' + family + '.json'
                  for prefix in ('originals', 'environment/migrated') for family in ('X01', 'X02', 'X03')]
        for name in names:
            with self.subTest(name=name), TemporaryDirectory() as temporary:
                root = Path(temporary)
                d = fixture()
                bundle, archive, files, bindings = synthetic_inputs(root, d)
                del files[name]
                (bundle / name).unlink()
                seal_replay(bundle, archive, d, files)
                with synthetic_bindings(bindings), self.assertRaises(ValueError):
                    mod.require_public_inputs(root, d)

    def test_private_paths_unsafe_file_types_and_symlinks_never_enter_replay(self):
        for name, raw in [('notes.txt', b'private local path /' + b'Users/synthetic-person/record'),
                          ('native/summary.json', b'{}'), ('vendor/code.py', b'# synthetic'),
                          ('actors/record.json', b'{}'), ('extra.db', b'synthetic'),
                          ('extra.jsonl', b'{}'), ('extra.bin', b'synthetic')]:
            with self.subTest(name=name), TemporaryDirectory() as temporary:
                root = Path(temporary)
                d = fixture()
                bundle, archive, files, bindings = synthetic_inputs(root, d)
                files[name] = raw
                seal_replay(bundle, archive, d, files)
                with synthetic_bindings(bindings), self.assertRaises(ValueError):
                    mod.require_public_inputs(root, d)
        for kind in ('bundle_link', 'archive_link', 'file_link', 'archive_inside_bundle'):
            with self.subTest(kind=kind), TemporaryDirectory() as temporary:
                root = Path(temporary)
                d = fixture()
                bundle, archive, _, bindings = synthetic_inputs(root, d)
                selected_bundle, selected_archive = bundle, archive
                if kind == 'bundle_link':
                    selected_bundle = root / 'bundle-link'
                    selected_bundle.symlink_to(bundle, target_is_directory=True)
                elif kind == 'archive_link':
                    selected_archive = root / 'archive-link.zip'
                    selected_archive.symlink_to(archive)
                elif kind == 'file_link':
                    target = root / 'linked-readme.txt'
                    target.write_bytes((bundle / 'README.md').read_bytes())
                    (bundle / 'README.md').unlink()
                    (bundle / 'README.md').symlink_to(target)
                else:
                    selected_archive = bundle / 'inside.zip'
                    selected_archive.write_bytes(archive.read_bytes())
                with synthetic_bindings(bindings), self.assertRaises(ValueError):
                    mod.require_public_inputs(root, d, selected_bundle, selected_archive)
        for name in ('', '/absolute.json', '../escape.json', './alias.json', 'a/../b.json',
                     'a//b.json', 'a\\b.json', 'C:relative.json', 'a\x00b.json'):
            with self.subTest(name=name):
                self.assertFalse(mod._safe_name(name))

    def test_zip_exact_inventory_bytes_and_entry_types_are_guarded_after_rehashing(self):
        for mutation in ('missing', 'changed', 'extra', 'duplicate', 'symlink'):
            with self.subTest(mutation=mutation), TemporaryDirectory() as temporary:
                root = Path(temporary)
                d = fixture()
                _, archive, files, bindings = synthetic_inputs(root, d)
                with zipfile.ZipFile(archive, 'w') as zipped:
                    for name, raw in sorted(files.items()):
                        if mutation == 'missing' and name == 'README.md':
                            continue
                        info = zipfile.ZipInfo(name)
                        info.create_system = 3
                        info.external_attr = (0o120777 if mutation == 'symlink' and name == 'README.md' else 0o100644) << 16
                        zipped.writestr(info, b'changed' if mutation == 'changed' and name == 'README.md' else raw)
                    if mutation in ('extra', 'duplicate'):
                        with self.assertWarns(UserWarning) if mutation == 'duplicate' else ExitStack():
                            zipped.writestr('README.md' if mutation == 'duplicate' else 'extra.txt', b'synthetic extra')
                d['replay']['zip_sha256'] = hashlib.sha256(archive.read_bytes()).hexdigest()
                with synthetic_bindings(bindings), self.assertRaises(ValueError):
                    mod.require_public_inputs(root, d)

    def test_saved_plan_identity_action_policy_inspection_and_source_bindings_fail_closed(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            d = fixture()
            _, _, files, bindings = synthetic_inputs(root, d)
            mutations = [('key', 'delayed_no_experience-Q99'), ('task_id', 'Q02'), ('source', 'A02'),
                         ('map', 'original'), ('expected_file', 'input/DELAYED_TASKS.json'),
                         ('action_file', '../private.json'), ('action_selector', True),
                         ('policy_selector', True), ('inspection_file', None)]
            for field, value in mutations:
                bad = copy.deepcopy(files)
                plan = json.loads(bad['replay_plan.json'])
                plan['entries'][0][field] = value
                bad['replay_plan.json'] = json_bytes(plan)
                with synthetic_bindings(bindings), self.subTest(field=field), self.assertRaises(ValueError):
                    mod._bind_saved_records(d, bad)
            for mutation in ('action', 'policy', 'submit_lock', 'inspection', 'map_source', 'expected_result', 'error'):
                bad = copy.deepcopy(files)
                plan = json.loads(bad['replay_plan.json'])
                first, second = plan['entries'][:2]
                if mutation == 'action':
                    saved = json.loads(bad[first['action_file']])
                    saved['prediction'] = 'uncertain'
                    bad[first['action_file']] = json_bytes(saved)
                elif mutation == 'policy':
                    saved = json.loads(bad[first['policy_file']])
                    saved['decision'] = 'submit'
                    bad[first['policy_file']] = json_bytes(saved)
                elif mutation == 'submit_lock':
                    saved = json.loads(bad[second['policy_file']])
                    saved['action']['value'] = -1
                    bad[second['policy_file']] = json_bytes(saved)
                elif mutation == 'inspection':
                    saved = json.loads(bad[first['inspection_file']])
                    saved['raw_bytes_read'] += 1
                    bad[first['inspection_file']] = json_bytes(saved)
                elif mutation == 'map_source':
                    name = 'input/environment/source_map_probes.json'
                    saved = json.loads(bad[name])
                    saved['A01'] = '../originals/X02.json'
                    bad[name] = json_bytes(saved)
                elif mutation == 'expected_result':
                    first['expected_result']['artifact_sha256'] = digest('different-artifact')
                else:
                    second['expected_result']['error']['message'] = 'different synthetic error'
                bad['replay_plan.json'] = json_bytes(plan)
                with synthetic_bindings(bindings), self.subTest(mutation=mutation), self.assertRaises(ValueError):
                    mod._bind_saved_records(d, bad)


class DelayedRenderingEngineering(unittest.TestCase):
    def test_ja_en_pages_keep_matching_accessible_ids_downloads_and_clock_meanings(self):
        d = fixture()
        pages = {}
        for lang in ('ja', 'en'):
            html = mod.render(lang, d)
            page = Page(html)
            pages[lang] = page
            self.assertEqual(page.languages, [lang])
            self.assertEqual(len(page.ids), len(set(page.ids)))
            for identity in ('actual-clocks', 'delayed-comparison', 'all-records', 'saved-replay', 'limits'):
                self.assertIn(identity, page.ids)
            for ref in ('../../' + mod.DATA_FILE, '../../' + mod.ZIP_FILE,
                        '../../' + mod.REPLAY + 'README.md', 'experience-retention-delayed.css',
                        '../2026-10-28-experience-retention/' + ('index.html' if lang == 'ja' else 'en.html')):
                self.assertIn(ref, page.refs)
            self.assertEqual(html.count('class="erd-scroll-hint"'), html.count('<table '))
            self.assertEqual(html.count('<caption><span class="erd-caption">'), html.count('<table '))
            self.assertIn('左右にスクロール' if lang == 'ja' else 'scroll horizontally', html)
            self.assertNotIn('PRIVATE_SENTINEL', html)
            self.assertNotIn('<script', html)
        self.assertEqual(set(pages['ja'].ids), set(pages['en'].ids))
        english = mod.render('en', d)
        for phrase in ('not a trial at exactly 24 hours', 'pre-call authoring authorization receipts',
                       'Provider sampling starts are unavailable', 'Native item execution start',
                       'Direct submission has no second authoring call', 'not total source I/O',
                       'same record has 5627 canonical characters', 'not a time-only effect or forgetting',
                       'keeps its at-publication pending state unchanged', 'does not regenerate fresh AI choices'):
            self.assertIn(phrase, english)
        with self.assertRaises(ValueError):
            mod.render('fr', d)

    def test_direct_submit_without_second_authorization_is_renderable_and_not_invented(self):
        d = fixture()
        for row in d['delayed']:
            row.update(policy_decision='submit', inspection=None)
            row['clocks'].update(inspection=None, final_authoring=None)
        refresh(d)
        self.assertIs(mod.validate_summary(d), d)
        self.assertIsNone(mod.clock_ranges(d)['final_authoring'])
        html = mod.render('en', d)
        self.assertIn('Direct submission has no second authoring call', html)
        self.assertIn('<th scope="row">Final authoring authorization</th><td>—</td><td>—</td><td>—</td>', html)
        self.assertIn('criterion was not met', mod.finding(d, 'en'))

    def test_finding_uses_actual_counts_and_does_not_invent_benefit_from_equal_acceptance(self):
        d = fixture()
        finding = mod.finding(d, 'en')
        self.assertIn('3/6 without the record → 3/6', finding)
        self.assertIn('inspections were 3 → 2', finding)
        self.assertIn('shows no accuracy gain', finding)
        self.assertIn('meet the predeclared bounded criterion', finding)
        self.assertIn('2 corrected and 2 regressed', finding)
        for row in d['delayed']:
            if row['arm'] == 'experience_record' and row['inspection'] is not None:
                row.update(policy_decision='submit', inspection=None)
                row['clocks'].update(inspection=None, final_authoring=None)
        refresh(d)
        self.assertIs(mod.validate_summary(d), d)
        self.assertIn('inspections were 3 → 0', mod.finding(d, 'en'))
        for row in d['delayed']:
            if row['arm'] == 'no_experience' and row['inspection'] is not None:
                row.update(policy_decision='submit', inspection=None)
                row['clocks'].update(inspection=None, final_authoring=None)
        refresh(d)
        self.assertIs(mod.validate_summary(d), d)
        finding = mod.finding(d, 'en')
        self.assertIn('criterion was not met', finding)
        self.assertIn('shows no accuracy gain', finding)
        self.assertIn('Speed, token, compute and spending savings were not measured', finding)


class DelayedPublicationEngineering(unittest.TestCase):
    def test_absence_is_identity_and_missing_explicit_source_refuses_without_writes(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'preserved.txt').write_bytes(b'synthetic preserved bytes\n')
            before = snapshot(root)
            self.assertIsNone(mod.optional_summary(root))
            self.assertIsNone(pub.optional_summary(root))
            self.assertEqual(pub.prepare_updates(root), {})
            self.assertEqual(mod.build_plan(root), {})
            self.assertEqual(pub.prepare_updates(root, bundle=root / 'missing-bundle', zip_path=root / 'missing.zip'), {})
            with self.assertRaises(FileNotFoundError):
                mod.load_summary(root)
            missing = root / 'missing-explicit-export.json'
            for call in (mod.optional_summary, mod.load_summary, pub.prepare_updates, mod.build_plan):
                with self.subTest(call=call.__name__), self.assertRaises((ValueError, FileNotFoundError)):
                    call(root, missing)
                self.assertEqual(snapshot(root), before)
        for call, args in [(pub.integrate_home, ('preserved', 'ja', None)),
                           (pub.integrate_listing, ('preserved', 'en', None)),
                           (pub.integrate_readme, ('preserved', None)),
                           (pub.integrate_sitemap, ('preserved', None))]:
            self.assertEqual(call(*args), 'preserved')

    def test_invalid_default_or_explicit_export_refuses_before_any_plan_or_writes(self):
        d = fixture()
        invalid = [b'{}', duplicate_json(d, ('delayed', 0, 'clocks')).encode(),
                   json.dumps(d).replace('"canonical_characters": 5627', '"canonical_characters": NaN', 1).encode()]
        for raw in invalid:
            for explicit in (False, True):
                with self.subTest(prefix=raw[:30], explicit=explicit), TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    temporary_site(root)
                    source = root / ('external-public-export.json' if explicit else mod.DATA_FILE)
                    source.parent.mkdir(parents=True, exist_ok=True)
                    source.write_bytes(raw)
                    before = snapshot(root)
                    for call in (mod.optional_summary, mod.load_summary, pub.prepare_updates, mod.build_plan):
                        with self.subTest(call=call.__name__), self.assertRaises(ValueError):
                            call(root, source if explicit else None)
                        self.assertEqual(snapshot(root), before)
                    self.assertFalse((root / mod.STUDY).exists())

    def test_export_directory_or_symlink_is_rejected_before_reading_replay(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'synthetic.json'
            write_json(source, fixture())
            directory = root / 'directory.json'
            directory.mkdir()
            link = root / 'linked.json'
            link.symlink_to(source)
            before = snapshot(root)
            for path in (directory, link):
                for call in (mod.optional_summary, mod.load_summary, pub.prepare_updates, mod.build_plan):
                    with self.subTest(path=path.name, call=call.__name__), self.assertRaises(ValueError):
                        call(root, path)
            self.assertEqual(snapshot(root), before)

    def test_default_broken_symlink_is_invalid_instead_of_optional_absence(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'preserved.txt').write_bytes(b'synthetic preserved bytes\n')
            source = root / mod.DATA_FILE
            source.parent.mkdir(parents=True)
            target = root / 'missing-synthetic-export.json'
            source.symlink_to(target)
            before = snapshot(root)
            for call in (mod.optional_summary, mod.load_summary, pub.optional_summary,
                         pub.prepare_updates, mod.build_plan):
                with self.subTest(call=call.__name__), self.assertRaises(ValueError):
                    call(root)
                self.assertTrue(source.is_symlink())
                self.assertFalse(source.exists())
                self.assertEqual(source.readlink(), target)
                self.assertEqual(snapshot(root), before)
                self.assertFalse((root / mod.STUDY).exists())

    def test_valid_summary_without_matching_sources_and_replay_never_plans_writes(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            temporary_site(root)
            source = root / 'external-public-export.json'
            write_json(source, fixture())
            before = snapshot(root)
            self.assertEqual(mod.load_summary(root, source), fixture())
            for call in (pub.prepare_updates, mod.build_plan):
                with self.subTest(call=call.__name__), self.assertRaises(ValueError):
                    call(root, source)
                self.assertEqual(snapshot(root), before)

    def test_external_source_bundle_and_zip_plan_is_pure_and_idempotent(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            stories, cards, blocks = temporary_site(root)
            d = fixture()
            bundle, archive, files, bindings = synthetic_inputs(root, d, external=True)
            source = root / 'external-public-export.json'
            raw = write_json(source, d)
            before = snapshot(root)
            with synthetic_bindings(bindings, mod, pub.study):
                self.assertEqual(mod.load_summary(root, source), d)
                updates = pub.prepare_updates(root, source, bundle, archive)
                self.assertEqual(snapshot(root), before)
                self.assertEqual(pub.prepare_updates(root, source, bundle, archive), updates)
                expected = {mod.DATA_FILE, mod.STUDY + 'index.html', mod.STUDY + 'en.html',
                    mod.STUDY + 'experience-retention-delayed.css', mod.ZIP_FILE,
                    *(mod.REPLAY + name for name in files),
                    'index.html', 'index.en.html', 'results.html', 'results.en.html', 'README.md', 'sitemap.xml'}
                self.assertEqual(set(updates), expected)
                self.assertTrue(all(type(value) is bytes for value in updates.values()))
                self.assertEqual(updates[mod.DATA_FILE], raw)
                self.assertEqual(updates[mod.ZIP_FILE], archive.read_bytes())
                for name, value in files.items():
                    self.assertEqual(updates[mod.REPLAY + name], value)
                for name in ('index.html', 'index.en.html'):
                    html = updates[name].decode()
                    for story in stories:
                        self.assertIn(story, html)
                    self.assertEqual(html.count('data-mechanism='), 4)
                    self.assertEqual(html.count('class="latest-study"'), 1)
                    self.assertIn('data-source="' + mod.DATA_FILE + '"', html)
                for name in ('results.html', 'results.en.html'):
                    html = updates[name].decode()
                    for card in cards:
                        self.assertIn(card, html)
                    self.assertEqual(html.count('class="study-card"'), 11)
                    self.assertEqual(html.count('data-study="experience-retention-delayed"'), 1)
                    self.assertIn('<strong>11</strong>', html)
                readme = updates['README.md'].decode()
                for block in blocks:
                    self.assertIn(block, readme)
                self.assertIn('Existing ten-study build instructions.', readme)
                self.assertIn('not exactly 24 hours', readme)
                for relative, value in updates.items():
                    path = root / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(value)
                self.assertEqual(pub.prepare_updates(root), updates)
                self.assertEqual(mod.optional_summary(root), d)
            after = snapshot(root)
            for name, value in before.items():
                if name not in updates:
                    self.assertEqual(after[name], value, name)
            for name in ('index.html', 'en.html'):
                self.assertIn(b'uncollected_pending', (root / mod.phase_one.STUDY / name).read_bytes())
            self.assertIn(b'uncollected_pending', (root / mod.phase_one.DATA_FILE).read_bytes())
            self.assertIn(b'Immediate study: uncollected_pending.', after['README.md'])
            for suffix in ('', 'en.html'):
                self.assertEqual(after['sitemap.xml'].decode().count('<loc>' + mod.BASE + mod.STUDY + suffix + '</loc>'), 1)

    def test_integration_anchor_failures_are_detected_without_partial_output(self):
        for mutation in ('home', 'listing', 'readme', 'sitemap'):
            with self.subTest(mutation=mutation), TemporaryDirectory() as temporary:
                root = Path(temporary)
                temporary_site(root)
                d = fixture()
                bundle, archive, _, bindings = synthetic_inputs(root, d, external=True)
                source = root / 'external-public-export.json'
                write_json(source, d)
                target = {'home': 'index.html', 'listing': 'results.html',
                          'readme': 'README.md', 'sitemap': 'sitemap.xml'}[mutation]
                (root / target).write_bytes(b'missing synthetic integration anchor\n')
                before = snapshot(root)
                with synthetic_bindings(bindings, mod, pub.study), self.assertRaises(ValueError):
                    pub.prepare_updates(root, source, bundle, archive)
                self.assertEqual(snapshot(root), before)
                self.assertFalse((root / mod.STUDY).exists())

    def test_rehashed_plaintext_conversation_extra_is_rejected_before_publication_writes(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            temporary_site(root)
            d = fixture()
            bundle, archive, files, bindings = synthetic_inputs(root, d, external=True)
            source = root / 'external-public-export.json'
            write_json(source, d)
            with synthetic_bindings(bindings, mod, pub.study):
                self.assertTrue(pub.prepare_updates(root, source, bundle, archive))
                files['conversation.txt'] = b'Synthetic private conversation fixture: keep this prose out of publication.\n'
                seal_replay(bundle, archive, d, files)
                write_json(source, d)
                self.assertIs(mod.validate_summary(d), d)
                before = snapshot(root)
                for call in (mod.require_public_inputs, pub.prepare_updates):
                    with self.subTest(call=call.__name__), self.assertRaises(ValueError):
                        if call is mod.require_public_inputs:
                            call(root, d, bundle, archive)
                        else:
                            call(root, source, bundle, archive)
                    self.assertEqual(snapshot(root), before)
                    self.assertFalse((root / mod.STUDY).exists())

    def test_rehashed_artifact_byte_substitution_is_rejected_before_publication_writes(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            temporary_site(root)
            d = fixture()
            bundle, archive, files, bindings = synthetic_inputs(root, d, external=True)
            source = root / 'external-public-export.json'
            write_json(source, d)
            with synthetic_bindings(bindings, mod, pub.study):
                self.assertTrue(pub.prepare_updates(root, source, bundle, archive))
                name = 'artifacts/no_experience/Q01.json'
                files[name] = json_bytes({'id': 'Q01', 'synthetic_value': 'substituted'})
                seal_replay(bundle, archive, d, files)
                write_json(source, d)
                self.assertIs(mod.validate_summary(d), d)
                before = snapshot(root)
                for call in (mod.require_public_inputs, pub.prepare_updates):
                    with self.subTest(call=call.__name__), self.assertRaisesRegex(ValueError, 'artifact byte hash'):
                        if call is mod.require_public_inputs:
                            call(root, d, bundle, archive)
                        else:
                            call(root, source, bundle, archive)
                    self.assertEqual(snapshot(root), before)
                    self.assertFalse((root / mod.STUDY).exists())


if __name__ == '__main__':
    unittest.main()

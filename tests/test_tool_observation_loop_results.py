"""Structural engineering fixtures live only in memory or temporary directories.

These tests never open a pilot export, native state, private observation or
conversation. Synthetic metadata verifies the public publication boundary.
"""
import copy
from datetime import datetime, timedelta, timezone
import hashlib
from html.parser import HTMLParser
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
import zipfile
from io import BytesIO

ROOT = Path(__file__).resolve().parents[1]


def module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


schema = module('tool_observation_schema_engineering', 'tools/tool_observation_schema.py')
mod = module('tool_observation_builder_engineering', 'tools/build_tool_observation_loop.py')
pub = module('tool_observation_publication_engineering', 'tools/tool_observation_loop_publication.py')


def digest(label):
    return hashlib.sha256(('synthetic-public-engineering-' + label).encode()).hexdigest()


def expected_counts(rows):
    """Expected arithmetic is independent of the production aggregator."""
    zero = sum(1 for row in rows if row['exit_code'] == 0)
    return {'operations': len(rows), 'exit_zero': zero,
            'exit_nonzero': len(rows) - zero,
            'plans_before_execution': sum(1 for row in rows if row['plan_before_execution']),
            'native_unchanged': sum(1 for row in rows if row['native_state_unchanged'] is True),
            'native_changed': sum(1 for row in rows if row['native_state_unchanged'] is False),
            'native_unmeasured': sum(1 for row in rows if row['native_state_unchanged'] is None)}


def fixture():
    """Artificial outcomes exercise the schema without claiming a real pilot."""
    operations = []
    specs = [('initialize', 'initialization', 0, False, 1),
             ('lre_capture', 'judgment', 0, False, 2),
             ('lre_review', 'judgment', 0, False, 2),
             ('shiori_draft', 'indexing', 0, True, 2),
             ('shiori_capture_raw', 'raw_capture', 0, False, 2),
             ('shiori_ingest', 'indexing', 0, False, 2),
             ('shiori_recall', 'unchanged', 0, True, 2),
             ('hydrate', 'changed_context', 1, True, 2),
             ('lre_read', 'legacy_return', -1, None, 2),
             ('shiori_raw_search', 'diagnostic', 0, True, 2),
             ('shiori_inspect', 'diagnostic', 0, True, 2)]
    start = datetime(2026, 10, 28, tzinfo=timezone.utc)
    for ordinal, (operation, phase, exit_code, unchanged, revision) in enumerate(specs, 1):
        began = start + timedelta(seconds=ordinal)
        operations.append({'ordinal': ordinal, 'phase': phase, 'operation': operation,
            'exit_code': exit_code, 'manifest_sha256': digest('manifest-' + str(ordinal)),
            'started_at_utc': began.isoformat().replace('+00:00', 'Z'),
            'finished_at_utc': (began + timedelta(microseconds=500000)).isoformat().replace('+00:00', 'Z'),
            'plan_before_execution': ordinal != 9, 'native_state_unchanged': unchanged,
            'revision': revision})
    contexts = []
    for index, (identity, condition) in enumerate(sorted(schema.CONTEXT_BINDINGS.items())):
        first = index + 7
        contexts.append({'id': identity, 'condition': condition, 'first_operation': first,
            'exit_code': operations[first - 1]['exit_code'], 'graph_support_path_count': index,
            'matched_cue_count': index + 1, 'top_score': 1.25 + index,
            'hops0_top_score': 0.5 + index, 'convergence_off_top_score': 0.75 + index,
            **{field: (True, False, None)[(index + offset) % 3]
               for offset, field in enumerate(sorted(schema.CONTEXT_FLAGS))}})
    return {'schema_version': 1, 'study_id': schema.STUDY_ID, 'date': '2026-10-28',
        'evidence_kind': 'actual_functional_pilot', 'operations': operations,
        'contexts': contexts, 'source_counts': {'tool_observations': 11,
            'actual_ai_judgments': 3, 'independent_events': 4},
        'engineering': [{'round': number, 'tests': tests, 'worker_invocations': workers,
            'failures': 0, 'errors': 0, 'evidence_kind': 'synthetic_engineering',
            'report_sha256': digest('engineering-' + str(number))}
            for number, tests, workers in [(1, 14, 93), (2, 15, 102)]],
        'counts': expected_counts(operations),
        'provenance': {key: digest(key) for key in schema.PROVENANCE},
        'scope': dict(schema.SCOPE)}


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
    """Produce a duplicate field at one selected dictionary, including lists."""
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


def temporary_site(root):
    """Only structural fixtures: nine older cards, four stories, pending data."""
    stories = ['<section class="story" id="story-' + str(index) + '"><p>synthetic story '
               + str(index) + '</p><script>syntheticAnimation(' + str(index) + ')</script></section>'
               for index in range(1, 5)]
    cards = ['<article class="study-card" data-study="older-' + str(index).zfill(2)
             + '"><h3>synthetic older study ' + str(index)
             + '</h3><p>uncollected_pending retained</p></article>' for index in range(1, 10)]
    files = {}
    for lang, name in [('ja', 'index.html'), ('en', 'index.en.html')]:
        files[name] = ('<html lang="' + lang + '"><body><section class="latest-study" '
            + 'aria-label="synthetic previous latest"><p>previous latest</p></section>'
            + ''.join(stories) + '</body></html>').encode()
    for lang, name in [('ja', 'results.html'), ('en', 'results.en.html')]:
        files[name] = ('<html lang="' + lang + '"><body><div class="status-strip">old status</div>\n'
            + '<div class="hero-metrics"><div class="metric">old metrics</div></div>'
            + '<section class="section" id="studies"><div class="section-heading"><h2>Studies</h2></div>'
            + ''.join(cards) + '</section></body></html>').encode()
    files['README.md'] = (b'# Synthetic engineering site\n\n## Public and private scope\n'
        b'Previous scope.\n\n## Build and verify the website\nPrevious commands.\n\n'
        b'## Preservation\nNine earlier studies; uncollected_pending stays pending.\n')
    files['sitemap.xml'] = b'<?xml version="1.0"?><urlset><url><loc>https://example.invalid/older/</loc></url></urlset>'
    for index in range(1, 10):
        for name in ('index.html', 'en.html'):
            files['studies/synthetic-older-' + str(index) + '/' + name] = b'unchanged synthetic dated study\n'
        files['data/synthetic-older-' + str(index) + '.json'] = b'{"status":"uncollected_pending"}\n'
        files['experiments/synthetic-older-' + str(index) + '/MANIFEST.json'] = b'{"synthetic":true}\n'
        files['downloads/synthetic-older-' + str(index) + '.zip'] = b'synthetic old archive sentinel\n'
    for index in range(1, 5):
        files['assets/synthetic-story-' + str(index) + '.js'] = ('syntheticAnimation(' + str(index) + ');\n').encode()
    for name, raw in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    return stories, cards, files


def write_source(path, d, raw=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    value = (json.dumps(d, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
             + '\n').encode() if raw is None else raw
    path.write_bytes(value)
    return value


def write_bundle(root, files):
    root.mkdir()
    for name, raw in files.items():
        (root / name).write_bytes(raw)


def refresh_manifest(bundle):
    files = {name: (bundle / name).read_bytes() for name in ('README.md', 'evidence.json', 'verify.py')}
    manifest = {'schema_version': 1, 'files': {name: {'sha256': hashlib.sha256(raw).hexdigest(),
        'bytes': len(raw)} for name, raw in files.items()}}
    (bundle / 'MANIFEST.json').write_text(json.dumps(manifest), encoding='utf-8')


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


class ToolObservationSchemaEngineering(unittest.TestCase):
    def setUp(self):
        self.d = fixture()

    def test_complete_synthetic_structure_and_independent_arithmetic(self):
        self.assertIs(schema.validate_summary(self.d), self.d)
        self.assertEqual(set(row['operation'] for row in self.d['operations']), schema.OPERATION_NAMES)
        self.assertEqual(set(row['phase'] for row in self.d['operations']), schema.PHASES)
        self.assertEqual(schema.aggregate_operations(self.d['operations']), expected_counts(self.d['operations']))
        self.assertEqual(self.d['counts'], {'operations': 11, 'exit_zero': 9, 'exit_nonzero': 2,
            'plans_before_execution': 10, 'native_unchanged': 5, 'native_changed': 5,
            'native_unmeasured': 1})

    def test_every_nested_dictionary_rejects_unknown_private_fields(self):
        for path in paths(self.d, lambda value: isinstance(value, dict)):
            bad = copy.deepcopy(self.d)
            at(bad, path)['private_source'] = 'PRIVATE_SENTINEL'
            with self.subTest(path=path), self.assertRaises(ValueError):
                schema.validate_summary(bad)

    def test_every_leaf_rejects_injected_free_text(self):
        for path in paths(self.d, lambda value: not isinstance(value, (dict, list))):
            with self.subTest(path=path), self.assertRaises(ValueError):
                schema.validate_summary(replaced(self.d, path, 'PRIVATE_SENTINEL'))

    def test_boolean_is_never_an_integer_and_integer_is_never_a_flag(self):
        for path in paths(self.d, lambda value: type(value) is int):
            for value in (True, False, 1.0):
                with self.subTest(path=path, value=value), self.assertRaises(ValueError):
                    schema.validate_summary(replaced(self.d, path, value))
        for path in paths(self.d, lambda value: type(value) is bool):
            with self.subTest(path=path), self.assertRaises(ValueError):
                schema.validate_summary(replaced(self.d, path, int(at(self.d, path))))

    def test_every_count_recalculates_and_fixed_engineering_rounds_remain_separate(self):
        for field in self.d['counts']:
            bad = copy.deepcopy(self.d)
            bad['counts'][field] += 1
            with self.subTest(field=field), self.assertRaises(ValueError):
                schema.validate_summary(bad)
        for index in (0, 1):
            for field in ('tests', 'worker_invocations'):
                bad = copy.deepcopy(self.d)
                bad['engineering'][index][field] += 1
                with self.subTest(index=index, field=field), self.assertRaises(ValueError):
                    schema.validate_summary(bad)
        bad = copy.deepcopy(self.d)
        bad['engineering'][1] = copy.deepcopy(bad['engineering'][0])
        with self.assertRaises(ValueError):
            schema.validate_summary(bad)
        bad = copy.deepcopy(self.d)
        bad['engineering'][0]['failures'] = 15
        with self.assertRaises(ValueError):
            schema.validate_summary(bad)

    def test_utc_clocks_are_valid_restricted_and_ordered(self):
        for value in ('2026-10-28', '2026-10-28T00:00:01', '2026-10-28T09:00:01+09:00',
                      '2026-02-30T00:00:01Z', '2026-10-28T00:00:60Z',
                      '2026-10-28T00:00:01.1234567Z', 'PRIVATE_SENTINEL'):
            for field in ('started_at_utc', 'finished_at_utc'):
                bad = copy.deepcopy(self.d)
                bad['operations'][0][field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    schema.validate_summary(bad)
        bad = copy.deepcopy(self.d)
        bad['operations'][0]['finished_at_utc'] = '2026-10-28T00:00:00Z'
        with self.assertRaises(ValueError):
            schema.validate_summary(bad)
        good = copy.deepcopy(self.d)
        good['operations'][0]['started_at_utc'] = '2026-10-28T00:00:01+00:00'
        good['operations'][0]['finished_at_utc'] = '2026-10-28T00:00:01.500000+00:00'
        self.assertIs(schema.validate_summary(good), good)

    def test_operation_sequence_boundaries_and_source_counts_fail_closed(self):
        for field, value in [('ordinal', 2), ('exit_code', -256), ('exit_code', 256),
                             ('revision', 0), ('revision', 2), ('revision', 3),
                             ('operation', 'lre_read'), ('phase', 'judgment'),
                             ('manifest_sha256', 'A' * 64)]:
            bad = copy.deepcopy(self.d)
            bad['operations'][0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                schema.validate_summary(bad)
        for operations in ([], self.d['operations'] * 100):
            bad = copy.deepcopy(self.d)
            bad['operations'] = operations
            with self.subTest(size=len(operations)), self.assertRaises(ValueError):
                schema.validate_summary(bad)
        bad = copy.deepcopy(self.d)
        bad['source_counts']['independent_events'] = 12
        with self.assertRaises(ValueError):
            schema.validate_summary(bad)
        bad = copy.deepcopy(self.d)
        bad['operations'][1]['revision'] = 1
        with self.assertRaises(ValueError):
            schema.validate_summary(bad)

    def test_contexts_bind_distinct_actual_phase_operations_and_exit_codes(self):
        changes = [('id', 'C02'), ('condition', 'changed_context'), ('first_operation', 1),
                   ('first_operation', 12), ('first_operation', 8), ('exit_code', 1)]
        for field, value in changes:
            bad = copy.deepcopy(self.d)
            bad['contexts'][0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                schema.validate_summary(bad)
        for collection in ('contexts', 'engineering'):
            bad = copy.deepcopy(self.d)
            bad[collection].pop()
            with self.subTest(collection=collection), self.assertRaises(ValueError):
                schema.validate_summary(bad)
        bad = copy.deepcopy(self.d)
        bad['contexts'][0]['first_operation'] = None
        with self.assertRaises(ValueError):
            schema.validate_summary(bad)
        bad['contexts'][0]['exit_code'] = None
        self.assertIs(schema.validate_summary(bad), bad)

    def test_duplicate_fields_at_every_nested_dictionary_are_rejected(self):
        with TemporaryDirectory() as temporary:
            source = Path(temporary) / 'synthetic.json'
            for path in paths(self.d, lambda value: isinstance(value, dict)):
                source.write_text(duplicate_json(self.d, path), encoding='utf-8')
                with self.subTest(path=path), self.assertRaisesRegex(ValueError, 'Duplicate'):
                    schema.read_summary(source)

    def test_nonfinite_json_is_rejected_before_schema_validation(self):
        with TemporaryDirectory() as temporary:
            source = Path(temporary) / 'synthetic.json'
            for value in ('NaN', 'Infinity', '-Infinity'):
                for marker in ('"ordinal": 1', '"graph_support_path_count": 0', '"tool_observations": 11'):
                    source.write_text(json.dumps(self.d).replace(marker, marker.split(':')[0] + ':' + value, 1), encoding='utf-8')
                    with self.subTest(value=value, marker=marker), self.assertRaisesRegex(ValueError, 'Nonfinite'):
                        schema.read_summary(source)


    def test_scores_are_finite_nonnegative_nullable_and_distinct_from_hit_identity(self):
        for field in schema.CONTEXT_SCORES:
            for value in (True, False, -1, -0.5, float('nan'), float('inf'), float('-inf'), 10 ** 1000):
                bad = copy.deepcopy(self.d)
                bad['contexts'][0][field] = value
                with self.subTest(field=field, value=str(value)[:20]), self.assertRaises(ValueError):
                    schema.validate_summary(bad)
            for value in (0, 2, 0.0, 2.5, None):
                good = copy.deepcopy(self.d)
                good['contexts'][0][field] = value
                self.assertIs(schema.validate_summary(good), good)
        good = copy.deepcopy(self.d)
        for row in good['contexts']:
            row.update(hops0_same_hits=True, convergence_off_same_hits=True)
        self.assertIs(schema.validate_summary(good), good)
        self.assertNotEqual(good['contexts'][0]['top_score'], good['contexts'][0]['hops0_top_score'])


class ToolObservationPublicationEngineering(unittest.TestCase):
    def setUp(self):
        self.d = fixture()

    def test_absent_default_and_missing_explicit_sources_do_not_write(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'preserved.txt').write_bytes(b'preserve this sentinel\n')
            before = snapshot(root)
            self.assertIsNone(mod.optional_summary(root))
            self.assertEqual(pub.prepare_updates(root), {})
            self.assertEqual(mod.build_plan(root), {})
            missing = root / 'missing-explicit-export.json'
            for call in (mod.optional_summary, pub.prepare_updates, mod.build_plan):
                with self.subTest(call=call.__name__), self.assertRaises((ValueError, FileNotFoundError)):
                    call(root, missing)
                self.assertEqual(snapshot(root), before)
            with self.assertRaises(FileNotFoundError):
                mod.load_summary(missing)
        for fn, args in [(pub.integrate_home, ('preserved', 'ja', None)),
                         (pub.integrate_listing, ('preserved', 'en', None)),
                         (pub.integrate_readme, ('preserved', None)),
                         (pub.integrate_sitemap, ('preserved', None))]:
            self.assertEqual(fn(*args), 'preserved')

    def test_invalid_default_or_explicit_sources_refuse_before_writes(self):
        texts = [b'{}', duplicate_json(self.d, ('contexts', 0)).encode(),
                 json.dumps(self.d).replace('"top_score": 1.25', '"top_score": NaN', 1).encode()]
        for raw in texts:
            for explicit in (False, True):
                with self.subTest(raw=raw[:30], explicit=explicit), TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    temporary_site(root)
                    source = root / ('external-public-export.json' if explicit else mod.DATA_FILE)
                    write_source(source, self.d, raw)
                    before = snapshot(root)
                    for call in (mod.optional_summary, pub.prepare_updates, mod.build_plan):
                        with self.subTest(call=call.__name__), self.assertRaises(ValueError):
                            call(root, source if explicit else None)
                        self.assertEqual(snapshot(root), before)
                    with self.assertRaises(ValueError):
                        mod.load_summary(source)
                    self.assertFalse((root / mod.STUDY).exists())

    def test_export_source_must_be_a_regular_file(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / 'synthetic.json'
            write_source(target, self.d)
            directory = root / 'directory.json'
            directory.mkdir()
            link = root / 'linked.json'
            link.symlink_to(target)
            before = snapshot(root)
            for source in (directory, link):
                for call in (mod.optional_summary, pub.prepare_updates, mod.build_plan):
                    with self.subTest(source=source.name, call=call.__name__), self.assertRaises(ValueError):
                        call(root, source)
            self.assertEqual(snapshot(root), before)

    def test_explicit_or_default_approved_structures_load_from_the_requested_paths(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'external' / 'public-export-v1.json'
            write_source(source, self.d)
            self.assertEqual(schema.read_summary(source), self.d)
            self.assertEqual(mod.load_summary(source), self.d)
            self.assertEqual(mod.optional_summary(root, source), self.d)
            self.assertIsNone(mod.optional_summary(root))
            default = root / mod.DATA_FILE
            write_source(default, self.d)
            self.assertEqual(mod.optional_summary(root), self.d)

    def test_deterministic_exact_four_file_bundle_and_zip_preserve_source_bytes(self):
        raw = (json.dumps(self.d, indent=2, ensure_ascii=False) + '\n').encode()
        files, archive = mod.evidence_package(self.d, raw)
        again, archive_again = mod.evidence_package(copy.deepcopy(self.d), raw)
        self.assertEqual(files, again)
        self.assertEqual(archive, archive_again)
        self.assertEqual(set(files), {'README.md', 'evidence.json', 'verify.py', 'MANIFEST.json'})
        self.assertEqual(files['evidence.json'], raw)
        manifest = json.loads(files['MANIFEST.json'])
        self.assertEqual(set(manifest['files']), set(files) - {'MANIFEST.json'})
        for name, row in manifest['files'].items():
            self.assertEqual(row, {'sha256': hashlib.sha256(files[name]).hexdigest(), 'bytes': len(files[name])})
        with zipfile.ZipFile(BytesIO(archive)) as bundle:
            self.assertEqual(bundle.namelist(), sorted(files))
            self.assertEqual({name: bundle.read(name) for name in bundle.namelist()}, files)
            for info in bundle.infolist():
                self.assertEqual(info.date_time, (1980, 1, 1, 0, 0, 0))
                self.assertEqual(info.create_system, 3)
                self.assertEqual(info.external_attr >> 16, 0o100644)
        changed = copy.deepcopy(self.d)
        changed['contexts'][0]['top_score'] += 1
        with self.assertRaises(ValueError):
            mod.evidence_package(changed, raw)

    def test_verifier_reports_only_disclosed_metadata_and_standalone_matches(self):
        raw = (json.dumps(self.d) + '\n').encode()
        files, _ = mod.evidence_package(self.d, raw)
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / 'bundle'
            write_bundle(root, files)
            report = schema.verify_bundle(root)
            self.assertEqual(report['status'], 'verified')
            self.assertEqual(report['files'], 4)
            self.assertEqual(report['counts'], self.d['counts'])
            self.assertEqual(report['evidence_sha256'], hashlib.sha256(raw).hexdigest())
            self.assertEqual(report['manifest_sha256'], hashlib.sha256(files['MANIFEST.json']).hexdigest())
            self.assertFalse(report['native_execution_replayed'])
            self.assertFalse(report['fresh_ai_choices_generated'])
            self.assertIn('not independently reconstructed', report['verification_scope'])
            before = snapshot(root)
            run = subprocess.run([sys.executable, '-B', str(root / 'verify.py'), '--bundle', str(root)],
                                 check=False, text=True, capture_output=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(json.loads(run.stdout), report)
            self.assertEqual(snapshot(root), before)

    def test_verifier_rejects_each_missing_tampered_extra_and_wrongcase_file(self):
        files, _ = mod.evidence_package(self.d, (json.dumps(self.d) + '\n').encode())
        mutations = [('missing', name) for name in files]
        mutations += [('tamper', name) for name in files]
        mutations += [('wrongcase', 'MANIFEST.json'), ('extra', 'unexpected.txt'), ('directory', 'nested')]
        for mutation, name in mutations:
            with self.subTest(mutation=mutation, name=name), TemporaryDirectory() as temporary:
                root = Path(temporary) / 'bundle'
                write_bundle(root, files)
                if mutation == 'missing':
                    (root / name).unlink()
                elif mutation == 'tamper':
                    (root / name).write_bytes(b'tampered synthetic data\n')
                elif mutation == 'wrongcase':
                    (root / name).rename(root / 'manifest.json')
                elif mutation == 'extra':
                    (root / name).write_bytes(b'unexpected\n')
                else:
                    (root / name).mkdir()
                with self.assertRaises((ValueError, OSError)):
                    schema.verify_bundle(root)

    def test_verifier_rejects_symlinks_and_rehashed_invalid_evidence(self):
        files, _ = mod.evidence_package(self.d, (json.dumps(self.d) + '\n').encode())
        with TemporaryDirectory() as temporary:
            outer = Path(temporary)
            root = outer / 'bundle'
            write_bundle(root, files)
            link = outer / 'linked-bundle'
            link.symlink_to(root, target_is_directory=True)
            with self.assertRaises(ValueError):
                schema.verify_bundle(link)
            target = outer / 'external-readme.txt'
            target.write_bytes(files['README.md'])
            (root / 'README.md').unlink()
            (root / 'README.md').symlink_to(target)
            with self.assertRaises(ValueError):
                schema.verify_bundle(root)
        for mutation in ('unknown', 'duplicate', 'nonfinite', 'badcount', 'bytes_boolean'):
            with self.subTest(mutation=mutation), TemporaryDirectory() as temporary:
                root = Path(temporary) / 'bundle'
                write_bundle(root, files)
                bad = copy.deepcopy(self.d)
                if mutation == 'unknown':
                    bad['contexts'][0]['private_trace'] = 'PRIVATE_SENTINEL'
                    write_source(root / 'evidence.json', bad)
                elif mutation == 'badcount':
                    bad['counts']['exit_zero'] += 1
                    write_source(root / 'evidence.json', bad)
                elif mutation == 'duplicate':
                    (root / 'evidence.json').write_text(duplicate_json(bad, ('scope',)), encoding='utf-8')
                elif mutation == 'nonfinite':
                    text = json.dumps(bad).replace('"top_score": 1.25', '"top_score": Infinity', 1)
                    (root / 'evidence.json').write_text(text, encoding='utf-8')
                refresh_manifest(root)
                if mutation == 'bytes_boolean':
                    manifest = json.loads((root / 'MANIFEST.json').read_text())
                    manifest['files']['README.md']['bytes'] = True
                    (root / 'MANIFEST.json').write_text(json.dumps(manifest))
                with self.assertRaises(ValueError):
                    schema.verify_bundle(root)
                run = subprocess.run([sys.executable, '-B', str(root / 'verify.py'), '--bundle', str(root)],
                                     check=False, text=True, capture_output=True)
                self.assertEqual(run.returncode, 1, run.stderr)
                self.assertEqual(json.loads(run.stdout)['status'], 'failed')

    def test_ja_en_rendering_has_matching_ids_links_and_honest_score_boundaries(self):
        pages = {}
        for lang in ('ja', 'en'):
            text = mod.render(lang, self.d)
            page = Page(text)
            pages[lang] = page
            self.assertEqual(page.languages, [lang])
            self.assertEqual(len(page.ids), len(set(page.ids)))
            self.assertIn('contexts', page.ids)
            self.assertIn('operations', page.ids)
            for name in (mod.DATA_FILE, mod.REPLAY + 'README.md', mod.ZIP_FILE):
                self.assertIn('../../' + name, page.refs)
            for row in self.d['contexts']:
                for field in schema.CONTEXT_SCORES:
                    self.assertIn(str(row[field]), text)
            self.assertNotIn('PRIVATE_SENTINEL', text)
        self.assertEqual(set(pages['ja'].ids), set(pages['en'].ids))
        english = mod.render('en', self.d)
        for phrase in ('excluding scores', 'not confidence', 'not external signatures',
                       'cannot reconstruct undisclosed native operations', 'separate frozen study',
                       'Synthetic engineering checks', 'not two independent experiences'):
            self.assertIn(phrase, english)
        with self.assertRaises(ValueError):
            mod.render('fr', self.d)

    def test_native_changes_are_observed_states_and_table_explanations_remain_outside_scroll(self):
        for lang, labels in [('en', ('Unchanged', 'Changed', 'Unmeasured')),
                             ('ja', ('変更なし', '変更あり', '未計測'))]:
            html = mod.render(lang, self.d)
            operations = html.split('<section class="section" id="operations"', 1)[1].split('</section>', 1)[0]
            for value, label in zip((True, False, None), labels):
                expected = sum(row['native_state_unchanged'] is value for row in self.d['operations'])
                self.assertEqual(operations.count('<td>' + label + '</td>'), expected)
            self.assertEqual(html.count('class="tol-scroll-hint"'), html.count('<table '))
            self.assertEqual(html.count('<caption><span class="tol-caption">'), html.count('<table '))
            self.assertIn('</p><div class="table-wrap" role="region" tabindex="0"', html)
            self.assertIn('左右にスクロール' if lang == 'ja' else 'scroll horizontally', html)

    def test_plan_is_pure_idempotent_and_preserves_old_nine_cards_four_stories(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            stories, cards, old = temporary_site(root)
            source = root / 'external' / 'public-export-v1.json'
            raw = write_source(source, self.d)
            before = snapshot(root)
            updates = pub.prepare_updates(root, source)
            self.assertEqual(snapshot(root), before)
            self.assertEqual(mod.build_plan(root, source), updates)
            self.assertEqual(updates[mod.DATA_FILE], raw)
            allowed = {mod.DATA_FILE, mod.STUDY + 'index.html', mod.STUDY + 'en.html',
                mod.STUDY + 'tool-observation-loop.css', mod.ZIP_FILE,
                *(mod.REPLAY + name for name in ('README.md', 'evidence.json', 'verify.py', 'MANIFEST.json')),
                'index.html', 'index.en.html', 'results.html', 'results.en.html', 'README.md', 'sitemap.xml'}
            self.assertEqual(set(updates), allowed)
            for name in ('index.html', 'index.en.html'):
                html = updates[name].decode()
                for story in stories:
                    self.assertIn(story, html)
                self.assertEqual(html.count('class="story"'), 4)
                self.assertEqual(html.count('class="latest-study"'), 1)
            for name in ('results.html', 'results.en.html'):
                html = updates[name].decode()
                for card in cards:
                    self.assertIn(card, html)
                self.assertEqual(html.count('class="study-card"'), 10)
                self.assertEqual(html.count('data-study="tool-observation-loop"'), 1)
            for relative, planned in updates.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(planned)
            self.assertEqual(pub.prepare_updates(root), updates)
            for name, raw in old.items():
                if name not in updates:
                    self.assertEqual((root / name).read_bytes(), raw)
            for name in ('results.html', 'results.en.html'):
                self.assertIn('uncollected_pending', (root / name).read_text())
            self.assertIn('uncollected_pending', (root / 'README.md').read_text())
            self.assertNotIn('manifest.json', {Path(name).name for name in updates})


if __name__ == '__main__':
    unittest.main()

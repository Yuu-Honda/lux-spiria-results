"""Synthetic validator fixtures only; never published as collected study data."""
from copy import deepcopy
from hashlib import sha256
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('experience_action_publication_tests', ROOT / 'tools/experience_action_publication.py')
publication = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(publication)
study, schema = publication.study, publication.study.schema
DIGEST = sha256(b'SYNTHETIC TEST ONLY').hexdigest()


def profile(world, stage):
    return 'cfg-' + format(int(world[1:]) * 10 + stage, '012x')


def accepted():
    return {'artifact_bytes': 19, 'artifact_sha256': DIGEST, 'checks': ['SYNTHETIC TEST ONLY'],
        'errors': [], 'exit_code': 0, 'expected_artifact_sha256': DIGEST, 'status': 'accepted'}


def action(build=False, evidence=None):
    return {'decision': 'build' if build else 'abstain', 'recipe': 'alpha' if build else None,
        'prediction': 'accepted' if build else 'unknown', 'reason': 'SYNTHETIC TEST ONLY: <reason> & data',
        'evidence': [] if evidence is None else evidence}


def fixture():
    """Invented mechanical test input; not research evidence or public output."""
    d = {'schema': schema.SCHEMA, 'date': '2026-10-30', 'analyzed_at_utc': '2026-10-30T00:00:00Z',
        'protocol_sha256': DIGEST, 'independent_engineered_histories': 3,
        'artifact_format_replications_of_mechanisms': 1, 'actual_teacher_contexts': 6,
        'actual_probe_contexts': 36, 'semantic_reviewer_contexts': 3,
        'engineering_tests': {'tests': 21, 'failures': 0, 'errors': 0, 'synthetic': True},
        'rows': [], 'aggregates': [], 'unique_original_observations': 42,
        'unique_operation_counts': {'synthetic_operation': 42},
        'provider_metadata': {key: None for key in ('provider', 'model', 'settings', 'tokens', 'compute')},
        'boundary': 'SYNTHETIC TEST ONLY', 'teachers': [], 'source_messages': [],
        'hashes': {'synthetic_test': DIGEST},
        'audit': {'status': 'approved', 'scope': 'SYNTHETIC TEST ONLY', 'report_sha256': DIGEST},
        'boundaries': ['SYNTHETIC TEST ONLY'], 'protection': dict(schema.PROTECTION)}
    for world in schema.WORLDS:
        for index in range(5):
            text = 'SYNTHETIC TEST ONLY tool ' + world + str(index) + ' <safe> & text'
            d['source_messages'].append({'id': 'obs-' + world + '-' + str(index), 'source_kind': 'tool_observation', 'text': text, 'text_sha256': sha256(text.encode()).hexdigest()})
        for stage, number in (('legacy', 1), ('current', 2)):
            text = 'SYNTHETIC TEST ONLY judgment ' + world + stage
            candidate = 'cand-' + world + '-' + stage
            d['source_messages'].append({'id': candidate, 'source_kind': 'actual_ai_judgment', 'text': text, 'text_sha256': sha256(text.encode()).hexdigest()})
            d['teachers'].append({'world': world, 'stage': stage, 'component': 'synthetic-component-' + world,
                'profile': profile(world, number), 'action': action(True), 'exit_code': 0,
                'artifact_validation': accepted(), 'candidate_id': candidate,
                'judgment': {'text': text, 'why_keep': 'SYNTHETIC TEST ONLY', 'review_action': 'retained', 'review_note': 'SYNTHETIC TEST ONLY'}})
    sources = schema.source_aliases(d['source_messages'])
    for phase, number in (('R', 2), ('L', 1), ('N', 3)):
        for arm in schema.ARMS:
            for world in schema.WORLDS:
                identity = phase + '-' + arm + '-' + world
                build = phase == 'R' and arm in ('full', 'no_writeback')
                query = arm != 'no_history'
                hits = []
                if build:
                    eid = 'judgment:cand-' + world + '-current' if arm == 'full' else 'tool:obs-' + world + '-0'
                    hits = [{'episode_id': eid, 'score': 1.0, 'matched_cues': [],
                        'support': [{'cue': ['concept', 'synthetic-alias'], 'weight': .5,
                            'path': [{'from': 'alias', 'to': 'component', 'type': 'shared_feature_not_causal', 'via': {'channel': 'concept', 'state': 'reported', 'subject': 'tool_work', 'value': 'synthetic-component'}}]}],
                        'indirect_zero_direct_match': True, 'source_kind': 'actual_ai_judgment' if arm == 'full' else 'tool_observation'}]
                evidence = [{'source_id': 'tool:obs-' + world + '-0', 'quote': sources['tool:obs-' + world + '-0']}] if build else []
                d['rows'].append({'assignment_id': identity, 'world': world, 'phase': phase, 'arm': arm,
                    'profile': profile(world, number), 'request': 'SYNTHETIC TEST ONLY <request>',
                    'action': action(build, evidence), 'exit_code': 0, 'artifact_accepted': build,
                    'artifact_validation': accepted() if build else None, 'abstained': not build,
                    'query_requested': query, 'query_status': 'available' if query else 'not_requested',
                    'query_result_bytes': 100 if query else 0, 'query_result_canonical_chars': 80 if query else 0,
                    'hits': hits, 'new_judgment_returned': build and arm == 'full',
                    'has_indirect_return': bool(hits), 'exact_quote_checks': [True] if build else [],
                    'all_quotes_exact': True, 'action_file_sha256': DIGEST,
                    'query_result_sha256': DIGEST if query else None, 'execution_result_sha256': DIGEST})
    d['aggregates'] = schema.recalculate(d['rows'])
    return d


class ExperienceActionResults(unittest.TestCase):
    def test_synthetic_fixture_and_arithmetic(self):
        d = fixture(); self.assertIs(schema.validate_summary(d), d)
        self.assertEqual(len(d['rows']), 36); self.assertEqual(len(d['aggregates']), 12)
        self.assertIn('equal acceptance', study.finding(d, 'en'))

    def test_citation_usage_and_alias_normalization_do_not_rewrite_actions(self):
        d = fixture(); row = d['rows'][0]
        row['action']['evidence'][0]['source_id'] = 'obs-W01-0'
        original = schema.canonical(row['action'])
        schema.validate_summary(d)
        self.assertEqual(original, schema.canonical(row['action']))
        use = schema.evidence_usage(d)
        self.assertEqual((use['eligible_nonempty_rows'], use['empty_evidence_rows'], use['eligible_tool_verbatim_quotes'], use['eligible_native_judgment_verbatim_quotes']), (6, 30, 6, 0))
        source = next(s for s in d['source_messages'] if s['id'] == 'cand-W01-current')
        row['action']['evidence'] = [{'source_id': 'cand-W01-current', 'quote': source['text']}]
        schema.validate_summary(d); use = schema.evidence_usage(d)
        self.assertEqual((use['eligible_tool_verbatim_quotes'], use['eligible_native_judgment_verbatim_quotes'], use['native_judgment_citing_rows']), (5, 1, 1))

    def test_installed_audited_data_matches_complete_publication(self):
        if not (ROOT / study.DATA_FILE).is_file():
            self.skipTest('Audited public export is not installed')
        d = study.optional_summary(ROOT)
        updates = publication.prepare_updates(ROOT)
        for name, expected in updates.items():
            self.assertEqual((ROOT / name).read_bytes(), expected, name)
        use = schema.evidence_usage(d)
        self.assertEqual(sum((use['eligible_nonempty_rows'], use['empty_evidence_rows'], use['out_of_type_notice_rows'], use['other_source_contract_false_rows'])), len(d['rows']))
        schema.verify_bundle(ROOT / study.REPLAY)

    def test_bad_schema_and_approval_refuse_before_plan(self):
        changes = [lambda d: d.update(extra='private'),
            lambda d: d['rows'].pop(),
            lambda d: d['rows'][0].update(extra='private'),
            lambda d: d['audit'].update(status='pending'),
            lambda d: d['protection'].update(os_isolation=True),
            lambda d: d['provider_metadata'].update(model='unverified'),
            lambda d: d['engineering_tests'].update(tests=57),
            lambda d: d['aggregates'][0].update(artifact_accepted=0),
            lambda d: d['rows'][0].update(profile=profile('W01', 1)),
            lambda d: d['rows'][0]['action'].update(reason='/' + 'Users/private/file'),
            lambda d: d['unique_operation_counts'].update(synthetic_operation=41)]
        with tempfile.TemporaryDirectory(dir=ROOT / 'tests') as name:
            root = Path(name)
            for change in changes:
                d = fixture(); change(d); source = root / 'export.json'
                source.write_text(json.dumps(d))
                before = {p.name: p.read_bytes() for p in root.iterdir()}
                with self.subTest(change=change), self.assertRaises(ValueError):
                    publication.prepare_updates(root, source)
                self.assertEqual(before, {p.name: p.read_bytes() for p in root.iterdir()})

    def test_absent_export_no_outputs(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tests') as name:
            root = Path(name)
            self.assertEqual(publication.prepare_updates(root), {})
            self.assertEqual(list(root.iterdir()), [])

    def test_complete_publication_plan_is_memory_only_and_exactly_allowlisted(self):
        d = fixture()
        with tempfile.TemporaryDirectory(dir=ROOT / 'tests') as name:
            root = Path(name)
            for filename in ('index.html', 'index.en.html', 'results.html', 'results.en.html', 'README.md', 'sitemap.xml'):
                (root / filename).write_bytes((ROOT / filename).read_bytes())
            source = root / 'audited-synthetic-test-input.json'
            source.write_text(schema.canonical(d))
            before = {p.name: p.read_bytes() for p in root.iterdir()}
            updates = publication.prepare_updates(root, source)
            self.assertEqual(before, {p.name: p.read_bytes() for p in root.iterdir()})
            expected = {study.DATA_FILE, study.STUDY + 'index.html', study.STUDY + 'en.html',
                study.STUDY + 'experience-action-loop.css', study.ZIP_FILE,
                *[study.REPLAY + n for n in ('README.md', 'evidence.json', 'verify.py', 'MANIFEST.json')],
                'index.html', 'index.en.html', 'results.html', 'results.en.html', 'README.md', 'sitemap.xml'}
            self.assertEqual(set(updates), expected)
            self.assertFalse(any((root / n).exists() for n in updates if '/' in n))
            self.assertEqual(updates[study.DATA_FILE], source.read_bytes())

    def test_duplicate_keys_and_nonfinite(self):
        for raw in (b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}'):
            with self.assertRaises(ValueError):
                schema.parse_json(raw)

    def test_source_hash_quote_and_graph_flags(self):
        changes = [lambda d: d['source_messages'][0].update(text='modified'),
            lambda d: d['rows'][0]['action']['evidence'][0].update(quote='not contained'),
            lambda d: d['rows'][0]['hits'][0].update(indirect_zero_direct_match=False),
            lambda d: d['rows'][0].update(has_indirect_return=False),
            lambda d: d['rows'][0].update(new_judgment_returned=False),
            lambda d: d['rows'][0]['hits'][0]['support'][0].update(weight=float('inf')),
            lambda d: d['rows'][0]['hits'][0]['support'][0]['path'][0]['via'].update(subject='private')]
        for change in changes:
            d = fixture(); change(d)
            with self.subTest(change=change), self.assertRaises(ValueError):
                schema.validate_summary(d)

    def test_actual_failed_quote_and_unavailable_notice_remain_outcomes(self):
        d = fixture()
        row = next(r for r in d['rows'] if (r['world'], r['phase'], r['arm']) == ('W02', 'L', 'no_history'))
        row['query_requested'] = True; row['query_status'] = 'unavailable'
        row['query_result_bytes'] = 80; row['query_result_canonical_chars'] = 70
        row['query_result_sha256'] = DIGEST
        row['action']['evidence'] = [{'source_id': 'QUERY_RESULT.json', 'quote': 'No history is supplied in this assigned condition.'}]
        row['exact_quote_checks'] = [False]; row['all_quotes_exact'] = False
        d['aggregates'] = schema.recalculate(d['rows'])
        self.assertIs(schema.validate_summary(d), d)
        html = study.render('en', d)
        self.assertIn('Eligible original-source check', html)
        self.assertIn(row['assignment_id'], html)
        self.assertIn('outside the preregistered eligible source types', html)
        self.assertIn('does not indicate fabricated quotations or mismatched notice text', html)
        self.assertIn('true for 35/36 rows and false for 1 row.', html)

    def test_profile_and_judgment_source_bindings(self):
        changes = [lambda d: d['teachers'][1].update(profile=d['teachers'][0]['profile']),
            lambda d: next(r for r in d['rows'] if r['phase'] == 'N').update(profile='cfg-ffffffffffff'),
            lambda d: d['rows'][0]['hits'][0].update(source_kind='tool_observation'),
            lambda d: d['teachers'][1]['judgment'].update(text='not the disclosed judgment'),
            lambda d: d['teachers'][1]['judgment'].update(review_action='deferred')]
        for change in changes:
            d = fixture(); change(d)
            with self.subTest(change=change), self.assertRaises(ValueError):
                schema.validate_summary(d)

    def test_hops0_and_no_writeback_constraints(self):
        d = fixture(); hop = next(r for r in d['rows'] if r['arm'] == 'hops0')
        hop['hits'] = deepcopy(d['rows'][0]['hits']); hop['has_indirect_return'] = True
        with self.assertRaises(ValueError):
            schema.validate_summary(d)
        d = fixture(); row = next(r for r in d['rows'] if r['arm'] == 'no_writeback')
        row['hits'] = deepcopy(d['rows'][0]['hits']); row['new_judgment_returned'] = True
        with self.assertRaises(ValueError):
            schema.validate_summary(d)

    def test_render_has_all_choices_actual_paths_and_boundaries(self):
        d = fixture()
        for lang in ('ja', 'en'):
            html = study.render(lang, d)
            for r in d['rows']:
                self.assertIn(r['assignment_id'], html)
            self.assertIn('shared_feature_not_causal', html)
            self.assertIn('scope="col"', html); self.assertIn('scope="row"', html)
            self.assertIn('tabindex="0"', html); self.assertIn('theme-dark.css', html)
            self.assertIn('&lt;reason&gt; &amp; data', html); self.assertNotIn('<request>', html)
            self.assertIn('21', html); self.assertIn('36', html)
        self.assertIn('empty-list', study.render('en', d))
        self.assertIn('not OS isolation', study.render('en', d))

    def test_download_inventory_determinism_and_standalone_verifier(self):
        d = fixture(); raw = (schema.canonical(d) + '\n').encode()
        files, archive = study.public_bundle(d, raw)
        self.assertEqual(set(files), {'README.md', 'evidence.json', 'verify.py', 'MANIFEST.json'})
        self.assertEqual(archive, study.public_bundle(d, raw)[1])
        with zipfile.ZipFile(io.BytesIO(archive)) as z:
            self.assertEqual(set(z.namelist()), set(files))
            self.assertTrue(all(z.read(name) == value for name, value in files.items()))
        manifest = schema.parse_json(files['MANIFEST.json'])
        for name, record in manifest['files'].items():
            self.assertEqual(record, {'sha256': sha256(files[name]).hexdigest(), 'bytes': len(files[name])})
        with tempfile.TemporaryDirectory(dir=ROOT / 'tests') as name:
            root = Path(name)
            for filename, value in files.items():
                (root / filename).write_bytes(value)
            result = subprocess.run(['python3', '-B', str(root / 'verify.py')], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('No native execution', result.stdout)
            (root / 'unexpected.txt').write_text('SYNTHETIC TEST ONLY')
            result = subprocess.run(['python3', '-B', str(root / 'verify.py')], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('exactly four', result.stderr)

    def test_integration_idempotent_and_old_content_preserved(self):
        d = fixture()
        for filename, lang in [('index.html', 'ja'), ('index.en.html', 'en')]:
            html = (ROOT / filename).read_text(); before = publication.LATEST.sub('', html)
            after = publication.integrate_home(html, lang, d)
            self.assertEqual(before, publication.LATEST.sub('', after))
            self.assertEqual(after, publication.integrate_home(after, lang, d))
        for filename, lang in [('results.html', 'ja'), ('results.en.html', 'en')]:
            html = (ROOT / filename).read_text(); after = publication.integrate_listing(html, lang, d)
            self.assertEqual(after, publication.integrate_listing(after, lang, d))
            self.assertEqual(after.count('data-study="experience-action-loop"'), 1)
            self.assertIn('2026-10-29-experience-retention-delayed', after)
        original = (ROOT / 'README.md').read_text()
        import re
        for start, end in ((publication.README_START, publication.README_END), (publication.BUILD_START, publication.BUILD_END)):
            original = re.sub(re.escape(start) + '.*?' + re.escape(end) + '\n\n', '', original, flags=re.S)
        after = publication.integrate_readme(original, d)
        self.assertEqual(after, publication.integrate_readme(after, d))
        removed = after
        for start, end in ((publication.README_START, publication.README_END), (publication.BUILD_START, publication.BUILD_END)):
            import re
            removed = re.sub(re.escape(start) + '.*?' + re.escape(end) + '\n\n', '', removed, flags=re.S)
        self.assertEqual(original, removed)
        sitemap = publication.integrate_sitemap((ROOT / 'sitemap.xml').read_text(), d)
        self.assertEqual(sitemap, publication.integrate_sitemap(sitemap, d))


if __name__ == '__main__':
    unittest.main()

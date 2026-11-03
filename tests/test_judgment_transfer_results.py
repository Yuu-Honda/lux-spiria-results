"""Mechanical preparation tests; synthetic values are never study evidence."""
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('judgment_transfer_test_publication', ROOT / 'tools/judgment_transfer_publication.py')
publication = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(publication)
study, schema = publication.study, publication.study.schema


def world(mechanism='A'):
    """Invented schema fixture only, never a collected history."""
    ops = ['op-00000001', 'op-00000002', 'op-00000003']
    effects = ['literal', 'trim', 'decimal'] if mechanism == 'A' else ['resume_after_checkpoint', 'replay_skip_existing_key', 'replay_upsert_by_key']
    records = [{'id': 'synthetic-1', 'key': '1', 'value': 'one'}, {'id': 'synthetic-2', 'key': '01', 'value': 'two'}, {'id': 'synthetic-3', 'key': ' 1 ', 'value': 'three'}] if mechanism == 'A' else [{'id': 'synthetic-1', 'value': 'new-one'}, {'id': 'synthetic-2', 'value': 'two'}]
    input_value = {'records': records} if mechanism == 'A' else {'records': records, 'initial_store': [{'id': 'synthetic-1', 'value': 'old-one'}], 'checkpoint': 1}
    def case(identity, version, contract):
        return {'case_id': identity, 'version': version, 'contract': {'kind': contract, 'text': 'SYNTHETIC TEST ONLY'}, 'input': deepcopy(input_value)}
    contracts = effects if mechanism == 'A' else ['preserve', 'preserve', 'refresh']
    return {'world_id': 'SYNTHETIC-' + mechanism, 'mechanism': mechanism, 'operations': ops,
        'versions': {'v1': dict(zip(ops, effects)), 'v2': dict(zip(ops, effects[1:] + effects[:1]))},
        'training_cases': [case('training-' + str(i), 'v1', contract) for i, contract in enumerate(contracts)],
        'probes': {'same_version': case('same', 'v1', contracts[0]), 'changed_version': case('changed', 'v2', contracts[0])}}


def refresh_packets(row, sources):
    """Re-sign a synthetic mutation as a collector could; shape must still fail."""
    task, feedback = row['task'], row['feedback']
    encode = lambda value: (schema.canonical(value) + '\n').encode('utf-8')
    task_text = encode(task).decode('utf-8')
    sources['task', row['assignment_id']]['text'] = task_text
    sources['task', row['assignment_id']]['text_sha256'] = sha256(task_text.encode()).hexdigest()
    initial, extra = task['initial_originals'], feedback['originals']
    summary = task['initial_judgment']['text'] if task['initial_judgment'] else ''
    diagnostic = feedback['diagnostic']['text'] if feedback['diagnostic'] else ''
    unique = {x['source_id']: x['text'] for x in initial + extra}
    chars = lambda items: sum(len(x['text']) for x in items)
    byte_count = lambda items: sum(len(x['text'].encode()) for x in items)
    metrics = {'initial_original_count': len(initial), 'requested_original_reads': len(extra),
        'duplicate_initial_reads': sum(x['source_id'] in {y['source_id'] for y in initial} for x in extra),
        'diagnostic_calls': int(row['policy']['calibration']), 'initial_packet_chars': len(task_text),
        'initial_packet_bytes': len(task_text.encode()), 'initial_summary_chars': len(summary),
        'initial_summary_bytes': len(summary.encode()), 'initial_raw_chars': chars(initial),
        'initial_raw_bytes': byte_count(initial), 'additional_raw_chars': chars(extra),
        'additional_raw_bytes': byte_count(extra), 'calibration_chars': len(diagnostic),
        'calibration_bytes': len(diagnostic.encode()), 'unique_original_count': len(unique),
        'unique_original_chars': sum(map(len, unique.values())),
        'unique_original_bytes': sum(len(t.encode()) for t in unique.values()),
        'duplicate_raw_bytes': byte_count(initial + extra) - sum(len(t.encode()) for t in unique.values())}
    feedback['io_accounting'] = metrics
    for _ in range(12):
        body = encode(feedback)
        sizes = {'feedback_packet_chars': len(body.decode()), 'feedback_packet_bytes': len(body),
            'total_transferred_packet_bytes': len(task_text.encode()) + len(body)}
        if all(metrics.get(k) == v for k, v in sizes.items()):
            break
        metrics.update(sizes)
    row['io'] = deepcopy(metrics)
    row['task_sha256'] = sha256(encode(task)).hexdigest()
    row['feedback_sha256'] = sha256(encode(feedback)).hexdigest()


def fixture():
    """Complete invented validator input; never serialized as research results."""
    digest = sha256(b'SYNTHETIC TEST ONLY').hexdigest()
    worlds = [dict(world('A' if index < 3 else 'B'), world_id='SYNTHETIC-' + str(index)) for index in range(6)]
    data = {'schema': schema.SCHEMA, 'date': '2026-11-03', 'analyzed_at_utc': '2026-11-03T00:00:00Z',
        'histories': 6, 'mechanisms': 2, 'teacher_contexts': 6, 'probe_contexts': 36,
        'teacher_rounds': [], 'rows': [], 'aggregates': [], 'matched_pairs': [],
        'primary_paired_accepted_difference': 0, 'process_counts': {'training_workers': 36,
            'diagnostic_workers': 36, 'target_workers': 0, 'native_capture_review_read_workers': 18},
        'protocol_sha256': digest, 'preregistration_sha256': digest,
        'provider_metadata': {key: None for key in ('provider', 'model', 'settings', 'tokens', 'compute')},
        'boundary': 'SYNTHETIC TEST ONLY', 'hashes': {'synthetic': digest},
        'audit': {'status': 'approved', 'scope': 'SYNTHETIC TEST ONLY', 'report_sha256': digest},
        'protection': dict(schema.PROTECTION), 'boundaries': ['SYNTHETIC TEST ONLY'],
        'source_messages': [], 'teacher_judgments': [], 'worlds': worlds}
    sources = {}
    def add_source(kind, identity, text, world_id):
        if (kind, identity) not in sources:
            source = {'id': identity, 'world_id': world_id, 'source_kind': kind,
                'text': text, 'text_sha256': sha256(text.encode()).hexdigest()}
            sources[kind, identity] = source
            data['source_messages'].append(source)
        return {'source_kind': kind, 'source_id': identity, 'text': text}
    for current in worlds:
        wid = current['world_id']
        originals, catalog = [], []
        for rnd in (1, 2):
            data['teacher_rounds'].append({'world_id': wid, 'round': rnd, 'allocated': 3, 'accepted': 0})
            for index, case in enumerate(current['training_cases']):
                text = f'SYNTHETIC TEST ONLY {wid} {rnd} {index}\n'
                identity = sha256(text.encode()).hexdigest()
                originals.append(add_source('original', identity, text, wid))
                catalog.append({'source_id': identity, 'content_sha256': identity,
                    'case_id': case['case_id'], 'round': rnd, 'operation': current['operations'][index]})
        provenance = sha256(('SYNTHETIC judgment ' + wid).encode()).hexdigest()
        judgment = add_source('judgment', 'judgment-' + provenance, 'SYNTHETIC TEST ONLY: judgment ' + wid, wid)
        teacher = {'world_id': wid, 'source_id': judgment['source_id'], 'text': judgment['text'], 'native_status': 'deferred',
            'native_receipt': {'candidate_id': 'SYNTHETIC-' + wid, 'source_ids': [s['source_id'] for s in originals],
                **{key: digest for key in ('candidate_record_sha256', 'capture_manifest_sha256', 'review_manifest_sha256', 'read_manifest_sha256')}}}
        data['teacher_judgments'].append(teacher)
        for phase in schema.PHASES:
            for arm in schema.ARMS:
                aid = 'p-' + format(len(data['rows']), '016x')
                probe = current['probes'][phase]
                policy = {'provisional_operation': None, 'prediction': 'SYNTHETIC TEST ONLY',
                    'original_source_ids': [originals[0]['source_id']], 'calibration': True, 'reason': 'SYNTHETIC TEST ONLY'}
                final = {'decision': 'abstain', 'operation': None, 'prediction': 'SYNTHETIC TEST ONLY', 'reason': 'SYNTHETIC TEST ONLY', 'evidence': []}
                record_schema = {'id': 'unique string', **({'key': 'string'} if current['mechanism'] == 'A' else {}), 'value': 'string'}
                task = {'schema': 'judgment-transfer-probe-task.v1', 'assignment_id': aid,
                    'current_version': probe['version'], 'task': {'case_id': probe['case_id'], 'current_version': probe['version'], 'contract_text': probe['contract']['text'], 'input': probe['input']},
                    'operations': current['operations'], 'schemas': {'records': record_schema,
                        'output': 'JSON groups [{key:string,members:[record id]}] plus intact original records' if current['mechanism'] == 'A' else 'SQLite records(id TEXT PRIMARY KEY,value TEXT NOT NULL) and exact JSON export',
                        'checkpoint': None if current['mechanism'] == 'A' else 'zero-based input-prefix length'},
                    'training_cases': [{'case_id': c['case_id'], 'current_version': c['version'], 'contract_text': c['contract']['text'], 'input': c['input']} for c in current['training_cases']],
                    'original_sources': deepcopy(catalog), 'original_source_read_limit': 6, 'current_diagnostic_call_limit': 1,
                    'policy_schema': dict(schema.POLICY_SCHEMA), 'final_schema': dict(schema.FINAL_SCHEMA),
                    'instruction': 'SYNTHETIC TEST ONLY', 'initial_originals': deepcopy(originals) if arm == 'all_raw_upfront' else [],
                    'initial_judgment': {**judgment, 'native_status': 'deferred', 'provenance_sha256': provenance} if arm == 'raw_plus_judgment' else None}
                diagnostic_text = 'SYNTHETIC TEST ONLY diagnostic ' + wid + phase
                diagnostic_id = 'diagnostic-' + sha256(schema.canonical(diagnostic_text).encode()).hexdigest()
                diagnostic = add_source('current_diagnostic', diagnostic_id, diagnostic_text, wid)
                policy_text, final_text = json.dumps(policy, indent=2) + '\n', json.dumps(final, indent=2) + '\n'
                policy_hash = sha256(policy_text.encode()).hexdigest()
                feedback = {'schema': 'judgment-transfer-policy-feedback.v1', 'assignment_id': aid,
                    'policy_sha256': policy_hash, 'originals': [deepcopy(originals[0])], 'diagnostic': diagnostic,
                    'status_notices': [], 'io_accounting': {}, 'diagnostic_manifest': {'manifest_path': 'assignments/' + aid + '/diagnostic/manifest.json', 'manifest_sha256': digest, 'exit_code': 0}}
                add_source('task', aid, 'SYNTHETIC pending packet', wid)
                available = [('task', aid), ('current_diagnostic', diagnostic_id)] + [('original', s['source_id']) for s in originals if arm == 'all_raw_upfront' or s == originals[0]]
                if arm == 'raw_plus_judgment':
                    available.append(('judgment', judgment['source_id']))
                row = {'assignment_id': aid, 'world_id': wid, 'mechanism': current['mechanism'], 'phase': phase, 'arm': arm,
                    'policy': policy, 'final': final, 'accepted': False, 'state_valid': None, 'process_completed': None,
                    'worker_exit_code': None, 'operation_status': None, 'abstained': True,
                    'old_version_acceptable': sorted(schema.acceptable_operations(current, 'same_version')),
                    'current_acceptable': sorted(schema.acceptable_operations(current, phase)),
                    'old_only_choice': False, 'provisional_old_only': False, 'operation_changed_after_feedback': False,
                    'citation_status': 'none', 'quote_checks': [], 'cited_original_source_count': 0,
                    'exact_cited_original_source_count': 0, 'exact_judgment_citations': 0, 'io': {},
                    'task_sha256': digest, 'policy_sha256': policy_hash, 'feedback_sha256': digest,
                    'final_sha256': sha256(final_text.encode()).hexdigest(), 'outcome_sha256': digest,
                    'target_manifest_sha256': None, 'available_sources': [{'source_kind': kind, 'source_id': sid} for kind, sid in available],
                    'target_artifact_sha256': None, 'target_validation': None, 'task': task, 'feedback': feedback,
                    'policy_raw_text': policy_text, 'final_raw_text': final_text}
                refresh_packets(row, sources)
                data['rows'].append(row)
    refresh_aggregates(data)
    return data


def refresh_aggregates(data):
    data['aggregates'] = schema.recalculate(data['rows'])
    data['matched_pairs'] = schema.matched_pairs(data['rows'], {w['world_id']: w for w in data['worlds']})


class JudgmentTransferPreparationTests(unittest.TestCase):
    def test_installed_actual_publication_verifier_and_saved_work_replay(self):
        if not (ROOT / study.DATA_FILE).is_file():
            self.skipTest('Audited judgment-transfer export is not installed')
        data = study.optional_summary(ROOT)
        for name, expected in publication.prepare_updates(ROOT).items():
            self.assertEqual((ROOT / name).read_bytes(), expected, name)
        manifest = schema.verify_bundle(ROOT / study.REPLAY)
        with zipfile.ZipFile(ROOT / study.ZIP_FILE) as archive:
            self.assertEqual(set(archive.namelist()), set(manifest['files']) | {'MANIFEST.json'})
            for name in archive.namelist():
                self.assertEqual(archive.read(name), (ROOT / study.REPLAY / name).read_bytes(), name)
        result = subprocess.run(['python3', '-B', str(ROOT / study.REPLAY / 'replay.py'), str(ROOT / study.REPLAY / 'evidence.json')], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        available = sum(r['target_validation'] is not None for r in data['rows'])
        self.assertIn('compared ' + str(available) + ' saved target operations', result.stdout)
        self.assertIn('No original trial, native LRE, fresh AI choices', result.stdout)

    def test_complete_synthetic_fixture_and_packet_arithmetic(self):
        data = fixture()
        self.assertIs(schema.validate_summary(data), data)
        self.assertEqual(len(data['rows']), 36)
        self.assertEqual(len(data['aggregates']), 18)
        self.assertEqual(data['rows'][0]['io']['requested_original_reads'], 1)
        self.assertEqual(data['rows'][2]['io']['duplicate_initial_reads'], 1)
        self.assertTrue(all(r['citation_status'] == 'none' for r in data['rows']))

    def test_nested_packet_gaps_rejected_after_legitimate_hash_and_io_recompute(self):
        baseline = fixture()
        schema.validate_summary(baseline)
        cases = [
            ('catalog-extra', 'raw_only', lambda r: r['task']['original_sources'][0].update(unexpected_private_payload='SYNTHETIC')),
            ('catalog-missing-key', 'raw_only', lambda r: r['task']['original_sources'][0].pop('case_id')),
            ('catalog-bool-round', 'raw_only', lambda r: r['task']['original_sources'][0].update(round=True)),
            ('catalog-bad-operation', 'raw_only', lambda r: r['task']['original_sources'][0].update(operation='SYNTHETIC-unknown')),
            ('original-extra', 'all_raw_upfront', lambda r: r['task']['initial_originals'][0].update(unexpected_private_payload='SYNTHETIC')),
            ('feedback-original-extra', 'raw_only', lambda r: r['feedback']['originals'][0].update(unexpected_private_payload='SYNTHETIC')),
            ('diagnostic-extra', 'raw_only', lambda r: r['feedback']['diagnostic'].update(unexpected_private_payload='SYNTHETIC')),
            ('judgment-extra', 'raw_plus_judgment', lambda r: r['task']['initial_judgment'].update(unexpected_private_payload='SYNTHETIC')),
            ('judgment-wrong-id', 'raw_plus_judgment', lambda r: r['task']['initial_judgment'].update(source_id='SYNTHETIC-wrong')),
            ('schemas-list', 'raw_only', lambda r: r['task'].update(schemas=['SYNTHETIC'])),
            ('schemas-record-extra', 'raw_only', lambda r: r['task']['schemas']['records'].update(unexpected_private_payload='SYNTHETIC')),
            ('policy-schema-bool', 'raw_only', lambda r: r['task'].update(policy_schema=False)),
            ('policy-schema-wrong-type', 'raw_only', lambda r: r['task']['policy_schema'].update(calibration=False)),
            ('final-schema-string', 'raw_only', lambda r: r['task'].update(final_schema='SYNTHETIC')),
            ('final-schema-extra', 'raw_only', lambda r: r['task']['final_schema'].update(unexpected_private_payload='SYNTHETIC')),
            ('diagnostic-manifest-extra', 'raw_only', lambda r: r['feedback']['diagnostic_manifest'].update(unexpected_private_payload='SYNTHETIC')),
            ('diagnostic-manifest-wrong-type', 'raw_only', lambda r: r['feedback']['diagnostic_manifest'].update(exit_code=True)),
            ('diagnostic-manifest-other-row', 'raw_only', lambda r: r['feedback']['diagnostic_manifest'].update(manifest_path='assignments/other/diagnostic/manifest.json')),
            ('diagnostic-manifest-primitive', 'raw_only', lambda r: r['feedback'].update(diagnostic_manifest='SYNTHETIC')),
            ('task-schema-unknown', 'raw_only', lambda r: r['task'].update(schema='SYNTHETIC-unknown')),
        ]
        for name, arm, mutate in cases:
            with self.subTest(name=name):
                data = deepcopy(baseline)
                row = next(r for r in data['rows'] if r['arm'] == arm)
                mutate(row)
                sources = {(s['source_kind'], s['id']): s for s in data['source_messages']}
                refresh_packets(row, sources)
                refresh_aggregates(data)
                with self.assertRaises(ValueError):
                    schema.validate_summary(data)

    def test_failure_notice_shape_and_no_diagnostic_nullable_binding(self):
        data = fixture()
        row = data['rows'][0]
        row['feedback']['diagnostic_manifest']['exit_code'] = 1
        notice = {'source_kind': 'status_notice', 'source_id': 'status-' + row['assignment_id'], 'text': schema.DIAGNOSTIC_FAILURE_NOTICE}
        row['feedback']['status_notices'] = [notice]
        source = {'id': notice['source_id'], 'source_kind': 'status_notice', 'world_id': row['world_id'], 'text': notice['text'], 'text_sha256': sha256(notice['text'].encode()).hexdigest()}
        data['source_messages'].append(source)
        row['available_sources'].append({'source_kind': 'status_notice', 'source_id': notice['source_id']})
        sources = {(s['source_kind'], s['id']): s for s in data['source_messages']}
        refresh_packets(row, sources)
        refresh_aggregates(data)
        schema.validate_summary(data)
        row['feedback']['status_notices'][0]['unexpected_private_payload'] = 'SYNTHETIC'
        refresh_packets(row, sources)
        refresh_aggregates(data)
        with self.assertRaises(ValueError):
            schema.validate_summary(data)
        data = fixture()
        row = data['rows'][0]
        row['policy']['calibration'] = False
        row['policy_raw_text'] = json.dumps(row['policy'], indent=2) + '\n'
        row['policy_sha256'] = sha256(row['policy_raw_text'].encode()).hexdigest()
        row['feedback'].update(diagnostic=None, diagnostic_manifest=None, policy_sha256=row['policy_sha256'])
        row['available_sources'] = [s for s in row['available_sources'] if s['source_kind'] != 'current_diagnostic']
        data['process_counts']['diagnostic_workers'] = 35
        sources = {(s['source_kind'], s['id']): s for s in data['source_messages']}
        refresh_packets(row, sources)
        refresh_aggregates(data)
        schema.validate_summary(data)
        row['feedback']['diagnostic_manifest'] = {'unexpected_private_payload': 'SYNTHETIC'}
        refresh_packets(row, sources)
        refresh_aggregates(data)
        with self.assertRaises(ValueError):
            schema.validate_summary(data)

    def test_replay_verifies_all_files_and_own_engine_pin_before_local_import(self):
        replay = (ROOT / 'tools/judgment_transfer_replay.py').read_bytes()
        for bad_record in (True, False):
            with self.subTest(bad_manifest_record=bad_record), tempfile.TemporaryDirectory() as temporary:
                folder = Path(temporary)
                sentinel = folder / 'SYNTHETIC-import-sentinel'
                malicious = ('from pathlib import Path\nPath(' + repr(str(sentinel)) + ').write_text("SYNTHETIC import executed")\n').encode()
                content = {'replay.py': replay, 'verify.py': malicious, 'world_engine.py': malicious,
                    'common.py': b'# SYNTHETIC TEST ONLY\n', 'README.md': b'SYNTHETIC TEST ONLY\n',
                    'worlds.json': b'{}\n', 'plans.json': b'[]\n', 'evidence.json': json.dumps({'hashes': {
                        'common_py_sha256': sha256(b'# SYNTHETIC TEST ONLY\n').hexdigest(),
                        'world_engine_py_sha256': sha256(b'expected SYNTHETIC engine').hexdigest()}}).encode()}
                manifest = {'schema': 'judgment-transfer-public-package.v1', 'replay': True,
                    'files': {name: {'bytes': len(raw), 'sha256': sha256(raw).hexdigest()} for name, raw in content.items()}}
                if bad_record:
                    manifest['files']['world_engine.py']['sha256'] = '0' * 64
                for name, raw in content.items():
                    (folder / name).write_bytes(raw)
                (folder / 'MANIFEST.json').write_text(json.dumps(manifest))
                result = subprocess.run(['python3', '-B', str(folder / 'replay.py'), str(folder / 'evidence.json')], capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('hash mismatch' if bad_record else 'own-engine digest mismatch', result.stderr)
                self.assertFalse(sentinel.exists(), 'No verifier or engine import may run before bootstrap verification')

    def test_no_export_means_empty_plan_and_no_writes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sentinel = root / 'prior-published-bytes'
            sentinel.write_bytes(b'SYNTHETIC PRESERVATION TEST')
            self.assertEqual(publication.prepare_updates(root), {})
            self.assertEqual({p.name for p in root.iterdir()}, {sentinel.name})
            self.assertEqual(sentinel.read_bytes(), b'SYNTHETIC PRESERVATION TEST')

    def test_bad_or_missing_explicit_input_never_plans_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bad = root / 'synthetic-invalid.json'
            bad.write_bytes(b'{"schema":"SYNTHETIC TEST ONLY"}')
            for source in (bad, root / 'missing.json'):
                with self.assertRaises(ValueError):
                    publication.prepare_updates(root, source)
            self.assertEqual({p.name for p in root.iterdir()}, {bad.name})

    def test_replay_without_export_rejected_before_write(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, 'Replay requires'):
                publication.prepare_updates(Path(temporary), replay=Path(temporary))
            self.assertEqual(list(Path(temporary).iterdir()), [])

    def test_parser_rejects_duplicates_nonfinite_and_extra_keys(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}'):
            with self.assertRaises(ValueError):
                schema.parse_json(raw)
        with self.assertRaises(ValueError):
            schema.keys({'a': 1, 'secret': 2}, {'a'}, 'SYNTHETIC')

    def test_bool_is_not_an_integer_measurement(self):
        with self.assertRaises(ValueError):
            schema.integer(True, 'synthetic count')

    def test_disclosed_operation_acceptance_checks_actual_contract(self):
        a = world('A')
        self.assertEqual(schema.acceptable_operations(a, 'same_version'), {'op-00000001'})
        self.assertEqual(schema.acceptable_operations(a, 'changed_version'), {'op-00000003'})
        b = world('B')
        self.assertEqual(schema.acceptable_operations(b, 'same_version'), {'op-00000001', 'op-00000002'})
        b['probes']['same_version']['input']['checkpoint'] = 0
        # Resume now conflicts and rolls back; valid prior state alone cannot pass.
        self.assertEqual(schema.acceptable_operations(b, 'same_version'), {'op-00000002'})

    def test_typed_quotation_none_false_and_available_are_distinct(self):
        text = 'SYNTHETIC TEST ONLY: saved source'
        source = {'text': text}
        sources = {('original', 'synthetic-source'): source}
        row = {'final': {'evidence': []}, 'quote_checks': [], 'citation_status': 'none',
            'cited_original_source_count': 0, 'exact_cited_original_source_count': 0, 'exact_judgment_citations': 0}
        schema.validate_quotes(row, sources, set())
        evidence = {'source_kind': 'original', 'source_id': 'synthetic-source', 'quote': 'saved source'}
        row['final']['evidence'] = [evidence]
        row.update(cited_original_source_count=1, exact_cited_original_source_count=0,
            citation_status='inaccurate_or_unavailable', quote_checks=[{'evidence_index': 0,
                'source_kind': 'original', 'source_id': 'synthetic-source', 'source_available': False,
                'quote_exact': False, 'available_source_text_sha256': None}])
        schema.validate_quotes(row, sources, set())
        row['quote_checks'][0].update(source_available=True, quote_exact=True,
            available_source_text_sha256=sha256(text.encode()).hexdigest())
        row.update(citation_status='exact_available_quotes', exact_cited_original_source_count=1)
        schema.validate_quotes(row, sources, {('original', 'synthetic-source')})
        row['quote_checks'][0]['quote_exact'] = False
        with self.assertRaises(ValueError):
            schema.validate_quotes(row, sources, {('original', 'synthetic-source')})

    def test_global_activation_collision_rejected_before_publication(self):
        paths = [ROOT / study.DATA_FILE, ROOT / study.STUDY / 'index.html', ROOT / study.STUDY / 'en.html', ROOT / 'README.md']
        before = {path: path.read_bytes() if path.is_file() else None for path in paths}
        command = ['python3', '-B', 'tools/build_pages.py', '--judgment-transfer', '/SYNTHETIC-NOT-AN-EXPORT', '--experience-action-loop', '/SYNTHETIC-NOT-AN-EXPORT']
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('Activate one external study per command', result.stderr)
        self.assertEqual({path: path.read_bytes() if path.is_file() else None for path in paths}, before)


if __name__ == '__main__':
    unittest.main()

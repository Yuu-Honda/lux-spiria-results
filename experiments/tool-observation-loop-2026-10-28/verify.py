#!/usr/bin/env python3
"""Validate an allowlisted public pilot export; verify saved metadata only.

This file is also the complete standalone public verifier. It never imports
private native code or reconstructs undisclosed operations or AI judgments.
"""
import argparse
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import re
import stat

STUDY_ID = 'tool-observation-loop-2026-10-28'
OPERATION_NAMES = frozenset({'initialize', 'lre_read', 'lre_capture', 'lre_review',
    'shiori_draft', 'shiori_capture_raw', 'shiori_ingest', 'shiori_recall',
    'shiori_raw_search', 'shiori_inspect', 'hydrate'})
PHASES = frozenset({'initialization', 'judgment', 'raw_capture', 'indexing',
    'unchanged', 'changed_context', 'legacy_return', 'diagnostic'})
SCOPE = {'isolated_native_instances': True, 'private_payloads_exported': False,
    'complete_native_replay': False, 'fresh_ai_regeneration': False,
    'delayed_study_unchanged': True, 'provider_metadata': None}
PROVENANCE = frozenset({'protocol_sha256', 'operation_contract_sha256',
    'adapter_revision_01_sha256', 'adapter_revision_02_sha256',
    'results_sha256', 'final_audit_sha256'})
CONTEXT_BINDINGS = {'C01': 'unchanged', 'C02': 'changed_context', 'C03': 'legacy_return'}
CONTEXT_FLAGS = frozenset({'tool_source_return', 'judgment_return', 'exact_input_match',
    'exact_stdout_match', 'exact_stderr_match', 'old_retained_preserved',
    'hops0_same_hits', 'convergence_off_same_hits'})
CONTEXT_SCORES = frozenset({'top_score', 'hops0_top_score', 'convergence_off_top_score'})
OPERATION_FIELDS = frozenset({'ordinal', 'phase', 'operation', 'exit_code',
    'manifest_sha256', 'started_at_utc', 'finished_at_utc',
    'plan_before_execution', 'native_state_unchanged', 'revision'})
TOP_FIELDS = frozenset({'schema_version', 'study_id', 'date', 'evidence_kind',
    'operations', 'contexts', 'source_counts', 'engineering', 'counts',
    'provenance', 'scope'})


def keys(value, expected, where):
    if type(value) is not dict or set(value) != set(expected):
        raise ValueError(where + ': unexpected or missing public fields')


def integer(value, where, minimum=0, maximum=None):
    if type(value) is not int or value < minimum or (maximum is not None and value > maximum):
        raise ValueError(where + ': invalid integer')


def digest(value, where):
    if type(value) is not str or re.fullmatch(r'[a-f0-9]{64}', value) is None:
        raise ValueError(where + ': lowercase SHA256 required')


def clock(value):
    if type(value) is not str or re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|\+00:00)', value) is None:
        raise ValueError('UTC clock: restricted RFC3339 required')
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError('UTC clock: invalid timestamp') from exc


def nullable_boolean(value, where):
    if value is not None and type(value) is not bool:
        raise ValueError(where + ': boolean or null required')


def nullable_score(value):
    if value is None:
        return
    if type(value) not in (int, float) or value < 0:
        raise ValueError('Ranking score: finite nonnegative number or null required')
    try:
        finite = math.isfinite(value)
    except OverflowError as exc:
        raise ValueError('Ranking score outside finite range') from exc
    if not finite:
        raise ValueError('Ranking score must be finite')


def aggregate_operations(rows):
    return {'operations': len(rows),
        'exit_zero': sum(row['exit_code'] == 0 for row in rows),
        'exit_nonzero': sum(row['exit_code'] != 0 for row in rows),
        'plans_before_execution': sum(row['plan_before_execution'] for row in rows),
        'native_unchanged': sum(row['native_state_unchanged'] is True for row in rows),
        'native_changed': sum(row['native_state_unchanged'] is False for row in rows),
        'native_unmeasured': sum(row['native_state_unchanged'] is None for row in rows)}


def validate_summary(d):
    keys(d, TOP_FIELDS, 'summary')
    if type(d['schema_version']) is not int or d['schema_version'] != 1 or d['study_id'] != STUDY_ID or d['date'] != '2026-10-28' or d['evidence_kind'] != 'actual_functional_pilot':
        raise ValueError('Unexpected frozen study identity/evidence kind')
    if type(d['operations']) is not list or not 1 <= len(d['operations']) <= 1000:
        raise ValueError('Retain bounded actual operations')
    operations = {}
    for ordinal, row in enumerate(d['operations'], 1):
        keys(row, OPERATION_FIELDS, 'operation')
        integer(row['ordinal'], 'operation ordinal', 1)
        if row['ordinal'] != ordinal:
            raise ValueError('Operation ordinals must be consecutive and unique')
        if type(row['phase']) is not str or row['phase'] not in PHASES or type(row['operation']) is not str or row['operation'] not in OPERATION_NAMES:
            raise ValueError('Unsupported public phase/operation')
        integer(row['exit_code'], 'actual exit code', -255, 255)
        digest(row['manifest_sha256'], 'original manifest')
        if clock(row['finished_at_utc']) < clock(row['started_at_utc']):
            raise ValueError('Operation ends before it starts')
        if type(row['plan_before_execution']) is not bool:
            raise ValueError('Actual pre-execution plan flag requires boolean')
        nullable_boolean(row['native_state_unchanged'], 'native-state equality')
        integer(row['revision'], 'adapter revision', 1, 2)
        if row['revision'] != (1 if ordinal == 1 else 2) or (ordinal == 1 and (row['operation'], row['phase']) != ('initialize', 'initialization')):
            raise ValueError('Retain original revision-1 initialize, followed by revision-2 operations')
        operations[ordinal] = row
    if type(d['contexts']) is not list or len(d['contexts']) != 3:
        raise ValueError('Retain exactly three bounded context checks')
    seen, assigned = set(), set()
    for row in d['contexts']:
        keys(row, CONTEXT_FLAGS | CONTEXT_SCORES | {'id', 'condition', 'first_operation', 'exit_code', 'graph_support_path_count', 'matched_cue_count'}, 'context')
        identity = row['id']
        if type(identity) is not str or identity not in CONTEXT_BINDINGS or identity in seen or row['condition'] != CONTEXT_BINDINGS[identity]:
            raise ValueError('Frozen context identity/condition missing or duplicated')
        seen.add(identity)
        first = row['first_operation']
        if first is None:
            if row['exit_code'] is not None:
                raise ValueError('No actual first operation requires null exit code')
        else:
            integer(first, 'context first operation', 1)
            if first not in operations or first in assigned or operations[first]['phase'] != row['condition']:
                raise ValueError('Context must bind its own distinct actual phase operation')
            integer(row['exit_code'], 'context actual exit code', -255, 255)
            if row['exit_code'] != operations[first]['exit_code']:
                raise ValueError('Context exit code must match its actual first operation')
            assigned.add(first)
        for field in CONTEXT_FLAGS:
            nullable_boolean(row[field], 'context ' + field)
        for field in ('graph_support_path_count', 'matched_cue_count'):
            if row[field] is not None:
                integer(row[field], 'actual ' + field)
        for field in CONTEXT_SCORES:
            nullable_score(row[field])
    keys(d['source_counts'], {'tool_observations', 'actual_ai_judgments', 'independent_events'}, 'source counts')
    for value in d['source_counts'].values():
        integer(value, 'source count')
    if d['source_counts']['independent_events'] > d['source_counts']['tool_observations']:
        raise ValueError('Independent event count exceeds original tool observations')
    if type(d['engineering']) is not list or len(d['engineering']) != 2:
        raise ValueError('Retain the two separate synthetic engineering rounds')
    seen = set()
    for row in d['engineering']:
        keys(row, {'round', 'tests', 'worker_invocations', 'failures', 'errors', 'evidence_kind', 'report_sha256'}, 'engineering')
        integer(row['round'], 'engineering round', 1, 2)
        if row['round'] in seen or row['evidence_kind'] != 'synthetic_engineering':
            raise ValueError('Duplicate or mislabeled engineering round')
        seen.add(row['round'])
        for field in ('tests', 'worker_invocations', 'failures', 'errors'):
            integer(row[field], 'engineering ' + field)
        if (row['tests'], row['worker_invocations']) != {1: (14, 93), 2: (15, 102)}[row['round']] or row['failures'] + row['errors'] > row['tests']:
            raise ValueError('Frozen engineering denominator differs')
        digest(row['report_sha256'], 'engineering report')
    calculated = aggregate_operations(d['operations'])
    keys(d['counts'], calculated, 'counts')
    for field, value in calculated.items():
        integer(d['counts'][field], 'count ' + field)
        if d['counts'][field] != value:
            raise ValueError('Every count must recalculate from actual operations')
    keys(d['provenance'], PROVENANCE, 'provenance')
    for value in d['provenance'].values():
        digest(value, 'provenance')
    keys(d['scope'], SCOPE, 'scope')
    for field, value in SCOPE.items():
        if type(d['scope'][field]) is not type(value) or d['scope'][field] != value:
            raise ValueError('Frozen privacy/replay/provider boundary differs')
    return d


def parse_json(raw):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError('Duplicate public JSON key')
            value[key] = item
        return value
    def nonfinite(value):
        raise ValueError('Nonfinite public JSON number')
    return json.loads(raw.decode('utf-8'), object_pairs_hook=unique, parse_constant=nonfinite)


def read_json(path):
    return parse_json(Path(path).read_bytes())


def read_summary(path):
    return validate_summary(read_json(path))


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def verify_bundle(bundle):
    bundle = Path(bundle)
    if bundle.is_symlink() or not bundle.is_dir():
        raise ValueError('Saved-evidence bundle must be a regular directory')
    actual = set()
    for path in bundle.rglob('*'):
        if not stat.S_ISREG(path.lstat().st_mode):
            raise ValueError('Saved-evidence bundle permits regular files only')
        actual.add(path.relative_to(bundle).as_posix())
    required = {'MANIFEST.json', 'README.md', 'evidence.json', 'verify.py'}
    if actual != required:
        raise ValueError('Exact saved-evidence inventory or MANIFEST case differs')
    manifest = read_json(bundle / 'MANIFEST.json')
    keys(manifest, {'schema_version', 'files'}, 'manifest')
    if type(manifest['schema_version']) is not int or manifest['schema_version'] != 1:
        raise ValueError('Unsupported manifest version')
    keys(manifest['files'], required - {'MANIFEST.json'}, 'manifest inventory')
    for name, row in manifest['files'].items():
        keys(row, {'sha256', 'bytes'}, 'manifest file')
        digest(row['sha256'], 'manifest SHA256'); integer(row['bytes'], 'manifest bytes')
        raw = (bundle / name).read_bytes()
        if len(raw) != row['bytes'] or sha256(raw) != row['sha256']:
            raise ValueError('Saved-evidence SHA256 or byte-size mismatch')
    d = read_summary(bundle / 'evidence.json')
    return {'status': 'verified', 'files': 4, 'manifest_sha256': sha256((bundle / 'MANIFEST.json').read_bytes()),
        'evidence_sha256': sha256((bundle / 'evidence.json').read_bytes()), 'counts': d['counts'],
        'verification_scope': 'Disclosed metadata hashes and arithmetic only; private native operations and exported claims are not independently reconstructed.',
        'native_execution_replayed': False, 'fresh_ai_choices_generated': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args(argv)
    try:
        report = verify_bundle(args.bundle)
    except (ValueError, OSError, UnicodeError) as error:
        report = {'status': 'failed', 'error_type': type(error).__name__, 'native_execution_replayed': False}
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False))
    return 0 if report['status'] == 'verified' else 1


if __name__ == '__main__':
    raise SystemExit(main())

"""Strict public saved-record verifier. Standard library; no trial/native calls.

Only disclosed arithmetic, source hashes, availability and typed quotation
checks are verified. Audit approval is required but not independently repeated.
"""
import argparse
from collections import Counter
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import re

SCHEMA = 'judgment-transfer-public.v1'
ARMS = ('raw_only', 'raw_plus_judgment', 'all_raw_upfront')
PHASES = ('same_version', 'changed_version')
SOURCE_KINDS = ('original', 'judgment', 'current_diagnostic', 'task', 'status_notice')
IO_FIELDS = ('initial_original_count', 'requested_original_reads', 'duplicate_initial_reads',
    'diagnostic_calls', 'initial_packet_chars', 'initial_packet_bytes',
    'initial_summary_chars', 'initial_summary_bytes', 'initial_raw_chars',
    'initial_raw_bytes', 'additional_raw_chars', 'additional_raw_bytes',
    'calibration_chars', 'calibration_bytes', 'unique_original_count',
    'unique_original_chars', 'unique_original_bytes', 'duplicate_raw_bytes',
    'feedback_packet_chars', 'feedback_packet_bytes', 'total_transferred_packet_bytes')
TOP_FIELDS = {'schema', 'date', 'analyzed_at_utc', 'histories', 'mechanisms',
    'teacher_contexts', 'probe_contexts', 'teacher_rounds', 'rows', 'aggregates',
    'matched_pairs', 'primary_paired_accepted_difference', 'process_counts',
    'protocol_sha256', 'preregistration_sha256', 'provider_metadata', 'boundary',
    'hashes', 'audit', 'protection', 'boundaries', 'source_messages',
    'teacher_judgments', 'worlds'}
ROW_FIELDS = {'assignment_id', 'world_id', 'mechanism', 'phase', 'arm', 'policy',
    'final', 'accepted', 'state_valid', 'process_completed', 'worker_exit_code',
    'operation_status', 'abstained', 'old_version_acceptable', 'current_acceptable',
    'old_only_choice', 'provisional_old_only', 'operation_changed_after_feedback',
    'citation_status', 'quote_checks', 'cited_original_source_count',
    'exact_cited_original_source_count', 'exact_judgment_citations', 'io',
    'task_sha256', 'policy_sha256', 'feedback_sha256', 'final_sha256',
    'outcome_sha256', 'target_manifest_sha256', 'available_sources',
    'target_artifact_sha256', 'target_validation', 'task', 'feedback',
    'policy_raw_text', 'final_raw_text'}
TASK_FIELDS = {'assignment_id', 'current_diagnostic_call_limit', 'current_version',
    'final_schema', 'initial_judgment', 'initial_originals', 'instruction',
    'operations', 'original_source_read_limit', 'original_sources', 'policy_schema',
    'schema', 'schemas', 'task', 'training_cases'}
FEEDBACK_FIELDS = {'assignment_id', 'diagnostic', 'diagnostic_manifest',
    'io_accounting', 'originals', 'policy_sha256', 'schema', 'status_notices'}
POLICY_SCHEMA = {'provisional_operation': 'one listed operation or null',
    'prediction': 'nonempty string; unknown is allowed',
    'original_source_ids': 'up to six distinct listed SHA256 source ids',
    'calibration': 'boolean', 'reason': 'nonempty string'}
FINAL_SCHEMA = {'decision': 'execute or abstain',
    'operation': 'listed operation when execute; null when abstain',
    'prediction': 'nonempty string; unknown is allowed', 'reason': 'nonempty string',
    'evidence': 'up to four {source_kind,source_id,quote}; exact quotations from available material only'}
DIAGNOSTIC_FAILURE_NOTICE = 'The committed diagnostic failed. Its failure output is preserved as current diagnostic evidence; its reservation is consumed and no retry is available.'
DIAGNOSTIC_MISSING_NOTICE = 'The committed diagnostic produced no readable output. Its reservation is consumed; no retry is available.'
AGGREGATE_FIELDS = {'phase', 'arm', 'mechanism', 'n', 'accepted', 'abstentions',
    'state_valid', 'operation_completed', 'operation_failures', 'worker_errors',
    'old_only_choices', 'provisional_old_only', 'changed_after_feedback',
    'citation_none', 'citation_inaccurate', 'exact_judgment_citations', 'io'}
PAIR_FIELDS = {'phase', 'world_id', 'mechanism', 'raw_only_accepted',
    'judgment_accepted', 'accepted_difference', 'diagnostic_call_difference',
    'additional_raw_byte_difference', 'total_packet_byte_difference'}
PROTECTION = {'public_export_only': True, 'private_vendor_source_excluded': True,
    'native_state_excluded': True, 'private_source_documents_excluded': True,
    'production_memory_written': False,
    'shared_host_instruction_allowlists': True, 'os_isolation': False}


def need(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def parse_json(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            need(key not in result, 'Duplicate public JSON key: ' + key)
            result[key] = value
        return result
    def nonfinite(value):
        raise ValueError('Nonfinite public JSON number: ' + value)
    return json.loads(raw.decode('utf-8') if isinstance(raw, bytes) else raw,
        object_pairs_hook=unique, parse_constant=nonfinite)


def keys(value, expected, where):
    need(type(value) is dict and set(value) == set(expected), where + ': exact public keys required')


def integer(value, where, minimum=0, maximum=None):
    need(type(value) is int and value >= minimum and (maximum is None or value <= maximum), where + ': integer out of range')


def string(value, where, empty=False):
    need(type(value) is str and (empty or bool(value.strip())) and '\x00' not in value, where + ': public string required')


def digest(value, where):
    need(type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None, where + ': lowercase SHA256 required')


def sequence(value, where):
    need(type(value) is list, where + ': list required')


def boolean(value, where):
    need(type(value) is bool, where + ': boolean required')


def strings(value, where, distinct=False):
    sequence(value, where)
    for item in value:
        string(item, where)
    need(not distinct or len(value) == len(set(value)), where + ': duplicate value')


def source_key(value, where):
    keys(value, {'source_kind', 'source_id'}, where)
    need(value['source_kind'] in SOURCE_KINDS, where + ': unknown source kind')
    string(value['source_id'], where + ' source id')
    return value['source_kind'], value['source_id']


def policy(value, operations):
    keys(value, {'provisional_operation', 'prediction', 'original_source_ids', 'calibration', 'reason'}, 'POLICY')
    need(value['provisional_operation'] is None or value['provisional_operation'] in operations, 'Invalid provisional operation')
    for field in ('prediction', 'reason'):
        string(value[field], 'POLICY ' + field)
    strings(value['original_source_ids'], 'POLICY source ids', distinct=True)
    need(len(value['original_source_ids']) <= 6, 'At most six original reads')
    boolean(value['calibration'], 'POLICY calibration')


def final(value, operations):
    keys(value, {'decision', 'operation', 'prediction', 'reason', 'evidence'}, 'FINAL')
    need(value['decision'] in ('execute', 'abstain'), 'Invalid FINAL decision')
    need((value['decision'] == 'execute' and value['operation'] in operations) or
         (value['decision'] == 'abstain' and value['operation'] is None), 'FINAL decision/operation disagree')
    for field in ('prediction', 'reason'):
        string(value[field], 'FINAL ' + field)
    sequence(value['evidence'], 'FINAL evidence')
    need(len(value['evidence']) <= 4, 'At most four typed quotations')
    for item in value['evidence']:
        keys(item, {'source_kind', 'source_id', 'quote'}, 'FINAL evidence')
        need(item['source_kind'] in SOURCE_KINDS, 'Unknown citation source kind')
        string(item['source_id'], 'Citation id')
        string(item['quote'], 'Citation quote')


def case(value, mechanism):
    keys(value, {'case_id', 'version', 'contract', 'input'}, 'World case')
    string(value['case_id'], 'Case id')
    need(value['version'] in ('v1', 'v2'), 'Unknown case version')
    keys(value['contract'], {'kind', 'text'}, 'Case contract')
    string(value['contract']['text'], 'Contract text')
    need(value['contract']['kind'] in ({'literal', 'trim', 'decimal'} if mechanism == 'A' else {'preserve', 'refresh'}), 'Unknown contract')
    keys(value['input'], {'records'} if mechanism == 'A' else {'records', 'initial_store', 'checkpoint'}, 'Case input')
    for name in ('records',) if mechanism == 'A' else ('records', 'initial_store'):
        sequence(value['input'][name], 'Input records')
        if name == 'records':
            need(bool(value['input'][name]), 'Nonempty input records required')
        seen = set()
        for record in value['input'][name]:
            keys(record, {'id', 'key', 'value'} if mechanism == 'A' else {'id', 'value'}, 'Input record')
            for field, item in record.items():
                string(item, 'Record ' + field, empty=field != 'id')
            need(record['id'] not in seen, 'Duplicate input record id')
            seen.add(record['id'])
    if mechanism == 'B':
        integer(value['input']['checkpoint'], 'Checkpoint', maximum=len(value['input']['records']))


def worlds(value):
    sequence(value, 'Worlds')
    need(len(value) == 6, 'Exactly six histories required')
    result = {}
    for world in value:
        keys(world, {'world_id', 'mechanism', 'operations', 'versions', 'training_cases', 'probes'}, 'Engineered world')
        string(world['world_id'], 'World id')
        need(world['world_id'] not in result and world['mechanism'] in ('A', 'B'), 'World identity/mechanism differs')
        ops = world['operations']
        strings(ops, 'Opaque operation ids', distinct=True)
        need(len(ops) == 3 and all(re.fullmatch('op-[a-f0-9]{8,32}', op) for op in ops), 'Three opaque operations required')
        keys(world['versions'], {'v1', 'v2'}, 'World versions')
        effects = {'literal', 'trim', 'decimal'} if world['mechanism'] == 'A' else {'resume_after_checkpoint', 'replay_skip_existing_key', 'replay_upsert_by_key'}
        for mapping in world['versions'].values():
            keys(mapping, ops, 'Version mapping')
            need(set(mapping.values()) == effects, 'Effect permutation differs')
        before = [world['versions']['v1'][op] for op in ops]
        after = [world['versions']['v2'][op] for op in ops]
        need(after in [before[1:] + before[:1], before[-1:] + before[:-1]], 'Version change must cyclically rotate effects')
        sequence(world['training_cases'], 'Training cases')
        need(len(world['training_cases']) == 3, 'Exactly three training cases')
        keys(world['probes'], PHASES, 'Probes')
        cases = world['training_cases'] + list(world['probes'].values())
        for item in cases:
            case(item, world['mechanism'])
        need(len({item['case_id'] for item in cases}) == 5, 'Distinct case ids required')
        need(all(c['version'] == 'v1' for c in world['training_cases']), 'Teacher version differs')
        same, changed = (world['probes'][p] for p in PHASES)
        need(same['version'] == 'v1' and changed['version'] == 'v2' and same['input'] == changed['input'] and same['contract'] == changed['contract'], 'Matched phases must keep input/contract')
        contracts = [c['contract']['kind'] for c in world['training_cases']]
        need(set(contracts) == effects if world['mechanism'] == 'A' else contracts.count('preserve') == 2 and contracts.count('refresh') == 1, 'Training coverage differs')
        result[world['world_id']] = world
    need(Counter(w['mechanism'] for w in result.values()) == {'A': 3, 'B': 3}, 'Three histories per mechanism required')
    return result


def recalculate(rows):
    result = []
    for phase in PHASES:
        for arm in ARMS:
            for mechanism in ('all', 'A', 'B'):
                group = [r for r in rows if r['phase'] == phase and r['arm'] == arm and (mechanism == 'all' or r['mechanism'] == mechanism)]
                result.append({'phase': phase, 'arm': arm, 'mechanism': mechanism, 'n': len(group),
                    'accepted': sum(r['accepted'] for r in group), 'abstentions': sum(r['abstained'] for r in group),
                    'state_valid': sum(r['state_valid'] is True for r in group),
                    'operation_completed': sum(r['process_completed'] is True for r in group),
                    'operation_failures': sum(r['process_completed'] is False for r in group),
                    'worker_errors': sum(r['worker_exit_code'] not in (None, 0) for r in group),
                    'old_only_choices': sum(r['old_only_choice'] for r in group),
                    'provisional_old_only': sum(r['provisional_old_only'] for r in group),
                    'changed_after_feedback': sum(r['operation_changed_after_feedback'] for r in group),
                    'citation_none': sum(r['citation_status'] == 'none' for r in group),
                    'citation_inaccurate': sum(r['citation_status'] == 'inaccurate_or_unavailable' for r in group),
                    'exact_judgment_citations': sum(r['exact_judgment_citations'] for r in group),
                    'io': {key: sum(r['io'][key] for r in group) for key in IO_FIELDS}})
    return result


def matched_pairs(rows, world_map):
    result = []
    for phase in PHASES:
        for world in world_map:
            group = {r['arm']: r for r in rows if r['phase'] == phase and r['world_id'] == world}
            j, raw = group['raw_plus_judgment'], group['raw_only']
            result.append({'phase': phase, 'world_id': world, 'mechanism': world_map[world]['mechanism'],
                'raw_only_accepted': raw['accepted'], 'judgment_accepted': j['accepted'],
                'accepted_difference': int(j['accepted']) - int(raw['accepted']),
                'diagnostic_call_difference': j['io']['diagnostic_calls'] - raw['io']['diagnostic_calls'],
                'additional_raw_byte_difference': j['io']['additional_raw_bytes'] - raw['io']['additional_raw_bytes'],
                'total_packet_byte_difference': j['io']['total_transferred_packet_bytes'] - raw['io']['total_transferred_packet_bytes']})
    return result


def acceptable_operations(world, phase):
    """Recalculate the disclosed acceptable recipes, without any execution."""
    probe = world['probes'][phase]
    rows = probe['input']['records']
    def normalize(key, kind):
        if kind == 'trim':
            return key.strip()
        if kind == 'decimal' and re.fullmatch('[+-]?[0-9]+', key):
            return str(int(key, 10))
        return key
    def partition(kind):
        groups = {}
        for row in rows:
            groups.setdefault(normalize(row['key'], kind), set()).add(row['id'])
        return {frozenset(members) for members in groups.values()}
    result = set()
    for op, effect in world['versions'][probe['version']].items():
        if world['mechanism'] == 'A':
            accepted = partition(effect) == partition(probe['contract']['kind'])
        else:
            initial = {r['id']: r['value'] for r in probe['input']['initial_store']}
            incoming = {r['id']: r['value'] for r in rows}
            expected = incoming | initial if probe['contract']['kind'] == 'preserve' else initial | incoming
            completed = True
            if effect == 'resume_after_checkpoint':
                suffix = rows[probe['input']['checkpoint']:]
                completed = not any(r['id'] in initial for r in suffix)
                actual = initial | {r['id']: r['value'] for r in suffix} if completed else initial
            elif effect == 'replay_skip_existing_key':
                actual = incoming | initial
            else:
                actual = initial | incoming
            accepted = completed and actual == expected
        if accepted:
            result.add(op)
    return result


def validate_summary(d):
    keys(d, TOP_FIELDS, 'Public export')
    need(d['schema'] == SCHEMA and d['date'] == '2026-11-03', 'Dated public schema differs')
    string(d['analyzed_at_utc'], 'Analysis time')
    need(datetime.fromisoformat(d['analyzed_at_utc'].replace('Z', '+00:00')).utcoffset() is not None, 'Analysis time requires timezone')
    for field, expected in {'histories': 6, 'mechanisms': 2, 'teacher_contexts': 6, 'probe_contexts': 36}.items():
        need(type(d[field]) is int and d[field] == expected, 'Frozen denominator differs: ' + field)
    for field in ('protocol_sha256', 'preregistration_sha256'):
        digest(d[field], field)
    keys(d['provider_metadata'], {'provider', 'model', 'settings', 'tokens', 'compute'}, 'Provider metadata')
    need(all(v is None for v in d['provider_metadata'].values()), 'Unverified provider metadata must remain null')
    keys(d['protection'], PROTECTION, 'Protection')
    need(d['protection'] == PROTECTION and all(type(v) is bool for v in d['protection'].values()), 'Public/shared-host boundaries differ')
    keys(d['audit'], {'status', 'scope', 'report_sha256'}, 'Independent audit')
    need(d['audit']['status'] == 'approved', 'Independent audit approval required')
    string(d['audit']['scope'], 'Audit scope')
    digest(d['audit']['report_sha256'], 'Audit report')
    string(d['boundary'], 'Boundary')
    strings(d['boundaries'], 'Boundaries')
    need(bool(d['boundaries']) and type(d['hashes']) is dict and bool(d['hashes']), 'Boundaries/hashes required')
    for name, value in d['hashes'].items():
        need(re.fullmatch('[A-Za-z][A-Za-z0-9_]*', name) is not None, 'Safe digest label required')
        digest(value, name)
    world_map = worlds(d['worlds'])
    sources, source_ids = {}, set()
    sequence(d['source_messages'], 'Sources')
    for source in d['source_messages']:
        keys(source, {'id', 'world_id', 'source_kind', 'text', 'text_sha256'}, 'Public source')
        string(source['id'], 'Source id')
        string(source['text'], 'Source text')
        digest(source['text_sha256'], 'Source text digest')
        identity = source['source_kind'], source['id']
        need(source['world_id'] in world_map and source['source_kind'] in SOURCE_KINDS and source['id'] not in source_ids, 'Source world/type/id differs')
        need(sha256(source['text'].encode('utf-8')).hexdigest() == source['text_sha256'], 'Source text SHA256 mismatch')
        if source['source_kind'] == 'original':
            need(source['id'] == source['text_sha256'], 'Original source id is exact stdout-byte digest')
        sources[identity] = source
        source_ids.add(source['id'])
    sequence(d['teacher_judgments'], 'Teacher judgments')
    need(len(d['teacher_judgments']) == 6, 'Six teacher judgments required')
    teachers = {}
    for teacher in d['teacher_judgments']:
        keys(teacher, {'world_id', 'source_id', 'text', 'native_status', 'native_receipt'}, 'Teacher judgment')
        need(teacher['world_id'] in world_map and teacher['world_id'] not in teachers, 'One teacher judgment per history required')
        string(teacher['source_id'], 'Judgment source id')
        string(teacher['text'], 'Judgment text')
        need(teacher['native_status'] in ('retained', 'deferred'), 'Native status must pass through retained/deferred')
        receipt = teacher['native_receipt']
        keys(receipt, {'candidate_id', 'source_ids', 'candidate_record_sha256', 'capture_manifest_sha256', 'review_manifest_sha256', 'read_manifest_sha256'}, 'Native receipt')
        string(receipt['candidate_id'], 'Native candidate id')
        strings(receipt['source_ids'], 'Native original sources', distinct=True)
        originals = {s['id'] for s in sources.values() if s['world_id'] == teacher['world_id'] and s['source_kind'] == 'original'}
        need(len(originals) == 6 and set(receipt['source_ids']) == originals, 'Native judgment must bind all six originals')
        for field in ('candidate_record_sha256', 'capture_manifest_sha256', 'review_manifest_sha256', 'read_manifest_sha256'):
            digest(receipt[field], field)
        source = sources.get(('judgment', teacher['source_id']))
        need(source is not None and source['world_id'] == teacher['world_id'] and source['text'] == teacher['text'], 'Teacher/source text binding differs')
        teachers[teacher['world_id']] = teacher
    sequence(d['teacher_rounds'], 'Teacher rounds')
    need(len(d['teacher_rounds']) == 12, 'All twelve teacher rounds required')
    round_ids = set()
    for item in d['teacher_rounds']:
        keys(item, {'world_id', 'round', 'allocated', 'accepted'}, 'Teacher round')
        identity = item['world_id'], item['round']
        need(item['world_id'] in world_map and item['round'] in (1, 2) and identity not in round_ids, 'Teacher round coverage differs')
        need(type(item['allocated']) is int and item['allocated'] == 3, 'Three training calls per teacher round')
        integer(item['accepted'], 'Training accepted', maximum=3)
        round_ids.add(identity)
    sequence(d['rows'], 'Probe rows')
    need(len(d['rows']) == 36, 'All 36 probes required')
    identities, assignments = set(), set()
    for row in d['rows']:
        validate_row(row, world_map, sources, teachers)
        identity = row['world_id'], row['phase'], row['arm']
        need(identity not in identities and row['assignment_id'] not in assignments, 'Duplicate world/phase/arm or assignment')
        identities.add(identity)
        assignments.add(row['assignment_id'])
    for world_id in world_map:
        catalogs = [r['task']['original_sources'] for r in d['rows'] if r['world_id'] == world_id]
        need(all(catalog == catalogs[0] for catalog in catalogs), 'All arms/phases must preserve source catalog order and metadata')
    sequence(d['aggregates'], 'Aggregates')
    for item in d['aggregates']:
        keys(item, AGGREGATE_FIELDS, 'Aggregate')
        for key in AGGREGATE_FIELDS - {'phase', 'arm', 'mechanism', 'io'}:
            integer(item[key], 'Aggregate ' + key)
    need(sorted(d['aggregates'], key=canonical) == sorted(recalculate(d['rows']), key=canonical), 'All 18 aggregates must recalculate')
    sequence(d['matched_pairs'], 'Matched pairs')
    for item in d['matched_pairs']:
        keys(item, PAIR_FIELDS, 'Matched pair')
        for key in ('raw_only_accepted', 'judgment_accepted'):
            boolean(item[key], key)
        for key in PAIR_FIELDS - {'phase', 'world_id', 'mechanism', 'raw_only_accepted', 'judgment_accepted'}:
            integer(item[key], key, minimum=-10**18)
    pairs = matched_pairs(d['rows'], world_map)
    need(sorted(d['matched_pairs'], key=canonical) == sorted(pairs, key=canonical), 'All twelve matched pairs must recalculate')
    integer(d['primary_paired_accepted_difference'], 'Primary difference', minimum=-6, maximum=6)
    need(d['primary_paired_accepted_difference'] == sum(p['accepted_difference'] for p in pairs if p['phase'] == 'same_version'), 'Primary difference must recalculate')
    keys(d['process_counts'], {'training_workers', 'diagnostic_workers', 'target_workers', 'native_capture_review_read_workers'}, 'Process counts')
    expected = {'training_workers': 36, 'diagnostic_workers': sum(r['io']['diagnostic_calls'] for r in d['rows']), 'target_workers': sum(not r['abstained'] for r in d['rows']), 'native_capture_review_read_workers': 18}
    need(d['process_counts'] == expected and all(type(v) is int for v in d['process_counts'].values()), 'Process counts must recalculate')
    need(re.search(r'(?:/(?:Users|home)/|file://|[A-Za-z]:\\\\)', canonical(d)) is None, 'Private local paths are not public evidence')
    return d


def validate_row(row, world_map, sources, teachers):
    keys(row, ROW_FIELDS, 'Probe row')
    need(row['world_id'] in world_map and row['phase'] in PHASES and row['arm'] in ARMS, 'Unknown world/phase/arm')
    world = world_map[row['world_id']]
    need(row['mechanism'] == world['mechanism'], 'Mechanism binding differs')
    need(type(row['assignment_id']) is str and re.fullmatch('p-[0-9a-f]{16}', row['assignment_id']) is not None, 'Opaque assignment id required')
    policy(row['policy'], world['operations'])
    final(row['final'], world['operations'])
    for field in ('accepted', 'abstained', 'old_only_choice', 'provisional_old_only', 'operation_changed_after_feedback'):
        boolean(row[field], field)
    for field in ('state_valid', 'process_completed'):
        need(row[field] is None or type(row[field]) is bool, field + ': nullable boolean required')
    for field in ('old_version_acceptable', 'current_acceptable'):
        strings(row[field], field, distinct=True)
        need(set(row[field]) <= set(world['operations']), 'Acceptable operation outside world')
    need(set(row['old_version_acceptable']) == acceptable_operations(world, 'same_version') and set(row['current_acceptable']) == acceptable_operations(world, row['phase']), 'Acceptable operations must recalculate from disclosed world')
    stale_only = set(row['old_version_acceptable']) - set(row['current_acceptable'])
    need(row['abstained'] == (row['final']['decision'] == 'abstain'), 'Abstention must recalculate')
    need(row['old_only_choice'] == (not row['abstained'] and row['final']['operation'] in stale_only), 'Final stale-only choice must recalculate')
    need(row['provisional_old_only'] == (row['policy']['provisional_operation'] in stale_only), 'Provisional stale-only choice must recalculate')
    need(row['operation_changed_after_feedback'] == (row['policy']['provisional_operation'] is not None and row['policy']['provisional_operation'] != row['final']['operation']), 'Changed-choice flag must recalculate')
    if row['worker_exit_code'] is not None:
        integer(row['worker_exit_code'], 'Worker exit', minimum=-255, maximum=255)
    if row['operation_status'] is not None:
        string(row['operation_status'], 'Operation status')
    for field in ('task_sha256', 'policy_sha256', 'feedback_sha256', 'final_sha256', 'outcome_sha256'):
        digest(row[field], field)
    for stem in ('policy', 'final'):
        string(row[stem + '_raw_text'], stem + ' exact raw text')
        need(parse_json(row[stem + '_raw_text']) == row[stem], 'Saved actor JSON text/object mismatch')
        need(sha256(row[stem + '_raw_text'].encode('utf-8')).hexdigest() == row[stem + '_sha256'], 'Saved actor raw UTF8 SHA256 mismatch')
    for field in ('target_manifest_sha256', 'target_artifact_sha256'):
        if row[field] is not None:
            digest(row[field], field)
    if row['abstained']:
        need(not row['accepted'] and all(row[f] is None for f in ('state_valid', 'process_completed', 'worker_exit_code', 'operation_status', 'target_manifest_sha256', 'target_artifact_sha256', 'target_validation')), 'Abstention cannot create target outcomes')
    elif row['target_validation'] is not None:
        validation = row['target_validation']
        keys(validation, {'accepted', 'state_valid', 'process_completed', 'reasons', 'validation_basis', 'artifact_sha256'}, 'Target validation')
        for field in ('accepted', 'state_valid', 'process_completed'):
            boolean(validation[field], field)
            need(validation[field] == row[field], 'Target validation flag differs')
        strings(validation['reasons'], 'Validation reasons')
        need(validation['validation_basis'] == 'independent_requested_contract_and_actual_artifact', 'Target validation basis differs')
        need(validation['artifact_sha256'] == row['target_artifact_sha256'], 'Artifact hash binding differs')
        need(row['accepted'] == (row['state_valid'] and row['process_completed']), 'Acceptance requires state validity and completion')
    else:
        need(not row['accepted'] and row['state_valid'] is None and row['process_completed'] is None and row['target_artifact_sha256'] is None, 'Unavailable actual evaluation must remain unavailable')
    keys(row['io'], IO_FIELDS, 'I/O accounting')
    for key, count in row['io'].items():
        integer(count, 'I/O ' + key)
    sequence(row['available_sources'], 'Available sources')
    available = set()
    for item in row['available_sources']:
        identity = source_key(item, 'Available source')
        need(identity in sources and sources[identity]['world_id'] == row['world_id'] and identity not in available, 'Available source binding differs')
        available.add(identity)
    originals = {s['id'] for s in sources.values() if s['world_id'] == row['world_id'] and s['source_kind'] == 'original'}
    need(len(originals) == 6 and set(row['policy']['original_source_ids']) <= originals, 'Six original catalog sources per history required')
    expected_originals = originals if row['arm'] == 'all_raw_upfront' else set(row['policy']['original_source_ids'])
    need({identity[1] for identity in available if identity[0] == 'original'} == expected_originals, 'Delivered original availability differs')
    teacher = teachers[row['world_id']]
    need((('judgment', teacher['source_id']) in available) == (row['arm'] == 'raw_plus_judgment'), 'Judgment availability must match treatment, including deferred')
    validate_packets(row, world, sources, available, teacher)
    validate_quotes(row, sources, available)


def validate_packets(row, world, sources, available, teacher):
    task, feedback = row['task'], row['feedback']
    keys(task, TASK_FIELDS, 'Actual TASK')
    keys(feedback, FEEDBACK_FIELDS, 'Actual FEEDBACK')
    need(task['assignment_id'] == row['assignment_id'] == feedback['assignment_id'], 'Packet assignment differs')
    need(feedback['schema'] == 'judgment-transfer-policy-feedback.v1', 'Feedback schema differs')
    need(task['schema'] == 'judgment-transfer-probe-task.v1', 'TASK schema differs')
    string(task['instruction'], 'TASK instruction')
    for name, expected in [('policy_schema', POLICY_SCHEMA), ('final_schema', FINAL_SCHEMA)]:
        keys(task[name], expected, 'TASK ' + name)
        need(task[name] == expected, 'TASK ' + name + ' differs from collector schema')
    expected_schemas = {'records': {'id': 'unique string', **({'key': 'string'} if world['mechanism'] == 'A' else {}), 'value': 'string'},
        'output': 'JSON groups [{key:string,members:[record id]}] plus intact original records' if world['mechanism'] == 'A' else 'SQLite records(id TEXT PRIMARY KEY,value TEXT NOT NULL) and exact JSON export',
        'checkpoint': None if world['mechanism'] == 'A' else 'zero-based input-prefix length'}
    keys(task['schemas'], expected_schemas, 'TASK schemas')
    keys(task['schemas']['records'], expected_schemas['records'], 'TASK record schema')
    need(task['schemas'] == expected_schemas, 'TASK schemas differ from mechanism-specific collector schema')
    need(type(task['original_source_read_limit']) is int and task['original_source_read_limit'] == 6 and type(task['current_diagnostic_call_limit']) is int and task['current_diagnostic_call_limit'] == 1, 'Evidence rights differ')
    probe = world['probes'][row['phase']]
    need(task['current_version'] == probe['version'], 'TASK current version differs')
    keys(task['task'], {'case_id', 'contract_text', 'current_version', 'input'}, 'Current task')
    need(task['task'] == {'case_id': probe['case_id'], 'contract_text': probe['contract']['text'], 'current_version': probe['version'], 'input': probe['input']}, 'Current input/contract binding differs')
    expected_training = [{'case_id': c['case_id'], 'contract_text': c['contract']['text'], 'current_version': c['version'], 'input': c['input']} for c in world['training_cases']]
    need(task['operations'] == world['operations'] and task['training_cases'] == expected_training, 'Operation/public-training-case bindings differ')
    sequence(task['original_sources'], 'Original source catalog')
    catalog = []
    catalog_coverage = set()
    for item in task['original_sources']:
        keys(item, {'source_id', 'content_sha256', 'case_id', 'round', 'operation'}, 'Original catalog entry')
        digest(item['source_id'], 'Catalog source id')
        digest(item['content_sha256'], 'Catalog content digest')
        integer(item['round'], 'Catalog training round', minimum=1, maximum=2)
        string(item['case_id'], 'Catalog case id')
        need(item['case_id'] in {c['case_id'] for c in world['training_cases']} and item['operation'] in world['operations'], 'Catalog training case/operation differs')
        catalog_coverage.add((item['round'], item['case_id']))
        catalog.append(item['source_id'])
        need(('original', item['source_id']) in sources and sources['original', item['source_id']]['world_id'] == row['world_id'], 'Original catalog source differs')
        need(item['content_sha256'] == item['source_id'], 'Original catalog content hash differs')
    need(len(catalog) == len(set(catalog)) == 6, 'Complete six-original catalog required')
    need(catalog_coverage == {(r, c['case_id']) for r in (1, 2) for c in world['training_cases']}, 'Catalog must cover three training cases in both rounds')
    initial, extra = task['initial_originals'], feedback['originals']
    sequence(initial, 'Initial originals')
    sequence(extra, 'Feedback originals')
    def delivered(items, kind):
        out = []
        for item in items:
            keys(item, {'source_id', 'source_kind', 'text'}, 'Delivered ' + kind)
            string(item['source_id'], 'Delivered source id')
            string(item['text'], 'Delivered text')
            need(item['source_kind'] == kind, 'Delivered source kind differs')
            source = sources.get((kind, item['source_id']))
            need(source is not None and source['world_id'] == row['world_id'] and source['text'] == item['text'], 'Delivered source corpus binding differs')
            out.append(item)
        return out
    delivered(initial + extra, 'original')
    need([s['source_id'] for s in initial] == (catalog if row['arm'] == 'all_raw_upfront' else []), 'Initial original order/exposure differs')
    need([s['source_id'] for s in extra] == row['policy']['original_source_ids'], 'Committed original read order differs')
    expected_available = {('original', s['source_id']) for s in initial + extra}
    task_text = canonical(task) + '\n'
    task_source = sources.get(('task', row['assignment_id']))
    need(task_source is not None and task_source['text'] == task_text, 'Disclosed task source must equal exact canonical TASK with newline')
    expected_available.add(('task', row['assignment_id']))
    summary = task['initial_judgment']
    if row['arm'] == 'raw_plus_judgment':
        keys(summary, {'source_id', 'source_kind', 'text', 'native_status', 'provenance_sha256'}, 'Initial judgment')
        digest(summary['provenance_sha256'], 'Judgment reread provenance digest')
        need(summary['source_kind'] == 'judgment' and summary['source_id'] == teacher['source_id'] == 'judgment-' + summary['provenance_sha256'] and summary['text'] == teacher['text'] and summary['native_status'] == teacher['native_status'], 'Initial judgment text/status/provenance differs')
        expected_available.add(('judgment', teacher['source_id']))
    else:
        need(summary is None, 'Other arms cannot expose initial judgment')
    diagnostic = feedback['diagnostic']
    reference = feedback['diagnostic_manifest']
    if row['policy']['calibration']:
        keys(reference, {'manifest_path', 'manifest_sha256', 'exit_code'}, 'Diagnostic manifest reference')
        need(reference['manifest_path'] == 'assignments/' + row['assignment_id'] + '/diagnostic/manifest.json', 'Diagnostic manifest must identify the allocated saved call')
        digest(reference['manifest_sha256'], 'Diagnostic manifest digest')
        integer(reference['exit_code'], 'Diagnostic worker exit', minimum=-255, maximum=255)
    else:
        need(reference is None and diagnostic is None, 'Unrequested diagnostic cannot have a manifest or output')
    if diagnostic is not None:
        delivered([diagnostic], 'current_diagnostic')
        need(row['policy']['calibration'], 'Unrequested diagnostic exposure')
        need(diagnostic['source_id'] == 'diagnostic-' + sha256(canonical(diagnostic['text']).encode('utf-8')).hexdigest(), 'Diagnostic source id must match collector text digest')
        expected_available.add(('current_diagnostic', diagnostic['source_id']))
    sequence(feedback['status_notices'], 'Status notices')
    delivered(feedback['status_notices'], 'status_notice')
    expected_notices = []
    if row['policy']['calibration'] and (diagnostic is None or reference['exit_code'] != 0):
        expected_notices = [{'source_kind': 'status_notice', 'source_id': 'status-' + row['assignment_id'], 'text': DIAGNOSTIC_MISSING_NOTICE if diagnostic is None else DIAGNOSTIC_FAILURE_NOTICE}]
    need(feedback['status_notices'] == expected_notices, 'Diagnostic failure/missing notices must match actual saved-call status')
    expected_available.update(('status_notice', item['source_id']) for item in feedback['status_notices'])
    need(available == expected_available, 'Available source set must derive from actual TASK/FEEDBACK delivery')
    need(feedback['policy_sha256'] == row['policy_sha256'], 'Feedback POLICY hash differs')
    task_raw, feedback_raw = task_text, canonical(feedback) + '\n'
    need(sha256(task_raw.encode('utf-8')).hexdigest() == row['task_sha256'] and sha256(feedback_raw.encode('utf-8')).hexdigest() == row['feedback_sha256'], 'Canonical TASK/FEEDBACK SHA256 mismatch')
    initial_texts, extra_texts = [s['text'] for s in initial], [s['text'] for s in extra]
    unique = {s['source_id']: s['text'] for s in initial + extra}
    summary_text = summary['text'] if summary else ''
    diagnostic_text = diagnostic['text'] if diagnostic else ''
    def byte_count(text):
        return len(text.encode('utf-8'))
    expected = {'initial_original_count': len(initial), 'requested_original_reads': len(extra),
        'duplicate_initial_reads': sum(s['source_id'] in {x['source_id'] for x in initial} for s in extra),
        'diagnostic_calls': int(row['policy']['calibration']),
        'initial_packet_chars': len(task_raw), 'initial_packet_bytes': byte_count(task_raw),
        'initial_summary_chars': len(summary_text), 'initial_summary_bytes': byte_count(summary_text),
        'initial_raw_chars': sum(map(len, initial_texts)), 'initial_raw_bytes': sum(map(byte_count, initial_texts)),
        'additional_raw_chars': sum(map(len, extra_texts)), 'additional_raw_bytes': sum(map(byte_count, extra_texts)),
        'calibration_chars': len(diagnostic_text), 'calibration_bytes': byte_count(diagnostic_text),
        'unique_original_count': len(unique), 'unique_original_chars': sum(map(len, unique.values())),
        'unique_original_bytes': sum(map(byte_count, unique.values())),
        'duplicate_raw_bytes': sum(map(byte_count, initial_texts + extra_texts)) - sum(map(byte_count, unique.values())),
        'feedback_packet_chars': len(feedback_raw), 'feedback_packet_bytes': byte_count(feedback_raw),
        'total_transferred_packet_bytes': byte_count(task_raw) + byte_count(feedback_raw)}
    need(row['io'] == feedback['io_accounting'] == expected, 'All disclosed source/packet I/O must recalculate')


def validate_quotes(row, sources, available):
    expected = []
    for index, item in enumerate(row['final']['evidence']):
        identity = item['source_kind'], item['source_id']
        text = sources[identity]['text'] if identity in available else None
        expected.append({'evidence_index': index, 'source_kind': item['source_kind'],
            'source_id': item['source_id'], 'source_available': text is not None,
            'quote_exact': text is not None and bool(item['quote']) and item['quote'] in text,
            'available_source_text_sha256': sha256(text.encode('utf-8')).hexdigest() if text is not None else None})
    sequence(row['quote_checks'], 'Typed quote checks')
    for check in row['quote_checks']:
        keys(check, {'evidence_index', 'source_kind', 'source_id', 'source_available', 'quote_exact', 'available_source_text_sha256'}, 'Typed quote check')
        integer(check['evidence_index'], 'Evidence index')
        boolean(check['source_available'], 'Source available')
        boolean(check['quote_exact'], 'Quote exact')
    need(row['quote_checks'] == expected, 'Typed quote checks must recalculate from available source corpus')
    citation_status = 'none' if not expected else 'exact_available_quotes' if all(c['quote_exact'] for c in expected) else 'inaccurate_or_unavailable'
    need(row['citation_status'] == citation_status, 'Citation status must recalculate; none stays none')
    counts = {
        'cited_original_source_count': len({e['source_id'] for e in row['final']['evidence'] if e['source_kind'] == 'original'}),
        'exact_cited_original_source_count': len({c['source_id'] for c in expected if c['source_kind'] == 'original' and c['quote_exact']}),
        'exact_judgment_citations': sum(c['source_kind'] == 'judgment' and c['quote_exact'] for c in expected)}
    for field, count in counts.items():
        integer(row[field], field)
        need(row[field] == count, field + ': citation count mismatch')


def verify_bundle(folder):
    """Check only this allowlisted public package; never follow a symlink."""
    folder = Path(folder)
    need(not folder.is_symlink() and folder.is_dir(), 'Regular public package directory required')
    manifest_path = folder / 'MANIFEST.json'
    need(not manifest_path.is_symlink() and manifest_path.is_file(), 'Regular package manifest required')
    manifest = parse_json(manifest_path.read_bytes())
    keys(manifest, {'schema', 'replay', 'files'}, 'Package manifest')
    need(manifest['schema'] == 'judgment-transfer-public-package.v1', 'Package schema differs')
    boolean(manifest['replay'], 'Package replay flag')
    names = {'evidence.json', 'verify.py', 'README.md'}
    if manifest['replay']:
        names |= {'worlds.json', 'plans.json', 'common.py', 'world_engine.py', 'replay.py'}
    keys(manifest['files'], names, 'Package inventory')
    need({p.name for p in folder.iterdir()} == names | {'MANIFEST.json'}, 'Unexpected public package files')
    for name, record in manifest['files'].items():
        keys(record, {'bytes', 'sha256'}, 'Package file record')
        integer(record['bytes'], 'Package file bytes')
        digest(record['sha256'], 'Package file digest')
        path = folder / name
        need(not path.is_symlink() and path.is_file(), 'Regular public package files required')
        raw = path.read_bytes()
        need(len(raw) == record['bytes'] and sha256(raw).hexdigest() == record['sha256'], 'Package file hash/length mismatch: ' + name)
    d = validate_summary(parse_json((folder / 'evidence.json').read_bytes()))
    if manifest['replay']:
        for name, label in [('common.py', 'common_py_sha256'), ('world_engine.py', 'world_engine_py_sha256')]:
            need(manifest['files'][name]['sha256'] == d['hashes'].get(label), 'Own-authored replay code pin differs')
        expected_worlds = {'schema': 'judgment-transfer-worlds.v1', 'worlds': d['worlds']}
        expected_plans = [{'assignment_id': r['assignment_id'], 'world_id': r['world_id'], 'phase': r['phase'], 'final': r['final'], 'target_artifact_sha256': r['target_artifact_sha256']} for r in d['rows']]
        need(parse_json((folder / 'worlds.json').read_bytes()) == expected_worlds, 'Saved replay worlds differ')
        need(parse_json((folder / 'plans.json').read_bytes()) == expected_plans, 'Saved replay plans differ')
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('evidence', type=Path)
    args = parser.parse_args(argv)
    need(not args.evidence.is_symlink() and args.evidence.is_file(), 'Regular public JSON required')
    d = validate_summary(parse_json(args.evidence.read_bytes()))
    if (args.evidence.parent / 'MANIFEST.json').exists():
        verify_bundle(args.evidence.parent)
    print('Verified 36 saved choices, 18 aggregates, 12 matched pairs and disclosed source hashes/typed quotes.')
    print('Primary same-version paired accepted difference:', d['primary_paired_accepted_difference'])


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, UnicodeError) as error:
        raise SystemExit(str(error)) from error

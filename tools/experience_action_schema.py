"""Public saved-evidence validation only; Python standard library, no native calls.

This file is also the downloadable verifier. It checks the disclosed schema,
hashes, quotation containment and arithmetic. It cannot repeat private native
operations, regenerate AI choices, or independently establish exported claims.
"""
import argparse
from collections import Counter
from datetime import datetime
from hashlib import sha256
import json
import math
from pathlib import Path
import re

SCHEMA = 'experience-action-loop-public.v1'
ARMS = ('full', 'hops0', 'no_writeback', 'no_history')
PHASES = ('R', 'L', 'N')
WORLDS = ('W01', 'W02', 'W03')
TOP_FIELDS = {'schema', 'date', 'analyzed_at_utc', 'protocol_sha256',
    'independent_engineered_histories', 'artifact_format_replications_of_mechanisms',
    'actual_teacher_contexts', 'actual_probe_contexts', 'semantic_reviewer_contexts',
    'engineering_tests', 'rows', 'aggregates', 'unique_original_observations',
    'unique_operation_counts', 'provider_metadata', 'boundary', 'teachers',
    'source_messages', 'hashes', 'audit', 'boundaries', 'protection'}
ROW_FIELDS = {'assignment_id', 'world', 'phase', 'arm', 'profile', 'request', 'action',
    'exit_code', 'artifact_accepted', 'artifact_validation', 'abstained',
    'query_requested', 'query_status', 'query_result_bytes',
    'query_result_canonical_chars', 'hits', 'new_judgment_returned',
    'has_indirect_return', 'exact_quote_checks', 'all_quotes_exact',
    'action_file_sha256', 'query_result_sha256', 'execution_result_sha256'}
AGGREGATE_FIELDS = {'phase', 'arm', 'n', 'artifact_accepted', 'builds',
    'abstentions', 'rejected_artifacts', 'operation_errors', 'queries',
    'indirect_return_queries', 'new_judgment_return_queries', 'all_quote_exact_rows',
    'query_result_bytes', 'query_result_canonical_chars'}
PROTECTION = {'public_export_only': True, 'private_vendor_source_excluded': True,
    'native_state_excluded': True, 'private_source_documents_excluded': True,
    'shared_host_instruction_allowlists': True, 'os_isolation': False}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False)


def parse_json(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate public JSON key: ' + key)
            result[key] = value
        return result
    def nonfinite(_):
        raise ValueError('Nonfinite public JSON number')
    return json.loads(raw.decode('utf-8'), object_pairs_hook=unique,
                      parse_constant=nonfinite)


def keys(value, expected, where):
    if type(value) is not dict or set(value) != set(expected):
        raise ValueError(where + ': exact public keys required')


def integer(value, where, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(where + ': integer out of range')


def string(value, where, empty=False):
    if type(value) is not str or (not empty and not value.strip()) or '\x00' in value:
        raise ValueError(where + ': nonempty public string required')


def digest(value, where):
    if type(value) is not str or re.fullmatch(r'[0-9a-f]{64}', value) is None:
        raise ValueError(where + ': lowercase SHA256 required')


def boolean(value, where):
    if type(value) is not bool:
        raise ValueError(where + ': boolean required')


def numeric(value, where):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError(where + ': finite nonnegative number required')


def sequence(value, where):
    if type(value) is not list:
        raise ValueError(where + ': list required')


def profile(value):
    if type(value) is not str or re.fullmatch(r'cfg-[0-9a-f]{12}', value) is None:
        raise ValueError('Opaque profile identifier required')


def strings(value, where):
    sequence(value, where)
    for item in value:
        string(item, where)


def action(value):
    keys(value, {'decision', 'recipe', 'prediction', 'reason', 'evidence'}, 'action')
    if value['decision'] not in ('build', 'abstain') or value['prediction'] not in ('accepted', 'rejected', 'unknown'):
        raise ValueError('Invalid action decision/prediction')
    if (value['decision'] == 'build' and value['recipe'] not in ('alpha', 'beta', 'gamma')) or (value['decision'] == 'abstain' and value['recipe'] is not None):
        raise ValueError('Recipe must match build/abstain decision')
    string(value['reason'], 'action reason'); sequence(value['evidence'], 'action evidence')
    for evidence in value['evidence']:
        keys(evidence, {'source_id', 'quote'}, 'action evidence')
        string(evidence['source_id'], 'evidence id'); string(evidence['quote'], 'quote')


def validation(value):
    if value is None:
        return
    keys(value, {'artifact_bytes', 'artifact_sha256', 'checks', 'errors', 'exit_code',
                 'expected_artifact_sha256', 'status'}, 'artifact validation')
    integer(value['artifact_bytes'], 'artifact bytes')
    integer(value['exit_code'], 'validation exit', -255)
    strings(value['checks'], 'validation checks'); strings(value['errors'], 'validation errors')
    if value['status'] not in ('accepted', 'rejected'):
        raise ValueError('Artifact status must be accepted/rejected')
    for field in ('artifact_sha256', 'expected_artifact_sha256'):
        if value[field] is not None:
            digest(value[field], field)
    if value['status'] == 'accepted' and (value['errors'] or value['exit_code'] != 0 or value['artifact_sha256'] is None or value['artifact_sha256'] != value['expected_artifact_sha256']):
        raise ValueError('Accepted artifact hash/errors/exit disagree')


def cue(value):
    if type(value) is not list or len(value) != 2:
        raise ValueError('A cue is exactly [channel, value]')
    for part in value:
        string(part, 'cue')


def hit(value):
    keys(value, {'episode_id', 'score', 'matched_cues', 'support',
                 'indirect_zero_direct_match', 'source_kind'}, 'hit')
    string(value['episode_id'], 'episode id'); numeric(value['score'], 'hit score')
    if value['source_kind'] not in ('tool_observation', 'actual_ai_judgment'):
        raise ValueError('Unknown hit source kind')
    sequence(value['matched_cues'], 'matched cues'); sequence(value['support'], 'support')
    for item in value['matched_cues']:
        cue(item)
    for support in value['support']:
        keys(support, {'cue', 'path', 'weight'}, 'support')
        cue(support['cue']); numeric(support['weight'], 'support weight')
        sequence(support['path'], 'graph path')
        for edge in support['path']:
            keys(edge, {'from', 'to', 'type', 'via'}, 'graph edge')
            for field in ('from', 'to', 'type'):
                string(edge[field], 'graph ' + field)
            keys(edge['via'], {'channel', 'state', 'subject', 'value'}, 'graph via')
            for part in edge['via'].values():
                string(part, 'graph via')
            if edge['via']['channel'] not in ('object', 'place', 'concept', 'relation') or edge['via']['state'] not in ('reported', 'mention') or edge['via']['subject'] != 'tool_work':
                raise ValueError('Graph via vocabulary differs from public protocol')
    boolean(value['indirect_zero_direct_match'], 'indirect return')
    if value['indirect_zero_direct_match'] != (not value['matched_cues'] and any(s['path'] for s in value['support'])):
        raise ValueError('Indirect flag must recalculate from actual support')


def source_aliases(messages):
    result = {}
    for message in messages:
        identity = message['id']
        prefix = 'tool:' if message['source_kind'] == 'tool_observation' else 'judgment:'
        base = identity[len(prefix):] if identity.startswith(prefix) else identity
        for alias in (base, prefix + base):
            if alias in result:
                raise ValueError('Duplicate/ambiguous public source alias')
            result[alias] = message['text']
    return result


def source_kind_aliases(messages):
    """Lookup aliases only: never rewrite the saved action or its source IDs."""
    result = {}
    for message in messages:
        prefix = 'tool:' if message['source_kind'] == 'tool_observation' else 'judgment:'
        base = message['id'][len(prefix):] if message['id'].startswith(prefix) else message['id']
        result.update({base: message['source_kind'], prefix + base: message['source_kind']})
    return result


def evidence_usage(d):
    """Disclosed source types and saved citations; return is not adoption."""
    kinds = source_kind_aliases(d['source_messages'])
    rows = d['rows']
    full = [r for r in rows if r['arm'] == 'full']
    counts = {'rows': len(rows),
        'eligible_original_source_true_rows': sum(r['all_quotes_exact'] for r in rows),
        'eligible_nonempty_rows': sum(bool(r['action']['evidence']) and r['all_quotes_exact'] for r in rows),
        'empty_evidence_rows': sum(not r['action']['evidence'] for r in rows),
        'out_of_type_notice_rows': sum(any(e['source_id'] == 'QUERY_RESULT.json' and not exact
            for e, exact in zip(r['action']['evidence'], r['exact_quote_checks'])) for r in rows),
        'other_source_contract_false_rows': sum(not r['all_quotes_exact'] and any(
            e['source_id'] != 'QUERY_RESULT.json' and not exact
            for e, exact in zip(r['action']['evidence'], r['exact_quote_checks'])) for r in rows),
        'eligible_tool_verbatim_quotes': 0, 'eligible_native_judgment_verbatim_quotes': 0,
        'native_judgment_citing_rows': 0, 'full_rows': len(full),
        'full_new_judgment_return_rows': sum(r['new_judgment_returned'] for r in full)}
    for row in rows:
        judgment_cited = False
        for evidence, exact in zip(row['action']['evidence'], row['exact_quote_checks']):
            if exact:
                kind = kinds.get(evidence['source_id'])
                if kind == 'tool_observation':
                    counts['eligible_tool_verbatim_quotes'] += 1
                elif kind == 'actual_ai_judgment':
                    counts['eligible_native_judgment_verbatim_quotes'] += 1
                    judgment_cited = True
        counts['native_judgment_citing_rows'] += judgment_cited
    return counts


def recalculate(rows):
    result = []
    for phase in PHASES:
        for arm in ARMS:
            group = [r for r in rows if (r['phase'], r['arm']) == (phase, arm)]
            result.append({'phase': phase, 'arm': arm, 'n': len(group),
                'artifact_accepted': sum(r['artifact_accepted'] for r in group),
                'builds': sum(r['action']['decision'] == 'build' for r in group),
                'abstentions': sum(r['abstained'] for r in group),
                'rejected_artifacts': sum(r['artifact_validation'] is not None and not r['artifact_accepted'] for r in group),
                'operation_errors': sum(r['exit_code'] not in (0, 2) for r in group),
                'queries': sum(r['query_requested'] for r in group),
                'indirect_return_queries': sum(r['has_indirect_return'] for r in group),
                'new_judgment_return_queries': sum(r['new_judgment_returned'] for r in group),
                'all_quote_exact_rows': sum(r['all_quotes_exact'] for r in group),
                'query_result_bytes': sum(r['query_result_bytes'] for r in group),
                'query_result_canonical_chars': sum(r['query_result_canonical_chars'] for r in group)})
    return result


def validate_summary(d):
    keys(d, TOP_FIELDS, 'public export')
    if d['schema'] != SCHEMA or d['date'] != '2026-10-30':
        raise ValueError('Only the dated experience-action public schema qualifies')
    string(d['analyzed_at_utc'], 'analysis UTC')
    try:
        datetime.fromisoformat(d['analyzed_at_utc'].replace('Z', '+00:00'))
    except ValueError as error:
        raise ValueError('Parseable analysis UTC required') from error
    for field, expected in {'independent_engineered_histories': 3,
            'artifact_format_replications_of_mechanisms': 1, 'actual_teacher_contexts': 6,
            'actual_probe_contexts': 36, 'semantic_reviewer_contexts': 3}.items():
        if type(d[field]) is not int or d[field] != expected:
            raise ValueError('Frozen context/history denominator differs: ' + field)
    digest(d['protocol_sha256'], 'protocol')
    keys(d['provider_metadata'], {'provider', 'model', 'settings', 'tokens', 'compute'}, 'provider metadata')
    if any(v is not None for v in d['provider_metadata'].values()):
        raise ValueError('Unverified provider/model/settings/token/compute must remain null')
    keys(d['engineering_tests'], {'tests', 'failures', 'errors', 'synthetic'}, 'engineering tests')
    if d['engineering_tests'] != {'tests': 21, 'failures': 0, 'errors': 0, 'synthetic': True} or type(d['engineering_tests']['synthetic']) is not bool or any(type(d['engineering_tests'][f]) is not int for f in ('tests', 'failures', 'errors')):
        raise ValueError('Keep 21 synthetic engineering checks separate from research')
    keys(d['protection'], PROTECTION, 'protection')
    if d['protection'] != PROTECTION or any(type(v) is not bool for v in d['protection'].values()):
        raise ValueError('Public-only/shared-host protection boundary differs')
    keys(d['audit'], {'status', 'scope', 'report_sha256'}, 'audit')
    if d['audit']['status'] != 'approved':
        raise ValueError('Independent applicability/artifact/protection audit approval required')
    string(d['audit']['scope'], 'audit scope'); digest(d['audit']['report_sha256'], 'audit report')
    string(d['boundary'], 'analysis boundary'); strings(d['boundaries'], 'boundaries')
    if not d['boundaries'] or type(d['hashes']) is not dict or not d['hashes']:
        raise ValueError('Explicit boundaries and integrity digests required')
    for name, value in d['hashes'].items():
        if re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', name) is None:
            raise ValueError('Safe integrity digest label required')
        digest(value, name)
    sequence(d['source_messages'], 'public sources')
    if len(d['source_messages']) != 21:
        raise ValueError('Retain exactly 21 deduplicated public source messages')
    source_ids = set()
    for source in d['source_messages']:
        keys(source, {'id', 'source_kind', 'text', 'text_sha256'}, 'public source')
        string(source['id'], 'source id'); string(source['text'], 'public source text')
        if source['id'] in source_ids or source['source_kind'] not in ('tool_observation', 'actual_ai_judgment'):
            raise ValueError('Public source identity/kind missing or duplicated')
        source_ids.add(source['id']); digest(source['text_sha256'], 'source text digest')
        if sha256(source['text'].encode('utf-8')).hexdigest() != source['text_sha256']:
            raise ValueError('Public source text hash differs')
    sources = source_aliases(d['source_messages'])
    source_kinds = source_kind_aliases(d['source_messages'])
    sequence(d['teachers'], 'teachers')
    if len(d['teachers']) != 6:
        raise ValueError('Retain all six teacher contexts')
    teacher_map = {}; candidates = set()
    for teacher in d['teachers']:
        keys(teacher, {'world', 'stage', 'component', 'profile', 'action', 'exit_code',
                      'artifact_validation', 'judgment', 'candidate_id'}, 'teacher')
        identity = (teacher['world'], teacher['stage'])
        if teacher['world'] not in WORLDS or teacher['stage'] not in ('legacy', 'current') or identity in teacher_map:
            raise ValueError('Teacher world/stage binding duplicated or invalid')
        string(teacher['component'], 'teacher component'); profile(teacher['profile'])
        action(teacher['action']); integer(teacher['exit_code'], 'teacher exit', -255)
        validation(teacher['artifact_validation'])
        judgment = teacher['judgment']
        keys(judgment, {'text', 'why_keep', 'review_action', 'review_note'}, 'teacher judgment')
        for field in ('text', 'why_keep', 'review_note'):
            string(judgment[field], 'judgment ' + field)
        if judgment['review_action'] not in ('retained', 'deferred'):
            raise ValueError('Teacher review action must be retained/deferred')
        if teacher['candidate_id'] is not None:
            string(teacher['candidate_id'], 'candidate id')
            if teacher['candidate_id'] in candidates:
                raise ValueError('Each teacher candidate identity must be unique')
            candidates.add(teacher['candidate_id'])
        if judgment['review_action'] == 'retained' and teacher['candidate_id'] is None:
            raise ValueError('Retained teacher requires candidate identity')
        if judgment['review_action'] == 'retained':
            alias = 'judgment:' + teacher['candidate_id']
            if source_kinds.get(alias) != 'actual_ai_judgment' or sources.get(alias) != judgment['text']:
                raise ValueError('Retained teacher judgment must bind to exact public source text')
        teacher_map[identity] = teacher
    if set(teacher_map) != {(w, s) for w in WORLDS for s in ('legacy', 'current')}:
        raise ValueError('Exactly one legacy/current teacher per world required')
    for world in WORLDS:
        if teacher_map[world, 'legacy']['profile'] == teacher_map[world, 'current']['profile']:
            raise ValueError('Changed and legacy conditions require distinct profiles')
    sequence(d['rows'], 'research rows')
    if len(d['rows']) != 36:
        raise ValueError('Retain all 36 fresh probe choices')
    seen = set(); assignments = set()
    for row in d['rows']:
        keys(row, ROW_FIELDS, 'research row'); identity = (row['world'], row['phase'], row['arm'])
        if row['world'] not in WORLDS or row['phase'] not in PHASES or row['arm'] not in ARMS or identity in seen:
            raise ValueError('Every world/phase/arm must occur exactly once')
        string(row['assignment_id'], 'assignment id')
        if row['assignment_id'] in assignments:
            raise ValueError('Duplicate assignment identity')
        seen.add(identity); assignments.add(row['assignment_id']); profile(row['profile'])
        known = {s: teacher_map[row['world'], s]['profile'] for s in ('legacy', 'current')}
        if (row['phase'] == 'R' and row['profile'] != known['current']) or (row['phase'] == 'L' and row['profile'] != known['legacy']) or (row['phase'] == 'N' and row['profile'] in known.values()):
            raise ValueError('Changed/legacy/unobserved profile binding differs')
        string(row['request'], 'probe request'); action(row['action']); validation(row['artifact_validation'])
        integer(row['exit_code'], 'operation exit', -255)
        for field in ('artifact_accepted', 'abstained', 'query_requested', 'new_judgment_returned', 'has_indirect_return', 'all_quotes_exact'):
            boolean(row[field], field)
        accepted = row['action']['decision'] == 'build' and row['artifact_validation'] is not None and row['artifact_validation']['status'] == 'accepted'
        if row['artifact_accepted'] != accepted or row['abstained'] != (row['action']['decision'] == 'abstain'):
            raise ValueError('Accepted/abstained flags must recalculate')
        if row['query_status'] not in ('available', 'unavailable', 'not_requested') or (row['query_status'] != 'not_requested') != row['query_requested']:
            raise ValueError('Requested query and status disagree')
        for field in ('query_result_bytes', 'query_result_canonical_chars'):
            integer(row[field], field)
        sequence(row['hits'], 'query hits')
        for item in row['hits']:
            hit(item)
            if source_kinds.get(item['episode_id']) != item['source_kind']:
                raise ValueError('Every returned hit must bind to a disclosed source of the same kind')
        if not row['query_requested'] and (row['hits'] or row['query_result_bytes'] or row['query_result_canonical_chars']):
            raise ValueError('Unrequested query has no return or cost')
        if row['arm'] == 'no_history' and (row['hits'] or row['query_status'] == 'available'):
            raise ValueError('No-history arm may receive an unavailable notice, but cannot return historical evidence')
        if row['arm'] == 'hops0' and any(s['path'] for h in row['hits'] for s in h['support']):
            raise ValueError('Hops-zero arm cannot contain traversed paths')
        candidate = teacher_map[row['world'], 'current']['candidate_id']
        retained = teacher_map[row['world'], 'current']['judgment']['review_action'] == 'retained'
        new_return = candidate is not None and retained and any(h['episode_id'] == 'judgment:' + candidate and h['source_kind'] == 'actual_ai_judgment' for h in row['hits'])
        if row['new_judgment_returned'] != new_return or row['has_indirect_return'] != any(h['indirect_zero_direct_match'] for h in row['hits']):
            raise ValueError('New-judgment and indirect return flags must recalculate')
        if row['arm'] in ('no_writeback', 'no_history') and new_return:
            raise ValueError('No-writeback/no-history cannot return new judgment')
        exact = [e['source_id'] in sources and e['quote'] in sources[e['source_id']] for e in row['action']['evidence']]
        if type(row['exact_quote_checks']) is not list or any(type(v) is not bool for v in row['exact_quote_checks']) or row['exact_quote_checks'] != exact or row['all_quotes_exact'] != all(exact):
            raise ValueError('Quotation checks must recalculate from public source text')
        for field in ('action_file_sha256', 'execution_result_sha256'):
            digest(row[field], field)
        if row['query_requested']:
            digest(row['query_result_sha256'], 'query result')
        elif row['query_result_sha256'] is not None:
            raise ValueError('Unrequested query has no result digest')
    for world in WORLDS:
        if len({r['profile'] for r in d['rows'] if r['world'] == world and r['phase'] == 'N'}) != 1:
            raise ValueError('All four N arms must use the same unobserved profile per world')
    expected = recalculate(d['rows']); sequence(d['aggregates'], 'aggregates')
    if len(d['aggregates']) != 12:
        raise ValueError('All twelve phase/arm aggregates required')
    for aggregate in d['aggregates']:
        keys(aggregate, AGGREGATE_FIELDS, 'aggregate')
        for field in AGGREGATE_FIELDS - {'phase', 'arm'}:
            integer(aggregate[field], 'aggregate ' + field)
    if sorted(d['aggregates'], key=lambda x: (x['phase'], x['arm'])) != sorted(expected, key=lambda x: (x['phase'], x['arm'])):
        raise ValueError('All public aggregate values must recalculate')
    integer(d['unique_original_observations'], 'unique original observations')
    if type(d['unique_operation_counts']) is not dict or not d['unique_operation_counts']:
        raise ValueError('Original operation count mapping required')
    for name, count in d['unique_operation_counts'].items():
        if re.fullmatch(r'[a-z][a-z0-9_]*', name) is None:
            raise ValueError('Safe public operation name required')
        integer(count, 'operation count')
    if sum(d['unique_operation_counts'].values()) != d['unique_original_observations']:
        raise ValueError('Unique observation counts must sum')
    # Sanitized public text must not contain private local paths or file URLs.
    if re.search(r'(?:/(?:Users|home)/|file://|[A-Za-z]:\\\\)', canonical(d)):
        raise ValueError('Private absolute local paths are not public evidence')
    return d


def verify_bundle(folder):
    """Check the downloadable package only, never a native research bundle."""
    names = {'README.md', 'evidence.json', 'verify.py', 'MANIFEST.json'}
    if {p.name for p in folder.iterdir()} != names or any(p.is_symlink() or not p.is_file() for p in folder.iterdir()):
        raise ValueError('Verifier package must have exactly four regular public files')
    manifest = parse_json((folder / 'MANIFEST.json').read_bytes())
    keys(manifest, {'schema_version', 'files'}, 'manifest')
    if type(manifest['schema_version']) is not int or manifest['schema_version'] != 1:
        raise ValueError('Unsupported public manifest version')
    keys(manifest['files'], names - {'MANIFEST.json'}, 'manifest inventory')
    for name, record in manifest['files'].items():
        keys(record, {'sha256', 'bytes'}, 'manifest file')
        digest(record['sha256'], 'manifest file'); integer(record['bytes'], 'manifest file bytes')
        raw = (folder / name).read_bytes()
        if record != {'sha256': sha256(raw).hexdigest(), 'bytes': len(raw)}:
            raise ValueError('Public manifest hash/size mismatch')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('evidence', nargs='?', type=Path, default=Path(__file__).with_name('evidence.json'))
    args = parser.parse_args(argv)
    if Path(__file__).name == 'verify.py':
        verify_bundle(Path(__file__).resolve().parent)
    if args.evidence.is_symlink() or not args.evidence.is_file():
        raise ValueError('Public evidence must be a regular nonsymlink file')
    d = validate_summary(parse_json(args.evidence.read_bytes()))
    print('Verified public schema, source hashes, eligible original-source flags and 36-row arithmetic. No native execution or fresh AI generation was performed.')
    print(json.dumps(evidence_usage(d), ensure_ascii=False, sort_keys=True))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, UnicodeError) as error:
        raise SystemExit(str(error)) from error

"""Publish audited delayed saved-action results in a new immutable dated study."""
import argparse
from datetime import datetime
from hashlib import sha256
from html import escape
import importlib.util
import json
import posixpath
from pathlib import Path, PurePosixPath
import re
import stat
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://yuu-honda.github.io/lux-spiria-results/'
DATA_FILE = 'data/experience-retention-delayed-2026-10-29.json'
STUDY = 'studies/2026-10-29-experience-retention-delayed/'
REPLAY = 'experiments/experience-retention-delayed-2026-10-29/'
ZIP_FILE = 'downloads/experience-retention-delayed-2026-10-29.zip'
_spec = importlib.util.spec_from_file_location('delayed_public_phase_one_helpers', ROOT / 'tools/build_experience_retention.py')
phase_one = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(phase_one)
ARMS, FORMATS, CATALOG = phase_one.ARMS, phase_one.FORMATS, phase_one.CATALOG
RESULT_FIELDS, INSPECTION_FIELDS, METRICS = phase_one.RESULT_FIELDS, phase_one.INSPECTION_FIELDS, phase_one.METRICS
CLASSIFICATIONS = phase_one.CLASSIFICATIONS
ACTION_LOOP_SHA256 = phase_one.ACTION_LOOP_SHA256
EXPERIENCE_IO_SHA256 = 'e66ca22700b19a6bae4340561bb5183473b605b8a07bb6e61f0c1bcb4ab78543'
PROTOCOL_SHA256 = phase_one.PROTOCOL_SHA256
MEMORY_SHA256 = '5c94f608ff5a6c7e85f311be8cdf45fa210f7da943fa8b832cf419fe8b64af8f'
MEMORY_FREEZE_SHA256 = '163ecfba23c2acc9867b8a31143e602def7e3f708ff116bf130eec3102df8803'
PHASE_ONE_SUMMARY_SHA256 = '9bcba25720e8e899dc3121fdf7340fb422a49428d50f22402026a8f80cb997c8'
DELAYED_TASK_SHA256 = 'dc72c36f5d78aacecef40c64b43da8737fbe460acf42afb7004a5d0cad8943da'
DELAYED_GOLD_SHA256 = 'ff8676dd7a6422d2ed45edd57dd9ac768ba128d4f9cb5dda499479ff027da935'
MEMORY_FREEZE_UNIX = 1793117550.4705799
SOURCE_FILES = {family: {**row, 'changed_sha256': changed} for (family, row), changed in zip(phase_one.SOURCE_FILES.items(), [
    '13230d5d92c70a527c6654667d32e79ac8939747b9b1df158f3895caabe3115a',
    '03039ac97f4f7c5595526f75b67b26e700d309e6871e4b124a9937c827d4f425',
    '738166e4c53e044b7d9ac926fca417fc517545910c20005b018dd50956d696b4'])}
SAMPLE = {'public_source_families': 3, 'delayed_unique_objectives': 3,
    'formats_per_objective': 2, 'delayed_items_per_arm': 6, 'arms': 2}
SCOPE_TRUE = {'same_frozen_memory', 'tasks_gold_frozen_before_training', 'per_arm_item_fresh_context',
    'all12_policies_frozen_before_any_inspection', 'all12_actions_frozen_before_execution',
    'one_action_per_item', 'same_current_evidence_and_inspection_opportunity',
    'fixed_paired_dispatch_order', 'independent_final_audit_approved',
    'phase_one_publication_unchanged', 'actual_elapsed_clock_guard'}
SCOPE_FALSE = {'probe_repairs', 'probe_feedback_updates', 'fresh_ai_regeneration_in_replay',
    'time_only_causal_effect_established', 'native_private_lre_used',
    'current_schema_pre_supplied', 'format_label_pre_supplied'}
PROVENANCE = {'action_loop_sha256', 'experience_io_sha256', 'protocol_sha256',
    'phase_one_public_summary_sha256', 'memory_freeze_sha256', 'delayed_task_commitment_sha256',
    'delayed_gold_commitment_sha256', 'policy_freeze_sha256', 'action_freeze_sha256',
    'results_sha256', 'final_audit_sha256', 'clock_projection_sha256'}
TOP_FIELDS = {'schema_version', 'study_id', 'date', 'status', 'sample', 'sources', 'memory',
    'clocks', 'delayed', 'counts', 'paired', 'engineering', 'scope', 'provenance', 'replay'}
TOP_CLOCKS = {'memory_freeze', 'not_before', 'collection_prepared', 'policy_phase_authorization',
    'policies_frozen', 'inspection_phase_authorization', 'inspections_frozen',
    'action_phase_authorization', 'actions_frozen'}
ITEM_CLOCKS = {'initial_authoring', 'inspection', 'final_authoring', 'execution'}
REPLAY_FIXED_FILES = {'README.md', 'MANIFEST.json', 'action_loop.py', 'experience_io.py',
    'replay.py', 'replay_plan.json', 'collection_metadata.json', 'input/ACTION_CONTRACT.txt',
    'input/DELAYED_TASKS.json', 'input/DELAYED_GOLD.json', 'input/SOURCE_PROVENANCE.json',
    'memory/experience_record.json', 'input/environment/source_map_original.json',
    'input/environment/source_map_changed.json', 'input/environment/source_map_probes.json'} | {
    prefix + family + '.json' for prefix in ('input/originals/', 'input/environment/migrated/')
    for family in SOURCE_FILES}
_keys, _integer, _digest = phase_one._keys, phase_one._integer, phase_one._digest


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


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


def point(value, where):
    _keys(value, {'utc', 'unix_seconds'}, where)
    phase_one._clock(value['unix_seconds'], where)
    phase_one._utc(value['utc'], value['unix_seconds'])
    return value['unix_seconds']


def recalculate(rows):
    counts = {arm: {fmt or 'all': phase_one.aggregate_attempts([(r['result'], r['inspection'])
        for r in rows if r['arm'] == arm and (fmt is None or r['format'] == fmt)])
        for fmt in (None, *FORMATS)} for arm in ARMS}
    bound = {(r['arm'], r['id']): r for r in rows}; paired = []
    for i in range(1, 7):
        identity = f'Q{i:02}'; a, b = (bound[arm, identity]['result']['validation_status'] == 'accepted' for arm in ARMS)
        paired.append({'id': identity, 'format': CATALOG[f'A{i:02}'][1],
            'classification': 'both_correct' if a and b else 'corrected' if b else 'regressed' if a else 'both_wrong'})
    return {'counts': counts, 'paired': paired}


def validate_summary(d):
    _keys(d, TOP_FIELDS, 'summary')
    if type(d['schema_version']) is not int or d['schema_version'] != 1 or d['study_id'] != 'experience-retention-delayed-2026-10-29' or d['date'] != '2026-10-29' or d['status'] != 'collected':
        raise ValueError('Only audited collected delayed results qualify')
    _keys(d['sample'], SAMPLE, 'sample')
    for key, expected in SAMPLE.items():
        _integer(d['sample'][key], 'sample')
        if d['sample'][key] != expected:
            raise ValueError('Frozen three-objective/two-format denominator differs')
    _keys(d['sources'], SOURCE_FILES, 'sources')
    for family, expected in SOURCE_FILES.items():
        _keys(d['sources'][family], expected, 'source')
        if d['sources'][family] != expected:
            raise ValueError('Frozen public source path/hash differs')
    _keys(d['memory'], {'sha256', 'canonical_characters', 'unchanged_from_phase_one'}, 'memory')
    if d['memory']['sha256'] != MEMORY_SHA256 or type(d['memory']['canonical_characters']) is not int or d['memory']['canonical_characters'] != 5627 or d['memory']['unchanged_from_phase_one'] is not True:
        raise ValueError('The exact phase-one frozen record must remain unchanged')
    _keys(d['clocks'], TOP_CLOCKS | {'minimum_elapsed_seconds', 'stage_freeze_clock_basis'}, 'clocks')
    if d['clocks']['stage_freeze_clock_basis'] != 'local_filesystem_mtime':
        raise ValueError('Stage-freeze clocks must disclose their local filesystem mtime basis')
    if type(d['clocks']['minimum_elapsed_seconds']) is not int or d['clocks']['minimum_elapsed_seconds'] != 86400:
        raise ValueError('Minimum elapsed time must remain 86400 seconds')
    times = {key: point(d['clocks'][key], key) for key in TOP_CLOCKS}
    if abs(times['memory_freeze'] - MEMORY_FREEZE_UNIX) > .001 or abs(times['not_before'] - times['memory_freeze'] - 86400) > .001:
        raise ValueError('Memory freeze/not-before clocks differ from phase one')
    if not times['not_before'] <= times['collection_prepared'] <= times['policy_phase_authorization'] <= times['policies_frozen'] <= times['inspection_phase_authorization'] <= times['inspections_frozen'] <= times['action_phase_authorization'] <= times['actions_frozen']:
        raise ValueError('Actual collection/freeze clocks must be chronological and due')
    if type(d['delayed']) is not list or len(d['delayed']) != 12:
        raise ValueError('Retain all twelve delayed items')
    seen = set()
    for row in d['delayed']:
        _keys(row, {'arm', 'id', 'source', 'family', 'format', 'policy_decision', 'inspection', 'result', 'clocks'}, 'delayed item')
        arm, identity = row['arm'], row['id']
        if type(arm) is not str or arm not in ARMS or type(identity) is not str or re.fullmatch('Q0[1-6]', identity) is None or (arm, identity) in seen:
            raise ValueError('Delayed arm/item identity missing or duplicated')
        source = 'A' + identity[1:]
        if (row['source'], row['family'], row['format']) != (source, *CATALOG[source]):
            raise ValueError('Frozen delayed source/family/format binding differs')
        if type(row['policy_decision']) is not str or row['policy_decision'] not in ('inspect', 'submit') or (row['policy_decision'] == 'inspect') != (row['inspection'] is not None):
            raise ValueError('Frozen policy and actual optional inspection disagree')
        phase_one._result(row['result']); phase_one._inspection(row['inspection'], row['family'], row['format'], d['sources'])
        _keys(row['clocks'], ITEM_CLOCKS, 'item clocks')
        observed = {key: point(row['clocks'][key], key) for key in ('initial_authoring', 'execution')}
        if not times['collection_prepared'] <= observed['initial_authoring'] <= times['policies_frozen']:
            raise ValueError('Initial authoring must be actually due and before policy freeze')
        if not times['actions_frozen'] <= observed['execution']:
            raise ValueError('Execution must follow actual action freeze')
        if row['inspection'] is None:
            if row['clocks']['inspection'] is not None or row['clocks']['final_authoring'] is not None:
                raise ValueError('Direct submission has no inspection or second authoring authorization')
        else:
            inspected = point(row['clocks']['inspection'], 'inspection')
            if not times['inspection_phase_authorization'] <= inspected <= times['inspections_frozen']:
                raise ValueError('Inspection must follow policy freeze and precede inspection freeze')
            final = point(row['clocks']['final_authoring'], 'final authoring authorization')
            if not times['inspections_frozen'] <= final <= times['actions_frozen']:
                raise ValueError('Final authorization must follow inspection freeze and precede action freeze')
        seen.add((arm, identity))
    expected = recalculate(d['delayed'])
    def check(actual, calculated):
        _keys(actual, calculated, 'counts')
        for key, value in calculated.items():
            if isinstance(value, dict):
                check(actual[key], value)
            else:
                _integer(actual[key], 'count')
                if actual[key] != value:
                    raise ValueError('Every actual count and cost must recalculate')
    check(d['counts'], expected['counts'])
    if type(d['paired']) is not list or len(d['paired']) != 6:
        raise ValueError('Retain all six paired delayed outcomes')
    pairs = {r['id']: r for r in expected['paired']}; seen = set()
    for row in d['paired']:
        _keys(row, {'id', 'format', 'classification'}, 'paired')
        if type(row['id']) is not str or row['id'] not in pairs or row['id'] in seen or row != pairs[row['id']]:
            raise ValueError('Paired classifications must recalculate')
        seen.add(row['id'])
    engineering = d['engineering']; _keys(engineering, {'evidence_kind', 'tests_run', 'failures', 'errors', 'report_sha256'}, 'engineering')
    if engineering['evidence_kind'] != 'synthetic_transport_preparation' or type(engineering['tests_run']) is not int or engineering['tests_run'] != 17:
        raise ValueError('Keep the 17 synthetic transport checks separate')
    for key in ('failures', 'errors'):
        _integer(engineering[key], 'engineering ' + key)
    if engineering['failures'] + engineering['errors'] > 17:
        raise ValueError('Engineering failures/errors exceed tests')
    _digest(engineering['report_sha256'], 'engineering report')
    _keys(d['scope'], SCOPE_TRUE | SCOPE_FALSE | {'provider_metadata'}, 'scope')
    for key in SCOPE_TRUE | SCOPE_FALSE:
        if type(d['scope'][key]) is not bool or d['scope'][key] != (key in SCOPE_TRUE):
            raise ValueError('Frozen delayed role/feedback/time boundary differs')
    if d['scope']['provider_metadata'] is not None:
        raise ValueError('Unverified provider metadata must remain null')
    _keys(d['provenance'], PROVENANCE, 'provenance')
    for value in d['provenance'].values():
        _digest(value, 'provenance')
    pinned = {'action_loop_sha256': ACTION_LOOP_SHA256, 'experience_io_sha256': EXPERIENCE_IO_SHA256,
        'protocol_sha256': PROTOCOL_SHA256, 'phase_one_public_summary_sha256': PHASE_ONE_SUMMARY_SHA256,
        'memory_freeze_sha256': MEMORY_FREEZE_SHA256, 'delayed_task_commitment_sha256': DELAYED_TASK_SHA256,
        'delayed_gold_commitment_sha256': DELAYED_GOLD_SHA256}
    if any(d['provenance'][key] != value for key, value in pinned.items()):
        raise ValueError('Frozen code/phase-one/task/gold commitment differs')
    _keys(d['replay'], {'manifest_sha256', 'readme_sha256', 'zip_sha256'}, 'replay')
    for value in d['replay'].values():
        _digest(value, 'replay')
    return d


def read_export(root=ROOT, source=None):
    path = root / DATA_FILE if source is None else Path(source)
    if source is None and not path.exists() and not path.is_symlink():
        return None
    if path.is_symlink() or not path.is_file():
        raise ValueError('Audited delayed public export must be an existing regular file')
    raw = path.read_bytes()
    return validate_summary(parse_json(raw)), raw


def load_summary(root=ROOT, source=None):
    export = read_export(root, source)
    if export is None:
        raise FileNotFoundError('Audited delayed export unavailable; no publication writes')
    return export[0]


def optional_summary(root=ROOT, source=None):
    export = read_export(root, source)
    return None if export is None else export[0]


def _safe_name(name):
    return type(name) is str and bool(name) and bool(PurePosixPath(name).parts) and '\\' not in name and '\x00' not in name and not PurePosixPath(name).is_absolute() and PurePosixPath(name).as_posix() == name and not any(p in ('.', '..') for p in PurePosixPath(name).parts) and re.match(r'^[A-Za-z]:', name) is None


def require_public_inputs(root, d, bundle=None, zip_path=None):
    validate_summary(d)
    for source in SOURCE_FILES.values():
        path = root / source['public_path']
        if not path.is_file() or sha256(path.read_bytes()).hexdigest() != source['original_sha256']:
            raise ValueError('Known original public source missing or changed')
    phase_one_path = root / phase_one.DATA_FILE
    if not phase_one_path.is_file() or sha256(phase_one_path.read_bytes()).hexdigest() != PHASE_ONE_SUMMARY_SHA256:
        raise ValueError('Immutable immediate-phase summary missing or changed')
    bundle = root / REPLAY if bundle is None else Path(bundle)
    archive = root / ZIP_FILE if zip_path is None else Path(zip_path)
    if bundle.is_symlink() or not bundle.is_dir() or archive.is_symlink() or not archive.is_file() or bundle.resolve() in archive.resolve().parents:
        raise ValueError('Replay bundle and separate external ZIP must be regular paths')
    files = {}
    for path in bundle.rglob('*'):
        mode = path.lstat().st_mode
        if stat.S_ISLNK(mode) or (not stat.S_ISDIR(mode) and not stat.S_ISREG(mode)):
            raise ValueError('Replay symlink/nonregular entry forbidden')
        if stat.S_ISREG(mode):
            name = path.relative_to(bundle).as_posix()
            if not _safe_name(name) or any(part.lower() in {'vendor', 'native', 'actors', 'receipts', 'runs', 'packets', 'roles'} for part in PurePosixPath(name).parts) or path.suffix.lower() in {'.db', '.sqlite', '.sqlite3', '.jsonl', '.bin', '.zip'}:
                raise ValueError('Unallowlisted private or unsafe replay file')
            files[name] = path.read_bytes()
    if 'MANIFEST.json' not in files or 'README.md' not in files or sha256(files['MANIFEST.json']).hexdigest() != d['replay']['manifest_sha256'] or sha256(files['README.md']).hexdigest() != d['replay']['readme_sha256'] or sha256(archive.read_bytes()).hexdigest() != d['replay']['zip_sha256']:
        raise ValueError('Exact uppercase MANIFEST/README/external ZIP hashes required')
    manifest = parse_json(files['MANIFEST.json']); _keys(manifest, {'schema_version', 'files'}, 'manifest')
    if type(manifest['schema_version']) is not int or manifest['schema_version'] != 1:
        raise ValueError('Unsupported replay manifest version')
    _keys(manifest['files'], set(files) - {'MANIFEST.json'}, 'exact replay inventory')
    for name, record in manifest['files'].items():
        _keys(record, {'sha256', 'bytes'}, 'manifest record'); _digest(record['sha256'], 'manifest'); _integer(record['bytes'], 'manifest bytes')
        if len(files[name]) != record['bytes'] or sha256(files[name]).hexdigest() != record['sha256']:
            raise ValueError('Replay manifest file hash/size differs')
    allowed = set(REPLAY_FIXED_FILES)
    for row in d['delayed']:
        suffix = row['arm'] + '/' + row['id'] + '.json'
        allowed.update({'actions/' + suffix, 'policies/' + suffix})
        if row['inspection'] is not None:
            allowed.add('observations/' + suffix)
        if row['result']['artifact_sha256'] is not None:
            allowed.add('artifacts/' + suffix)
    if set(files) != allowed:
        raise ValueError('Replay file inventory exceeds or misses the fixed public allowlist')
    required = {'action_loop.py': ACTION_LOOP_SHA256, 'experience_io.py': EXPERIENCE_IO_SHA256,
        'memory/experience_record.json': MEMORY_SHA256, 'input/DELAYED_TASKS.json': DELAYED_TASK_SHA256,
        'input/DELAYED_GOLD.json': DELAYED_GOLD_SHA256}
    for family, source in SOURCE_FILES.items():
        required['input/originals/' + family + '.json'] = source['original_sha256']
        required['input/environment/migrated/' + family + '.json'] = source['changed_sha256']
    for name, digest in required.items():
        if name not in files or sha256(files[name]).hexdigest() != digest:
            raise ValueError('Frozen public replay code/record/tasks/gold differs')
    if not {'replay.py', 'replay_plan.json', 'input/environment/source_map_original.json', 'input/environment/source_map_changed.json', 'input/environment/source_map_probes.json'} <= set(files):
        raise ValueError('Saved-action replay code and plan required')
    for name, raw in files.items():
        if name.startswith(('input/originals/', 'input/environment/migrated/')):
            continue
        text = raw.decode('utf-8')
        if re.search(r'/' + r'Users/|/private/var/|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|(?:sk-|ghp_)[A-Za-z0-9]{20,}', text):
            raise ValueError('Private path/runtime identifier/secret pattern in replay')
    with zipfile.ZipFile(archive) as z:
        names = z.namelist()
        if len(names) != len(set(names)) or set(names) != set(files) or any(z.read(name) != raw for name, raw in files.items()):
            raise ValueError('External ZIP must exactly match the audited replay file set and bytes')
        if any(stat.S_ISLNK(z.getinfo(name).external_attr >> 16) for name in names):
            raise ValueError('ZIP symlinks forbidden')
    _bind_saved_records(d, files)
    return files, archive.read_bytes()


def _bind_saved_records(d, files):
    plan = parse_json(files['replay_plan.json']); _keys(plan, {'schema_version', 'entries'}, 'replay plan')
    if type(plan['schema_version']) is not int or plan['schema_version'] != 1 or type(plan['entries']) is not list or len(plan['entries']) != 12:
        raise ValueError('Replay must retain exactly twelve saved delayed actions')
    bound = {(r['arm'], r['id']): r for r in d['delayed']}; seen = set()
    def selected(path, selector):
        if not _safe_name(path) or path not in files:
            raise ValueError('Replay plan path must be manifest-listed')
        value = parse_json(files[path])
        if selector is None and type(value) is dict:
            return value
        if type(selector) is int and type(value) is list and 0 <= selector < len(value) and type(value[selector]) is dict:
            return value[selector]
        raise ValueError('Replay action/policy selector differs')
    fields = {'key', 'task_id', 'source', 'map', 'action_file', 'action_selector', 'policy_file', 'policy_selector', 'expected_file', 'expected_result', 'inspection_file'}
    for entry in plan['entries']:
        _keys(entry, fields, 'replay entry')
        match = re.fullmatch(r'delayed_(no_experience|experience_record)-(Q0[1-6])', entry['key']) if type(entry['key']) is str else None
        if match is None or match.groups() in seen:
            raise ValueError('Replay key must uniquely bind delayed arm/item')
        key = match.groups(); seen.add(key); row = bound[key]
        if (entry['task_id'], entry['source'], entry['map'], entry['expected_file']) != (row['id'], row['source'], 'probes', 'input/DELAYED_GOLD.json'):
            raise ValueError('Replay plan assigned source/task/gold differs')
        suffix = row['arm'] + '/' + row['id'] + '.json'
        if (entry['action_file'], entry['policy_file'], entry['action_selector'], entry['policy_selector']) != ('actions/' + suffix, 'policies/' + suffix, None, None):
            raise ValueError('Replay must preserve one assigned saved action and policy file per item')
        action = selected(entry['action_file'], entry['action_selector']); policy = selected(entry['policy_file'], entry['policy_selector'])
        _keys(policy, {'id', 'decision', 'rationale'} if row['policy_decision'] == 'inspect' else {'id', 'decision', 'action'}, 'saved policy')
        if row['policy_decision'] == 'inspect' and type(policy['rationale']) is not str:
            raise ValueError('Saved requested-inspection rationale must remain text')
        if row['policy_decision'] == 'submit' and canonical(policy['action']) != canonical(action):
            raise ValueError('Submitted saved action must remain locked')
        mapping = parse_json(files['input/environment/source_map_probes.json']); _keys(mapping, CATALOG, 'probe map')
        target = mapping[row['source']]
        if type(target) is not str or '\\' in target or '\x00' in target or PurePosixPath(target).is_absolute():
            raise ValueError('Replay map must name a relative public source')
        target = posixpath.normpath('input/environment/' + target)
        if target not in files or sha256(files[target]).hexdigest() != d['sources'][row['family']][row['format'] + '_sha256']:
            raise ValueError('Replay assigned actual source hash/format differs')
        r = row['result']
        if r['artifact_sha256'] is not None and sha256(files['artifacts/' + suffix]).hexdigest() != r['artifact_sha256']:
            raise ValueError('Saved actual artifact byte hash differs')
        if action.get('id') != row['id'] or policy.get('id') != row['id'] or policy.get('decision') != row['policy_decision'] or sha256(canonical(action).encode('utf-8')).hexdigest() != r['action_sha256'] or len(canonical(action)) != r['canonical_characters'] or action.get('prediction') != r['prediction']:
            raise ValueError('Saved actual action/policy hash, prediction or character count differs')
        expected = entry['expected_result']; _keys(expected, {'id', 'execution_status', 'validation_status', 'artifact_sha256', 'error'}, 'replay expected result')
        if expected['id'] != row['id'] or any(expected[k] != r[k] for k in ('execution_status', 'validation_status', 'artifact_sha256')):
            raise ValueError('Saved replay expected result differs')
        error = expected['error']
        if error is not None:
            _keys(error, {'type', 'message'}, 'saved actual error')
            if any(type(v) is not str for v in error.values()):
                raise ValueError('Actual error type/message must remain text')
        if (error is None) != (r['error'] is None) or (error is not None and (error.get('type') != r['error']['type'] or sha256(canonical(error).encode('utf-8')).hexdigest() != r['error']['sha256'])):
            raise ValueError('Actual saved error digest differs')
        if row['inspection'] is None:
            if entry['inspection_file'] is not None:
                raise ValueError('No requested inspection requires no saved inspection')
        else:
            name = entry['inspection_file']; record = selected(name, None); inspection = row['inspection']
            if name != 'observations/' + suffix or record.get('source') != row['source'] or sha256(files[name]).hexdigest() != inspection['record_sha256'] or any(record.get(k) != inspection[k] for k in ('raw_sha256', 'raw_bytes_read', 'returned_canonical_characters')) or sha256(canonical(record.get('observation')).encode('utf-8')).hexdigest() != inspection['observation_sha256']:
                raise ValueError('Actual saved inspection hash/cost/projection differs')


def t(ja, en, lang):
    return ja if lang == 'ja' else en


def label(arm, lang):
    return t('経験記録なし', 'No experience record', lang) if arm == ARMS[0] else t('同じ凍結した経験記録あり', 'Same frozen experience record', lang)


def elapsed_label(seconds):
    return f'{int(seconds // 3600)}h {int(seconds % 3600 // 60):02}m'


def clock_ranges(d):
    ranges = {}
    for stage in ('initial_authoring', 'final_authoring', 'execution'):
        values = [r['clocks'][stage]['unix_seconds'] for r in d['delayed'] if r['clocks'][stage] is not None]
        ranges[stage] = (min(values), max(values)) if values else None
    return ranges


def efficient_record_use(d):
    a, b = (d['counts'][arm]['all'] for arm in ARMS)
    return a['accepted'] == b['accepted'] and b['inspections'] < a['inspections'] and all(b[k] <= a[k] for k in ('execution_errors', 'invalid_actions', 'abstentions'))


def paired_counts(d, fmt=None):
    return {key: sum(r['classification'] == key for r in d['paired'] if fmt is None or r['format'] == fmt) for key in CLASSIFICATIONS}


CSS = '''.erd-study{max-width:1200px;margin:auto}.erd-study .study-hero h1{text-wrap:balance}.erd-study .lead{max-width:900px}.erd-study .section{padding:2.3rem 0}.erd-study .table-wrap{max-width:100%;overflow:auto;overscroll-behavior-x:contain;border:1px solid #34434d;border-radius:12px}.erd-study table{border-collapse:collapse;min-width:660px;width:100%}.erd-study th,.erd-study td{padding:.8rem;text-align:left;border-bottom:1px solid #34434d;vertical-align:top}.erd-study caption{text-align:left;padding:1rem;color:#b8c7cf}.erd-study .erd-caption{display:block;max-width:calc(100vw - 6rem);white-space:normal;overflow-wrap:anywhere}.erd-study .erd-scroll-hint{font-size:.85rem;color:#b8c7cf;margin:.6rem 0;max-width:70ch}.erd-study .note{color:#b8c7cf}.erd-study .boundary-box{margin:1rem 0}.erd-study .erd-digests td{word-break:break-all;font-family:monospace}.erd-study details{margin:1rem 0}.erd-study summary{cursor:pointer;padding:.8rem}.erd-study .download-links{display:flex;flex-wrap:wrap;gap:1rem}.erd-study code{overflow-wrap:anywhere}@media(max-width:700px){.erd-study .section{padding:1.6rem 0}}'''


def table(caption, headings, rows, lang, css=''):
    hint = t('横に長い表は、表の中を左右にスクロールできます。表にフォーカスして左右キーも使えます。', 'Wide tables scroll horizontally. Focus the table region and use the arrow keys.', lang)
    return '<p class="erd-scroll-hint">' + hint + '</p><div class="table-wrap" role="region" tabindex="0" aria-label="' + escape(caption, quote=True) + '"><table class="' + css + '"><caption><span class="erd-caption">' + escape(caption) + '</span></caption><thead><tr>' + ''.join('<th scope="col">' + escape(str(x)) + '</th>' for x in headings) + '</tr></thead><tbody>' + ''.join('<tr><th scope="row">' + escape(str(row[0])) + '</th>' + ''.join('<td>' + escape(str(x)) + '</td>' for x in row[1:]) + '</tr>' for row in rows) + '</tbody></table></div>'


def section(identity, title, body):
    return f'<section class="section" id="{identity}" aria-labelledby="{identity}-title"><div class="section-heading"><h2 id="{identity}-title">{title}</h2></div>{body}</section>'


def finding(d, lang):
    a, b = (d['counts'][arm]['all'] for arm in ARMS); pairs = paired_counts(d)
    text = '<p>' + t(f'同じ遅延6項目の受理は、記録なし {a["accepted"]}/6 → 同じ記録あり {b["accepted"]}/6。追加の構造確認は {a["inspections"]}回 → {b["inspections"]}回でした。', f'On the same six delayed items, acceptance was {a["accepted"]}/6 without the record → {b["accepted"]}/6 with the same frozen record. Optional schema inspections were {a["inspections"]} → {b["inspections"]}.', lang) + '</p>'
    text += '<p>' + t(f'対応する項目では修正{pairs["corrected"]}、後退{pairs["regressed"]}でした。各条件6項目は3つの新規目的×2形式で、6つの独立した目的・経験ではありません。', f'Paired items show {pairs["corrected"]} corrected and {pairs["regressed"]} regressed. Six items per arm are three further objectives × two formats, not six independent objectives or experiences.', lang) + '</p>'
    if a['accepted'] == b['accepted']:
        text += '<p>' + t('受理数は同じで、この標本では精度向上を観測していません。', 'Acceptance was equal; this sample shows no accuracy gain.', lang) + '</p>'
    if efficient_record_use(d):
        text += '<p><strong>' + t('同じ受理数・少ない追加確認・実行エラー等を増やさない、という事前の限定基準を満たしました。凍結した外部記録全体の有無による差です。', 'Equal acceptance, fewer inspections and no added execution errors, invalid actions or abstentions meet the predeclared bounded criterion for access to the whole frozen external record.', lang) + '</strong></p>'
    else:
        text += '<p><strong>' + t('同じ受理数・少ない追加確認・実行エラー等を増やさない、という事前の確認効率基準は満たしませんでした。この標本で記録による精度や追加確認の利益を作りません。', 'The predeclared equal-acceptance/fewer-inspections/no-added-errors criterion was not met. These results do not establish an accuracy or optional-inspection benefit from the record.', lang) + '</strong></p>'
    text += '<p class="note">' + t('追加確認の費用は総source I/Oではありません。全操作のexecutorは、両条件とも指定したsourceを読み成果物を計算します。速度・token・compute・費用の節約は測っていません。', 'Optional-inspection cost is not total source I/O. Every action executor reads its assigned source to compute an artifact in both arms. Speed, token, compute and spending savings were not measured.', lang) + '</p>'
    return text


def render(lang, d):
    if lang not in ('ja', 'en'):
        raise ValueError('Supported languages are ja and en')
    validate_summary(d); frozen = d['clocks']['memory_freeze']['unix_seconds']; ranges = clock_ranges(d)
    initial = ranges['initial_authoring']; elapsed = (initial[0] - frozen, initial[1] - frozen)
    title = t('同じ凍結記録を、実際の遅延後に使う。', 'Use the same frozen record after an actual delay.', lang)
    body = '<div class="erd-study"><section class="study-hero"><p class="kicker">COLLECTED DELAYED STUDY / 2026-10-29</p><h1>' + title + '</h1><p class="lead">' + t(f'記録凍結から実際に{elapsed_label(elapsed[0])}〜{elapsed_label(elapsed[1])}後、12の新しい項目コンテキストへ同じ外部記録を渡すかどうかを比較しました。これは24時間ちょうどの試験ではなく、86400秒以上という下限を超えて実行した遅延試験です。', f'Initial authoring was authorized {elapsed_label(elapsed[0])}–{elapsed_label(elapsed[1])} after the record freeze. Twelve fresh item contexts received the same external record or no record. This was later than the 86400-second minimum, not a trial at exactly 24 hours.', lang) + '</p><p class="note">' + t('保存済みの実結果です。新しいAI判断を再生成する表示や、同じ主体の心理的保持を示す試験ではありません。', 'These are recorded actual outcomes, not fresh AI regeneration or a test of one subject’s psychological retention.', lang) + '</p></section>'
    body += section('finding', t('遅延後の正しさと、追加確認を別々に読む。', 'Read delayed correctness and optional inspection separately.', lang), finding(d, lang))
    clocks = '<p>' + t('initial/final authoringの時計は、実際の呼出し前の著述許可時刻です。providerのsampling開始時刻は公開されておらず、ここから推定しません。executionは実native項目のstarted_atです。確認の作業時刻を著述の時計と分けて残します。', 'Initial/final authoring clocks are real pre-call authoring authorization receipts. Provider sampling starts are unavailable and are not inferred. Execution clocks are actual native item started_at timestamps. Inspection work is recorded separately from authoring authorization.', lang) + '</p>'
    clocks += '<p>' + t('3つのstage記録のlocal modification timeを、元ファイルのfilesystem mtimeとして示します。正確な完了を計測したtimestampではありません。3つのraw phase-entry許可guardも個別に表示し、完了時刻とは区別します。phase-entryが最後の出力より後でも、provider時刻や完了時刻へ読み替えません。これはlocalな時計証拠で、外部署名・外部attestationではありません。元の実試行や記録時刻は変更していません。', 'The three stage-record local modification times are original state-file filesystem mtimes, not instrumented exact completion timestamps. All three raw phase-entry authorization guards are separately shown and are not completion times. A phase-entry may follow the last output; it is not relabeled as a provider or completion timestamp. This is local clock evidence, not an external signature or attestation. Original trial records and their times were not altered.', lang) + '</p>'
    rows = [[key + (' / local filesystem mtime' if key in ('policies_frozen', 'inspections_frozen', 'actions_frozen') else ''), d['clocks'][key]['utc'], f'{d["clocks"][key]["unix_seconds"] - frozen:.6f}'] for key in ('memory_freeze', 'not_before', 'collection_prepared', 'policy_phase_authorization', 'policies_frozen', 'inspection_phase_authorization', 'inspections_frozen', 'action_phase_authorization', 'actions_frozen')]
    clocks += table(t('実際のcheckpoint / UTCと記録凍結からの秒数。', 'Actual checkpoints: UTC and seconds since record freeze.', lang), ['Checkpoint', 'UTC', 'Elapsed seconds'], rows, lang)
    rows = []
    names = {'initial_authoring': t('初期著述の許可', 'Initial authoring authorization', lang), 'final_authoring': t('最終著述の許可', 'Final authoring authorization', lang), 'execution': t('native項目の実行開始', 'Native item execution start', lang)}
    for stage, limits in ranges.items():
        if limits is None:
            rows.append([names[stage], '—', '—', '—'])
        else:
            points = [r['clocks'][stage] for r in d['delayed'] if r['clocks'][stage] is not None]
            rows.append([names[stage], min(points, key=lambda p: p['unix_seconds'])['utc'], max(points, key=lambda p: p['unix_seconds'])['utc'], f'{limits[0] - frozen:.6f} – {limits[1] - frozen:.6f}'])
    clocks += table(t('著述許可と実行の実時計を混ぜない。', 'Keep actual authorization and execution clocks distinct.', lang), ['Stage', 'First UTC', 'Last UTC', 'Elapsed seconds range'], rows, lang)
    body += section('actual-clocks', t('予定ではなく、実際に経過した時間。', 'Actual elapsed time, separate from scheduling.', lang), clocks)
    design = '<p>' + t('凍結済みの別の3目的を各2形式で実行し、各条件6項目。条件×項目ごとに新しいコンテキストを使いました。全12初期方策を確認結果の前に固定し、選択された実確認の後に全12行動を実行結果の前に固定。各項目は確認最大1回・実行1回で、probe修正や結果を使った記録更新はありません。', 'Three further objectives frozen before training were each executed in two formats, six items per arm. Every arm/item used a fresh context. All twelve policies froze before inspection outputs; all twelve actions froze before execution outcomes. Each item permits at most one inspection and one action, without probe repairs or feedback-driven record updates.', lang) + '</p>'
    design += '<p>' + t('同じ記録は5627 canonical文字で、phase oneのhashと完全に同じです。元形式とpayloadへの意図した包み替えは同じ数値・型を保ちます。opaque handle・family・source hash・確認機会は同じで、schemaや形式の答えを予め渡しません。固定した対応順は、providerや時間の影響を相殺した保証ではありません。', 'The same record has 5627 canonical characters and exactly the phase-one digest. Original and deliberately payload-wrapped formats preserve values and types. Handles, families, source digests and inspection opportunities are equal, without pre-supplied schema/format answers. Fixed paired dispatch does not establish provider/time counterbalancing.', lang) + '</p>'
    rows = []
    for arm in ARMS:
        for fmt in ('all', *FORMATS):
            c = d['counts'][arm][fmt]; rows.append([label(arm, lang), fmt, f'{c["accepted"]}/{c["attempts"]}', c['execution_errors'], c['invalid_actions'], c['abstentions'], c['inspections'], c['source_bytes_read'], c['returned_canonical_characters']])
    design += table(t('元形式・変更形式の層を保持。費用は追加確認だけの値。', 'Retain original/changed strata. Costs cover optional inspections only.', lang), ['Arm', 'Format', 'Accepted', 'Exec error', 'Invalid', 'Abstention', 'Inspections', 'Inspection bytes', 'Projection chars'], rows, lang)
    rows = [[fmt or 'all', *paired_counts(d, fmt).values()] for fmt in (None, *FORMATS)]
    design += table(t('同じ目的と形式で、記録なし → 同じ記録あり。', 'Matched objective and format: no record → the same record.', lang), ['Format', 'Both correct', 'Corrected', 'Regressed', 'Both wrong'], rows, lang)
    body += section('delayed-comparison', t('3目的×2形式を、条件内で対応させる。', 'Pair three objectives × two formats within this block.', lang), design)
    rows = [[label(r['arm'], lang), r['id'], r['format'], r['policy_decision'], r['result']['execution_status'], r['result']['validation_status'], r['result']['prediction'], r['result']['canonical_characters'], int(r['result']['budget_exceeded'])] for r in d['delayed']]
    records = table(t('失敗・棄権・不確実な予測も含む全12項目。', 'All twelve items, retaining failures, abstentions and uncertain predictions.', lang), ['Arm', 'ID', 'Format', 'Policy', 'Execution', 'Validation', 'Prediction', 'Action chars', 'Overrun'], rows, lang)
    rows = [[label(r['arm'], lang), r['id'], r['clocks']['initial_authoring']['utc'], '—' if r['clocks']['inspection'] is None else r['clocks']['inspection']['utc'], '—' if r['clocks']['final_authoring'] is None else r['clocks']['final_authoring']['utc'], r['clocks']['execution']['utc']] for r in d['delayed']]
    records += '<details><summary>' + t('項目別の著述許可・確認・実行時計', 'Per-item authorization, inspection and execution clocks', lang) + '</summary>' + table(t('直接submitに第2の著述呼出しはない。', 'Direct submission has no second authoring call.', lang), ['Arm', 'ID', 'Initial authorization', 'Inspection', 'Final authorization', 'Native execution start'], rows, lang) + '</details>'
    records += '<p>' + t('行動上限は両条件で6000 canonical文字です。超過は削除せず別に数え、正誤へ自動変換しません。実入力長や確認回数の違いを、同じcompute・速度・費用とは扱いません。', 'Both arms share a 6000-character canonical action cap. Overruns are retained and counted separately, not automatically converted to incorrectness. Different actual input lengths and inspections do not establish equal compute, latency or spend.', lang) + '</p>'
    body += section('all-records', t('全選択と実結果を残す。', 'Retain every choice and actual outcome.', lang), records)
    e = d['engineering']; engineering = table(t('人工的なtransport準備確認。12の実項目と合算しない。', 'Synthetic transport preparation; do not pool with twelve actual items.', lang), ['Evidence', 'Tests', 'Failures', 'Errors'], [[e['evidence_kind'], e['tests_run'], e['failures'], e['errors']]], lang)
    body += section('engineering', t('工学確認と、実試行の単位を分ける。', 'Separate engineering checks from actual trials.', lang), engineering)
    limits = '<p>' + t('比較は、遅延block内で凍結した外部記録全体を渡すかどうかです。直後試験とは目的も時間も異なるため、直後→遅延の差を時間だけの効果や忘却として読みません。新しいコンテキストによる外部記録の再読は、同一主体の心理的保持、重み学習、自然な会話記憶、忘却曲線の実証ではありません。', 'The comparison is access to the whole frozen external record within the delayed block. Objectives and time both differ from the immediate trial, so immediate-to-delayed differences are not a time-only effect or forgetting. Fresh contexts rereading an external record do not establish one subject’s psychological retention, weight learning, natural conversation memory or a forgetting curve.', lang) + '</p>'
    limits += '<p>' + t('訓練時のreview templateはlegacy_scopeを明示的に求めていました。自発的な概念学習を示すものではありません。', 'The training review template explicitly requested legacy_scope; this is not unprompted conceptual learning.', lang) + '</p>'
    limits += '<p>' + t('既知の公開数値source上の人工的なファイル課題です。以前から公開された値への事前接触は除外できません。役割は同じhost上の読取allowlistで分け、OS隔離ではありません。provider/model/settings/token/computeは未確認のnullです。private native LRE、SHIORI機構・速度、native Wake、Emotion、生物学的な脳、AGIや意識を検証していません。', 'These are engineered file tasks over known public numeric sources; prior exposure to previously public values cannot be excluded. Roles share a host with read allowlists rather than OS isolation. Provider/model/settings/token/compute metadata is unverified and null. Private native LRE, SHIORI mechanisms/speed, native Wake, Emotion, biological brains, AGI and consciousness were not tested.', lang) + '</p>'
    limits += '<p><a href="../2026-10-28-experience-retention/' + ('index.html' if lang == 'ja' else 'en.html') + '">' + t('2026-10-28の直後公開物', 'The 2026-10-28 immediate publication', lang) + '</a>' + t('は、公開時点の未収集状態をそのまま保持します。今回の実際に収集した結果は、この別の日付・data・replayとして追加しました。過去10研究と4つの概要animationは変更しません。', ' keeps its at-publication pending state unchanged. These actually collected results append a separate date, data file and replay. All ten earlier studies and four overview animations are preserved.', lang) + '</p>'
    limits += '<details><summary>' + t('監査・凍結の識別hash', 'Audit and freeze identity digests', lang) + '</summary>' + table('SHA256', ['Artifact', 'SHA256'], [[key, d['provenance'][key]] for key in sorted(PROVENANCE)], lang, 'erd-digests') + '</details>'
    body += section('limits', t('外部記録を再利用した、という範囲で読む。', 'Read this as reuse of an external record.', lang), limits)
    replay = '<p>' + t('公開済みの数値source、同じ凍結記録、今回の保存済み方策・実行・goldと変更していないexecutorから、保存ACTIONを再実行できます。これは新しいAI選択を再生成せず、遅延したactor試行をやり直すものでもありません。manifestはbundle全体のbyte/hashを検証し、各操作へ割り当てたsource aliasは1つです。', 'Public numeric sources, the same frozen record, saved policies/actions/gold and the unchanged executor support saved-action replay. It does not regenerate fresh AI choices or repeat delayed actor collection. The manifest verifies bundle bytes/hashes, and each execution receives only its assigned source alias.', lang) + '</p><div class="download-links"><a href="../../' + DATA_FILE + '">' + t('公開集計JSON', 'Public summary JSON', lang) + '</a><a href="../../' + REPLAY + 'README.md">' + t('保存ACTIONリプレイ', 'Saved-action replay', lang) + '</a><a href="../../' + ZIP_FILE + '" download>ZIP ↓</a></div>'
    body += section('saved-replay', t('保存した操作を、結果と照合する。', 'Replay saved actions against recorded outcomes.', lang), replay)
    body += '</div>'
    home = '../../index.html' if lang == 'ja' else '../../index.en.html'; results = '../../results.html' if lang == 'ja' else '../../results.en.html'
    canonical_url = BASE + STUDY + ('' if lang == 'ja' else 'en.html'); manifest = 'site.webmanifest' if lang == 'ja' else 'site.en.webmanifest'
    switch = '<a href="index.html" lang="ja" hreflang="ja"' + (' aria-current="page"' if lang == 'ja' else '') + '>日本語</a><a href="en.html" lang="en" hreflang="en"' + (' aria-current="page"' if lang == 'en' else '') + '>EN</a>'
    description = t('実際に24時間以上経過した後の、同じ外部記録の再利用。3目的×2形式・2条件の全実結果、著述許可と実行時計、追加確認費用を保持。', 'Reuse of the same external record after actual elapsed time exceeding 24 hours. Three objectives × two formats in two arms, with actual outcomes, authorization/execution clocks and optional-inspection costs.', lang)
    return f'<!doctype html>\n<html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title} — LUX SPIRIA Results</title><meta name="description" content="{description}"><link rel="canonical" href="{canonical_url}"><link rel="alternate" hreflang="ja" href="{BASE+STUDY}"><link rel="alternate" hreflang="en" href="{BASE+STUDY}en.html"><link rel="alternate" hreflang="x-default" href="{BASE+STUDY}"><meta name="theme-color" content="#090d12"><link rel="icon" type="image/png" sizes="32x32" href="../../assets/favicon-32.png"><link rel="apple-touch-icon" sizes="180x180" href="../../assets/apple-touch-icon.png"><link rel="manifest" href="../../{manifest}"><link rel="stylesheet" href="../../site.css"><link rel="stylesheet" href="../../theme-dark.css"><link rel="stylesheet" href="experience-retention-delayed.css"></head><body><a class="skip-link" href="#main">{t("本文へ", "Skip to content", lang)}</a><div class="page"><header class="masthead"><a class="brand" href="{results}"><img src="../../assets/lux-symbol.png" alt="" width="44" height="44"><span class="brand-wordmark">LUX SPIRIA<span class="brand-subtitle">RESEARCH RESULTS</span></span></a><nav aria-label="{t("主なページ", "Main navigation", lang)}"><a href="{results}#studies">{t("研究結果", "Studies", lang)}</a><a href="#actual-clocks">{t("実際の時計", "Actual clocks", lang)}</a><a href="{home}">{t("全体像", "Overview", lang)}</a><span class="lang">{switch}</span></nav></header><main id="main">{body}</main><footer class="footer"><nav aria-label="{t("資料", "Resources", lang)}"><a href="{home}">LUX SPIRIA</a><a href="../../LICENSE">License / LSP-1.0</a><a href="https://github.com/Yuu-Honda/lux-spiria-results">GitHub ↗</a></nav><small>COLLECTED DELAYED RESULT / 2026-10-29</small></footer></div></body></html>'


def build_plan(root=ROOT, source=None, bundle=None, zip_path=None):
    spec = importlib.util.spec_from_file_location('delayed_public_command', ROOT / 'tools/experience_retention_delayed_publication.py')
    publication = importlib.util.module_from_spec(spec); spec.loader.exec_module(publication)
    return publication.prepare_updates(root, source, bundle, zip_path)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--experience-retention-delayed', type=Path)
    parser.add_argument('--experience-retention-delayed-replay', type=Path)
    parser.add_argument('--experience-retention-delayed-zip', type=Path)
    args = parser.parse_args(argv)
    updates = build_plan(ROOT, args.experience_retention_delayed, args.experience_retention_delayed_replay, args.experience_retention_delayed_zip)
    for relative, raw in updates.items():
        path = ROOT / relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
    print('Built audited collected delayed study.' if updates else 'No audited delayed export; no publication writes.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, UnicodeError, zipfile.BadZipFile) as error:
        raise SystemExit(str(error)) from error

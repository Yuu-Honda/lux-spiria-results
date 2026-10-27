"""Publish audited immediate record-use data; delayed outcomes are forbidden here.

Only existing public files and an audited allowlisted export are read. Optional
inspection cost is distinct from the source reads required by every execution.
"""
from datetime import datetime, timezone
from hashlib import sha256
from html import escape
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://yuu-honda.github.io/lux-spiria-results/'
DATA_FILE = 'data/experience-retention-2026-10-28.json'
STUDY = 'studies/2026-10-28-experience-retention/'
REPLAY = 'experiments/experience-retention-2026-10-28/'
ZIP_FILE = 'downloads/experience-retention-2026-10-28.zip'
ACTION_LOOP_SHA256 = '61495538507742ab5c3d55721a4115bf9fb24542b605525c63edc6b8f4cb7297'
PROTOCOL_SHA256 = '8d675c231d358b5412839fccd4829785920b867e48eab915f02cec141d37434a'
ARMS = ('no_experience', 'experience_record')
FORMATS = ('original', 'changed')
CATALOG = {'A01': ('X02', 'changed'), 'A02': ('X01', 'original'),
           'A03': ('X03', 'changed'), 'A04': ('X02', 'original'),
           'A05': ('X01', 'changed'), 'A06': ('X03', 'original')}
TRAINING_BINDINGS = {**{f'T{i:02}': (f'X{i:02}', f'X{i:02}', 'original') for i in range(1, 4)},
                     **{f'C{i:02}': (f'X{i:02}', f'X{i:02}', 'changed') for i in range(1, 4)}}
SOURCE_FILES = {
    'X01': {'public_path': 'data/shiori-event-adoption-2026-10-24.json', 'original_sha256': 'fc7bfaed1b721a8d6fb95609b8edaa74c8cce1a9d10a238cf4b85083fededffe'},
    'X02': {'public_path': 'data/shiori-event-compatibility-2026-10-22.json', 'original_sha256': 'da314ce28940785dac7b097f07ab028b378757f1af6efbfe32d7867be3c3c2bd'},
    'X03': {'public_path': 'data/shiori-retrieval-hypotheses-2026-10-21.json', 'original_sha256': '54c09696c06e5ddcc0031d73663fc4d46e82d3b79e8aa4223d15449d4edd7680'}}
SAMPLE = {'public_source_families': 3, 'training_unique_objectives': 3, 'training_initial_items': 6,
          'maximum_training_repairs': 6, 'immediate_unique_objectives': 3,
          'formats_per_objective': 2, 'immediate_items_per_arm': 6, 'arms': 2}
RESULT_FIELDS = {'execution_status', 'error', 'validation_status', 'artifact_sha256', 'prediction',
                 'prediction_agreement', 'canonical_characters', 'action_sha256', 'budget_exceeded'}
INSPECTION_FIELDS = {'raw_sha256', 'raw_bytes_read', 'returned_canonical_characters',
                     'observation_sha256', 'record_sha256'}
METRICS = ('attempts', 'accepted', 'rejected', 'artifacts_written', 'execution_errors', 'invalid_actions',
           'abstentions', 'budget_exceeded', 'predicted_accepted_failures', 'uncertain_predictions',
           'inspections', 'source_bytes_read', 'returned_canonical_characters', 'action_canonical_characters')
ERROR_TYPES = {'KeyError', 'IndexError', 'TypeError', 'ValueError', 'ZeroDivisionError', 'OverflowError',
               'InvalidAction', 'ExecutionError', 'ActionError', 'HarnessError', 'OSError',
               'FileNotFoundError', 'PermissionError', 'RuntimeError', 'JSONDecodeError'}
CLASSIFICATIONS = ('both_correct', 'corrected', 'regressed', 'both_wrong')
CHANGE_TYPES = ('conditional_update', 'confirmation', 'deferred')
SCOPE_TRUE = {'own_training_actions', 'same_training_context', 'per_arm_item_fresh_probe_context',
              'all12_policies_frozen_before_any_inspection', 'all12_actions_frozen_before_execution',
              'same_current_evidence_and_inspection_opportunity', 'record_frozen_before_probes',
              'fixed_paired_dispatch_order', 'engineered_format_change',
              'independent_input_review_approved', 'independent_final_audit_approved', 'review_template_requests_legacy_scope'}
SCOPE_FALSE = {'pre_supplied_current_schema', 'actual_format_label_supplied', 'probe_legacy_preservation_instruction',
               'probe_feedback_updates', 'probe_repairs', 'fresh_ai_regeneration_in_replay'}
PROVENANCE = {'action_loop_sha256', 'protocol_sha256', 'input_freeze_sha256', 'task_review_sha256',
              'training_results_sha256', 'memory_sha256', 'memory_freeze_sha256',
              'initial_policy_freeze_sha256', 'immediate_action_freeze_sha256', 'results_sha256',
              'final_audit_sha256', 'delayed_task_commitment_sha256', 'delayed_gold_commitment_sha256'}
TOP_FIELDS = {'schema_version', 'study_id', 'date', 'sample', 'sources', 'training', 'immediate',
              'counts', 'paired', 'memory', 'delay', 'scope', 'provenance', 'replay'}


def _keys(value, expected, where):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise ValueError(f'{where}: unexpected/missing public fields')


def _integer(value, where, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f'{where}: expected integer at least {minimum}')


def _digest(value, where):
    if not isinstance(value, str) or not re.fullmatch('[a-f0-9]{64}', value):
        raise ValueError(f'{where}: lowercase SHA-256 only')


def _result(row):
    _keys(row, RESULT_FIELDS, 'action result')
    status = row['execution_status']; validation = row['validation_status']
    if not isinstance(status, str) or status not in ('ok', 'unavailable', 'invalid_action', 'execution_error'):
        raise ValueError('Unsupported execution status')
    if not isinstance(validation, str) or validation not in ('accepted', 'rejected'):
        raise ValueError('Unsupported validation status')
    if status in ('invalid_action', 'execution_error'):
        _keys(row['error'], {'type', 'sha256'}, 'error')
        if not isinstance(row['error']['type'], str) or row['error']['type'] not in ERROR_TYPES:
            raise ValueError('Preserve an allowlisted actual exception class')
        _digest(row['error']['sha256'], 'canonical raw-error hash')
        if row['artifact_sha256'] is not None or validation != 'rejected':
            raise ValueError('Failed execution requires no artifact and rejected validation')
    else:
        if row['error'] is not None: raise ValueError('Completed execution requires null error')
        _digest(row['artifact_sha256'], 'artifact')
    if validation == 'accepted' and status != 'ok':
        raise ValueError('Numeric supported tasks require a completed artifact')
    prediction = row['prediction']
    if not isinstance(prediction, str) or prediction not in ('accepted', 'rejected', 'uncertain'):
        raise ValueError('Unsupported actual prediction')
    if prediction == 'uncertain':
        if row['prediction_agreement'] is not None: raise ValueError('Uncertain prediction agreement must remain null')
    elif type(row['prediction_agreement']) is not bool or row['prediction_agreement'] != (prediction == validation):
        raise ValueError('Prediction agreement does not recalculate')
    _integer(row['canonical_characters'], 'actual canonical action characters', 1)
    if type(row['budget_exceeded']) is not bool or row['budget_exceeded'] != (row['canonical_characters'] > 6000):
        raise ValueError('Action cap violation disagrees')
    _digest(row['action_sha256'], 'actual action')


def _inspection(row, family, fmt, sources):
    if row is None: return
    _keys(row, INSPECTION_FIELDS, 'inspection')
    for key in ('raw_sha256', 'observation_sha256', 'record_sha256'): _digest(row[key], 'inspection ' + key)
    if row['raw_sha256'] != sources[family][fmt + '_sha256']:
        raise ValueError('Inspection must read the assigned actual source/format digest')
    _integer(row['raw_bytes_read'], 'actual inspection raw bytes', 1)
    _integer(row['returned_canonical_characters'], 'actual inspection projection characters', 1)


def aggregate_attempts(attempts):
    """Each pair is (action result, optional actual inspection), including repairs."""
    total = {key: 0 for key in METRICS}
    for result, inspection in attempts:
        total['attempts'] += 1; total[result['validation_status']] += 1
        total['artifacts_written'] += int(result['artifact_sha256'] is not None)
        total['execution_errors'] += int(result['execution_status'] == 'execution_error')
        total['invalid_actions'] += int(result['execution_status'] == 'invalid_action')
        total['abstentions'] += int(result['execution_status'] == 'unavailable')
        total['budget_exceeded'] += int(result['budget_exceeded'])
        total['predicted_accepted_failures'] += int(result['prediction'] == 'accepted' and result['validation_status'] == 'rejected')
        total['uncertain_predictions'] += int(result['prediction'] == 'uncertain')
        total['action_canonical_characters'] += result['canonical_characters']
        if inspection is not None:
            total['inspections'] += 1
            total['source_bytes_read'] += inspection['raw_bytes_read']
            total['returned_canonical_characters'] += inspection['returned_canonical_characters']
    return total


def recalculate(training, immediate):
    counts = {'training': {}, 'immediate': {}}
    for fmt in FORMATS:
        rows = [row for row in training if row['format'] == fmt]
        counts['training'][fmt] = {
            stage: aggregate_attempts([(row[stage], row[stage + '_inspection']) for row in rows if row[stage] is not None])
            for stage in ('initial', 'repair')}
    for arm in ARMS:
        counts['immediate'][arm] = {
            fmt or 'all': aggregate_attempts([(row['result'], row['inspection']) for row in immediate
                                              if row['arm'] == arm and (fmt is None or row['format'] == fmt)])
            for fmt in (None, *FORMATS)}
    bound = {(row['arm'], row['id']): row for row in immediate}
    paired = []
    for i in range(1, 7):
        task = f'P{i:02}'; fmt = CATALOG[f'A{i:02}'][1]
        a, b = (bound[arm, task]['result']['validation_status'] == 'accepted' for arm in ARMS)
        paired.append({'id': task, 'format': fmt, 'classification': 'both_correct' if a and b else 'corrected' if b else 'regressed' if a else 'both_wrong'})
    return {'counts': counts, 'paired': paired}


def _clock(value, where):
    if type(value) not in (int, float):
        raise ValueError(where + ': positive finite Unix seconds required')
    try: finite = math.isfinite(value)
    except OverflowError as error: raise ValueError(where + ': Unix seconds outside finite range') from error
    if not finite or value <= 0:
        raise ValueError(where + ': positive finite Unix seconds required')


def _utc(value, seconds):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|\+00:00)', value):
        raise ValueError('UTC clock requires restricted RFC3339 timestamp')
    try: parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as error: raise ValueError('Invalid actual UTC clock') from error
    if abs(parsed.timestamp() - seconds) > .001: raise ValueError('UTC/Unix clocks disagree')


def validate_summary(d):
    _keys(d, TOP_FIELDS, 'summary')
    if type(d['schema_version']) is not int or d['schema_version'] != 1 or d['study_id'] != 'experience-retention-2026-10-28' or d['date'] != '2026-10-28':
        raise ValueError('Unexpected study identity')
    _keys(d['sample'], SAMPLE, 'sample')
    for key, value in SAMPLE.items():
        _integer(d['sample'][key], 'sample')
        if d['sample'][key] != value: raise ValueError('Frozen sample denominator differs')
    _keys(d['sources'], SOURCE_FILES, 'sources')
    for family, frozen in SOURCE_FILES.items():
        row = d['sources'][family]; _keys(row, {'public_path', 'original_sha256', 'changed_sha256'}, 'source')
        if any(row[key] != value for key, value in frozen.items()): raise ValueError('Frozen public source path/hash differs')
        _digest(row['changed_sha256'], 'engineered source digest')
        if row['changed_sha256'] == row['original_sha256']: raise ValueError('Engineered wrapper cannot equal original source bytes')
    if not isinstance(d['training'], list) or len(d['training']) != 6: raise ValueError('Retain all six training initials')
    seen = set()
    for row in d['training']:
        _keys(row, {'id', 'source', 'family', 'format', 'initial', 'repair', 'initial_inspection', 'repair_inspection'}, 'training')
        task = row['id']
        if not isinstance(task, str) or task not in TRAINING_BINDINGS or task in seen: raise ValueError('Training task binding missing/duplicate')
        if (row['source'], row['family'], row['format']) != TRAINING_BINDINGS[task]: raise ValueError('Frozen training source/family/format differs')
        _result(row['initial']); _inspection(row['initial_inspection'], row['family'], row['format'], d['sources'])
        if row['repair'] is not None:
            if row['initial']['validation_status'] != 'rejected': raise ValueError('Only a failed own initial permits one repair')
            _result(row['repair']); _inspection(row['repair_inspection'], row['family'], row['format'], d['sources'])
        elif row['repair_inspection'] is not None: raise ValueError('No repair means no repair inspection')
        seen.add(task)
    if not isinstance(d['immediate'], list) or len(d['immediate']) != 12: raise ValueError('Retain all twelve immediate probes')
    seen = set()
    for row in d['immediate']:
        _keys(row, {'arm', 'id', 'source', 'family', 'format', 'policy_decision', 'inspection', 'result'}, 'immediate')
        arm, task = row['arm'], row['id']
        if not isinstance(arm, str) or arm not in ARMS or not isinstance(task, str) or not re.fullmatch('P0[1-6]', task) or (arm, task) in seen:
            raise ValueError('Immediate arm/task binding missing/duplicate')
        source = 'A' + task[1:]
        if (row['source'], row['family'], row['format']) != (source, *CATALOG[source]): raise ValueError('Frozen probe source/family/format differs')
        if not isinstance(row['policy_decision'], str) or row['policy_decision'] not in ('inspect', 'submit'):
            raise ValueError('Unsupported frozen policy decision')
        if (row['policy_decision'] == 'inspect') != (row['inspection'] is not None): raise ValueError('Requested inspection and actual inspection must agree')
        _inspection(row['inspection'], row['family'], row['format'], d['sources']); _result(row['result'])
        seen.add((arm, task))
    expected = recalculate(d['training'], d['immediate'])
    def check_counts(actual, computed):
        _keys(actual, computed, 'counts')
        for key, value in computed.items():
            if isinstance(value, dict): check_counts(actual[key], value)
            else:
                _integer(actual[key], 'count')
                if actual[key] != value: raise ValueError('Every count/cost must recalculate from retained actual records')
    check_counts(d['counts'], expected['counts'])
    if not isinstance(d['paired'], list) or len(d['paired']) != 6: raise ValueError('Retain all six paired immediate outcomes')
    pairs = {row['id']: row for row in expected['paired']}; seen = set()
    for row in d['paired']:
        _keys(row, {'id', 'format', 'classification'}, 'paired')
        if not isinstance(row['id'], str) or row['id'] not in pairs or row['id'] in seen or row != pairs[row['id']]: raise ValueError('Paired classification does not recalculate')
        seen.add(row['id'])
    memory = d['memory']; _keys(memory, {'change_types', 'grounded', 'legacy_scope_preserved', 'canonical_characters', 'sha256'}, 'memory')
    for key in ('change_types', 'grounded', 'legacy_scope_preserved'):
        if not isinstance(memory[key], list) or len(memory[key]) != 3: raise ValueError('Memory retains exactly three family entries')
    if any(not isinstance(value, str) or value not in CHANGE_TYPES for value in memory['change_types']): raise ValueError('Preserve actual memory classifications')
    if any(type(value) is not bool for key in ('grounded', 'legacy_scope_preserved') for value in memory[key]): raise ValueError('Actual independent memory audit flags require booleans')
    _integer(memory['canonical_characters'], 'actual memory canonical characters', 1); _digest(memory['sha256'], 'actual memory')
    delay = d['delay']; _keys(delay, {'status', 'minimum_elapsed_seconds', 'clock_start_utc', 'clock_start_unix_seconds', 'not_before_utc', 'not_before_unix_seconds', 'planned_unique_objectives', 'planned_items_per_arm'}, 'delay')
    if delay['status'] != 'uncollected_pending': raise ValueError('This immutable phase-one publication cannot contain delayed results')
    for key, value in [('minimum_elapsed_seconds', 86400), ('planned_unique_objectives', 3), ('planned_items_per_arm', 6)]:
        _integer(delay[key], 'delay ' + key)
        if delay[key] != value: raise ValueError('Frozen delayed plan differs')
    for key in ('clock_start_unix_seconds', 'not_before_unix_seconds'): _clock(delay[key], key)
    _utc(delay['clock_start_utc'], delay['clock_start_unix_seconds']); _utc(delay['not_before_utc'], delay['not_before_unix_seconds'])
    if abs(delay['not_before_unix_seconds'] - delay['clock_start_unix_seconds'] - 86400) > .001: raise ValueError('Delayed not-before must equal actual memory-freeze clock plus 86400 seconds')
    _keys(d['scope'], SCOPE_TRUE | SCOPE_FALSE | {'provider_metadata'}, 'scope')
    for key in SCOPE_TRUE | SCOPE_FALSE:
        if type(d['scope'][key]) is not bool or d['scope'][key] != (key in SCOPE_TRUE): raise ValueError('Frozen role/interface/feedback boundary differs')
    if d['scope']['provider_metadata'] is not None: raise ValueError('Unverified provider metadata remains null')
    _keys(d['provenance'], PROVENANCE, 'provenance')
    for value in d['provenance'].values(): _digest(value, 'provenance')
    if d['provenance']['protocol_sha256'] != PROTOCOL_SHA256 or d['provenance']['action_loop_sha256'] != ACTION_LOOP_SHA256: raise ValueError('Frozen protocol/executor digest differs')
    if memory['sha256'] != d['provenance']['memory_sha256']: raise ValueError('Memory and provenance hash differ')
    _keys(d['replay'], {'manifest_sha256', 'readme_sha256', 'zip_sha256'}, 'replay')
    for value in d['replay'].values(): _digest(value, 'replay')
    return d


def load_summary(root=None):
    root = ROOT if root is None else root; path = root / DATA_FILE
    if not path.is_file(): raise FileNotFoundError('Audited experience-retention export unavailable; no publication writes')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result: raise ValueError('Duplicate public JSON field')
            result[key] = value
        return result
    def nonfinite(value): raise ValueError('Nonfinite public JSON number is forbidden')
    return validate_summary(json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique, parse_constant=nonfinite))


def optional_summary(root=None):
    root = ROOT if root is None else root
    return load_summary(root) if (root / DATA_FILE).is_file() else None


def require_public_inputs(root, d):
    for source in SOURCE_FILES.values():
        path = root / source['public_path']
        if not path.is_file() or sha256(path.read_bytes()).hexdigest() != source['original_sha256']: raise ValueError('Frozen original public source missing/changed')
    for relative, key in [(REPLAY + 'MANIFEST.json', 'manifest_sha256'), (REPLAY + 'README.md', 'readme_sha256'), (ZIP_FILE, 'zip_sha256')]:
        path = root / relative
        # macOS commonly resolves names case-insensitively; publication must
        # still match the exact Git filename required by the replay utility.
        if not path.is_file() or path.name not in {entry.name for entry in path.parent.iterdir()} or sha256(path.read_bytes()).hexdigest() != d['replay'][key]:
            raise ValueError('Audited MANIFEST/README/external ZIP missing, mis-cased or changed')


def t(ja, en, lang): return ja if lang == 'ja' else en


def label(arm, lang): return t('経験記録なし', 'No experience record', lang) if arm == ARMS[0] else t('同じ凍結した経験記録あり', 'Same frozen experience record', lang)


def selected_probe(d, arm, fmt=None): return [row for row in d['immediate'] if row['arm'] == arm and (fmt is None or row['format'] == fmt)]


def paired_counts(d, fmt=None): return {key: sum(row['classification'] == key for row in d['paired'] if fmt is None or row['format'] == fmt) for key in CLASSIFICATIONS}


def efficient_record_use(d):
    a, b = (d['counts']['immediate'][arm]['all'] for arm in ARMS)
    return a['accepted'] == b['accepted'] and b['inspections'] < a['inspections'] and all(b[key] <= a[key] for key in ('execution_errors', 'invalid_actions', 'abstentions'))


def finding(d, lang):
    a, b = (d['counts']['immediate'][arm]['all'] for arm in ARMS); p = paired_counts(d)
    text = f'<p>{t(f"同じ6項目の受理は、経験記録なし {a['accepted']}/6 → 記録あり {b['accepted']}/6。追加の構造確認は {a['inspections']}回 → {b['inspections']}回でした。", f"On the same six items, acceptance was {a['accepted']}/6 without the record → {b['accepted']}/6 with it. Additional schema inspections were {a['inspections']} → {b['inspections']}.", lang)}</p>'
    text += f'<p>{t(f"対応する項目では修正{p['corrected']}、後退{p['regressed']}。6項目は3つの新規目的を2形式で実行したもので、6つの独立した目的ではありません。", f"Paired items show {p['corrected']} corrected and {p['regressed']} regressed. Six items are three held-out objectives in two formats, not six independent objectives.", lang)}</p>'
    if a['accepted'] == b['accepted']:
        text += f'<p>{t("成果物の受理数は同じで、この標本では精度向上は確認できませんでした。", "Artifact acceptance was equal; this sample shows no accuracy gain.", lang)}</p>'
    if efficient_record_use(d):
        saved = a['inspections'] - b['inspections']
        text += f'<p><strong>{t(f"同じ6項目全体で、追加の構造確認が{saved}回少ない差でした。受理数を保ち、実行エラー・無効操作・棄権を増やさない、という条件での凍結記録全体の限定的な利用効果です。", f"Across the six matched items, there were {saved} fewer optional structural inspections. Equal acceptance with no added execution errors, invalid actions or abstentions meets the bounded benefit criterion for access to the whole frozen record.", lang)}</strong></p>'
    else:
        text += f'<p>{t("同じ受理数・少ない追加確認・追加エラーなし、という事前条件を満たす利用効果は、この標本では確認できませんでした。各指標の差を分けて読みます。", "The predeclared equal-acceptance/fewer-inspections/no-added-errors criterion was not met on this sample. Read each outcome and cost separately.", lang)}</p>'
    text += f'<p class="note">{t("追加確認が0回でも、総source I/Oが0という意味ではありません。両条件とも実行器が成果物を計算する際に指定ファイルを読みます。速度・token・計算量の節約は測っていません。", "Zero additional inspections does not mean zero total source I/O. In both arms, the executor reads the assigned file to calculate the artifact. Speed, token and compute savings were not measured.", lang)}</p>'
    return text


def table(caption, heads, rows, css=''):
    return f'<div class="table-wrap" role="region" tabindex="0" aria-label="{escape(caption, quote=True)}"><table class="{css}"><caption>{escape(caption)}</caption><thead><tr>' + ''.join(f'<th scope="col">{escape(str(v))}</th>' for v in heads) + '</tr></thead><tbody>' + ''.join('<tr><th scope="row">' + escape(str(row[0])) + '</th>' + ''.join(f'<td>{escape(str(v))}</td>' for v in row[1:]) + '</tr>' for row in rows) + '</tbody></table></div>'


def section(sid, kicker, title, body): return f'<section class="section" id="{sid}" aria-labelledby="{sid}-title"><div class="section-heading"><p class="eyebrow">{kicker}</p><h2 id="{sid}-title">{title}</h2></div>{body}</section>'


def render(lang, summary=None):
    if lang not in ('ja', 'en'): raise ValueError('Supported languages are ja and en')
    d = load_summary() if summary is None else validate_summary(summary)
    body = f'<div class="er-study"><section class="study-hero"><p class="kicker">STUDY / EXPERIENCE RECORD USE / IMMEDIATE</p><h1>{t("自分の実行経験を、<br>次の操作に使えるか。", "Can an AI use its own execution record<br>on the next task?", lang)}</h1><p class="lead">{t("AIが自分で選んだ操作を実行し、実際の結果から外部の経験記録を作りました。別の新しいAIコンテキストへその記録を渡すかどうかで、同じ新規目的の受理と、必要だと判断した追加の構造確認を比べます。", "An AI chose its own operations, saw actual execution outcomes and authored an external experience record. Fresh AI contexts received that record or no record, then faced the same held-out objectives. We compare artifact acceptance and optional additional schema inspection.", lang)}</p><p class="note">2026-10-28 · {t("直後の実行記録。24時間後の試験は未収集で、予約は結果ではありません。", "Immediate execution record. The ≥24-hour trial is uncollected; scheduling is not a result.", lang)}</p></section>'
    purpose = f'<p>{t("主比較は経験記録なし → 同じ凍結した経験記録ありです。現在の課題、opaque handle、出典群、実際のsource hash、任意の実ファイル確認機会は同じです。予め現在のschemaや形式の答えを渡しません。プローブ共通指示には旧形式維持の直接指示がありません。一方、経験記録のテンプレートは旧条件の適用範囲を尋ね、内容はAIが選びます。記録全体の有無を比較し、生の経験と追加レビューの効果を分離した比較ではありません。", "The causal comparison is no experience record → the same frozen experience record. Current tasks, opaque handles, source families, actual source digests and optional inspection opportunities are equal. No current schema/format answer is pre-supplied. The common probe instructions contain no direct legacy-preservation instruction; the experience-record template does ask for the applicability of earlier conditions, with content chosen by the AI. The intervention is access to the whole record; it does not isolate review from raw experience.", lang)}</p>'
    body += section('finding', '01 / QUESTION AND FINDING', t('正しさと、追加確認を別々に読む。', 'Read correctness and additional inspection separately.', lang), purpose + finding(d, lang))
    training = f'<ol class="er-sequence"><li>{t("1つの新しいAIコンテキストが、元形式3項目の初回操作と予測を自分で選び、実行前に固定。", "One fresh AI context chooses and freezes its own initial operations and predictions for three original-format items.", lang)}</li><li>{t("実結果を同じコンテキストへ返し、失敗した初回だけ最大1回修正。", "Actual outcomes return to that context; only failed initials permit at most one repair.", lang)}</li><li>{t("同じ3目的を意図した包み替え形式でも行い、自分で選ぶ初回操作・実結果・失敗時の最大1修正を保持。", "Repeat the same three objectives after engineered wrapping, retaining the actor’s own initial choices, outcomes and at most one repair per failed initial.", lang)}</li><li>{t("同じコンテキストが3出典群の経験記録を作り、実際に選んだ分類と根拠を凍結。失敗や更新分類は要求しない。", "That context authors and freezes three family entries with its actual classifications and grounding. Failures and update labels are not forced.", lang)}</li></ol>'
    training_rows = []
    for fmt in FORMATS:
        for stage in ('initial', 'repair'):
            r = d['counts']['training'][fmt][stage]
            training_rows.append([fmt, stage, r['attempts'], r['accepted'], r['execution_errors'], r['invalid_actions'], r['abstentions'], r['predicted_accepted_failures'], r['uncertain_predictions'], r['inspections']])
    training += table(t('本人が今回選んだ初回と、許された修正を全件保持。', 'Retain all own current initials and permitted repairs.', lang), ['Format', 'Stage', 'Attempts', 'Accepted', 'Exec error', 'Invalid', 'Abstention', 'Predicted accepted / failed', 'Uncertain', 'Inspection'], training_rows, 'er-wide')
    own_failures = sum(row['initial']['validation_status'] == 'rejected' for row in d['training'])
    repaired = sum(row['repair'] is not None and row['repair']['validation_status'] == 'accepted' for row in d['training'])
    training += f'<p>{t(f"本人の失敗した初回は{own_failures}件、実際の修正で受理へ変わったのは{repaired}件です。不確実という予測は、受理を断定して失敗した予測と区別します。", f"There were {own_failures} failed own initials, and {repaired} became accepted through actual repairs. An uncertain prediction is distinct from a confidently predicted acceptance that failed.", lang)}</p>'
    if own_failures == 0: training += f'<p class="note">{t("本人の初回失敗がなかったため、本人の誤りを修正する能力の証拠にはなりません。", "With no failed own initials, this provides no evidence of own-error correction.", lang)}</p>'
    training += f'<p>{t("元ファイルの値と型を保ち、payloadの下へ移す形式変更は意図した介入です。自然障害や自然な会話記憶ではありません。元の公開原本バイト列は変更しません。", "Moving unchanged parsed values/types under payload is an engineered format intervention, not a natural outage or natural dialogue memory. Original public-file bytes remain unchanged.", lang)}</p>'
    body += section('training', '02 / OWN ACTIONS AND ACTUAL FEEDBACK', t('自分で選び、実行し、失敗した場合だけ直す。', 'Choose, execute and repair only an actual failed initial.', lang), training)
    probes = f'<p>{t("直後の3つの新規目的を各2形式で実行し、各条件6項目。条件×項目ごとに別の新しいコンテキストを使い、計12コンテキストです。まず全12初期方策を確認結果の前に固定し、inspectを選んだ項目だけ実ファイルを確認。同じ項目コンテキストで行動を選び、全12行動を実行結果の前に固定しました。submitで選んだ操作は後から変えません。", "Three held-out immediate objectives are executed in two formats: six items per arm, each arm/item in a separate fresh context, 12 contexts total. All 12 initial policies freeze before any inspection output. Only requested inspections run, then the same item context chooses its action. All 12 actions freeze before execution outcomes; submitted initial actions remain locked.", lang)}</p>'
    probes += f'<p>{t("各項目は追加確認最大1回・行動1回。結果を見た再試行、probeの記録更新、他項目の会話共有はありません。奇数IDは記録なし→あり、偶数はあり→なしという固定順で、providerや時間の効果を相殺した保証ではありません。各操作で使えるsource aliasは指定1つに絞ります。", "Each item permits at most one inspection and one action, with no outcome-based retry, probe memory update or cross-item conversation. Fixed dispatch is no-record first on odd IDs and record first on even IDs; this does not establish provider/time counterbalancing. Each execution exposes only its assigned source alias.", lang)}</p>'
    rows = []
    for arm in ARMS:
        for fmt in ('all', *FORMATS):
            r = d['counts']['immediate'][arm][fmt]
            rows.append([label(arm, lang), fmt, f"{r['accepted']}/{r['attempts']}", r['execution_errors'], r['invalid_actions'], r['abstentions'], r['inspections'], r['source_bytes_read'], r['returned_canonical_characters']])
    probes += table(t('追加の構造確認に限った回数・読取バイト・返却文字数。総I/Oではない。', 'Counts, bytes and returned characters concern optional schema inspections only, not total I/O.', lang), ['Arm', 'Format', 'Accepted', 'Exec error', 'Invalid', 'Abstention', 'Inspections', 'Inspection raw bytes', 'Projection chars'], rows, 'er-wide')
    pairs = [[fmt or 'all', *paired_counts(d, fmt).values()] for fmt in (None, *FORMATS)]
    probes += table(t('同じ目的・同じ形式：記録なし → 記録あり。', 'Matched objective and format: no record → record.', lang), ['Format', 'Both correct', 'Corrected', 'Regressed', 'Both wrong'], pairs)
    body += section('immediate', '03 / FROZEN HELD-OUT PROBES', t('同じ課題に、記録を渡すかどうかを比べる。', 'Compare record access on the same held-out tasks.', lang), probes)
    m = d['memory']; memory = table(t('AIが選んだ分類と独立監査。1=確認、0=確認できず。', 'Actor-chosen labels and independent audit. 1=verified, 0=not verified.', lang), ['Family', 'Change type', 'Grounded', 'Legacy scope'], [[f'X{i+1:02}', change, int(m['grounded'][i]), int(m['legacy_scope_preserved'][i])] for i, change in enumerate(m['change_types'])])
    memory += f'<p>{t(f"記録は{m['canonical_characters']}/6000 canonical文字、超過{int(m['canonical_characters'] > 6000)}件。conditional_update {m['change_types'].count('conditional_update')}、confirmation {m['change_types'].count('confirmation')}、deferred {m['change_types'].count('deferred')}です。分類は実際の選択を保持し、更新や成長をコードが作りません。", f"The record has {m['canonical_characters']}/6000 canonical characters, with {int(m['canonical_characters'] > 6000)} cap violations: {m['change_types'].count('conditional_update')} conditional_update, {m['change_types'].count('confirmation')} confirmation and {m['change_types'].count('deferred')} deferred. Actual chosen labels are preserved; code does not author an update or growth.", lang)}</p>'
    total_attempts = 18 + sum(row['repair'] is not None for row in d['training'])
    memory += f'<p>{t(f"実行は全{total_attempts}項目（初回学習6＋修正{total_attempts-18}＋直後12）。provider要求数や独立した{total_attempts}目的を意味しません。canonical JSONはUnicode本文を保ち、キー順・整形空白だけをそろえて数えます。行動上限6000文字は両条件で同じですが、実際の入力長と確認回数は異なり、同じ計算量・速度・費用とは言えません。", f"There are {total_attempts} execution items (six training initials + {total_attempts-18} repairs + 12 immediate probes), not {total_attempts} provider requests or independent objectives. Canonical JSON retains Unicode string text while standardizing key order and formatting. Both arms share a 6000-character action cap, but actual input lengths and inspection choices differ; equal compute, latency or spend are unverified.", lang)}</p>'
    memory += table(t('実際の行動payload文字数と上限超過。超過だけでは不正解にしない。', 'Actual action payload characters and cap violations; overrun alone does not change correctness.', lang), ['Stage / arm', 'Attempts', 'Canonical action characters', 'Overruns'], [[label(arm, lang), d['counts']['immediate'][arm]['all']['attempts'], d['counts']['immediate'][arm]['all']['action_canonical_characters'], d['counts']['immediate'][arm]['all']['budget_exceeded']] for arm in ARMS])
    body += section('memory-cost', '04 / ACTUAL RECORD AND COSTS', t('記録の分類と、実行費用を混ぜない。', 'Keep record labels separate from measured costs.', lang), memory)
    delay = d['delay']; pending = f'<div class="boundary-box"><p><strong>{t("24時間後：未収集・結果なし。", "At least 24 hours later: uncollected, no results.", lang)}</strong></p><p>{t("3つの別目的×2形式×2条件の計画とgoldは先に固定しました。現在の公開物はコミットメントhashだけを持ち、将来の課題・gold・回答・成績を含みません。予約や時計の経過を実行結果として扱いません。", "Three further objectives × two formats × two arms were frozen in advance. This publication carries commitment hashes only, without future tasks, gold, answers or scores. Scheduling or elapsed time is not an execution result.", lang)}</p></div>'
    pending += f'<dl class="er-clock"><dt>{t("実際の記録凍結時刻 / UTC", "Actual record-freeze clock / UTC", lang)}</dt><dd>{escape(delay['clock_start_utc'])}</dd><dt>{t("実行可能になる最短時刻 / UTC", "Earliest allowed collection / UTC", lang)}</dt><dd>{escape(delay['not_before_utc'])}</dd></dl>'
    pending += f'<p>{t("実際に86400秒以上経過した後、別の研究root・日付・data・ページとして追加します。直後の本dataとページはその時点の未収集状態を保持します。同じ外部記録を新しいコンテキストで読み直す設計は外部保存と持ち運びの試験で、同じ主体の心理的保持、重み学習や忘却曲線の検証ではありません。", "After at least 86400 actual elapsed seconds, a separate research root, date, data file and page will append results. This immediate data/page keeps its at-publication pending state. Fresh contexts rereading the same external record tests external persistence and portability, not one subject’s psychological retention, weight learning or a forgetting curve.", lang)}</p>'
    body += section('delayed-pending', '05 / PROSPECTIVE DELAYED PHASE', t('予約と、観測された結果を分ける。', 'Separate a scheduled trial from an observed result.', lang), pending)
    detail = []
    for row in d['training']:
        for stage in ('initial', 'repair'):
            r = row[stage]
            if r is not None: detail.append(['training / ' + stage, row['id'], row['family'], row['format'], r['execution_status'], r['validation_status'], r['prediction'], '—' if r['prediction_agreement'] is None else int(r['prediction_agreement']), int(row[stage + '_inspection'] is not None), r['canonical_characters']])
    for row in d['immediate']:
        r = row['result']; detail.append([label(row['arm'], lang), row['id'], row['family'], row['format'], r['execution_status'], r['validation_status'], r['prediction'], '—' if r['prediction_agreement'] is None else int(r['prediction_agreement']), int(row['inspection'] is not None), r['canonical_characters']])
    records = '<details><summary>' + t('初回・修正・全12probeの実行記録', 'All initials, repairs and 12 probe execution records', lang) + '</summary>' + table(t('失敗・棄権・不確実な予測も残す。', 'Retain failed, abstaining and uncertain choices.', lang), ['Stage / arm', 'ID', 'Family', 'Format', 'Execution', 'Validation', 'Prediction', 'Agreement', 'Inspection', 'Characters'], detail, 'er-items') + '</details>'
    body += section('records', '06 / ALL ACTUAL ATTEMPTS', t('成功した操作だけを残さない。', 'Retain every actual attempt.', lang), records)
    limits = f'<p>{t("3つの既知の公開数値ファイル上の、意図した形式変更と人工的なtool interfaceの記述試験です。原本の値は公開済みで、事前接触や訓練での露出を除外できません。typed expected値と実成果物を機械的に比較し、コードが意味理解や心理的学習を採点するわけではありません。", "This is a descriptive engineered-format task over three known public numeric files and an artificial tool interface. Original values were previously public; prior exposure or training cannot be excluded. Code compares actual artifacts against typed expected values rather than grading semantic understanding or psychological learning.", lang)}</p>'
    limits += f'<p>{t("役割は同じhost上の読取指示で分け、OS隔離を保証しません。provider identity・設定・要求数・token・computeは未取得のnullです。自然な想起、同一主体の持続、特定のLRE/SHIORI機構、binary速度や網、native ChatGPT、全Wake/Emotion、生物学的な脳、AGI・意識の証明へ広げません。", "Roles share a host with read-allowlist instructions, not OS isolation. Provider identity, settings, requests, tokens and compute are unavailable and remain null. These results do not establish natural recall, continuous identity, a particular LRE/SHIORI mechanism, binary speed/graph effects, native ChatGPT, full Wake/Emotion, biological brains, AGI or consciousness.", lang)}</p>'
    limits += f'<p><a href="../../{DATA_FILE}">{t("全記録・集計JSON", "All records and aggregate JSON", lang)}</a></p><details><summary>{t("監査と遅延課題のコミットメントhash", "Audit and delayed-task commitment digests", lang)}</summary>' + table('SHA-256', ['Artifact', 'SHA-256'], [[key, d['provenance'][key]] for key in sorted(PROVENANCE)], 'er-digests') + '</details>'
    body += section('limits', '07 / LIMITS', t('外部の経験記録を使う、という範囲で読む。', 'Read this as use of an external experience record.', lang), limits)
    replay = f'<p>{t("公開原本、直後の課題・保存済み選択・確認記録・成果物・コードで、保存処理を再実行できます。新しいAI判断の再生成ではありません。将来の課題とgoldは含めません。過去8研究とそのdata・リプレイ・ダウンロード、4つの概要ストーリーは保持します。", "Public originals, immediate tasks, saved choices, inspection records, artifacts and code support deterministic replay. Replay does not regenerate fresh AI judgment or include future tasks/gold. Eight earlier studies/data/replays/downloads and four overview stories are preserved.", lang)}</p><div class="download-links"><a href="../../{REPLAY}README.md">{t("公開リプレイ手順", "Public replay instructions", lang)} ↗</a><a href="../../{ZIP_FILE}" download>ZIP ↓</a></div>'
    body += section('public-replay', '08 / PUBLIC REPLAY', t('保存された選択と実結果をたどる。', 'Trace saved choices and actual results.', lang), replay)
    return _document(lang, body + '</div>')


def _document(lang, body):
    title = t('経験記録の直後利用と未収集の遅延試験', 'Immediate experience-record use and pending delayed trial', lang)
    desc = t('自分で選んだ操作と実結果から凍結した経験記録。記録なし／ありで同じ12probeの受理・追加確認を比較し、24時間後は未収集として保持。', 'A frozen record of own operations and actual outcomes. Matched immediate probes compare record access, artifact acceptance and additional inspection; the ≥24-hour trial remains uncollected.', lang)
    canonical = BASE + STUDY + ('' if lang == 'ja' else 'en.html')
    results = '../../results.html' if lang == 'ja' else '../../results.en.html'; home = '../../index.html' if lang == 'ja' else '../../index.en.html'
    switch = ''.join(f'<a href="{href}" lang="{code}" hreflang="{code}"' + (' aria-current="page"' if lang == code else '') + f'>{name}</a>' for href, code, name in [('index.html', 'ja', '日本語'), ('en.html', 'en', 'EN')])
    return f'''<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title} — LUX SPIRIA Results</title><meta name="description" content="{desc}"><link rel="canonical" href="{canonical}"><link rel="alternate" hreflang="ja" href="{BASE+STUDY}"><link rel="alternate" hreflang="en" href="{BASE+STUDY}en.html"><link rel="alternate" hreflang="x-default" href="{BASE+STUDY}"><meta name="theme-color" content="#090d12"><meta property="og:type" content="website"><meta property="og:title" content="{title} — LUX SPIRIA Results"><meta property="og:description" content="{desc}"><meta property="og:url" content="{canonical}"><meta property="og:image" content="{BASE}assets/lux-symbol.png"><link rel="icon" type="image/png" sizes="32x32" href="../../assets/favicon-32.png"><link rel="apple-touch-icon" sizes="180x180" href="../../assets/apple-touch-icon.png"><link rel="manifest" href="../../{'site' if lang=='ja' else 'site.en'}.webmanifest"><link rel="stylesheet" href="../../site.css"><link rel="stylesheet" href="../../theme-dark.css"><link rel="stylesheet" href="experience-retention.css"></head><body><a class="skip-link" href="#main">{t('本文へ','Skip to content',lang)}</a><div class="page"><header class="masthead"><a class="brand" href="{results}" aria-label="LUX SPIRIA Results"><img src="../../assets/lux-symbol.png" alt="" width="44" height="44"><span class="brand-wordmark">LUX SPIRIA<span class="brand-subtitle">RESEARCH RESULTS</span></span></a><nav aria-label="{t('主なページ','Main navigation',lang)}"><a href="{results}#studies">{t('研究結果','Studies',lang)}</a><a href="#delayed-pending">{t('遅延試験は未収集','Delayed trial pending',lang)}</a><a href="{home}">{t('全体像','Overview',lang)}</a><span class="lang">{switch}</span></nav></header><main id="main">{body}</main><footer class="footer"><nav aria-label="{t('資料と規約','Resources and terms',lang)}"><a href="{home}">LUX SPIRIA</a><a href="../../LICENSE">License / LSP-1.0</a><a href="https://github.com/Yuu-Honda/lux-spiria-results">GitHub ↗</a></nav><small>IMMEDIATE RESULT RECORD / 2026-10-28 · DELAYED UNCOLLECTED</small></footer></div></body></html>'''


def build():
    d = load_summary(); require_public_inputs(ROOT, d)
    pages = {'index.html': render('ja', d), 'en.html': render('en', d)}
    destination = ROOT / STUDY; destination.mkdir(parents=True, exist_ok=True)
    for name, text in pages.items(): (destination / name).write_text(text, encoding='utf-8')
    return pages


if __name__ == '__main__':
    try: build()
    except (FileNotFoundError, ValueError) as error: raise SystemExit(str(error)) from error

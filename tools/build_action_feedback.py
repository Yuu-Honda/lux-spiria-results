"""Publish only an audited prospective action-feedback public export.

This module reads no actor/source-private research inputs. The absent/invalid
export path writes nothing. Counts are recalculated from all 33 public item rows;
unknown recursive fields, prose, enums and duplicate JSON keys are rejected.
"""
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://yuu-honda.github.io/lux-spiria-results/'
DATA_FILE = 'data/action-feedback-2026-10-27.json'
STUDY = 'studies/2026-10-27-action-feedback/'
REPLAY = 'experiments/action-feedback-2026-10-27/'
ZIP_FILE = 'downloads/action-feedback-2026-10-27.zip'
ARMS = ('prior_plan_only', 'raw_feedback', 'raw_feedback_and_review')
PRACTICE = tuple(f'P{i:02d}' for i in range(1, 7))
TRANSFER = tuple(f'T{i:02d}' for i in range(1, 7))
REPEATS = tuple(f'R{i:02d}' for i in range(1, 4))
LATER_ORDER = ('T01', 'R01', 'T02', 'T03', 'R02', 'T04', 'T05', 'R03', 'T06')
DISPATCH_ORDER = ('raw_feedback', 'raw_feedback_and_review', 'prior_plan_only')
SOURCE_IDS = ('D01', 'D02', 'D03')
SOURCE_FILES = {
    'D01': {'public_path': 'data/shiori-pilot-2026-10-13.json',
            'sha256': '5f1a09df554ac6a57b0ead347ae4f3bbd4ec9ed4866fc44e96f82926194f21c7'},
    'D02': {'public_path': 'data/shiori-cross-session-2026-10-21.json',
            'sha256': '09f075d9f84bfb336912946b6f268056e2c0b1b8fd6ca8e58eb28d3d1ab34c99'},
    'D03': {'public_path': 'data/working-memory-source-fixed-2026-10-24.json',
            'sha256': 'a7ce1a4553cd7b85f0780bf9f178c6940c2300461caaa90ade6025736f80a8b6'},
}
SOURCE_PATHS = {row['public_path'] for row in SOURCE_FILES.values()}
SAMPLE = {'sources': 3, 'practice': 6, 'practice_supported': 3,
          'practice_unavailable': 3, 'transfer': 6, 'transfer_supported': 3,
          'transfer_unavailable': 3, 'repeated_practice': 3,
          'later_tasks_per_arm': 9, 'later_arms': 3, 'total_actual_actions': 33}
DESIGN_COUNTS = {'action_canonical_character_cap': 6000,
                 'review_canonical_character_cap': 6000,
                 'practice_actor_contexts': 1, 'later_actor_contexts': 3,
                 'review_author_contexts': 1, 'later_actions_frozen_before_feedback': 27}
PROVENANCE = {'code_sha256', 'protocol_sha256', 'addendum_sha256',
              'input_freeze_sha256', 'practice_action_sha256',
              'later_action_freeze_sha256', 'memory_sha256',
              'results_sha256', 'final_audit_sha256'}
METHOD_TRUE = {'prospective_protocol_before_authoring_and_actions',
               'task_gold_and_sources_frozen_before_actions',
               'practice_actions_frozen_before_execution',
               'review_actual_ai_authored_after_feedback',
               'all_later_actions_frozen_before_feedback',
               'same_current_full_sources_tasks_dsl_and_caps',
               'fixed_common_later_task_order', 'fixed_arm_dispatch_order',
               'external_review_in_fresh_context', 'all_first_actions_retained',
               'mechanical_typed_artifact_validation',
               'source_only_actual_ai_task_and_gold_authoring',
               'instruction_separated_roles_same_host',
               'repeated_positive_objectives_exactly_match_practice',
               'public_saved_action_replay_available'}
METHOD_FALSE = {'counterbalanced_order', 'equal_input_lengths_verified',
                'equal_provider_compute_verified', 'continuous_actor_identity',
                'model_parameter_updates', 'fresh_ai_regeneration_in_replay',
                'engine_runs_in_browser'}
LIMITS_FALSE = {'unseen_source_file_transfer', 'natural_memory_verified',
                'semantic_memory_comprehension_verified',
                'population_accuracy_estimated', 'source_retrieval_tested',
                'shiori_graph_or_binary_speed_tested', 'full_wake_verified',
                'emotion_effect_verified', 'native_chatgpt_integration_tested',
                'biological_brain_verified', 'agi_or_consciousness_verified',
                'provider_or_time_effects_controlled'}
PROVIDER_FIELDS = {'model_identity', 'settings', 'request_count', 'token_compute'}
ITEM_FIELDS = {'arm', 'task_id', 'source', 'supported', 'artifact_status',
               'validator_accepted', 'execution_failure', 'schema_error',
               'artifact_written', 'prediction', 'canonical_output_characters',
               'action_sha256', 'artifact_sha256'}
METRICS = ('actions', 'supported', 'unavailable', 'correct_supported',
           'correct_abstention', 'incorrect_supported', 'incorrect_unavailable',
           'execution_failures', 'schema_errors', 'artifacts_written',
           'prediction_accepted', 'prediction_rejected', 'prediction_uncertain',
           'prediction_acceptance_matches', 'prediction_acceptance_mismatches',
           'canonical_output_characters', 'output_cap_violations')
STRATA = ('all', 'transfer', 'repeat')
PAIRS = {'feedback_to_review': ('raw_feedback', 'raw_feedback_and_review'),
         'prior_to_feedback': ('prior_plan_only', 'raw_feedback'),
         'prior_to_review': ('prior_plan_only', 'raw_feedback_and_review')}
PAIR_METRICS = ('actions', 'both_correct', 'corrected', 'regressed', 'both_incorrect')
COST_FIELDS = {'actions', 'contexts', 'input_packet_characters',
               'raw_output_characters', 'canonical_output_characters',
               'maximum_output_characters', 'output_cap_violations'}
MEMORY_FIELDS = {'entries', 'confirmations', 'revisions', 'deferred',
                 'canonical_characters', 'cap_violations', 'sha256'}
VERIFICATION_FLAGS = {'independent_code_audit_approved',
                      'independent_input_review_approved',
                      'independent_final_audit_approved',
                      'gold_unchanged_after_revision'}
VERIFICATION_COUNTS = {'pre_action_input_rejections': 1,
                       'conditional_instruction_revisions': 2,
                       'expected_artifact_fields_checked': 38}
TOP_FIELDS = {'schema_version', 'study_id', 'date', 'sample', 'design', 'sources',
              'provenance', 'method', 'limits', 'provider', 'items', 'practice',
              'arms', 'paired', 'costs', 'memory', 'verification', 'replay'}


def _keys(value, expected, where):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise ValueError(f'{where}: unexpected or missing public fields')


def _integer(value, where, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f'{where}: expected an integer at least {minimum}')


def _digest(value, where):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value):
        raise ValueError(f'{where}: expected SHA-256 only')


def _fixed_counts(value, expected, where):
    _keys(value, expected, where)
    for key, count in expected.items():
        _integer(value[key], where + '.' + key)
        if value[key] != count:
            raise ValueError(f'{where}.{key}: differs from the frozen design')


def _flags(value, true, false, where):
    _keys(value, true | false, where)
    for key in true | false:
        if type(value[key]) is not bool or value[key] != (key in true):
            raise ValueError(f'{where}.{key}: unsupported flag')


def phase(task_id):
    return 'practice' if task_id in PRACTICE else 'transfer' if task_id in TRANSFER else 'repeat'


def aggregate_items(items):
    """Recalculate additive public metrics from actual or in-memory test rows."""
    result = {key: 0 for key in METRICS}
    for item in items:
        supported, accepted = item['supported'], item['validator_accepted']
        result['actions'] += 1
        result['supported' if supported else 'unavailable'] += 1
        result[('correct_supported' if supported else 'correct_abstention') if accepted else
               ('incorrect_supported' if supported else 'incorrect_unavailable')] += 1
        result['execution_failures'] += int(item['execution_failure'])
        result['schema_errors'] += int(item['schema_error'])
        result['artifacts_written'] += int(item['artifact_written'])
        prediction = item['prediction']
        result['prediction_' + prediction] += 1
        if prediction != 'uncertain':
            result['prediction_acceptance_matches' if (prediction == 'accepted') == accepted else
                   'prediction_acceptance_mismatches'] += 1
        result['canonical_output_characters'] += item['canonical_output_characters']
        result['output_cap_violations'] += int(item['canonical_output_characters'] > 6000)
    return result


def paired_items(before, after):
    """Pair identical task IDs; public item rows guarantee joint consistency."""
    before = {item['task_id']: item for item in before}
    after = {item['task_id']: item for item in after}
    if set(before) != set(after):
        raise ValueError('paired: identical frozen task IDs are required')
    result = {key: 0 for key in PAIR_METRICS}
    for task_id in before:
        first, final = before[task_id]['validator_accepted'], after[task_id]['validator_accepted']
        result['actions'] += 1
        result['both_correct' if first and final else 'regressed' if first else
               'corrected' if final else 'both_incorrect'] += 1
    return result


def recalculate(items):
    """Build practice/arm/paired aggregates; never generate actions or meaning."""
    practice = [item for item in items if item['arm'] == 'practice']
    arms = {arm: {stratum: [item for item in items if item['arm'] == arm and
                          (stratum == 'all' or phase(item['task_id']) == stratum)]
                  for stratum in STRATA} for arm in ARMS}
    return {'practice': aggregate_items(practice),
            'arms': {arm: {stratum: aggregate_items(rows) for stratum, rows in parts.items()}
                     for arm, parts in arms.items()},
            'paired': {pair: {stratum: paired_items(arms[before][stratum], arms[after][stratum])
                              for stratum in STRATA}
                       for pair, (before, after) in PAIRS.items()}}


def _items(rows, repeat_mapping):
    if not isinstance(rows, list) or len(rows) != 33:
        raise ValueError('items: all 33 actual actions must be retained')
    bound = {}
    for row in rows:
        _keys(row, ITEM_FIELDS, 'item')
        arm, task = row['arm'], row['task_id']
        if arm not in ('practice', *ARMS) or not isinstance(arm, str):
            raise ValueError('item: unsupported arm')
        allowed = PRACTICE if arm == 'practice' else LATER_ORDER
        if not isinstance(task, str) or task not in allowed or (arm, task) in bound:
            raise ValueError('item: missing, duplicate or unsupported frozen task binding')
        if not isinstance(row['source'], str) or row['source'] not in SOURCE_IDS:
            raise ValueError('item: source aliases must be D01–D03')
        for key in ('supported', 'validator_accepted', 'execution_failure', 'schema_error', 'artifact_written'):
            if type(row[key]) is not bool:
                raise ValueError(f'item.{key}: expected boolean')
        if row['artifact_status'] not in ('artifact', 'source_unavailable', 'none') or not isinstance(row['artifact_status'], str):
            raise ValueError('item: unsupported artifact status')
        if row['prediction'] not in ('accepted', 'rejected', 'uncertain') or not isinstance(row['prediction'], str):
            raise ValueError('item: unsupported prediction')
        _integer(row['canonical_output_characters'], 'item output characters', 1)
        _digest(row['action_sha256'], 'item action digest')
        if row['artifact_written']:
            _digest(row['artifact_sha256'], 'item artifact digest')
        elif row['artifact_sha256'] is not None:
            raise ValueError('item: an unwritten artifact must have a null digest')
        if row['schema_error'] and row['execution_failure']:
            raise ValueError('item: schema and execution failure branches are exclusive')
        failed = row['schema_error'] or row['execution_failure']
        if failed:
            if row['artifact_written'] or row['artifact_status'] != 'none':
                raise ValueError('item: a failed action has no written artifact')
        elif not row['artifact_written'] or row['artifact_status'] not in ('artifact', 'source_unavailable'):
            raise ValueError('item: successful execution requires its written artifact/status')
        if row['validator_accepted'] and (row['execution_failure'] or row['schema_error'] or
                not row['artifact_written'] or row['artifact_status'] != ('artifact' if row['supported'] else 'source_unavailable')):
            raise ValueError('item: accepted artifact disagrees with support/execution/schema status')
        bound[arm, task] = row
    if set(bound) != {('practice', task) for task in PRACTICE} | {(arm, task) for arm in ARMS for task in LATER_ORDER}:
        raise ValueError('items: every practice and arm/task pair must occur once')
    for arm in ('practice', *ARMS):
        for stratum, tasks, expected_supported in (
                [('practice', PRACTICE, 3)] if arm == 'practice' else
                [('transfer', TRANSFER, 3), ('repeat', REPEATS, 3)]):
            if sum(bound[arm, task]['supported'] for task in tasks) != expected_supported:
                raise ValueError('items: frozen supported/unavailable denominators differ')
            for source in SOURCE_IDS:
                selected = [bound[arm, task] for task in tasks if bound[arm, task]['source'] == source]
                if len(selected) != (1 if stratum == 'repeat' else 2) or sum(row['supported'] for row in selected) != 1:
                    raise ValueError('items: each source must retain its supported and unavailable objective')
    for task in LATER_ORDER:
        if len({(bound[arm, task]['source'], bound[arm, task]['supported']) for arm in ARMS}) != 1:
            raise ValueError('items: task support/source binding differs between arms')
    positive_practice = {task for task in PRACTICE if bound['practice', task]['supported']}
    if set(repeat_mapping.values()) != positive_practice:
        raise ValueError('repeat_mapping: repeat all three positive practice objectives once')
    for repeat, original in repeat_mapping.items():
        if bound[ARMS[0], repeat]['source'] != bound['practice', original]['source']:
            raise ValueError('repeat_mapping: source binding changed from practice')
    return bound


def validate_summary(d):
    _keys(d, TOP_FIELDS, 'summary')
    if type(d['schema_version']) is not int or d['schema_version'] != 1 or d['study_id'] != 'action-feedback-2026-10-27' or d['date'] != '2026-10-27':
        raise ValueError('Unexpected study identity')
    _fixed_counts(d['sample'], SAMPLE, 'sample')
    _keys(d['design'], {*DESIGN_COUNTS, 'practice_task_order', 'later_task_order', 'arm_dispatch_order', 'repeat_mapping'}, 'design')
    _fixed_counts({key: d['design'][key] for key in DESIGN_COUNTS}, DESIGN_COUNTS, 'design counts')
    for key, order in [('practice_task_order', PRACTICE), ('later_task_order', LATER_ORDER), ('arm_dispatch_order', DISPATCH_ORDER)]:
        if not isinstance(d['design'][key], list) or d['design'][key] != list(order):
            raise ValueError('design: fixed order differs; this was not counterbalanced')
    repeat_mapping = d['design']['repeat_mapping']
    _keys(repeat_mapping, REPEATS, 'repeat_mapping')
    if any(not isinstance(value, str) or value not in PRACTICE for value in repeat_mapping.values()):
        raise ValueError('repeat_mapping: allowlisted practice task IDs only')
    _keys(d['sources'], SOURCE_IDS, 'sources')
    paths = []
    for alias, row in d['sources'].items():
        _keys(row, {'public_path', 'sha256'}, 'source')
        if not isinstance(row['public_path'], str) or row['public_path'] not in SOURCE_PATHS:
            raise ValueError('source: existing allowlisted public file path required')
        paths.append(row['public_path'])
        _digest(row['sha256'], 'source digest')
        if row != SOURCE_FILES[alias]:
            raise ValueError('source: frozen alias/path/raw-hash binding changed')
    if len(set(paths)) != 3:
        raise ValueError('sources: three distinct complete public files required')
    _keys(d['provenance'], PROVENANCE, 'provenance')
    for digest in d['provenance'].values():
        _digest(digest, 'provenance')
    _flags(d['method'], METHOD_TRUE, METHOD_FALSE, 'method')
    _flags(d['limits'], set(), LIMITS_FALSE, 'limits')
    _keys(d['provider'], PROVIDER_FIELDS, 'provider')
    if any(value is not None for value in d['provider'].values()):
        raise ValueError('provider: unavailable identity/settings/request/token-compute must remain null')
    _items(d['items'], repeat_mapping)
    calculated = recalculate(d['items'])
    for field in ('practice', 'arms', 'paired'):
        # Exact recursive shapes and integer types are checked independently;
        # dict equality alone would allow bools to masquerade as integer counts.
        def compare(value, expected, where):
            _keys(value, expected, where)
            for key, wanted in expected.items():
                if isinstance(wanted, dict):
                    compare(value[key], wanted, where + '.' + key)
                else:
                    _integer(value[key], where + '.' + key)
                    if value[key] != wanted:
                        raise ValueError(f'{where}.{key}: does not recalculate from all actual items')
        compare(d[field], calculated[field], field)
    _keys(d['costs'], ('practice', *ARMS), 'costs')
    for arm, row in d['costs'].items():
        _keys(row, COST_FIELDS, 'cost row')
        for field in COST_FIELDS:
            _integer(row[field], 'cost.' + field)
        items = [item for item in d['items'] if item['arm'] == arm]
        if row['actions'] != len(items) or row['contexts'] != 1:
            raise ValueError('costs: one context per actor; action records are not provider requests')
        if row['input_packet_characters'] < 1 or row['raw_output_characters'] < 1:
            raise ValueError('costs: actual input and raw output lengths required')
        if (row['canonical_output_characters'] != sum(item['canonical_output_characters'] for item in items) or
                row['maximum_output_characters'] != max(item['canonical_output_characters'] for item in items) or
                row['output_cap_violations'] != sum(item['canonical_output_characters'] > 6000 for item in items)):
            raise ValueError('costs: canonical item counts/maxima/overruns do not recalculate')
    memory = d['memory']
    _keys(memory, MEMORY_FIELDS, 'memory')
    for field in MEMORY_FIELDS - {'sha256'}:
        _integer(memory[field], 'memory.' + field)
    if memory['entries'] != 6 or sum(memory[key] for key in ('confirmations', 'revisions', 'deferred')) != 6:
        raise ValueError('memory: six actual AI entries partition into confirmation/revision/deferred')
    if memory['canonical_characters'] < 1 or memory['cap_violations'] != int(memory['canonical_characters'] > 6000):
        raise ValueError('memory: canonical review cap and actual violation flag disagree')
    _digest(memory['sha256'], 'memory digest')
    if memory['sha256'] != d['provenance']['memory_sha256']:
        raise ValueError('memory: provenance digest disagrees')
    v = d['verification']
    _keys(v, {*VERIFICATION_FLAGS, *VERIFICATION_COUNTS, 'controller_code_checks', 'controller_code_passed'}, 'verification')
    _flags({key: v[key] for key in VERIFICATION_FLAGS}, VERIFICATION_FLAGS, set(), 'verification flags')
    _fixed_counts({key: v[key] for key in VERIFICATION_COUNTS}, VERIFICATION_COUNTS, 'verification counts')
    for key in ('controller_code_checks', 'controller_code_passed'):
        _integer(v[key], 'verification.' + key)
    if v['controller_code_passed'] > v['controller_code_checks']:
        raise ValueError('verification: passed code checks exceed checks')
    _keys(d['replay'], {'readme_sha256', 'zip_sha256'}, 'replay')
    for digest in d['replay'].values():
        _digest(digest, 'replay')
    return d


def load_summary(root=None):
    root = ROOT if root is None else root
    path = root / DATA_FILE
    if not path.is_file():
        raise FileNotFoundError('Audited action-feedback export unavailable; no publication writes')
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate public JSON field')
            result[key] = value
        return result
    return validate_summary(json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique_object))


def optional_summary(root=None):
    root = ROOT if root is None else root
    return load_summary(root) if (root / DATA_FILE).is_file() else None


def require_public_inputs(root, d):
    """Actual builds bind unchanged public sources and the audited replay files."""
    for source in d['sources'].values():
        path = root / source['public_path']
        if not path.is_file() or sha256(path.read_bytes()).hexdigest() != source['sha256']:
            raise ValueError('An audited complete public source is missing or changed')
    for relative, field in [(REPLAY + 'README.md', 'readme_sha256'), (ZIP_FILE, 'zip_sha256')]:
        path = root / relative
        if not path.is_file() or sha256(path.read_bytes()).hexdigest() != d['replay'][field]:
            raise ValueError('Audited replay README/ZIP missing or changed; no publication writes')


def t(ja, en, lang):
    return ja if lang == 'ja' else en


def label(arm, lang):
    return {'practice': t('共通の練習', 'Shared practice', lang),
            'prior_plan_only': t('以前の計画だけ', 'Prior plan only', lang),
            'raw_feedback': t('実際のフィードバック', 'Raw execution feedback', lang),
            'raw_feedback_and_review': t('同じフィードバック＋AIレビュー', 'Same feedback + AI review', lang)}[arm]


def table(caption, heads, rows, css=''):
    return (f'<div class="table-wrap" role="region" tabindex="0" aria-label="{escape(caption, quote=True)}"><table class="{css}"><caption>{escape(caption)}</caption><thead><tr>' +
            ''.join(f'<th scope="col">{escape(str(value))}</th>' for value in heads) + '</tr></thead><tbody>' +
            ''.join('<tr><th scope="row">' + escape(str(row[0])) + '</th>' + ''.join(f'<td>{escape(str(value))}</td>' for value in row[1:]) + '</tr>' for row in rows) + '</tbody></table></div>')


def section(sid, kicker, title, body):
    return f'<section class="section" id="{sid}" aria-labelledby="{sid}-title"><div class="section-heading"><p class="eyebrow">{kicker}</p><h2 id="{sid}-title">{title}</h2></div>{body}</section>'


def finding(d, lang):
    """Data-derived observations; no improvement or failure is presumed."""
    pair = d['paired']['feedback_to_review']['all']
    result = f'<p>{t(f"同じ後続9課題で、フィードバックだけ → 同じフィードバック＋AIレビューへの変更により、検証に通るようになった課題は{pair['corrected']}件、通らなくなった課題は{pair['regressed']}件でした。", f"On the same nine later tasks, raw feedback → the same feedback plus AI review corrected {pair['corrected']} validator outcomes and regressed {pair['regressed']}.", lang)}</p>'
    if pair['corrected'] == pair['regressed'] == 0:
        result += f'<p><strong>{t("この標本では、レビューの追加によって、どの成果物が検証に通るかは変わりませんでした。", "On this sample, adding the review did not change which artifacts passed validation.", lang)}</strong></p>'
    practice = d['practice']
    if practice['correct_supported'] + practice['correct_abstention'] == 6:
        result += f'<p>{t("練習6件はすべて固定した契約に適合したため、失敗を経験して修正する学習は今回検査できませんでした。", "All six practice artifacts met the frozen contract, so learning through correction of practice errors could not be tested.", lang)}</p>'
    if all(d['arms'][arm]['all']['correct_supported'] == 6 and d['arms'][arm]['all']['correct_abstention'] == 3 for arm in ARMS):
        result += f'<p class="note">{t("後続課題は全3条件で対象あり6件の完了と対象なし3件の正しい棄権がそろいました。この設計課題での天井であり、自然な記憶や一般的な学習能力を示しません。", "All three arms completed six supported objectives and correctly abstained on three unavailable objectives. This is a ceiling on these engineered tasks, not evidence of natural memory or general learning ability.", lang)}</p>'
    return result


def outcome_table(rows, lang, caption):
    heads = [t('条件', 'Condition', lang), t('対象あり・正しい完了', 'Correct supported completion', lang),
             t('対象なし・正しい棄権', 'Correct unavailable abstention', lang),
             t('対象あり・不一致', 'Incorrect supported', lang), t('対象なし・不一致', 'Incorrect unavailable', lang),
             t('実行失敗', 'Execution failures', lang), t('schemaエラー', 'Schema errors', lang)]
    return table(caption, heads, [[name, f'{row["correct_supported"]} / {row["supported"]}',
                                  f'{row["correct_abstention"]} / {row["unavailable"]}' if row['unavailable'] else '—',
                                  row['incorrect_supported'], row['incorrect_unavailable'],
                                  row['execution_failures'], row['schema_errors']] for name, row in rows], 'af-outcomes')


def _paired_table(d, lang):
    rows = []
    for name, (before, after) in PAIRS.items():
        for stratum in STRATA:
            row = d['paired'][name][stratum]
            group = {'all': t('後続9件', 'All nine later tasks', lang),
                     'transfer': t('新しい目的6件', 'Six new objectives', lang),
                     'repeat': t('同じ練習目的3件', 'Three exact practice repeats', lang)}[stratum]
            rows.append([label(before, lang) + ' → ' + label(after, lang), group,
                         *[row[key] for key in PAIR_METRICS]])
    return table(t('同じtask IDを対応づけた結果。新しい目的と完全な反復を分ける。', 'Paired identical task IDs; new objectives and exact repeats remain separate.', lang),
                 [t('比較', 'Comparison', lang), t('層', 'Stratum', lang), t('課題', 'Tasks', lang),
                  t('両方正しい', 'Both correct', lang), t('修正', 'Corrected', lang),
                  t('後退', 'Regressed', lang), t('両方不一致', 'Both incorrect', lang)], rows, 'af-paired')


def _item_table(d, lang):
    rows = []
    for arm, tasks in [('practice', PRACTICE), *((arm, LATER_ORDER) for arm in DISPATCH_ORDER)]:
        bound = {item['task_id']: item for item in d['items'] if item['arm'] == arm}
        for task in tasks:
            item = bound[task]
            rows.append([label(arm, lang), task, item['source'],
                         t('あり', 'Supported', lang) if item['supported'] else t('なし', 'Unavailable', lang),
                         item['prediction'], t('適合', 'Accepted', lang) if item['validator_accepted'] else t('不一致', 'Rejected', lang),
                         item['artifact_status'], int(item['execution_failure']), int(item['schema_error']),
                         item['canonical_output_characters'], int(item['canonical_output_characters'] > 6000)])
    return table(t('保持した実際の全33行。予測と実行後の検証は別の列。', 'All 33 retained actual rows; prediction and post-execution validation are separate.', lang),
                 [t('条件', 'Condition', lang), 'Task', 'Source', t('対象', 'Support', lang),
                  t('AIの予測', 'AI prediction', lang), t('実際の検証', 'Actual validation', lang),
                  'Artifact status', t('実行失敗', 'Execution failure', lang), 'Schema error',
                  t('canonical文字数', 'Canonical characters', lang), t('上限超過', 'Cap overrun', lang)], rows, 'af-items')


def render(lang, summary=None):
    if lang not in ('ja', 'en'):
        raise ValueError('Supported languages are ja and en')
    d = load_summary() if summary is None else validate_summary(summary)
    title = t('予測し、実行し、<br>次の行動を比べる。', 'Predict. Execute.<br>Compare the next action.', lang)
    body = f'<div class="af-study"><section class="study-hero"><p class="kicker">STUDY / PROSPECTIVE ACTION FEEDBACK / v1</p><h1>{title}</h1><p class="lead">{t("公開済みの実データ3ファイルに対し、AIが数値の取り出し方・計算・棄権を選び、実際にJSON成果物を書きました。その結果を受けたAIレビューを追加すると、同じ新しい課題への行動は変わるかを調べた、範囲を絞った試験です。", "An AI chose paths, calculations or abstention over three real, previously published data files and wrote actual JSON artifacts. This bounded pilot asks whether adding an AI review of those results changes the next action on matched new tasks.", lang)}</p><p class="note"><time datetime="2026-10-27">2026-10-27</time> · {t("保存済みの実行記録。閲覧中にAIや実行エンジンは動きません。", "Stored execution record. Browsing runs neither an AI nor the execution engine.", lang)}</p></section>'
    purpose = f'<div class="boundary-box"><p>{t("主比較は、実際のフィードバックだけ → 同じフィードバック＋AIレビューです。以前の計画だけの条件は、フィードバックを明示的に与える違いをみる別の診断です。全条件に同じ現在の完全な公開ファイルを渡すので、前の行動を再計算することもできます。情報を隠した記憶試験ではありません。", "The primary comparison is raw execution feedback → the same feedback plus an AI review. Prior plan only is a separate diagnostic of explicit feedback access. Every arm receives the same current complete public files and can recompute earlier actions; this is not a hidden-information memory test.", lang)}</p></div>'
    purpose += finding(d, lang)
    body += section('purpose', '01 / PURPOSE', t('結果を見る前に、問いと行動を固定する。', 'Freeze the question and action before seeing results.', lang), purpose)
    steps = [
        (t('データと課題を固定', 'Freeze data and objectives', lang), t('3つの公開ファイル、課題の意味、期待する型付き成果物を実際のAIが確認し、行動前に固定。', 'Actual AI roles author and review objectives and expected typed artifacts against three public files before actions.', lang)),
        (t('予測して行動を選ぶ', 'Predict and choose an action', lang), t('新しいAI役割が練習6件で、get・sum・sub・divまたは対象なしを選び、検証結果を予測。', 'A fresh AI role chooses get, sum, sub, div or source-unavailable for six practice tasks and predicts validation.', lang)),
        (t('実ファイルへ書く', 'Write real artifacts', lang), t('コードが固定した公開ファイルを読み、選ばれたDSLを実行して、実際のJSON成果物を保存。', 'Code reads the frozen public files, executes the chosen DSL and saves actual JSON artifacts.', lang)),
        (t('実際の結果を返す', 'Return actual feedback', lang), t('実行結果と固定した期待値の型・値を比較。失敗を選別せず、成果物と検証結果を保持。', 'Compare actual artifact types and values with frozen expectations; retain artifacts and verdicts without selecting successes.', lang)),
        (t('AIが判断を振り返る', 'AI reviews its judgments', lang), t('別の新しいAI役割が、以前の判断・結果・確認または修正・理由・不確実性・次の検査を外部記録にする。', 'A different fresh AI role records prior judgment, outcome, confirmation or revision, reason, uncertainty and a future check.', lang)),
        (t('同じ後続課題を実行', 'Execute matched later tasks', lang), t('新しい目的6件と同じ練習目的3件を各条件で選ぶ。後続27行すべてを固定してから実行結果を返す。', 'Each arm acts on six new objectives and three exact practice repeats. Freeze all 27 later actions before returning any later outcome.', lang)),
    ]
    flow = '<ol class="af-flow">' + ''.join(f'<li><span aria-hidden="true">{index:02d}</span><h3>{head}</h3><p>{text}</p></li>' for index, (head, text) in enumerate(steps, 1)) + '</ol>'
    flow += f'<p>{t("6件の練習、各条件9件の後続課題で、実際の行動は計33件です。これは33回のprovider要求を意味しません。Pythonが決めるのはパスの解決・演算・書き込み・型付き期待値との機械的比較で、課題、予測、振り返りの意味内容を作ったのは実際のAIです。", "Six practice actions plus nine later actions in each of three arms make 33 actual actions, not 33 provider requests. Python resolves paths, calculates, writes files and mechanically compares typed expectations. Actual AI roles authored task meaning, predictions and the review.", lang)}</p>'
    body += section('sequence', '02 / ACTUAL EXECUTION', t('予測から、実際の書き込みと次の課題へ。', 'From prediction to real writes and the next objective.', lang), flow)
    arms = [
        (label('prior_plan_only', lang), t('練習課題・行動・予測。実行結果・検証・レビューは渡さない。', 'Practice tasks, actions and predictions; no execution outputs, validation or review.', lang)),
        (label('raw_feedback', lang), t('同じ練習課題・行動・予測に、実際の成果物・実行結果・検証を加える。', 'The same practice tasks, actions and predictions plus actual artifacts, execution outputs and validation.', lang)),
        (label('raw_feedback_and_review', lang), t('同一のフィードバック一式に、実際のAIが作った結果後の判断レビューを加える。', 'The identical feedback bundle plus an actual AI-authored post-outcome judgment review.', lang)),
    ]
    arm_content = table(t('主比較は2行目 → 3行目。共通の現在の原文と同じ9課題は全条件に渡す。', 'Primary comparison: second → third row. All arms receive the same current files and nine later tasks.', lang), [t('条件', 'Arm', lang), t('過去から渡すもの', 'Prior information supplied', lang)], arms, 'af-arms')
    arm_content += f'<p class="note">{t("全条件の課題順は T01, R01, T02, T03, R02, T04, T05, R03, T06。条件の開始順はフィードバック、フィードバック＋レビュー、以前の計画だけです。各条件1つの新しいAIコンテキストで、順序のカウンターバランスはしていません。providerや時刻の違いは制御できていません。", "Every arm used T01, R01, T02, T03, R02, T04, T05, R03, T06. Dispatch order was raw feedback, feedback + review, then prior plan only. There was one fresh AI context per arm and no counterbalancing. Provider and time effects remain uncontrolled.", lang)}</p>'
    body += section('arms', '03 / THREE ARMS', t('同じフィードバックに、レビューだけを足す。', 'Add the review to the same feedback.', lang), arm_content)
    results = outcome_table([(label('practice', lang), d['practice'])], lang, t('練習6件：対象あり3・対象なし3', 'Six practice tasks: three supported, three unavailable', lang))
    results += outcome_table([(label(arm, lang), d['arms'][arm]['transfer']) for arm in ARMS], lang, t('新しい目的6件：同じ公開ファイル上の対象あり3・対象なし3', 'Six new objectives over the same files: three supported, three unavailable', lang))
    results += outcome_table([(label(arm, lang), d['arms'][arm]['repeat']) for arm in ARMS], lang, t('完全に同じ練習目的3件：すべて対象あり', 'Three exact positive practice repeats; all supported', lang))
    results += f'<p class="note">{t("新しい目的は未見のファイルを意味しません。同じ3ファイル上の6つの異なる新規課題です。反復3件は同じ試行内での確認で、長期保持や自律的な想起の検査ではありません。実行失敗とschemaエラーは区別して記録し、対象ありの完了と対象なしの棄権は別の母数で示します。", "New objectives do not mean unseen files: there are six distinct new tasks over the same three files. The three repeats are within-run checks, not delayed retention or autonomous recall. Execution failures and schema errors are recorded separately; supported completion and unavailable abstention use different denominators.", lang)}</p>'
    results += _paired_table(d, lang)
    body += section('results', '04 / ARTIFACT RESULTS', t('新しい目的と、完全な反復を分けて読む。', 'Read new objectives separately from exact repeats.', lang), results)
    predictions = []
    for arm in ('practice', *ARMS):
        items = [item for item in d['items'] if item['arm'] == arm]
        for prediction in ('accepted', 'rejected', 'uncertain'):
            selected = [item for item in items if item['prediction'] == prediction]
            predictions.append([label(arm, lang), prediction, len(selected),
                                sum(item['validator_accepted'] for item in selected),
                                sum(not item['validator_accepted'] for item in selected)])
    pred = table(t('行動前の予測と、実際の機械的検証。校正能力の一般評価ではない。', 'Pre-action prediction versus actual mechanical validation; not a general calibration assessment.', lang),
                 [t('条件', 'Arm', lang), t('予測', 'Prediction', lang), t('件数', 'Items', lang),
                  t('実際に適合', 'Actually accepted', lang), t('実際に不一致', 'Actually rejected', lang)], predictions)
    pred += '<details><summary>' + t('実際の全33行を見る', 'Inspect all 33 actual rows', lang) + '</summary>' + _item_table(d, lang) + '</details>'
    body += section('predictions', '05 / PREDICTION AND OUTCOME', t('予測と、実行後の結果を区別する。', 'Distinguish predictions from observed results.', lang), pred)
    memory = d['memory']
    review = table(t('外部のAIレビュー6項目の実際の分類', 'Actual classifications of six external AI-review entries', lang),
                   [t('確認', 'Confirmations', lang), t('修正', 'Revisions', lang), t('保留', 'Deferred', lang),
                    t('canonical文字数 / 上限', 'Canonical characters / cap', lang), t('上限超過', 'Cap violations', lang)],
                   [[memory['confirmations'], memory['revisions'], memory['deferred'], f'{memory["canonical_characters"]} / 6000', memory['cap_violations']]])
    review += f'<p>{t("この記録は、フィードバック後に別の実際のAIが作った外部入力です。同一の連続した主体の変化やモデルのパラメータ更新ではありません。confirmationは判断の確認で、誤りの修正を意味しません。分類の原文根拠は独立監査し、公開リプレイにも記録します。", "The record is external input authored by a different actual AI after feedback. It is not a change in one continuous subject or a model-parameter update. A confirmation is not an error correction. Independent audit checks the classifications against the record, which is also included in public replay.", lang)}</p>'
    costs = []
    for arm in ('practice', *ARMS):
        row = d['costs'][arm]
        costs.append([label(arm, lang), row['actions'], row['contexts'], row['input_packet_characters'],
                      row['raw_output_characters'], row['canonical_output_characters'],
                      f'{row["maximum_output_characters"]} / 6000', row['output_cap_violations']])
    review += table(t('実際の入力長・生の出力長・項目別canonical JSON長は別の単位。', 'Actual input length, raw output length and per-item canonical JSON length are different units.', lang),
                    [t('条件', 'Arm', lang), t('行動', 'Actions', lang), t('コンテキスト', 'Contexts', lang),
                     t('入力文字数', 'Input characters', lang), t('生の出力文字数', 'Raw output characters', lang),
                     t('canonical合計', 'Canonical sum', lang), t('canonical最大 / 上限', 'Canonical max / cap', lang),
                     t('超過項目', 'Over-cap items', lang)], costs, 'af-costs')
    review += f'<p class="note">{t("各行動とレビューはそれぞれ6,000 canonical文字の許可上限です。canonical JSONはUnicodeを保ち、キー順と整形空白を揃え、文字列本文は変えません。上限超過だけを成果物の意味上の不一致にはしません。入力長は異なり、同じ上限でも計算量の一致は示せません。モデル識別・設定・provider要求数・token計算量は取得できずnullです。", "Actions and review each have a permitted cap of 6,000 canonical characters. Canonical JSON retains Unicode and standardizes keys and formatting without changing string text. Cap overrun alone is not an artifact-value error. Input lengths differ, and equal caps do not establish equal compute. Model identity, settings, provider request counts and token compute were unavailable and remain null.", lang)}</p>'
    body += section('review-costs', '06 / EXTERNAL REVIEW AND COST', t('判断の確認・修正と、入力長を記録する。', 'Record judgment confirmations, revisions and input length.', lang), review)
    sources = table(t('全条件へ同じ完全な公開ファイルを渡した。', 'Every arm received the same complete public files.', lang), ['Alias', t('公開ファイル', 'Public file', lang), 'SHA-256'],
                    [[key, value['public_path'], value['sha256']] for key, value in d['sources'].items()], 'af-digests')
    v = d['verification']
    sources += f'<p>{t(f"行動前の入力第1版は、対象なし2課題が測定済みであるかのように読めたため却下しました。P02/P04の条件付きの依頼文だけを修正し、期待する成果物は同じバイト列のままです。期待成果物の数値38項目を検査しました。コントローラーの工学的確認は{v['controller_code_passed']}/{v['controller_code_checks']}件で、独立したコード・入力・最終監査を通過しています。工学的確認は記憶精度ではありません。", f"The first pre-action input draft was rejected because two unavailable objectives presupposed a measurement. Only the conditional instruction wording for P02/P04 was revised; expected artifacts retained identical bytes. All 38 expected numeric fields were checked. Controller engineering checks passed {v['controller_code_passed']}/{v['controller_code_checks']}, with independent code, input and final audits approved. Engineering checks are not memory-accuracy measurements.", lang)}</p>'
    body += section('provenance', '07 / FROZEN INPUTS AND REVIEW', t('測定した実データと、行動前の修正を残す。', 'Retain the real data and pre-action correction.', lang), sources)
    limits = f'<div class="boundary-box"><p>{t("3つのschema出典と6つの異なる新規目的に限る、設計された数値処理の小規模な記述的試験です。型と数値の完全一致による検証は、この契約に適した機械的な採点であり、意味記憶の理解・自律的な判断・心理的な学習の実証ではありません。集団の正答率や統計的な優位性は推定しません。", "This is a small descriptive pilot of engineered numerical work over three schema sources and six distinct new objectives. Exact typed-value validation suits this contract; it does not demonstrate semantic memory comprehension, autonomous meaningful judgment or psychological learning. No population accuracy or statistical superiority is estimated.", lang)}</p></div>'
    limits += f'<p>{t("公開済みのファイルなので事前学習での接触は除外できません。役割への課題の配布前だけ目的を隠しました。全役割は同じhostで指示によりアクセスを分け、OSで隔離したものではありません。検索選択、SHIORIの網・二値処理の速度、全Wake、Emotion、ChatGPTへのnative統合、自然な記憶、生物学的な脳、AGI、意識は検証していません。", "Previously public files may have prior training exposure. Objectives were withheld only until each actor packet was delivered. Roles shared a host with instruction-limited access, not OS isolation. Source retrieval, SHIORI graph/binary speed, full Wake, Emotion, native ChatGPT integration, natural memory, biological brains, AGI and consciousness were not tested.", lang)}</p>'
    limits += f'<p><a href="../../{DATA_FILE}">{t("全33行と集計JSON", "All 33 rows and aggregate JSON", lang)}</a></p><details><summary>{t("監査用ハッシュ", "Audit digests", lang)}</summary>' + table('SHA-256', ['Artifact', 'SHA-256'], [[key, d['provenance'][key]] for key in sorted(PROVENANCE)], 'af-digests') + '</details>'
    body += section('limits', '08 / LIMITS', t('実行した行動と、まだ言えないことを分ける。', 'Separate executed actions from unverified claims.', lang), limits)
    replay = f'<p>{t("この公開データ作業台では、課題・固定した期待値・保存済みのAI行動・実際の結果・DSLコードを公開し、ローカルで決定的に再実行できます。保存済みの行動のリプレイであり、新しいAI生成や今回の標本を越えた再現ではありません。以前の6つの非公開会話研究の原文公開範囲は変わりません。", "This public-data workbench includes objectives, frozen expectations, saved AI actions, actual results and DSL code for deterministic local replay. It replays saved actions, not fresh AI generation or replication beyond this sample. Original-text publication boundaries of the six earlier private-conversation studies remain unchanged.", lang)}</p>'
    replay += f'<div class="download-links"><a href="../../{REPLAY}README.md">{t("公開リプレイの手順", "Public replay instructions", lang)} ↗</a><a href="../../{ZIP_FILE}" download>{t("リプレイ一式 / ZIP", "Replay bundle / ZIP", lang)} ↓</a></div>'
    body += section('public-replay', '09 / PUBLIC REPLAY', t('保存した行動を、公開データで確かめる。', 'Check saved actions against public data.', lang), replay)
    return _document(lang, body + '</div>')


def _document(lang, body):
    title = t('実行結果から次の行動を比べる', 'Compare the next action after execution feedback', lang)
    description = t('公開データ3ファイル上の実際の33行動。フィードバックとAIレビュー、同じ新規目的、完全反復、限界と公開リプレイ。', '33 actual actions over three public data files: feedback, AI review, matched new objectives, exact repeats, limits and public replay.', lang)
    canonical = BASE + STUDY + ('' if lang == 'ja' else 'en.html')
    results = '../../results.html' if lang == 'ja' else '../../results.en.html'
    home = '../../index.html' if lang == 'ja' else '../../index.en.html'
    languages = ''.join(f'<a href="{href}" lang="{code}" hreflang="{code}"' + (' aria-current="page"' if lang == code else '') + f'>{name}</a>' for href, code, name in [('index.html', 'ja', '日本語'), ('en.html', 'en', 'EN')])
    return f'''<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — LUX SPIRIA Results</title><meta name="description" content="{description}">
<link rel="canonical" href="{canonical}"><link rel="alternate" hreflang="ja" href="{BASE + STUDY}"><link rel="alternate" hreflang="en" href="{BASE + STUDY}en.html"><link rel="alternate" hreflang="x-default" href="{BASE + STUDY}">
<meta name="theme-color" content="#090d12"><meta property="og:type" content="website"><meta property="og:title" content="{title} — LUX SPIRIA Results"><meta property="og:description" content="{description}"><meta property="og:url" content="{canonical}"><meta property="og:image" content="{BASE}assets/lux-symbol.png">
<link rel="icon" type="image/png" sizes="32x32" href="../../assets/favicon-32.png"><link rel="apple-touch-icon" sizes="180x180" href="../../assets/apple-touch-icon.png"><link rel="manifest" href="../../{'site' if lang == 'ja' else 'site.en'}.webmanifest"><link rel="stylesheet" href="../../site.css"><link rel="stylesheet" href="../../theme-dark.css"><link rel="stylesheet" href="action-feedback.css">
</head><body><a class="skip-link" href="#main">{t('本文へ', 'Skip to content', lang)}</a><div class="page"><header class="masthead"><a class="brand" href="{results}" aria-label="LUX SPIRIA Results"><img src="../../assets/lux-symbol.png" alt="" width="44" height="44"><span class="brand-wordmark">LUX SPIRIA<span class="brand-subtitle">RESEARCH RESULTS</span></span></a><nav aria-label="{t('主なページ', 'Main navigation', lang)}"><a href="{results}#studies">{t('研究結果', 'Studies', lang)}</a><a href="#limits">{t('限界', 'Limits', lang)}</a><a href="{home}">{t('研究の全体像', 'Project overview', lang)}</a><span class="lang" aria-label="{t('表示言語', 'Language', lang)}">{languages}</span></nav></header><main id="main">{body}</main><footer class="footer"><nav aria-label="{t('資料と規約', 'Resources and terms', lang)}"><a href="{home}">LUX SPIRIA</a><a href="../../LICENSE">License / LSP-1.0</a><a href="https://github.com/Yuu-Honda/lux-spiria-results">GitHub ↗</a></nav><small>RESULT RECORD / 2026-10-27 · v1</small></footer></div></body></html>'''


def build():
    d = load_summary()
    require_public_inputs(ROOT, d)
    pages = {'index.html': render('ja', d), 'en.html': render('en', d)}
    destination = ROOT / STUDY
    destination.mkdir(parents=True, exist_ok=True)
    for name, html in pages.items():
        (destination / name).write_text(html, encoding='utf-8')
    return pages


if __name__ == '__main__':
    try:
        build()
    except (FileNotFoundError, ValueError) as error:
        raise SystemExit(str(error)) from error

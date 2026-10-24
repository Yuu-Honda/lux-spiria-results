"""Build the 2026-10-24 JA/EN study from an audited public export only.

This standalone builder reads exactly DATA_FILE, never private research inputs.
Missing data, unknown recursive fields, unsupported strings, or inconsistent
aggregates fail before an output directory or page is created. There is no
placeholder data and no integration with the overview or previous builders.

Contract constants below define the public export. Condition IDs are four ARMS
crossed with three VARIANTS, followed by the privileged source ceiling. Every
condition and both kinds of strata contain the same additive METRICS. The two
strata partitions independently recalculate every condition metric. They are
descriptive partitions of four source clusters, not independent replications.
"""
from html import escape
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = 'data/shiori-event-adoption-2026-10-24.json'
STUDY = 'studies/2026-10-24-event-adoption/'
BASE = 'https://yuu-honda.github.io/lux-spiria-results/'
ARMS = ('recovery_raw', 'strict_source_gate', 'event_review_only',
        'strict_and_event_review')
VARIANTS = ('normal', 'hops0', 'without_convergence')
CONDITIONS = tuple(f'{arm}:{variant}' for variant in VARIANTS for arm in ARMS) + ('designated_source_ceiling',)
KINDS = {'literal': 4, 'paraphrase': 12, 'confusable': 8, 'absent': 8}
CLUSTERS = ('C01', 'C02', 'C03', 'C04')
OUTCOMES = ('correct_supported', 'correct_abstention', 'partial_supported',
            'missed_answer', 'wrong_or_unsupported')
ERRORS = ('binding_errors', 'proposal_completion_errors',
          'unsupported_claim_items', 'mechanical_evidence_error_items',
          'retrieval_failures_for_supported_queries',
          'reader_unsupported_assertions',
          'reader_answer_use_failures_when_support_available')
METRICS = ('queries',) + OUTCOMES + ERRORS
DENOMINATORS = {'all_frozen_queries', 'supported_queries',
                'corpus_unsupported_queries', 'fully_supporting_supported_queries',
                'independent_source_clusters'}
SAMPLE = {'source_sessions': 4, 'whole_retained_messages': 95, 'queries': 32,
          'supported_queries': 16, 'corpus_unsupported_queries': 16}
SOURCE_INDEX = {'literal_witness_occurrences': 344,
                'unique_native_feature_entries': 284, 'canonical_concepts': 230}
PROVENANCE = {'protocol_sha256', 'source_selection_sha256', 'source_index_sha256',
              'query_freeze_sha256', 'reader_answer_pool_sha256',
              'primary_assessment_sha256', 'evaluation_sha256', 'final_audit_sha256'}
METHOD_TRUE = {'source_only_ai_indexing_and_review',
               'shared_unique_query_source_answers_reused',
               'saved_actual_ai_outputs_replayed',
               'source_ceiling_privileged', 'instruction_separated_roles_same_host'}
METHOD_FALSE = {'automatic_index_learning', 'fresh_ai_regeneration_tested',
                'source_ceiling_deployable'}
LIMITS_FALSE = {'external_source_audit_possible_from_public_data',
                'engine_rerun_possible_from_public_data', 'natural_daily_recall_verified',
                'biological_brain_verified', 'agi_verified', 'emotion_verified',
                'full_wake_verified'}
CALL_FIELDS = {'successful_reader_contexts', 'failed_collection_attempts',
               'actual_distinct_reader_calls_including_retained_attempts',
               'failed_output_call_metadata_unavailable', 'primary_assessor_calls',
               'final_audit_assessor_calls'}
REUSE_FIELDS = {'unique_query_source_answer_pool_items',
                'unique_answer_items_used_in_condition_lookups',
                'condition_answer_lookups', 'reused_condition_answer_lookups',
                'unique_mechanical_evidence_error_items'}
NATIVE_METRICS = {'positive_scene_at_1_hits', 'positive_wrong_scene_returns',
                  'positive_no_return', 'confusable_false_returns',
                  'confusable_no_return', 'absent_false_returns', 'absent_no_return'}
VERIFICATION_FIELDS = {'independent_audit_verified', 'code_engineering_checks',
                       'code_engineering_passed', 'synthetic_procedure_checks',
                       'synthetic_procedure_passed'}
TOP_FIELDS = {'schema_version', 'study_id', 'date', 'sample', 'source_index',
              'provenance', 'method', 'limits', 'calls', 'answer_reuse',
              'conditions', 'native_scene_diagnostics', 'secondary', 'verification'}


def _keys(value, expected, where):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise ValueError(f'{where}: unexpected or missing public fields')


def _integer(value, where):
    if type(value) is not int or value < 0:
        raise ValueError(f'{where}: expected a nonnegative integer')


def _fixed_counts(value, expected, where):
    _keys(value, expected, where)
    for key, count in expected.items():
        _integer(value[key], f'{where}.{key}')
        if value[key] != count:
            raise ValueError(f'{where}.{key}: disagrees with the frozen design')


def _flags(value, true_fields, false_fields, where):
    _keys(value, true_fields | false_fields, where)
    for key in true_fields | false_fields:
        if type(value[key]) is not bool or value[key] != (key in true_fields):
            raise ValueError(f'{where}.{key}: unsupported flag')


def _metrics(value, where):
    _keys(value, METRICS, where)
    for key in METRICS:
        _integer(value[key], f'{where}.{key}')
    if sum(value[key] for key in OUTCOMES) != value['queries']:
        raise ValueError(f'{where}: exclusive answer outcomes must sum to queries')
    # Every per-condition error is a flagged answer-item/query count, not the
    # number of atomic claims or entries in a mechanical-error list.
    for key in ERRORS:
        if value[key] > value['queries']:
            raise ValueError(f'{where}.{key}: query failure count exceeds queries')
    if value['reader_unsupported_assertions'] != value['unsupported_claim_items']:
        raise ValueError(f'{where}: unsupported-answer item diagnostics must agree')


def _strata(value, keys, row, where):
    _keys(value, keys, where)
    for key, metrics in value.items():
        _metrics(metrics, f'{where}.{key}')
    for metric in METRICS:
        if sum(part[metric] for part in value.values()) != row[metric]:
            raise ValueError(f'{where}: {metric} does not recalculate the condition')


def _conditions(rows):
    if not isinstance(rows, list) or len(rows) != len(CONDITIONS):
        raise ValueError('conditions: all 12 retrieval conditions and one ceiling required')
    seen = set()
    for row in rows:
        _keys(row, {'id', *METRICS, 'primary_denominators',
                    'query_kind_strata', 'source_cluster_strata'}, 'condition')
        cid = row['id']
        if not isinstance(cid, str) or cid not in CONDITIONS or cid in seen:
            raise ValueError('condition: expected unique allowlisted condition IDs')
        seen.add(cid)
        _metrics({key: row[key] for key in METRICS}, cid)
        if row['queries'] != 32:
            raise ValueError(f'{cid}: all frozen queries must be retained')
        den = row['primary_denominators']
        _keys(den, DENOMINATORS, 'primary_denominators')
        for key in DENOMINATORS:
            _integer(den[key], key)
        if any(den[key] != count for key, count in {
                'all_frozen_queries': 32, 'supported_queries': 16,
                'corpus_unsupported_queries': 16, 'independent_source_clusters': 4}.items()):
            raise ValueError(f'{cid}: primary denominators must retain the frozen design')
        available = den['fully_supporting_supported_queries']
        if available > 16 or row['reader_answer_use_failures_when_support_available'] > available:
            raise ValueError(f'{cid}: support-available denominator is inconsistent')
        if row['retrieval_failures_for_supported_queries'] > 16:
            raise ValueError(f'{cid}: retrieval failures exceed supported queries')
        _strata(row['query_kind_strata'], KINDS, row, 'query_kind_strata')
        _strata(row['source_cluster_strata'], CLUSTERS, row, 'source_cluster_strata')
        if any(part['queries'] != 8 for part in row['source_cluster_strata'].values()):
            raise ValueError('source_cluster_strata: all four frozen source clusters must retain eight queries')
        for kind, count in KINDS.items():
            part = row['query_kind_strata'][kind]
            if part['queries'] != count:
                raise ValueError('query_kind_strata: frozen kind denominator changed')
            positive = kind in ('literal', 'paraphrase')
            forbidden = ('correct_abstention',) if positive else (
                'correct_supported', 'partial_supported', 'missed_answer',
                'retrieval_failures_for_supported_queries',
                'reader_answer_use_failures_when_support_available')
            if any(part[key] for key in forbidden):
                raise ValueError('query_kind_strata: outcome does not match corpus support status')
        if sum(row[key] for key in ('correct_supported', 'partial_supported', 'missed_answer')) > 16 or row['correct_abstention'] > 16:
            raise ValueError(f'{cid}: supported/unsupported outcomes exceed their denominators')
    return {row['id']: row for row in rows}


def _native(rows):
    _keys(rows, CONDITIONS[:-1], 'native_scene_diagnostics')
    for cid, row in rows.items():
        _keys(row, NATIVE_METRICS, 'native_scene_diagnostics row')
        for key in NATIVE_METRICS:
            _integer(row[key], key)
        if sum(row[key] for key in ('positive_scene_at_1_hits', 'positive_wrong_scene_returns', 'positive_no_return')) != 16:
            raise ValueError('native_scene_diagnostics: supported scene outcomes must sum to 16')
        for kind in ('confusable', 'absent'):
            if row[f'{kind}_false_returns'] + row[f'{kind}_no_return'] != 8:
                raise ValueError(f'native_scene_diagnostics: {kind} outcomes must sum to 8')


def _secondary(value):
    """Optional actual diagnostics only; null means no reported measurement."""
    _keys(value, {'graph', 'timing', 'native_preparation'}, 'secondary')
    prep = value['native_preparation']
    if prep is not None:
        _keys(prep, {'primary_native_calls', 'independent_verification_native_calls',
                     'fresh_process_replay_equal', 'unique_query_candidate_pairs',
                     'candidate_count_distribution'}, 'native_preparation')
        for key in ('primary_native_calls', 'independent_verification_native_calls',
                    'unique_query_candidate_pairs'):
            _integer(prep[key], key)
        if type(prep['fresh_process_replay_equal']) is not bool:
            raise ValueError('native_preparation: replay comparison must be boolean')
        distribution = prep['candidate_count_distribution']
        if not isinstance(distribution, dict) or not distribution:
            raise ValueError('native_preparation: candidate distribution required')
        for key, count in distribution.items():
            if not isinstance(key, str) or not re.fullmatch(r'(0|[1-9][0-9]?)', key) or int(key) > 40:
                raise ValueError('native_preparation: candidate counts must be public integers 0–40')
            _integer(count, 'candidate distribution frequency')
        if sum(distribution.values()) != 32 or sum(int(key) * count for key, count in distribution.items()) != prep['unique_query_candidate_pairs']:
            raise ValueError('native_preparation: distribution must reconcile 32 queries and unique pairs')
    graph = value['graph']
    if graph is not None:
        _keys(graph, {'counting_unit', 'native_calls', 'graph_expansions',
                      'returned_path_segments', 'associated_hits', 'ablation_selection_changes'}, 'graph')
        if graph['counting_unit'] != 'normal_unique_native_route_executions':
            raise ValueError('graph: count normal routes only, without multiplying shared arms or ablations')
        for key in ('native_calls', 'graph_expansions', 'returned_path_segments', 'associated_hits'):
            _integer(graph[key], key)
        changes = graph['ablation_selection_changes']
        expected = {f'{arm}:{variant}' for arm in ARMS for variant in VARIANTS[1:]}
        _keys(changes, expected, 'ablation_selection_changes')
        for count in changes.values():
            _integer(count, 'changed selections')
            if count > 32:
                raise ValueError('graph: changed selections exceed frozen queries')
    timing = value['timing']
    if timing is not None:
        _keys(timing, {'measurement_scope', 'primary_native_wrapper_seconds',
                       'verification_native_wrapper_seconds'}, 'timing')
        if timing['measurement_scope'] != 'native_wrapper_excludes_ai_orchestration_index_build':
            raise ValueError('timing: unsupported measurement scope')
        for key in ('primary_native_wrapper_seconds', 'verification_native_wrapper_seconds'):
            elapsed = timing[key]
            if type(elapsed) not in (int, float) or not 0 <= elapsed < float('inf'):
                raise ValueError('timing: elapsed seconds must be finite and nonnegative')
        if prep is None or not prep['primary_native_calls'] or not prep['independent_verification_native_calls']:
            raise ValueError('timing: both actual native call counts are required')


def validate_summary(d):
    """Recursively allowlist and reconcile public data before any rendering."""
    _keys(d, TOP_FIELDS, 'summary')
    if (type(d['schema_version']) is not int or d['schema_version'] != 1 or
            d['study_id'] != 'shiori-event-adoption-2026-10-24' or d['date'] != '2026-10-24'):
        raise ValueError('Unexpected study identity')
    _fixed_counts(d['sample'], SAMPLE, 'sample')
    _fixed_counts(d['source_index'], SOURCE_INDEX, 'source_index')
    _keys(d['provenance'], PROVENANCE, 'provenance')
    for value in d['provenance'].values():
        if not isinstance(value, str) or not re.fullmatch('[a-f0-9]{64}', value):
            raise ValueError('provenance: named SHA-256 digests only')
    _flags(d['method'], METHOD_TRUE, METHOD_FALSE, 'method')
    _flags(d['limits'], set(), LIMITS_FALSE, 'limits')
    calls = d['calls']
    _keys(calls, CALL_FIELDS, 'calls')
    for key in CALL_FIELDS - {'actual_distinct_reader_calls_including_retained_attempts',
                               'failed_output_call_metadata_unavailable'}:
        _integer(calls[key], key)
    if calls['successful_reader_contexts'] != 4:
        raise ValueError('calls: four successful reader contexts are required')
    unavailable = calls['failed_output_call_metadata_unavailable']
    if type(unavailable) is not bool:
        raise ValueError('calls: metadata availability must be boolean')
    actual = calls['actual_distinct_reader_calls_including_retained_attempts']
    if actual is None:
        if not unavailable or not calls['failed_collection_attempts']:
            raise ValueError('calls: an unknown total requires retained failure metadata to be unavailable')
    else:
        _integer(actual, 'actual distinct reader calls')
        if actual < calls['successful_reader_contexts']:
            raise ValueError('calls: actual calls cannot be fewer than successful contexts')
    if unavailable and not calls['failed_collection_attempts']:
        raise ValueError('calls: unavailable failed-output metadata requires a failed attempt')
    if calls['primary_assessor_calls'] != 1:
        raise ValueError('calls: the primary assessment must remain separate from final audits')
    reuse = d['answer_reuse']
    _keys(reuse, REUSE_FIELDS, 'answer_reuse')
    for key in REUSE_FIELDS:
        _integer(reuse[key], key)
    used = reuse['unique_answer_items_used_in_condition_lookups']
    if (not 0 < used <= reuse['unique_query_source_answer_pool_items'] or
            reuse['condition_answer_lookups'] - used != reuse['reused_condition_answer_lookups']):
        raise ValueError('answer_reuse: reused lookups must reconcile with unique used items')
    if reuse['unique_mechanical_evidence_error_items'] > reuse['unique_query_source_answer_pool_items']:
        raise ValueError('answer_reuse: unique mechanical errors exceed unique pool items')
    _conditions(d['conditions'])
    if reuse['condition_answer_lookups'] != sum(row['queries'] for row in d['conditions']):
        raise ValueError('answer_reuse: condition lookups must cover all 13 frozen conditions')
    _native(d['native_scene_diagnostics'])
    _secondary(d['secondary'])
    v = d['verification']
    _keys(v, VERIFICATION_FIELDS, 'verification')
    if type(v['independent_audit_verified']) is not bool or not v['independent_audit_verified']:
        raise ValueError('verification: an independently audited export is required')
    for key in VERIFICATION_FIELDS - {'independent_audit_verified'}:
        _integer(v[key], key)
    for prefix in ('code_engineering', 'synthetic_procedure'):
        if v[prefix + '_passed'] > v[prefix + '_checks']:
            raise ValueError('verification: passes exceed engineering checks')
    return d


def load_summary():
    path = ROOT / DATA_FILE
    if not path.is_file():
        raise FileNotFoundError('Audited public summary is unavailable; no study pages were written')
    return validate_summary(json.loads(path.read_text(encoding='utf-8')))


def t(ja, en, lang):
    return ja if lang == 'ja' else en


def label(cid, lang):
    if cid == 'designated_source_ceiling':
        return t('指定原文の上限比較（特権的）', 'Designated-source ceiling (privileged)', lang)
    arm, variant = cid.split(':')
    name = {
        'recovery_raw': t('検索仮説・ゲートなし', 'Recovery retrieval · no gate', lang),
        'strict_source_gate': t('厳格な原文ゲート', 'Strict source gate', lang),
        'event_review_only': t('出来事の適合レビュー', 'Event compatibility review', lang),
        'strict_and_event_review': t('原文＋出来事レビュー', 'Source + event review', lang),
    }[arm]
    suffix = {'normal': t('通常', 'Normal', lang), 'hops0': 'hops=0',
              'without_convergence': 'convergence=false'}[variant]
    return name + ' / ' + suffix


def section(sid, eyebrow, title, body):
    return f'<section class="section" id="{sid}" aria-labelledby="{sid}-title"><div class="section-heading"><p class="eyebrow">{eyebrow}</p><h2 id="{sid}-title">{title}</h2></div>{body}</section>'


def table(caption, heads, rows, css=''):
    def cell(value):
        return escape(str(value))
    return (f'<div class="table-wrap" role="region" tabindex="0" aria-label="{escape(caption, quote=True)}"><table class="{css}">'
            f'<caption>{cell(caption)}</caption><thead><tr>' +
            ''.join(f'<th scope="col">{cell(value)}</th>' for value in heads) +
            '</tr></thead><tbody>' + ''.join('<tr><th scope="row">' + cell(row[0]) +
            '</th>' + ''.join(f'<td>{cell(value)}</td>' for value in row[1:]) + '</tr>' for row in rows) +
            '</tbody></table></div>')


def _outcome_table(rows, lang, caption, name=lambda row: row['id']):
    heads = [t('条件・層', 'Condition / stratum', lang), t('質問', 'Queries', lang),
             t('根拠あり・正答', 'Correct supported', lang),
             t('正しい棄権', 'Correct abstention', lang),
             t('根拠あり・部分回答', 'Partial supported', lang),
             t('回答を逃した', 'Missed answer', lang),
             t('誤り・根拠なし', 'Wrong / unsupported', lang)]
    return table(caption, heads, [[name(row), *[row[key] for key in ('queries',) + OUTCOMES]] for row in rows], 'answer-table')


def _error_table(rows, lang, caption):
    heads = [t('条件', 'Condition', lang), t('指示対象の取り違え', 'Binding errors', lang),
             t('提案・完了の取り違え', 'Proposal / completion errors', lang),
             t('根拠のない主張項目', 'Unsupported claim items', lang),
             t('機械的な証拠エラー項目', 'Mechanical evidence error items', lang),
             t('対象ありの検索失敗 / 16', 'Supported retrieval failures / 16', lang),
             t('readerの根拠なし断言', 'Reader unsupported assertions', lang),
             t('十分な原文あり・回答利用失敗 / その母数', 'Answer-use failures / fully supporting queries', lang)]
    values = []
    for row in rows:
        den = row['primary_denominators']['fully_supporting_supported_queries']
        values.append([label(row['id'], lang), *[row[key] for key in ERRORS[:-1]],
                       f"{row[ERRORS[-1]]} / {den}"])
    return table(caption, heads, values, 'error-table')


def _chart(rows, lang):
    caption = t('通常4条件。正答は根拠あり16問、正しい棄権は対象なし16問を別々に表示。',
                'Four normal conditions. Correct supported answers and correct abstentions each have a separate denominator of 16.', lang)
    bars = []
    for row in rows:
        parts = []
        for key, ja, en in [('correct_supported', '根拠あり・正答', 'Correct supported'),
                            ('correct_abstention', '正しい棄権', 'Correct abstention')]:
            count = row[key]
            parts.append(f'<div class="adoption-bar"><span>{t(ja, en, lang)}</span><span class="adoption-track" aria-hidden="true"><span style="width:{count / 16 * 100:.4f}%"></span></span><strong>{count} / 16</strong></div>')
        bars.append(f'<li><h3>{escape(label(row["id"], lang))}</h3>{"".join(parts)}</li>')
    return f'<figure class="adoption-chart"><figcaption>{caption}</figcaption><ol>{"".join(bars)}</ol></figure>'


def _result_interpretation(rows, lang):
    raw, strict, event, combined = (rows[f'{arm}:normal'] for arm in ARMS)
    complete_ja = f'通常条件の根拠ある完全回答は、ゲートなし{raw["correct_supported"]}/16、出来事レビュー単独{event["correct_supported"]}/16、厳格な原文ゲート{strict["correct_supported"]}/16、原文＋出来事レビュー{combined["correct_supported"]}/16でした。厳格ゲートと併用条件の回答の取り逃しは、それぞれ{strict["missed_answer"]}/16と{combined["missed_answer"]}/16です。'
    complete_en = f'Complete supported answers in normal execution were {raw["correct_supported"]}/16 without a gate, {event["correct_supported"]}/16 with event review alone, {strict["correct_supported"]}/16 with the strict source gate and {combined["correct_supported"]}/16 with both. The strict and combined conditions missed {strict["missed_answer"]}/16 and {combined["missed_answer"]}/16 supported answers, respectively.'
    abstentions = [row['correct_abstention'] for row in rows.values()]
    assertions = [row['reader_unsupported_assertions'] for row in rows.values()]
    def span(values):
        return str(min(values)) if min(values) == max(values) else f'{min(values)}–{max(values)}'
    negative_ja = f'全13条件の正しい棄権は{span(abstentions)}/16、根拠なし断言のある回答項目は{span(assertions)}/32でした。これらは全体の無誤りを意味しません。根拠のある質問への部分回答や取り逃しは別に評価します。'
    negative_en = f'Across all 13 conditions, correct abstentions were {span(abstentions)}/16 and answer items flagged for unsupported assertions were {span(assertions)}/32. These figures do not mean zero errors overall: partial and missed supported answers are assessed separately.'
    return f'<p>{t(complete_ja, complete_en, lang)}</p><p class="note">{t(negative_ja, negative_en, lang)}</p>'


def _unchanged_ablation_answer_counts(rows):
    return sum(all(rows[f'{arm}:{variant}'][key] == rows[f'{arm}:normal'][key]
                   for key in OUTCOMES)
               for arm in ARMS for variant in VARIANTS[1:])


def render(lang, summary=None):
    if lang not in ('ja', 'en'):
        raise ValueError('Supported languages are ja and en')
    d = load_summary() if summary is None else validate_summary(summary)
    rows = {row['id']: row for row in d['conditions']}
    normal = [rows[f'{arm}:normal'] for arm in ARMS]
    all_rows = [rows[cid] for cid in CONDITIONS]
    body = f'''<div class="adoption-study"><section class="study-hero"><p class="kicker">STUDY / EVENT ANSWER ADOPTION / v1</p><h1>{t('取り出した原文を、<br>回答へ正しく使えたか。', 'Was retrieved source evidence<br>used correctly in answers?', lang)}</h1><p class="lead">{t('実会話4件・全95メッセージと、固定した新規32問。検索の場面選択に加え、保存済みの実際のAI回答を、根拠ある正答・正しい棄権・部分回答・回答の取り逃し・誤りや根拠のない回答に分けて評価しました。', 'Four archived conversations, all 95 retained messages, and 32 frozen new queries. Alongside source-scene selection, saved actual AI answers were assessed as correct supported answers, correct abstentions, partial supported answers, missed answers, or wrong or unsupported answers.', lang)}</p><p class="note"><time datetime="2026-10-24">2026-10-24</time> · {t('保存済みの実行記録。閲覧中にAIや検索エンジンは動きません。', 'Stored execution record. Browsing runs neither an AI nor the retrieval engine.', lang)}</p></section>'''
    result = _chart(normal, lang)
    result += _outcome_table(normal, lang, t('通常4条件の回答評価。各行は32問。', 'Answer assessment for all four normal conditions; 32 queries per row.', lang), lambda row: label(row['id'], lang))
    result += f'<p class="note">{t("5つの回答結果は排他的で、各行の合計は32です。根拠ある正答の母数は16、正しい棄権の母数はコーパス内に対象がない16。別々の母数を総合点へ合算しません。検索の誤返却と、根拠のない回答は別の指標です。", "The five exclusive answer outcomes sum to 32 per row. Correct supported answers use 16 supported queries; correct abstentions use 16 corpus-unsupported queries. These denominators are not pooled into one score. False retrieval returns and unsupported answers are different measurements.", lang)}</p>'
    result += _result_interpretation(rows, lang)
    body += section('answers', '01 / ANSWER OUTCOMES', t('回答の正しさを、検索と分けて測る。', 'Measure answer correctness separately from retrieval.', lang), result)
    errors = _error_table(normal, lang, t('通常条件の失敗診断。指標同士は重複しうる。', 'Normal-condition failure diagnostics; metrics may overlap.', lang))
    errors += f'<p>{t("各エラーは、そのフラグが付いた回答項目・質問の数です。主張の個数や機械的エラー一覧の長さではありません。各条件の母数は32問、対象ありの検索失敗は16問。readerの根拠なし断言は、同じ根拠なし主張フラグを数えるため、根拠のない主張項目と同数です。エラー同士を足して失敗質問数にしません。十分な原文があるときの回答利用失敗は、その原文が利用可能だった対象あり質問だけを母数にします。", "Each error counts flagged answer items / queries, not atomic claims or entries in a mechanical-error list. Per-condition errors use 32 queries; supported retrieval failures use 16. Reader unsupported assertions count the same unsupported-claim flag and therefore equal unsupported-claim items. Error columns must not be added into a failed-query total. Answer-use failure uses only supported queries with fully supporting source material available as its denominator.", lang)}</p>'
    body += section('failures', '02 / FAILURE DIAGNOSTICS', t('原文への到達と、原文の使い方。', 'Reaching source material and using it.', lang), errors)
    ablations = [rows[f'{arm}:{variant}'] for variant in VARIANTS[1:] for arm in ARMS]
    abl = _outcome_table(ablations, lang, t('同じ32問・保存済み回答での全8無効化条件', 'All eight ablation conditions on the same 32 queries and saved answers', lang), lambda row: label(row['id'], lang))
    abl += _error_table(ablations, lang, t('全8無効化条件の失敗診断', 'Failure diagnostics for all eight ablation conditions', lang))
    abl += f'<p class="note">{t("通常・hops=0・convergence=falseの3条件を全4方式で報告します。回答は条件ごとに新しく生成したものではなく、同じ質問と選択原文の組合せに対応する保存済みの実際の回答を再利用します。差はこの固定標本の診断です。", "All four arms report normal, hops=0 and convergence=false variants. Answers were not newly generated for each condition: the same saved actual answer for a unique query/source pair is reused. Differences are diagnostics on this frozen sample.", lang)}</p>'
    unchanged = _unchanged_ablation_answer_counts(rows)
    ablation_ja = f'全8無効化条件のうち{unchanged}/8条件で、5分類の回答結果の件数は対応する通常実行と同じでした。これは集計の一致であり、公開JSONだけから各質問の回答の同一性までは確認できません。'
    ablation_en = f'In {unchanged}/8 ablation conditions, all five answer-outcome counts matched the corresponding normal execution. This is aggregate agreement; public JSON alone does not establish answer identity for each query.'
    abl += f'<p>{t(ablation_ja, ablation_en, lang)}</p>'
    body += section('ablations', '03 / ALL ABLATIONS', t('網と合流を止めた結果も残す。', 'Retain graph and convergence ablations.', lang), abl)
    ceiling = [rows['designated_source_ceiling']]
    ceil = f'<div class="boundary-box"><p>{t("指定原文の上限比較は、著者が関連づけた原文を特権的に与える診断です。数学的な上界や最大精度の保証ではありません。検索できたことや、運用可能な検索方式の性能を意味しません。通常の検索4方式の順位づけには含めません。", "The designated-source ceiling supplies the author-associated source as a privileged diagnostic. It is not a mathematical upper bound or a guarantee of maximum accuracy. It does not demonstrate successful retrieval or a deployable retrieval policy. It is excluded from rankings of the four retrieval arms.", lang)}</p></div>'
    ceil += _outcome_table(ceiling, lang, t('特権的な指定原文の上限比較', 'Privileged designated-source ceiling', lang), lambda row: label(row['id'], lang))
    ceil += _error_table(ceiling, lang, t('特権的な上限比較の失敗診断', 'Failure diagnostics for the privileged ceiling', lang))
    ceiling_row = ceiling[0]
    ceiling_ja = f'指定原文を与えた診断でも、対象あり16問の完全回答は{ceiling_row["correct_supported"]}/16、部分回答は{ceiling_row["partial_supported"]}/16、取り逃しは{ceiling_row["missed_answer"]}/16でした。原文が与えられることと、要求をすべて満たして答えられることは別です。'
    ceiling_en = f'With the designated source supplied, the privileged diagnostic produced {ceiling_row["correct_supported"]}/16 complete supported answers, {ceiling_row["partial_supported"]}/16 partial answers and {ceiling_row["missed_answer"]}/16 missed answers. Receiving a source is separate from satisfying every requirement of the query.'
    ceil += f'<p>{t(ceiling_ja, ceiling_en, lang)}</p>'
    body += section('ceiling', '04 / PRIVILEGED CEILING', t('原文を与えても残る失敗を調べる。', 'Inspect failures when designated source evidence is supplied.', lang), ceil)
    native = []
    for cid in CONDITIONS[:-1]:
        row = d['native_scene_diagnostics'][cid]
        native.append([label(cid, lang), f"{row['positive_scene_at_1_hits']} / 16",
                       f"{row['positive_wrong_scene_returns']} / 16",
                       f"{row['positive_no_return']} / 16",
                       f"{row['confusable_false_returns']} / 8",
                       f"{row['confusable_no_return']} / 8",
                       f"{row['absent_false_returns']} / 8",
                       f"{row['absent_no_return']} / 8"])
    nat = table(t('検索12条件の場面選択。特権的な上限比較は検索ではないため含めない。', 'Scene selection for 12 retrieval conditions. The privileged ceiling is not retrieval and is excluded.', lang),
                [t('条件', 'Condition', lang), 'Scene@1', t('対象あり・別場面', 'Supported wrong scene', lang),
                 t('対象あり・返却なし', 'Supported no return', lang), t('紛らわしい・誤返却', 'Confusable false return', lang),
                 t('紛らわしい・返却なし', 'Confusable no return', lang), t('対象なし・誤返却', 'Absent false return', lang),
                 t('対象なし・返却なし', 'Absent no return', lang)], native, 'native-table')
    nat += f'<p class="note">{t("scene@1は事前指定した原文場面が選ばれたかです。場面が正しくても回答が誤ることがあり、誤候補が返ってもAIが棄権することがあります。原文が示す出来事と世界で起きた出来事の真偽も別です。", "Scene@1 records selection of a predesignated original-source scene. A correct scene can still yield a wrong answer; an AI can abstain after a false candidate return. Source-grounded compatibility also differs from the truth of events in the world.", lang)}</p>'
    body += section('retrieval', '05 / SEPARATE SCENE DIAGNOSTICS', t('場面の取得率は、回答の正答率ではない。', 'Scene retrieval is a separate endpoint.', lang), nat)
    strata = f'<p>{t("32問は4つの出典クラスターに由来します。独立した32の会話エピソードとして扱いません。C01–C04はこの研究だけの匿名ラベルで、出典IDではありません。各条件で質問種別とクラスターの両方から全指標を再計算し、一致を検証します。", "The 32 queries come from four source clusters; they are not 32 independent conversation episodes. C01–C04 are opaque study-local labels, not source IDs. Every condition metric is reconciled independently across query kinds and source clusters.", lang)}</p>'
    for row in all_rows:
        tables = []
        for field, caption in [('query_kind_strata', t('質問種別の回答結果', 'Answer outcomes by query kind', lang)),
                               ('source_cluster_strata', t('匿名出典クラスターの回答結果', 'Answer outcomes by opaque source cluster', lang))]:
            parts = [dict(metrics, id=key) for key, metrics in row[field].items()]
            tables.append(_outcome_table(parts, lang, caption))
        strata += f'<details><summary>{escape(label(row["id"], lang))}</summary>{"".join(tables)}</details>'
    body += section('strata', '06 / DESCRIPTIVE STRATA', t('種別と4クラスターを確認する。', 'Inspect query kinds and four source clusters.', lang), strata)
    c, r = d['calls'], d['answer_reuse']
    actual = t('不明（失敗出力の呼出しメタデータなし）', 'Unknown (failed-output call metadata unavailable)', lang) if c['actual_distinct_reader_calls_including_retained_attempts'] is None else c['actual_distinct_reader_calls_including_retained_attempts']
    method = table(t('回答プールと条件ルックアップ。呼出し回数とは別。', 'Answer pool and condition lookups, distinct from model calls.', lang),
                   [t('記録単位', 'Recorded unit', lang), t('実際の件数', 'Actual count', lang)], [
                       [t('一意な質問・原文組の回答プール項目', 'Unique query/source answer-pool items', lang), r['unique_query_source_answer_pool_items']],
                       [t('条件が利用した一意な回答項目', 'Unique answer items used by conditions', lang), r['unique_answer_items_used_in_condition_lookups']],
                       [t('全条件の回答ルックアップ', 'Answer lookups across conditions', lang), r['condition_answer_lookups']],
                       [t('同じ保存回答の再利用ルックアップ', 'Reused lookups of the same saved answers', lang), r['reused_condition_answer_lookups']],
                       [t('全プール内の一意な機械的証拠エラー回答項目', 'Unique mechanical-evidence error answer items in the complete pool', lang), r['unique_mechanical_evidence_error_items']],
                       [t('成功したreaderコンテキスト／バッチ', 'Successful reader contexts / batches', lang), c['successful_reader_contexts']],
                       [t('保持した収集失敗試行', 'Retained failed collection attempts', lang), c['failed_collection_attempts']],
                       [t('保持した失敗を含む実際の異なるreader呼出し', 'Actual distinct reader calls including retained attempts', lang), actual],
                       [t('主評価のassessor呼出し', 'Primary assessor calls', lang), c['primary_assessor_calls']],
                       [t('最終監査のassessor呼出し（別集計）', 'Final-audit assessor calls (separate)', lang), c['final_audit_assessor_calls']],
                   ])
    method += f'<p>{t("一意な質問・原文の組合せについて実際のAI回答を一度保存し、同じ組合せを選んだ条件から繰り返し参照します。条件ルックアップ数は、新しいAI生成数でも独立した回答標本数でもありません。成功した4コンテキストと、保持した失敗試行、呼出し総数、主評価と最終監査を分けて報告します。", "An actual AI answer is saved once for each unique query/source combination, then referenced again by conditions selecting that combination. Condition lookups are neither fresh AI generations nor independent answer samples. Four successful contexts, retained failed attempts, total calls, primary assessment and final audits are reported separately.", lang)}</p>'
    method += f'<p>{t("索引は、原文だけを読むAIによる手作業の作成とレビューです。344件の文字列証拠の出現から、284件の一意なnative特徴登録と230件の標準化概念を得ました。これらは異なる単位であり、検索を反復した自動学習ではありません。役割は同じホスト上の指示で分離しました。", "The index was manually created and reviewed by an AI reading source material only. There were 344 literal witness occurrences, 284 unique native feature entries and 230 canonical concepts. These are distinct units, not automatic learning from repeated retrieval. Roles were separated by instructions on the same host.", lang)}</p>'
    method += f'<p class="note">{t("reader用の参照ラベルは不透明でしたが、原文メッセージの追跡情報には内部の出典ケースIDとアーカイブの来歴が残っていました。質問種別・期待する出典・方式・順位・点数・条件への直接の対応表フィールドは渡していません。それでも出典ケースの同一性は完全には匿名化されていません。共有ホスト上の指示による役割分離で、技術的な隔離ではありません。固定入力は実際に使った状態で保持し、この制限を後から取り除く再試行はしていません。原文や内部IDは公開JSON・ページに含めません。", "Reader wrapper references were opaque, but the original-message trace retained internal source-case IDs and archive provenance. Reader inputs had no direct query-kind, expected-source, arm, rank, score or condition mapping fields. Source-case identities were therefore not fully anonymous. Roles were instruction-separated on a shared host, without technical isolation. Frozen inputs were retained as used, without a retrospective retry to remove this limitation. Original messages and internal IDs are absent from public JSON and pages.", lang)}</p>'
    method += f'<p class="note">{t("表のreader・assessor呼出し数は、編成した役割・コンテキストの呼出し数であり、認証済みのprovider request IDやサービスへの実リクエスト数ではありません。基盤モデルの識別子・設定は提供されず、確認できませんでした。意味評価の主担当は1つで、評価者間の意味判定一致率は測っていません。件数や公開範囲の監査を、追加の意味評価者として数えません。", "Reader and assessor call counts denote orchestration role/context invocations, not authenticated provider request IDs or service-request counts. Underlying model identity and settings were not exposed and were unavailable. One primary semantic assessor performed grading; semantic inter-rater agreement was not measured. Count and privacy audits do not constitute additional semantic graders.", lang)}</p>'
    method += f'<details><summary>{t("採点前の失敗と修正", "Failures and corrections before scoring", lang)}</summary><p>{t("索引の初回レビューは主体の帰属2件を却下しました。修正後のnative構築も重複する特徴登録で停止し、出力を残しませんでした。344件の原文証拠をすべて保ち、重複を284件の一意な登録へ整理して再レビューしました。これらはコードと質問の固定前の修正です。", "The first index review rejected two subject-attribution errors. A later native build stopped on duplicate feature registrations before creating outputs. All 344 original witnesses were retained while duplicates were normalized to 284 unique registrations and reviewed again. These corrections preceded code and question freeze.", lang)}</p><p>{t("最初の出来事レビューは、原文の断片以上を支持した5件の要件判定を却下しました。採点前の1回の修正で、その5件の支持状態・引用・理由だけを直し、作者とは別の同じ確認役が再確認しました。候補全体の判定、原文、質問、索引、検索で得た候補は変えていません。元の版、却下、補助処理の失敗、修正版を保持しています。", "The first event review rejected five requirement judgments that claimed more support than their quoted fragments supplied. One pre-score repair changed only those judgments' support states, evidence and reasons. The same reviewer, in a context separate from the author’s, rechecked the repair. Overall candidate verdicts, originals, questions, index and native retrieval candidates were unchanged. Original versions, rejection, helper failures and repaired artifacts remain retained.", lang)}</p></details>'
    body += section('method', '07 / SAVED ACTUAL ANSWERS', t('保存した実際の回答を共有する。', 'Share saved actual answers across conditions.', lang), method)
    secondary = _secondary_content(d['secondary'], lang, rows)
    if secondary:
        body += section('secondary', '08 / SECONDARY DIAGNOSTICS', t('実際に記録した補助診断。', 'Secondary diagnostics actually recorded.', lang), secondary)
    proposed = f'<p class="kicker">{t("提案 / 未実施", "PROPOSED / NOT EXECUTED", lang)}</p><p>{t("次の研究案は、質問が要求する各点のカバレッジと、原文の根拠に沿った読み直しを検証することです。その後、実際の新しい出来事で、結果を見る前の予測 → 実際の行動・結果 → 次の選択 → 履歴の保持、という順序を記録して評価する案です。架空の出来事で代用せず、実記録を使います。この一連の評価は今回実施しておらず、生物学的な脳の再現を認定するものでもありません。", "The next research proposal is to test coverage of each query requirement and a reread grounded in source evidence. A subsequent proposal would record real new episodes in this order: prediction before the outcome → actual action and result → next choice → retention of the history. It would use actual records rather than fictional episodes. This sequence was not executed in the present study and would not certify biological brain reproduction.", lang)}</p>'
    body += section('next-research', '09 / PROPOSED RESEARCH', t('次に確かめることを、未実施の案として残す。', 'Retain the next research steps as unexecuted proposals.', lang), proposed)
    v = d['verification']
    boundary = f'<div class="boundary-box"><p>{t("この小規模な選択標本で、固定した原文と保存済みの実際のAI回答を評価した記録です。新しいAI生成による再現、自然な日常想起、脳の再現、AGI、Emotion、全Wakeを検証したものではありません。特権的な上限比較から運用性能を主張しません。", "This is an assessment of frozen source material and saved actual AI answers on a small selected sample. It does not verify reproducibility through fresh AI generation, natural daily recall, biological brain reproduction, AGI, Emotion or full Wake. The privileged ceiling does not establish operational performance.", lang)}</p></div>'
    boundary += f'<p>{t("公開するのは方法、全条件の集計、匿名の層別集計と監査用ハッシュです。原文・質問本文・出典ID・特徴語彙・SQLite・非公開の実行コードは含みません。公開ファイルで集計の整合性を確認できますが、原文照合や検索エンジンの再実行はできません。", "Public material contains the method, all-condition aggregates, opaque strata and audit digests. It excludes original text, query text, source IDs, feature vocabulary, SQLite and private execution code. Public files support aggregate consistency checks, but not source auditing or retrieval-engine reruns.", lang)}</p>'
    check_ja = f'コードの工学的確認は{v["code_engineering_passed"]}/{v["code_engineering_checks"]}、合成入力による手順確認は{v["synthetic_procedure_passed"]}/{v["synthetic_procedure_checks"]}。これらは実会話32問の研究結果と別です。公開用データの独立監査を確認しました。'
    check_en = f'Code engineering checks: {v["code_engineering_passed"]}/{v["code_engineering_checks"]}. Synthetic procedure checks: {v["synthetic_procedure_passed"]}/{v["synthetic_procedure_checks"]}. These are separate from the 32 real-query study outcomes. Independent audit of the public export was verified.'
    boundary += f'<p>{t(check_ja, check_en, lang)}</p>'
    boundary += f'<p><a href="../../{DATA_FILE}">{t("公開集計JSONを読む", "Read the public aggregate JSON", lang)}</a></p>'
    digests = table(t('内容を含まない監査用SHA-256', 'Audit SHA-256 digests without source content', lang), ['Artifact', 'SHA-256'], [[key, d['provenance'][key]] for key in sorted(PROVENANCE)], 'digest-table')
    boundary += f'<details><summary>{t("監査用ハッシュ", "Audit digests", lang)}</summary>{digests}</details>'
    body += section('scope', 'PUBLIC SCOPE / LIMITS', t('確認した範囲を保つ。', 'Keep the verification boundaries explicit.', lang), boundary)
    return _document(lang, body + '</div>')


def _secondary_content(value, lang, rows=None):
    result = ''
    prep = value['native_preparation']
    if prep is not None:
        equal = t('一致', 'Equal', lang) if prep['fresh_process_replay_equal'] else t('不一致', 'Unequal', lang)
        result += table(t('nativeの準備と独立した新規プロセスでの再実行', 'Native preparation and independent replay in a fresh process', lang),
                        [t('主実行のnative呼出し', 'Primary native calls', lang),
                         t('独立検証のnative呼出し', 'Independent-verification native calls', lang),
                         t('一意な質問・候補の組合せ', 'Unique query/candidate pairs', lang),
                         t('新規プロセスでの再実行', 'Fresh-process replay', lang)],
                        [[prep['primary_native_calls'], prep['independent_verification_native_calls'],
                          prep['unique_query_candidate_pairs'], equal]])
        result += table(t('質問ごとの重複除去後の候補数分布', 'Deduplicated candidate-count distribution per query', lang),
                        [t('候補数', 'Candidates', lang), t('質問数 / 32', 'Queries / 32', lang)],
                        [[key, f'{count} / 32'] for key, count in sorted(prep['candidate_count_distribution'].items(), key=lambda item: int(item[0]))])
        multiple = sum(count for key, count in prep['candidate_count_distribution'].items() if int(key) > 1)
        result += f'<p class="note">{t(f"複数候補があった質問は{multiple}/32問。候補の組合せ数は回答プール項目数や、正しく答えた質問数ではありません。", f"{multiple}/32 queries had multiple candidates. Query/candidate pairs are distinct from answer-pool items and correctly answered queries.", lang)}</p>'
    graph = value['graph']
    if graph is not None:
        result += table(t('通常native経路の返却出力だけを集計。方式間の共有を重複加算しない。', 'Normal native route outputs only; shared routes are not multiplied across arms.', lang),
                        ['Normal native calls', 'Graph expansions', 'Returned path segments', 'Associated hit records'],
                        [[graph[key] for key in ('native_calls', 'graph_expansions', 'returned_path_segments', 'associated_hits')]])
        result += table(t('通常に対して最終場面が変わった質問数', 'Queries whose final scene changed from normal execution', lang),
                        [t('無効化条件', 'Ablation condition', lang), t('変更 / 32', 'Changes / 32', lang)],
                        [[label(cid, lang), f'{count} / 32'] for cid, count in graph['ablation_selection_changes'].items()])
        normal_calls = graph['native_calls']
        count_ja = f'この表は全方式が共有する通常経路{normal_calls}回だけの集計です。全無効化条件を含む呼出し数や、一意なepisode数ではありません。'
        count_en = f'This table counts {normal_calls} normal route executions shared across all arms, not calls across all ablations or unique episodes.'
        result += f'<p class="note">{t(count_ja, count_en, lang)} {t("経路展開は実際のgraph_expansionsカウンタです。返却経路の区間数は通常出力の各hit.pathの長さを合計したもので、探索した全辺数ではありません。associated件数はretrieval_kindがassociatedである返却hitレコード数で、異なる質問や経路に同じepisodeが現れる場合があります。一意な記憶数ではありません。", "Expansions are the actual graph_expansions counter. Returned path segments sum len(hit.path) over normal route outputs; they are not a total traversed-edges counter. Associated hits count returned hit records whose retrieval_kind is associated. The same episode may recur across queries or routes; these are not unique memories.", lang)}</p>'
        result += f'<p class="note">{t("カウンタ単独では、回答改善や、保存・検索の速さは示せません。網や合流の寄与は無効化比較と分けずに判断します。最終場面の一致は非公開の完全なIDをnullも含めて比較しました。", "Counters alone do not establish answer improvement or storage/search speed. Graph and convergence contributions require the ablation comparisons. Final-scene equality was compared internally using complete private IDs, including null.", lang)}</p>'
        if rows is not None:
            raw_change = graph['ablation_selection_changes']['recovery_raw:without_convergence']
            unchanged = _unchanged_ablation_answer_counts(rows)
            graph_ja = f'ゲートなし・convergence=falseでは、最終場面の選択が{raw_change}/32問で通常実行から変わりました。回答結果の集計は全8無効化条件のうち{unchanged}/8条件で同じでした。{graph["graph_expansions"]}回の経路展開、返却経路の{graph["returned_path_segments"]}区間、associatedの{graph["associated_hits"]}返却レコードがあっても、それだけで回答への有効性は示せません。'
            graph_en = f'Without a gate and with convergence disabled, final source selection changed on {raw_change}/32 queries. Answer-outcome counts were unchanged in {unchanged}/8 ablation conditions. The {graph["graph_expansions"]} expansions, {graph["returned_path_segments"]} returned path segments and {graph["associated_hits"]} associated hit records do not by themselves establish answer efficacy.'
            result += f'<p>{t(graph_ja, graph_en, lang)}</p>'
            if unchanged == 8:
                result += f'<p>{t("この4出典クラスターでは、網や合流による追加の回答改善は示されていません。場面選択の変化と回答結果の件数を分けて解釈します。", "This four-source-cluster sample did not demonstrate an incremental answer benefit from graph traversal or convergence. Source-selection changes and answer-outcome counts are interpreted separately.", lang)}</p>'
    timing = value['timing']
    if timing is not None:
        result += table(t('native wrapperのperf_counter記録。主実行と検証を分ける。', 'Native-wrapper perf_counter record; primary and verification are separate.', lang),
                        [t('段階', 'Stage', lang), t('記録した合計秒', 'Recorded total seconds', lang)],
                        [[t('主実行', 'Primary', lang), timing['primary_native_wrapper_seconds']],
                         [t('独立検証', 'Independent verification', lang), timing['verification_native_wrapper_seconds']]])
        result += f'<p class="note">{t("AI呼出し、オーケストレーション、索引作成を含まないwrapper計測です。二値処理だけの速度向上、全処理の速度向上、他方式に対する優位は主張しません。", "Wrapper timings exclude AI calls, orchestration and index construction. They do not establish a binary-only speedup, end-to-end speed improvement or superiority over another system.", lang)}</p>'
    return result


def _document(lang, body):
    title = t('原文から回答への採用', 'From source retrieval to answer adoption', lang)
    desc = t('実会話4件・95メッセージ・固定32問での回答採用評価。全条件、失敗、再利用、特権的上限と限界。',
             'Answer adoption on four archived conversations, 95 messages and 32 frozen queries: all conditions, failures, answer reuse, privileged ceiling and limits.', lang)
    canonical = BASE + STUDY + ('' if lang == 'ja' else 'en.html')
    home = '../../results.html' if lang == 'ja' else '../../results.en.html'
    hub = '../../index.html' if lang == 'ja' else '../../index.en.html'
    languages = ''.join(f'<a href="{href}" lang="{code}" hreflang="{code}"' + (' aria-current="page"' if lang == code else '') + f'>{name}</a>' for href, code, name in [('index.html', 'ja', '日本語'), ('en.html', 'en', 'EN')])
    return f'''<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — LUX SPIRIA Results</title><meta name="description" content="{desc}">
<link rel="canonical" href="{canonical}"><link rel="alternate" hreflang="ja" href="{BASE + STUDY}"><link rel="alternate" hreflang="en" href="{BASE + STUDY}en.html"><link rel="alternate" hreflang="x-default" href="{BASE + STUDY}">
<meta name="theme-color" content="#090d12"><meta property="og:type" content="website"><meta property="og:title" content="{title} — LUX SPIRIA Results"><meta property="og:description" content="{desc}"><meta property="og:url" content="{canonical}"><meta property="og:image" content="{BASE}assets/lux-symbol.png">
<link rel="icon" type="image/png" sizes="32x32" href="../../assets/favicon-32.png"><link rel="apple-touch-icon" sizes="180x180" href="../../assets/apple-touch-icon.png"><link rel="manifest" href="../../{'site' if lang == 'ja' else 'site.en'}.webmanifest"><link rel="stylesheet" href="../../site.css"><link rel="stylesheet" href="event-adoption.css">
</head><body><a class="skip-link" href="#main">{t('本文へ', 'Skip to content', lang)}</a><div class="page">
<header class="masthead"><a class="brand" href="{home}" aria-label="LUX SPIRIA Results"><img src="../../assets/lux-symbol.png" alt="" width="44" height="44"><span class="brand-wordmark">LUX SPIRIA<span class="brand-subtitle">RESEARCH RESULTS</span></span></a><nav aria-label="{t('主なページ', 'Main navigation', lang)}"><a href="{home}#studies">{t('研究結果', 'Studies', lang)}</a><a href="#scope">{t('公開範囲', 'Public scope', lang)}</a><a href="{hub}">{t('研究の全体像', 'Project overview', lang)}</a><span class="lang" aria-label="{t('表示言語', 'Language', lang)}">{languages}</span></nav></header>
<main id="main">{body}</main><footer class="footer"><nav aria-label="{t('資料と規約', 'Resources and terms', lang)}"><a href="{hub}">LUX SPIRIA</a><a href="../../LICENSE">License / LSP-1.0</a><a href="https://github.com/Yuu-Honda/lux-spiria-results">GitHub ↗</a></nav><small>RESULT RECORD / 2026-10-24 · v1</small></footer>
</div></body></html>'''


def build():
    d = load_summary()
    # Render both first: no output path is created on any validation/render error.
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

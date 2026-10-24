"""Render only an independently audited, recursively allowlisted public export.

No private inputs, fallback outcomes, source text, or query text are accepted.
The missing/invalid-export path performs no writes. Constants are the public
contract; artificial test fixtures are never publication inputs.
"""
from html import escape
from functools import lru_cache
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = 'data/working-memory-source-fixed-2026-10-24.json'
STUDY = 'studies/2026-10-24-working-memory/'
BASE = 'https://yuu-honda.github.io/lux-spiria-results/'
CONDITIONS = ('first_pass', 'plain_reread', 'structured_state')
COHORTS = {'fresh': (12, 6, 6), 'known': (8, 6, 2)}
OUTCOMES = ('correct_supported', 'correct_abstention', 'partial_supported',
            'missed_answer', 'wrong_or_unsupported')
ERRORS = ('binding_errors', 'proposal_completion_errors',
          'unsupported_claim_items', 'mechanical_evidence_error_items')
METRICS = ('queries',) + OUTCOMES + ERRORS
PAIRS = {'first_to_plain': ('first_pass', 'plain_reread'),
         'first_to_structured': ('first_pass', 'structured_state'),
         'plain_to_structured': ('plain_reread', 'structured_state')}
SAMPLE = {'whole_source_sessions': 6, 'whole_retained_messages': 173,
          'fresh_source_sessions': 2, 'fresh_retained_messages': 78,
          'fresh_queries': 12, 'fresh_supported_queries': 6,
          'fresh_unsupported_queries': 6, 'known_source_sessions': 4,
          'known_retained_messages': 95, 'known_queries': 8,
          'known_supported_queries': 6, 'known_unsupported_queries': 2}
DESIGN = {'shared_first_answers': 20, 'assessed_answer_items': 60,
          'production_records': 140, 'producer_contexts': 12,
          'primary_assessor_contexts': 1, 'plan_payload_character_cap': 1200,
          'critic_payload_character_cap': 6000, 'final_payload_character_cap': 6000,
          'answer_character_cap': 2000, 'claim_cap': 10,
          'evidence_entry_cap': 24, 'working_state_slot_cap': 6}
PROVENANCE = {'protocol_sha256', 'source_selection_sha256',
              'reader_sources_sha256', 'query_freeze_sha256',
              'production_records_sha256', 'answer_pool_sha256',
              'primary_assessment_sha256', 'final_audit_sha256'}
METHOD_TRUE = {'source_fixed_privileged', 'original_bodies_preserved',
               'trace_and_path_metadata_stripped', 'all_meaning_roles_actual_ai',
               'shared_first_answers_frozen', 'same_originals_and_first_answers',
               'query_only_plans', 'all_critics_before_any_final',
               'all_answers_frozen_before_blind_assessment',
               'same_stage_caps_and_evidence', 'prelocked_item_orders',
               'collection_counterbalanced', 'instruction_separated_roles_same_host',
               'provider_identity_settings_and_request_counts_unavailable'}
METHOD_FALSE = {'controller_authored_semantics', 'fresh_per_condition_first_pass',
                'verified_equal_provider_tokens_or_compute', 'fully_anonymous_bodies'}
LIMITS_FALSE = {'retrieval_improvement_verified', 'shiori_speed_verified',
                'graph_benefit_verified', 'real_action_feedback_learning_executed',
                'full_wake_verified', 'emotion_effect_verified',
                'natural_daily_recall_verified', 'biological_brain_verified',
                'agi_verified', 'external_source_audit_possible_from_public_data',
                'private_experiment_rerun_possible_from_public_data'}
# Each row counts emitted per-item records, not provider requests. A context can
# emit many records. The shared first pass is charged once, never to both arms.
# The compatible emitted_payload_characters key counts canonical JSON payloads:
# ensure_ascii=False, sorted keys and compact separators, not raw file length.
COST_DESIGN = {'first_pass:final': (20, 2, 6000),
               'plain_reread:plan': (20, 1, 1200),
               'plain_reread:critic': (20, 2, 6000),
               'plain_reread:final': (20, 2, 6000),
               'structured_state:plan': (20, 1, 1200),
               'structured_state:critic': (20, 2, 6000),
               'structured_state:final': (20, 2, 6000)}
COST_FIELDS = {'records', 'contexts', 'emitted_payload_characters',
               'maximum_payload_characters', 'payload_cap_violation_records',
               'answer_characters', 'maximum_answer_characters',
               'answer_cap_violation_records', 'claim_cap_violation_records',
               'evidence_cap_violation_records', 'slot_cap_violation_records'}
VERIFICATION = {'independent_audit_verified', 'code_engineering_checks',
                'code_engineering_passed', 'synthetic_procedure_checks',
                'synthetic_procedure_passed'}
TOP_FIELDS = {'schema_version', 'study_id', 'date', 'sample', 'design',
              'provenance', 'method', 'limits', 'cohorts', 'costs', 'verification'}


def _keys(value, expected, where):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise ValueError(f'{where}: unexpected or missing public fields')


def _integer(value, where):
    if type(value) is not int or value < 0:
        raise ValueError(f'{where}: expected a nonnegative integer')


def _fixed(value, expected, where):
    _keys(value, expected, where)
    for key, count in expected.items():
        _integer(value[key], f'{where}.{key}')
        if value[key] != count:
            raise ValueError(f'{where}.{key}: frozen design differs')


def _flags(value, true, false, where):
    _keys(value, true | false, where)
    for key in true | false:
        if type(value[key]) is not bool or value[key] != (key in true):
            raise ValueError(f'{where}.{key}: unsupported method or limit flag')


def _metrics(value, total, where, supported=None):
    _keys(value, METRICS, where)
    for key in METRICS:
        _integer(value[key], f'{where}.{key}')
    if value['queries'] != total or sum(value[key] for key in OUTCOMES) != total:
        raise ValueError(f'{where}: exclusive outcomes must retain the frozen denominator')
    if any(value[key] > total for key in ERRORS):
        raise ValueError(f'{where}: flagged answer-item errors exceed denominator')
    if supported is True and value['correct_abstention']:
        raise ValueError(f'{where}: supported query cannot be a correct abstention')
    if supported is False and any(value[key] for key in ('correct_supported', 'partial_supported', 'missed_answer')):
        raise ValueError(f'{where}: unsupported queries require abstention or wrong/unsupported')
    # Invalid source evidence prevents a complete source-bound supported answer;
    # payload-budget flags are deliberately absent from semantic outcome logic.
    if supported is True and value['correct_supported'] + value['mechanical_evidence_error_items'] > total:
        raise ValueError(f'{where}: invalid source evidence cannot be fully correct')


def _pair(value, before, after, where):
    _keys(value, {'matrix', 'corrected', 'regressed'}, where)
    matrix = value['matrix']
    _keys(matrix, OUTCOMES, where + '.matrix')
    complete = {'correct_supported', 'correct_abstention'}
    for outcome in OUTCOMES:
        _keys(matrix[outcome], OUTCOMES, where + '.matrix row')
    for outcome in OUTCOMES:
        for target in OUTCOMES:
            _integer(matrix[outcome][target], where + '.matrix cell')
            # A single source-bound query cannot change corpus support status.
            negative = {'correct_abstention'}
            positive = {'correct_supported', 'partial_supported', 'missed_answer'}
            if ((outcome in negative and target in positive) or
                    (outcome in positive and target in negative)) and matrix[outcome][target]:
                raise ValueError(f'{where}: transition changes corpus support status')
    for outcome in OUTCOMES:
        if sum(matrix[outcome].values()) != before[outcome]:
            raise ValueError(f'{where}: transition row does not recalculate before outcome')
        if sum(matrix[source][outcome] for source in OUTCOMES) != after[outcome]:
            raise ValueError(f'{where}: transition column does not recalculate after outcome')
    for field, predicate in (
            ('corrected', lambda a, b: a not in complete and b in complete),
            ('regressed', lambda a, b: a in complete and b not in complete)):
        _integer(value[field], where + '.' + field)
        count = sum(matrix[a][b] for a in OUTCOMES for b in OUTCOMES if predicate(a, b))
        if value[field] != count:
            raise ValueError(f'{where}: paired corrected/regressed counts do not reconcile')


def _joint_pairs_realizable(pairs, supported, unsupported):
    """Decide integer three-way feasibility without publishing per-item data.

    Assign the first/plain pair counts to structured outcomes while consuming
    both other pair margins. All margins total at most 12 frozen queries, so
    memoized bounded integer search stays small and needs no solver dependency.
    A triple with any supported-only outcome consumes the supported budget;
    one with a correct abstention consumes the unsupported budget. An all-wrong
    triple can use either remaining support stratum. This also preserves each
    query's corpus support status across all three conditions.
    """
    size = len(OUTCOMES)
    def flatten(pair):
        matrix = pairs[pair]['matrix']
        return tuple(matrix[a][b] for a in OUTCOMES for b in OUTCOMES)

    positive = {OUTCOMES.index(key) for key in ('correct_supported', 'partial_supported', 'missed_answer')}
    abstention = OUTCOMES.index('correct_abstention')
    def kind(a, b, c):
        values = {a, b, c}
        if values & positive:
            return -1 if abstention in values else 1
        return 2 if abstention in values else 0

    def allocations(capacities, total, prefix=()):
        if len(capacities) == 1:
            if 0 <= total <= capacities[0]:
                yield prefix + (total,)
            return
        lower = max(0, total - sum(capacities[1:]))
        for count in range(lower, min(capacities[0], total) + 1):
            yield from allocations(capacities[1:], total - count, prefix + (count,))

    @lru_cache(maxsize=None)
    def feasible(ab, ac, bc, positive_left, negative_left):
        if not any(ab):
            return not any(ac) and not any(bc)
        choice = None
        for index, count in enumerate(ab):
            if not count:
                continue
            a, b = divmod(index, size)
            candidates, capacities, kinds = [], [], []
            for c in range(size):
                category = kind(a, b, c)
                capacity = min(ac[a * size + c], bc[b * size + c])
                if category == 1:
                    capacity = min(capacity, positive_left)
                elif category == 2:
                    capacity = min(capacity, negative_left)
                if category >= 0 and capacity:
                    candidates.append(c)
                    capacities.append(capacity)
                    kinds.append(category)
            if sum(capacities) < count:
                return False
            score = (len(candidates), -count)
            if choice is None or score < choice[0]:
                choice = (score, index, a, b, count, candidates, capacities, kinds)
        _, index, a, b, count, candidates, capacities, kinds = choice
        remaining_ab = list(ab)
        remaining_ab[index] = 0
        for values in allocations(capacities, count):
            positive_used = sum(value for value, category in zip(values, kinds) if category == 1)
            negative_used = sum(value for value, category in zip(values, kinds) if category == 2)
            if positive_used > positive_left or negative_used > negative_left:
                continue
            remaining_ac, remaining_bc = list(ac), list(bc)
            for c, value in zip(candidates, values):
                remaining_ac[a * size + c] -= value
                remaining_bc[b * size + c] -= value
            if feasible(tuple(remaining_ab), tuple(remaining_ac), tuple(remaining_bc),
                        positive_left - positive_used, negative_left - negative_used):
                return True
        return False

    return feasible(flatten('first_to_plain'), flatten('first_to_structured'),
                    flatten('plain_to_structured'), supported, unsupported)


def _costs(rows):
    _keys(rows, COST_DESIGN, 'costs')
    for key, (records, contexts, cap) in COST_DESIGN.items():
        row = rows[key]
        _keys(row, COST_FIELDS, 'costs.' + key)
        for field in COST_FIELDS:
            _integer(row[field], 'costs.' + key + '.' + field)
        if row['records'] != records or row['contexts'] != contexts:
            raise ValueError('costs: per-item production records and contexts must retain frozen design')
        if row['emitted_payload_characters'] < records:
            raise ValueError('costs: actual emitted records require recorded payload characters')
        if any(row[field] > records for field in COST_FIELDS if field.endswith('_violation_records')):
            raise ValueError('costs: violation records exceed emitted records')
        for prefix, maximum, limit in (
                ('emitted_payload', 'maximum_payload_characters', cap),
                ('answer', 'maximum_answer_characters', DESIGN['answer_character_cap'])):
            total = row[prefix + '_characters']
            peak = row[maximum]
            field = 'payload_cap_violation_records' if prefix == 'emitted_payload' else 'answer_cap_violation_records'
            violations = row[field]
            if peak > total or total > records * peak:
                raise ValueError('costs: character sum and maximum disagree')
            if ((violations == 0 and peak > limit) or
                    (violations > 0 and (peak <= limit or total < violations * (limit + 1)))):
                raise ValueError('costs: character caps and violation counts disagree')
            minimum = 1 if prefix == 'emitted_payload' else 0
            # The maximum must actually occur, exactly `violations` records
            # exceed the cap, and every other record stays within the cap.
            if violations:
                minimum_total = peak + (violations - 1) * (limit + 1) + (records - violations) * minimum
                maximum_total = violations * peak + (records - violations) * limit
            else:
                minimum_total = peak + (records - 1) * minimum
                maximum_total = records * peak
            if peak < minimum or not minimum_total <= total <= maximum_total:
                raise ValueError('costs: character totals, maximum and violation count are not jointly realizable')
        if (row['answer_characters'] > row['emitted_payload_characters'] or
                row['maximum_answer_characters'] > row['maximum_payload_characters']):
            raise ValueError('costs: answer characters exceed JSON payload characters')
        # Whichever record attains the payload maximum can contain at most
        # one answer maximum. All other answers must fit both their individual
        # answer maxima and the remaining records' total payload characters.
        answer_total_ceiling = row['maximum_answer_characters'] + min(
            row['emitted_payload_characters'] - row['maximum_payload_characters'],
            (records - 1) * row['maximum_answer_characters'])
        if row['answer_characters'] > answer_total_ceiling:
            raise ValueError('costs: answer and payload character totals are not jointly realizable')
        if not key.endswith(':final') and any(row[field] for field in (
                'answer_characters', 'maximum_answer_characters', 'answer_cap_violation_records')):
            raise ValueError('costs: non-answer stages cannot emit final-answer characters')
    if sum(row['records'] for row in rows.values()) != DESIGN['production_records'] or sum(row['contexts'] for row in rows.values()) != DESIGN['producer_contexts']:
        raise ValueError('costs: totals must retain distinct record/context counting units')


def validate_summary(d):
    """Reject every unknown recursive field or nonallowlisted string before IO."""
    _keys(d, TOP_FIELDS, 'summary')
    if (type(d['schema_version']) is not int or d['schema_version'] != 1 or
            d['study_id'] != 'working-memory-source-fixed-2026-10-24' or
            d['date'] != '2026-10-24'):
        raise ValueError('Unexpected study identity')
    _fixed(d['sample'], SAMPLE, 'sample')
    _fixed(d['design'], DESIGN, 'design')
    _keys(d['provenance'], PROVENANCE, 'provenance')
    for digest in d['provenance'].values():
        if not isinstance(digest, str) or not re.fullmatch('[a-f0-9]{64}', digest):
            raise ValueError('provenance: SHA-256 digests only')
    _flags(d['method'], METHOD_TRUE, METHOD_FALSE, 'method')
    _flags(d['limits'], set(), LIMITS_FALSE, 'limits')
    _keys(d['cohorts'], COHORTS, 'cohorts')
    for cohort, (total, positive, negative) in COHORTS.items():
        part = d['cohorts'][cohort]
        _keys(part, {'conditions', 'paired'}, 'cohort')
        _keys(part['conditions'], CONDITIONS, 'conditions')
        for condition, row in part['conditions'].items():
            _keys(row, {'metrics', 'support_strata'}, 'condition')
            _metrics(row['metrics'], total, condition)
            _keys(row['support_strata'], {'supported', 'unsupported'}, 'support_strata')
            _metrics(row['support_strata']['supported'], positive, condition + '.supported', True)
            _metrics(row['support_strata']['unsupported'], negative, condition + '.unsupported', False)
            for metric in METRICS:
                if sum(group[metric] for group in row['support_strata'].values()) != row['metrics'][metric]:
                    raise ValueError('support_strata: every metric must recalculate condition totals')
        _keys(part['paired'], PAIRS, 'paired')
        for pair, (before, after) in PAIRS.items():
            _pair(part['paired'][pair], part['conditions'][before]['metrics'],
                  part['conditions'][after]['metrics'], cohort + '.' + pair)
        if not _joint_pairs_realizable(part['paired'], positive, negative):
            raise ValueError(f'{cohort}: paired matrices have no jointly realizable integer three-condition table')
    _costs(d['costs'])
    v = d['verification']
    _keys(v, VERIFICATION, 'verification')
    if type(v['independent_audit_verified']) is not bool or not v['independent_audit_verified']:
        raise ValueError('verification: independently audited actual public export required')
    for field in VERIFICATION - {'independent_audit_verified'}:
        _integer(v[field], 'verification.' + field)
    for prefix in ('code_engineering', 'synthetic_procedure'):
        if v[prefix + '_passed'] > v[prefix + '_checks']:
            raise ValueError('verification: passed engineering checks exceed checks')
    return d


def load_summary(root=None):
    path = (ROOT if root is None else root) / DATA_FILE
    if not path.is_file():
        raise FileNotFoundError('Audited actual public export unavailable; no working-memory pages were written')
    def unique_object(pairs):
        value = {}
        for key, child in pairs:
            if key in value:
                raise ValueError('Duplicate public JSON field is forbidden')
            value[key] = child
        return value
    return validate_summary(json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique_object))


def optional_summary(root=None):
    path = (ROOT if root is None else root) / DATA_FILE
    return load_summary(root) if path.is_file() else None


def t(ja, en, lang):
    return ja if lang == 'ja' else en


def label(condition, lang):
    return {'first_pass': t('共通の初回回答（診断）', 'Shared first answer (diagnostic)', lang),
            'plain_reread': t('通常の読み直し', 'Ordinary reread', lang),
            'structured_state': t('構造化した作業状態', 'Structured working state', lang)}[condition]


def cohort_label(cohort, lang):
    return t('新規12問', 'Fresh 12 queries', lang) if cohort == 'fresh' else t('既知8問・選択した回帰確認', 'Known 8 queries · selected regressions', lang)


def table(caption, heads, rows, css=''):
    return (f'<div class="table-wrap" role="region" tabindex="0" aria-label="{escape(caption, quote=True)}"><table class="{css}"><caption>{escape(caption)}</caption><thead><tr>' +
            ''.join(f'<th scope="col">{escape(str(cell))}</th>' for cell in heads) + '</tr></thead><tbody>' +
            ''.join('<tr><th scope="row">' + escape(str(row[0])) + '</th>' + ''.join(f'<td>{escape(str(cell))}</td>' for cell in row[1:]) + '</tr>' for row in rows) + '</tbody></table></div>')


def section(sid, kicker, title, body):
    return f'<section class="section" id="{sid}" aria-labelledby="{sid}-title"><div class="section-heading"><p class="eyebrow">{kicker}</p><h2 id="{sid}-title">{title}</h2></div>{body}</section>'


def _outcomes(d, cohort, lang):
    total, positive, negative = COHORTS[cohort]
    rows = d['cohorts'][cohort]['conditions']
    heads = [t('条件', 'Condition', lang), t('根拠あり・正答', 'Correct supported', lang),
             t('正しい棄権', 'Correct abstention', lang), t('部分回答', 'Partial supported', lang),
             t('回答を逃した', 'Missed answer', lang), t('誤り・根拠なし', 'Wrong / unsupported', lang)]
    values = []
    for cid in CONDITIONS:
        row = rows[cid]['metrics']
        values.append([label(cid, lang), f'{row[OUTCOMES[0]]} / {positive}', f'{row[OUTCOMES[1]]} / {negative}', *[row[key] for key in OUTCOMES[2:]]])
    result = table(cohort_label(cohort, lang), heads, values, 'wm-outcomes')
    result += f'<p class="note">{t(f"各行は{total}問。正答の母数は対象あり{positive}問、正しい棄権はコーパス内に対象がない{negative}問。5分類の件数は排他的です。", f"Each row retains {total} queries. Correct supported answers use {positive} supported queries; correct abstentions use {negative} corpus-unsupported queries. The five outcome counts are exclusive.", lang)}</p>'
    for support, count in [('supported', positive), ('unsupported', negative)]:
        name = t('対象あり', 'Supported', lang) if support == 'supported' else t('コーパス内に対象なし', 'Corpus-unsupported', lang)
        result += '<details><summary>' + name + f' / {count}</summary>' + table(name, heads, [[label(cid, lang), *[rows[cid]['support_strata'][support][key] for key in OUTCOMES]] for cid in CONDITIONS], 'wm-outcomes') + '</details>'
    errors = [t('指示対象の取り違え', 'Binding errors', lang), t('提案・完了の取り違え', 'Proposal / completion errors', lang), t('根拠なし主張', 'Unsupported claim items', lang), t('機械的な証拠エラー', 'Mechanical evidence error items', lang)]
    result += table(t('失敗フラグの付いた回答項目数。列は重複しうる。', 'Flagged answer-item counts; columns may overlap.', lang), [heads[0], *errors], [[label(cid, lang), *[rows[cid]['metrics'][key] for key in ERRORS]] for cid in CONDITIONS], 'wm-errors')
    return result


def _paired(d, cohort, lang):
    result = ''
    names = dict(zip(OUTCOMES, [t('正答', 'Correct supported', lang), t('正しい棄権', 'Correct abstention', lang), t('部分', 'Partial', lang), t('取り逃し', 'Missed', lang), t('誤り・根拠なし', 'Wrong / unsupported', lang)]))
    for key, (before, after) in PAIRS.items():
        pair = d['cohorts'][cohort]['paired'][key]
        name = label(before, lang) + ' → ' + label(after, lang)
        result += f'<details><summary>{escape(name)} · {t("正答へ修正", "Corrected", lang)} {pair["corrected"]} / {t("正答から後退", "Regressed", lang)} {pair["regressed"]}</summary>'
        result += table(t('行＝変更前、列＝変更後。件数であり独立した再試行ではない。', 'Rows = before, columns = after. Counts are paired items, not independent retries.', lang), [t('前 → 後', 'Before → after', lang), *names.values()], [[names[outcome], *[pair['matrix'][outcome][target] for target in OUTCOMES]] for outcome in OUTCOMES], 'wm-transitions') + '</details>'
    return result


def _cost_table(d, lang):
    heads = [t('条件・段階', 'Condition / stage', lang), t('項目記録', 'Item records', lang), t('コンテキスト', 'Contexts', lang), t('canonical JSON文字数', 'Canonical JSON characters', lang), t('canonical最大文字数 / 上限', 'Canonical maximum / cap', lang), t('payload超過項目', 'Payload overruns', lang), t('回答文字数', 'Answer characters', lang), t('回答超過項目', 'Answer overruns', lang), t('主張 / 証拠 / slot超過項目', 'Claim / evidence / slot overruns', lang)]
    rows = []
    for key, (_, _, cap) in COST_DESIGN.items():
        cid, stage = key.split(':')
        row = d['costs'][key]
        rows.append([label(cid, lang) + ' / ' + stage, row['records'], row['contexts'], row['emitted_payload_characters'], f'{row["maximum_payload_characters"]} / {cap}', row['payload_cap_violation_records'], row['answer_characters'], row['answer_cap_violation_records'], ' / '.join(str(row[field]) for field in ('claim_cap_violation_records', 'evidence_cap_violation_records', 'slot_cap_violation_records'))])
    return table(t('実出力のpayloadをcanonical JSONで計数。JSONの整形空白・キー順を揃え、原文文字列は変更しない。上限にはJSON自体も含む。', 'Actual payloads counted in canonical JSON; serialization formatting standardized, original string text unchanged. Caps include the JSON payload itself.', lang), heads, rows, 'wm-costs')


def _finding(d, lang):
    """Describe validated public counts without presuming any outcome direction."""
    unchanged = all(
        all(part['conditions'][cid]['metrics'][key] == part['conditions']['first_pass']['metrics'][key]
            for cid in CONDITIONS for key in OUTCOMES) and
        all(pair['matrix'][before][after] == 0
            for pair in part['paired'].values()
            for before in OUTCOMES for after in OUTCOMES if before != after)
        for part in d['cohorts'].values())
    result = ''
    if unchanged:
        result += f'<p><strong>{t("今回の標本では、構造化による回答結果の追加の改善は確認できませんでした。", "No additional improvement in answer outcomes from structuring was observed on this sample.", lang)}</strong></p>'
        fresh = d['cohorts']['fresh']['conditions']['first_pass']['metrics']
        _, supported, unsupported = COHORTS['fresh']
        if fresh['correct_supported'] == supported and fresh['correct_abstention'] == unsupported:
            result += f'<p>{t(f"新規12問は、対象あり{supported}問への完全回答と対象なし{unsupported}問への正しい棄権が共通の初回回答からそろっており、この標本では改善の余地がありませんでした。", f"All fresh 12 queries were already correct at the shared first answer: {supported}/{supported} complete supported answers and {unsupported}/{unsupported} correct abstentions, leaving no headroom on this sample.", lang)}</p>'
        known_partial = d['cohorts']['known']['conditions']['plain_reread']['metrics']['partial_supported']
        if known_partial:
            result += f'<p>{t(f"意図して選んだ既知8問では、部分回答{known_partial}問が両方式で残りました。", f"In the deliberately selected known eight-query set, {known_partial} partial supported answers remained in both arms.", lang)}</p>'
        result += f'<p class="note">{t("新規側の標本と、意図して選んだ既知の回帰確認から、構造化した作業状態の一般的な劣位は示せません。", "The fresh sample and deliberately selected known regressions do not establish general inferiority of a structured working state.", lang)}</p>'
    for cohort, (_, supported, unsupported) in COHORTS.items():
        part = d['cohorts'][cohort]
        before = part['conditions']['plain_reread']['metrics']
        after = part['conditions']['structured_state']['metrics']
        pair = part['paired']['plain_to_structured']
        result += f'<p>{t(f"{cohort_label(cohort, lang)}：通常の読み直し → 構造化した作業状態で、根拠ある完全回答 {before['correct_supported']}/{supported} → {after['correct_supported']}/{supported}、正しい棄権 {before['correct_abstention']}/{unsupported} → {after['correct_abstention']}/{unsupported}、部分回答 {before['partial_supported']} → {after['partial_supported']}。正答への修正 {pair['corrected']}問、正答からの後退 {pair['regressed']}問でした。", f"{cohort_label(cohort, lang)}: ordinary reread → structured working state yielded {before['correct_supported']}/{supported} → {after['correct_supported']}/{supported} complete supported answers, {before['correct_abstention']}/{unsupported} → {after['correct_abstention']}/{unsupported} correct abstentions, and {before['partial_supported']} → {after['partial_supported']} partial supported answers; {pair['corrected']} transitioned to a complete correct answer or correct abstention and {pair['regressed']} regressed from those outcomes.", lang)}</p>'
    return result


def verification_version_note(verification, lang):
    """Qualify the audited 27/70 check totals without changing their schema."""
    if not all(verification[key] == count for key, count in (
            ('code_engineering_checks', 27), ('code_engineering_passed', 27),
            ('synthetic_procedure_checks', 70), ('synthetic_procedure_passed', 70))):
        return ''
    return t('最終版では全単体テスト27件を実行しました。別枠の70件の手続き検査は、保持した修正前版での57件と最終版での日時入力13ケースです。間のコントローラー変更は日時入力検証だけでした。これらは工程上の検査であり、記憶精度を測るものではありません。',
             'The final controller version ran its full 27-test unit suite. The separate 70 procedure checks comprise 57 on the retained predecessor and 13 timestamp-input cases on the final version; the intervening controller change was timestamp validation only. These are engineering and procedure checks, not memory-accuracy measurements.', lang)


def render(lang, summary=None):
    if lang not in ('ja', 'en'):
        raise ValueError('Supported languages are ja and en')
    d = load_summary() if summary is None else validate_summary(summary)
    title = t('同じ原文を読み直し、<br>作業状態を構造化する。', 'Reread the same source.<br>Structure the working state.', lang)
    body = f'<div class="wm-study"><section class="study-hero"><p class="kicker">STUDY / SOURCE-FIXED WORKING MEMORY / v1</p><h1>{title}</h1><p class="lead">{t("特権的に原文を固定し、同じ初回回答から、通常の読み直しと構造化した作業状態を比較しました。新規12問と、選択した既知8問の回帰確認を、別々に報告します。", "With source material fixed by privileged selection, ordinary rereading and a structured working state started from the same first answer. Fresh 12-query results and deliberately selected known 8-query regressions are reported separately.", lang)}</p><p class="note"><time datetime="2026-10-24">2026-10-24</time> · {t("保存した実際のAI出力。閲覧中にAIは動きません。", "Saved actual AI outputs. Browsing does not run an AI.", lang)}</p></section>'
    primary = _finding(d, lang)
    primary += f'<div class="boundary-box"><p>{t("主比較は、通常の読み直し → 構造化した作業状態です。共通の初回回答は少ない段階数の診断であり、計算量を揃えた主比較ではありません。両方式とも質問だけの計画 → 原文の批評・読み直し → 最終回答を実行し、同じ原文と初回回答を受け取りました。", "The primary comparison is ordinary reread → structured working state. The shared first answer is a lower-stage diagnostic, not the matched primary comparison. Both arms executed a query-only plan → source critique/reread → final answer and received the same originals and first answer.", lang)}</p></div>'
    primary += f'<p>{t("新規側は未使用だった実会話2件の保存された全78メッセージ（50＋28）から原文に基づいて新たに作った12問です。既知側は以前の4件・保存された全95メッセージに基づき、旧部分回答3問・旧完全回答3問・紛らわしい1問・対象なし1問を意図して選びました。6出典・173メッセージを使い、20問を20の独立した出典や反復として扱いません。", "The fresh set contains 12 newly source-authored queries from two unused archived sources and all 78 retained messages (50 + 28). The known set deliberately selects three prior partial answers, three prior complete answers, one confusable and one absent case from four older sources and all 95 retained messages. There are six sources and 173 messages; the 20 queries are not 20 independent sources or replications.", lang)}</p>'
    body += section('comparison', '01 / PRIMARY COMPARISON', t('通常の読み直しを、主な比較対象にする。', 'Use ordinary rereading as the primary comparator.', lang), primary)
    body += section('fresh', '02 / FRESH QUERIES', cohort_label('fresh', lang), _outcomes(d, 'fresh', lang) + _paired(d, 'fresh', lang))
    body += section('known', '03 / SELECTED REGRESSIONS', cohort_label('known', lang), _outcomes(d, 'known', lang) + _paired(d, 'known', lang))
    assessment = f'<p>{t("正答への修正は、不完全・誤りから根拠ある正答または正しい棄権への遷移です。後退はその逆です。部分回答の変化をすべて改善と呼びません。指示対象、提案と完了、根拠なし主張の意味評価は実際のAIが行い、機械的な証拠照合は別に数えます。無効な原文根拠がある回答は完全な原文準拠の正答になりません。文字数などの予算超過だけで、意味上の誤答にはしません。", "Corrected means a transition from incomplete/wrong to a correct supported answer or correct abstention; regressed is the reverse. Other partial-answer changes are not automatically called improvements. Actual AI roles assessed referents, proposal versus completion, and unsupported claims. Mechanical evidence checks are separate. Invalid source grounding prevents a fully source-bound correct answer. A budget overrun alone is not a semantic error.", lang)}</p>'
    body += section('assessment', '04 / ASSESSMENT', t('意味の評価と、機械的な検査を分ける。', 'Separate semantic assessment from mechanical checks.', lang), assessment)
    cost = _cost_table(d, lang)
    cost += f'<p>{t("共通初回20件・計画40件・批評40件・最終40件で、実際の項目別生成記録は140件です。生成用コンテキストは、計画2・共通初回2・批評4・最終4の計12。140回のモデル要求を意味しません。60回答を固定し、1つの主評価コンテキストで盲検評価しました。全ての批評を最終回答より先に完了しました。", "There are 140 actual per-item production records: 20 shared first answers, 40 plans, 40 critiques and 40 final answers. Producer contexts total 12: two plan, two shared-first, four critic and four final contexts. This does not mean 140 provider requests. All 60 answers were frozen before blind assessment in one primary assessor context. Every critique finished before any final answer.", lang)}</p>'
    cost += f'<p class="note">{t("同じ段階・許可上限・証拠を用いました。計画は1,200文字、批評と最終payloadは6,000文字、回答は2,000文字、主張10・証拠24・作業状態slot6が上限です。実出力のpayloadは、Unicodeをエスケープせず、キー順を固定し、最小の区切りを使うcanonical JSONで計数します。JSONの整形空白・キー順を揃え、原文文字列は変更しません。これは整形された出力ファイル全体の長さやprovider token数ではありません。文字数と超過を個別に報告します。モデル識別・設定・provider要求数は取得できず、provider token数や計算量の一致は検証していません。", "Stages, permitted caps and evidence were shared. Caps were 1,200 plan characters, 6,000 critic/final payload characters, 2,000 answer characters, 10 claims, 24 evidence entries and six working-state slots. Actual payloads are counted in canonical JSON with Unicode retained, sorted keys and compact separators; serialization formatting is standardized and original string text is unchanged. These counts are not raw indented output-file lengths or provider tokens. Characters and overruns are reported separately. Model identity/settings and provider request counts were unavailable; equal provider tokens or compute were not verified.", lang)}</p>'
    body += section('costs', '05 / RECORDED COSTS', t('生成記録・文字数・上限を残す。', 'Retain production records, characters and caps.', lang), cost)
    method = f'<p>{t("計画、批評、回答、独立評価の意味内容は実際のAI役割が作りました。Pythonは原文との対応・引用・固定・上限・件数を検査しました。原文の本文は変更せず、trace・case UUID・pathメタデータを除き、readerにはrole・text・順序・時刻と不透明なIDだけを渡しました。本文自体に識別情報が残る場合があり、完全な匿名化ではありません。意味役割には親タスク履歴を渡さず、同じhost上で指示により役割を分離しました。", "Actual AI roles produced the semantic plans, critiques, answers and independent grades. Python verified source bindings, quotes, freezes, caps and counts. Original bodies were unchanged; trace, case UUID and path metadata were stripped, and reader inputs allowlisted role, text, order, timestamp and opaque IDs. Bodies may themselves identify a source, so this is not full anonymity. Meaning roles received no parent-task history and were instruction-separated on a shared host.", lang)}</p>'
    method += f'<p>{t("保存された各出典行の全発言を使用しましたが、プラットフォームの全履歴を取得したものではありません。原文の選択は特権的に固定されています。検索改善、SHIORIの保存・検索速度、網や合流の効果、実際の行動結果を使う学習、全Wake、Emotionの効果を測った試験ではありません。", "All messages retained in each archived source row were used; the archives are partial relative to the platform history. Source selection was fixed by privilege. This study does not measure retrieval improvements, SHIORI storage/search speed, graph or convergence effects, learning from real action outcomes, full Wake or Emotion effects.", lang)}</p>'
    body += section('method', '06 / SOURCE-FIXED METHOD', t('原文を固定した比較の範囲を保つ。', 'Keep the source-fixed comparison within its scope.', lang), method)
    proposed = f'<p class="kicker">{t("提案 / 未実施", "PROPOSED / NOT EXECUTED", lang)}</p><p>{t("次の案は、結果を見る前の予測 → 実際の行動と結果 → 次の選択 → 履歴の保持を、実際の新しい出来事で記録することです。この連鎖は今回実行していません。架空の出来事を実測の代わりにはせず、生物学的な脳・AGIの実証とも呼びません。", "A next proposal is to record prediction before the result → actual action and outcome → next choice → retention of history in real new episodes. This sequence was not executed here. Fictional episodes would not substitute for actual measurements, nor would the sequence establish biological brain reproduction or AGI.", lang)}</p>'
    body += section('next-research', '07 / PROPOSED NEXT RESEARCH', t('次の連鎖は、未実施の案として残す。', 'Retain the next sequence as an unexecuted proposal.', lang), proposed)
    v = d['verification']
    scope = f'<div class="boundary-box"><p>{t("小規模な選択標本での記述的な比較です。新規と既知を別々に読み、一般的な優位性・自然な日常想起・人格連続性・脳の再現・AGIを主張しません。", "This is a descriptive comparison on a small selected sample. Fresh and known results remain separate. It does not establish general superiority, natural daily recall, personality continuity, brain reproduction or AGI.", lang)}</p></div>'
    scope += f'<p>{t("公開するのは許可した集計・固定した方法・監査用ハッシュだけです。原文、質問、出典ID、特徴語彙、SQLite、非公開の実験コードやpathは含みません。公開ファイルで集計の整合性は検査できますが、原文照合や非公開実験の再実行はできません。", "Public material contains allowlisted aggregates, the frozen method and audit digests. It excludes originals, questions, source IDs, feature vocabulary, SQLite, private experiment code and paths. Public files support aggregate consistency checks, not source auditing or private-experiment reruns.", lang)}</p>'
    scope += f'<p>{t(f"コードの工学的確認 {v['code_engineering_passed']}/{v['code_engineering_checks']}、合成入力による手順確認 {v['synthetic_procedure_passed']}/{v['synthetic_procedure_checks']}。これらは実際のAI回答60件の研究結果と別です。公開集計の独立監査を確認しました。", f"Code engineering checks {v['code_engineering_passed']}/{v['code_engineering_checks']}; synthetic procedure checks {v['synthetic_procedure_passed']}/{v['synthetic_procedure_checks']}. These are separate from the 60 actual AI answer outcomes. Independent audit of the public export was verified.", lang)}</p>'
    version_note = verification_version_note(v, lang)
    if version_note:
        scope += f'<p>{version_note}</p>'
    scope += f'<p><a href="../../{DATA_FILE}">{t("公開集計JSON", "Public aggregate JSON", lang)}</a></p><details><summary>{t("監査用ハッシュ", "Audit digests", lang)}</summary>' + table('SHA-256', ['Artifact', 'SHA-256'], [[key, d['provenance'][key]] for key in sorted(PROVENANCE)], 'wm-digests') + '</details>'
    body += section('scope', 'PUBLIC SCOPE / LIMITS', t('結果と、確認できる範囲を残す。', 'Retain results and verification boundaries.', lang), scope)
    return _document(lang, body + '</div>')


def _document(lang, body):
    title = t('原文を固定した作業記憶の比較', 'Source-fixed working-memory comparison', lang)
    description = t('同じ原文と初回回答から、通常の読み直しと構造化した作業状態を比較。新規12問と選択した既知8問を別々に報告。', 'Ordinary rereading and structured working state from the same source and first answer. Fresh 12 queries and selected known 8-query regressions reported separately.', lang)
    canonical = BASE + STUDY + ('' if lang == 'ja' else 'en.html')
    results = '../../results.html' if lang == 'ja' else '../../results.en.html'
    home = '../../index.html' if lang == 'ja' else '../../index.en.html'
    languages = ''.join(f'<a href="{href}" lang="{code}" hreflang="{code}"' + (' aria-current="page"' if lang == code else '') + f'>{name}</a>' for href, code, name in [('index.html', 'ja', '日本語'), ('en.html', 'en', 'EN')])
    return f'''<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — LUX SPIRIA Results</title><meta name="description" content="{description}">
<link rel="canonical" href="{canonical}"><link rel="alternate" hreflang="ja" href="{BASE + STUDY}"><link rel="alternate" hreflang="en" href="{BASE + STUDY}en.html"><link rel="alternate" hreflang="x-default" href="{BASE + STUDY}">
<meta name="theme-color" content="#090d12"><meta property="og:type" content="website"><meta property="og:title" content="{title} — LUX SPIRIA Results"><meta property="og:description" content="{description}"><meta property="og:url" content="{canonical}"><meta property="og:image" content="{BASE}assets/lux-symbol.png">
<link rel="icon" type="image/png" sizes="32x32" href="../../assets/favicon-32.png"><link rel="apple-touch-icon" sizes="180x180" href="../../assets/apple-touch-icon.png"><link rel="manifest" href="../../{'site' if lang == 'ja' else 'site.en'}.webmanifest"><link rel="stylesheet" href="../../site.css"><link rel="stylesheet" href="../../theme-dark.css"><link rel="stylesheet" href="working-memory.css">
</head><body><a class="skip-link" href="#main">{t('本文へ', 'Skip to content', lang)}</a><div class="page"><header class="masthead"><a class="brand" href="{results}" aria-label="LUX SPIRIA Results"><img src="../../assets/lux-symbol.png" alt="" width="44" height="44"><span class="brand-wordmark">LUX SPIRIA<span class="brand-subtitle">RESEARCH RESULTS</span></span></a><nav aria-label="{t('主なページ', 'Main navigation', lang)}"><a href="{results}#studies">{t('研究結果', 'Studies', lang)}</a><a href="#scope">{t('公開範囲', 'Public scope', lang)}</a><a href="{home}">{t('研究の全体像', 'Project overview', lang)}</a><span class="lang" aria-label="{t('表示言語', 'Language', lang)}">{languages}</span></nav></header><main id="main">{body}</main><footer class="footer"><nav aria-label="{t('資料と規約', 'Resources and terms', lang)}"><a href="{home}">LUX SPIRIA</a><a href="../../LICENSE">License / LSP-1.0</a><a href="https://github.com/Yuu-Honda/lux-spiria-results">GitHub ↗</a></nav><small>RESULT RECORD / 2026-10-24 · v1</small></footer></div></body></html>'''


def build():
    d = load_summary()
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

"""Build only the dated event-compatibility study from audited public data.

No private source, query, label, native AI output or evaluation artifact is read.
Missing data and recursive allowlist/consistency failures stop before any write.
The separate main-site builder and all earlier studies are left untouched.
"""
from collections import Counter
from html import escape as E
import importlib.util
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = 'data/shiori-event-compatibility-2026-10-22.json'
STUDY = 'studies/2026-10-22-event-compatibility/'
ARMS = ('recovery_raw', 'strict_source_gate', 'event_review_only',
        'strict_and_event_review')
PROVENANCE_FIELDS = {
    'protocol_sha256', 'code_freeze_sha256', 'query_freeze_sha256',
    'source_selection_audit_sha256', 'source_packet_sha256', 'source_index_sha256',
    'cue_analysis_sha256', 'cue_review_sha256',
    'event_analysis_sha256', 'event_review_sha256', 'evaluation_sha256',
    'known_regression_evaluation_sha256', 'private_report_sha256',
    'sealed_manifest_sha256', 'final_independent_audit_sha256',
}
CATEGORIES = ('literal', 'paraphrase', 'confusable', 'absent')
ABLATIONS = ('hops0', 'without_convergence')
RESULT_FIELDS = {'target_hit', 'returned_candidate', 'search_executed'}
RETRIEVAL_FIELDS = {
    'original_native_top20_target_present',
    'recovery_semantic_native_top20_target_present', 'union_target_present',
    'original_native_candidates', 'semantic_native_candidates',
    'unique_union_candidates', 'native_route_count',
    'graph_expansions', 'graph_edges', 'associated_hits',
}
TARGET_FIELDS = {
    'original_native_top20_target_present',
    'recovery_semantic_native_top20_target_present', 'union_target_present',
}
METRICS = ('positive_hits', 'positive_wrong_scene_returns', 'literal_hits',
           'paraphrase_hits', 'confusable_false_returns', 'absent_false_returns',
           'native_searches', 'pre_search_abstentions')
SAMPLE_VALUES = {
    'sessions': 4, 'messages_per_session': 8, 'source_messages': 32,
    'queries': 32, 'positive_queries': 16, 'literal_queries': 4,
    'paraphrase_queries': 12, 'confusable_queries': 8, 'absent_queries': 8,
    'reviewed_features': 115, 'cue_concepts': 114,
    'archive_sessions': 171, 'excluded_sessions': 95, 'eligible_sessions': 10,
}
METHOD_TRUE = {
    'original_query_first', 'unchanged_native_candidate_retrieval',
    'event_review_after_native_retrieval',
    'event_review_sees_query_and_linked_originals',
    'native_rank_score_path_and_strict_gate_hidden', 'query_labels_and_kind_hidden',
    'event_review_independently_reviewed', 'event_review_artifact_bound',
    'first_passing_native_order', 'source_index_source_only',
    'source_index_reviewed_before_code_freeze',
    'source_selection_locked_before_semantic_reading',
    'source_count_decoded_body_strings', 'query_author_source_only',
    'query_author_algorithm_protocol_not_provided', 'seeded_query_order_and_ids',
    'role_isolation_instruction_only', 'same_host',
}
METHOD_FALSE = {'score_mixing', 'model_identity_recorded'}
VERIFICATION_TRUE = {
    'saved_actual_ai_outputs_replayed', 'independent_replay_verified',
    'initial_index_build_failed', 'initial_index_build_partial_db_writes',
    'initial_failure_before_queries', 'corrected_preflight_fails_before_writes',
}
VERIFICATION_FALSE = {
    'world_event_truth_verified', 'answer_adoption_verified',
    'model_regeneration_tested', 'timing_measured', 'daily_recall_verified',
    'biological_brain_verified', 'emotion_verified', 'full_wake_verified',
    'external_source_audit_possible_from_public_data',
}
VERIFICATION_COUNTS = {
    'code_engineering_tests', 'code_engineering_passed',
    'synthetic_engineering_tests', 'synthetic_engineering_passed',
    'failed_index_artifacts_retained', 'native_primary_search_calls',
    'preparation_replay_native_search_calls',
    'independent_replay_native_search_calls', 'known_regression_native_search_calls',
    'known_regression_preparation_replay_native_search_calls',
    'known_regression_independent_replay_native_search_calls',
    'final_audit_additional_native_search_calls',
    'known_regression_final_audit_additional_native_search_calls',
}
TOP_FIELDS = {'schema_version', 'study_id', 'date', 'endpoint', 'provenance',
              'sample', 'method', 'per_query', 'conditions',
              'known_regression', 'verification'}

# Read established public presentation helpers, without running their builder.
_spec = importlib.util.spec_from_file_location('event_public_helpers', ROOT / 'tools/build_pages.py')
_pages = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_pages)
T, section, table, cards = _pages.T, _pages.section, _pages.table, _pages.cards


def _keys(obj, expected, where):
    if not isinstance(obj, dict) or set(obj) != set(expected):
        raise ValueError(f'{where}: unexpected or missing public fields')


def _integer(value, where):
    if type(value) is not int or value < 0:
        raise ValueError(f'{where}: expected a nonnegative integer')


def _flags(obj, true_fields, false_fields, where):
    for key in true_fields | false_fields:
        if type(obj[key]) is not bool or obj[key] != (key in true_fields):
            raise ValueError(f'{where}: unsupported method or verification flag {key}')


def _result(result, positive, where, *, ablation=False):
    _keys(result, RESULT_FIELDS | ({'same_selection_as_normal'} if ablation else set()), where)
    if any(type(value) is not bool for value in result.values()):
        raise ValueError(f'{where}: outcomes must be booleans')
    if result['target_hit'] and (not positive or not result['returned_candidate']):
        raise ValueError(f'{where}: target hit requires a positive query and a return')
    if result['returned_candidate'] and not result['search_executed']:
        raise ValueError(f'{where}: return requires search')


def recalculate_conditions(queries):
    """All public outcome aggregates derive only from opaque per-query booleans."""
    rows = []
    for arm in ARMS:
        positives = [q for q in queries if q['category'] in ('literal', 'paraphrase')]
        rows.append({
            'id': arm,
            'positive_hits': sum(q['conditions'][arm]['target_hit'] for q in positives),
            'positive_wrong_scene_returns': sum(q['conditions'][arm]['returned_candidate'] and not q['conditions'][arm]['target_hit'] for q in positives),
            'literal_hits': sum(q['conditions'][arm]['target_hit'] for q in queries if q['category'] == 'literal'),
            'paraphrase_hits': sum(q['conditions'][arm]['target_hit'] for q in queries if q['category'] == 'paraphrase'),
            'confusable_false_returns': sum(q['conditions'][arm]['returned_candidate'] for q in queries if q['category'] == 'confusable'),
            'absent_false_returns': sum(q['conditions'][arm]['returned_candidate'] for q in queries if q['category'] == 'absent'),
            'native_searches': sum(q['conditions'][arm]['search_executed'] for q in queries),
            'pre_search_abstentions': sum(not q['conditions'][arm]['search_executed'] for q in queries),
        })
    return rows


def recalculate_ablations(queries):
    """Recalculate each separate diagnostic set from opaque result flags."""
    rows = []
    for ablation in ABLATIONS:
        abq = [{'category': q['category'], 'conditions': q['ablations'][ablation]} for q in queries]
        for result in recalculate_conditions(abq):
            arm = result['id']
            rows.append(dict(result, ablation=ablation,
                             changed_selections=sum(not q['ablations'][ablation][arm]['same_selection_as_normal'] for q in queries)))
    return rows


def _ablations(q, positive):
    _keys(q['ablations'], ABLATIONS, 'ablations')
    for ablation in ABLATIONS:
        _keys(q['ablations'][ablation], ARMS, 'ablation arms')
        raw = q['ablations'][ablation]['recovery_raw']
        for arm in ARMS:
            result = q['ablations'][ablation][arm]
            _result(result, positive, 'ablation result', ablation=True)
            normal = q['conditions'][arm]
            if result['search_executed'] != raw['search_executed']:
                raise ValueError('Ablation arms must share native retrieval')
            if result['returned_candidate'] and not raw['returned_candidate']:
                raise ValueError('An ablation gate cannot add a candidate to the raw union')
            if result['same_selection_as_normal'] and any(result[key] != normal[key] for key in ('target_hit', 'returned_candidate')):
                raise ValueError('Equal selections require equal return and target outcomes')
            if not result['returned_candidate'] and not normal['returned_candidate'] and not result['same_selection_as_normal']:
                raise ValueError('Two null selections must be marked equal')


def _queries(queries, prefix, *, fresh):
    if (not isinstance(queries, list) or len(queries) != 32 or
            any(not isinstance(q, dict) for q in queries) or
            [q.get('id') for q in queries] != [f'{prefix}{i:02}' for i in range(1, 33)]):
        raise ValueError('Queries require 32 sequential opaque study-local IDs')
    for q in queries:
        _keys(q, {'id', 'category', 'conditions', 'ablations'} | ({'retrieval'} if fresh else set()), 'query')
        if q['category'] not in CATEGORIES:
            raise ValueError('Unsupported query category')
        positive = q['category'] in ('literal', 'paraphrase')
        _keys(q['conditions'], ARMS, 'query conditions')
        for result in q['conditions'].values():
            _result(result, positive, 'condition result')
        raw = q['conditions']['recovery_raw']
        for result in q['conditions'].values():
            if result['search_executed'] != raw['search_executed']:
                raise ValueError('All arms share unchanged native retrieval')
            if result['returned_candidate'] and not raw['returned_candidate']:
                raise ValueError('A gate cannot add a candidate to the raw union')
        _ablations(q, positive)
        if not fresh:
            continue
        r = q['retrieval']
        _keys(r, RETRIEVAL_FIELDS, 'retrieval')
        for key in TARGET_FIELDS:
            if type(r[key]) is not bool or (not positive and r[key]):
                raise ValueError('Target coverage requires a positive query and boolean flags')
        for key in RETRIEVAL_FIELDS - TARGET_FIELDS:
            _integer(r[key], key)
        if r['native_route_count'] not in (1, 2):
            raise ValueError('Native route count must be one or two')
        if any(r[k] > 20 for k in ('original_native_candidates', 'semantic_native_candidates')):
            raise ValueError('Each native route is limited to top 20')
        original, semantic, union = (r[k] for k in ('original_native_candidates', 'semantic_native_candidates', 'unique_union_candidates'))
        if not max(original, semantic) <= union <= original + semantic:
            raise ValueError('Full union count must deduplicate the native candidate routes')
        if r['native_route_count'] == 1 and (semantic or r['recovery_semantic_native_top20_target_present']):
            raise ValueError('A missing semantic route has no candidates or target coverage')
        for flag, count in [('original_native_top20_target_present', original), ('recovery_semantic_native_top20_target_present', semantic), ('union_target_present', union)]:
            if r[flag] and not count:
                raise ValueError('Target coverage requires at least one candidate')
        if r['union_target_present'] != (r['original_native_top20_target_present'] or r['recovery_semantic_native_top20_target_present']):
            raise ValueError('Full union target coverage must equal the union of route coverage')
        if raw['returned_candidate'] != bool(union) or not raw['search_executed']:
            raise ValueError('Recovery raw returns the first candidate from executed native retrieval')
        if any(result['target_hit'] for result in q['conditions'].values()) and not r['union_target_present']:
            raise ValueError('A selected target must be present in the full union')
    if Counter(q['category'] for q in queries) != {'literal': 4, 'paraphrase': 12, 'confusable': 8, 'absent': 8}:
        raise ValueError('Category denominators must be 4 literal, 12 paraphrase, 8 confusable, 8 absent')


def _conditions(conditions, queries, where):
    if not isinstance(conditions, list) or len(conditions) != 4:
        raise ValueError(f'{where}: all four arms are required')
    for row, expected in zip(conditions, recalculate_conditions(queries)):
        _keys(row, {'id', *METRICS}, where)
        for key in METRICS:
            _integer(row[key], key)
        if row != expected:
            raise ValueError(f'{where}: aggregate disagrees with per-query outcomes or fixed arm order')


def validate_summary(d):
    """Validate every recursive field before a page can be rendered or written."""
    _keys(d, TOP_FIELDS, 'summary')
    if (type(d['schema_version']) is not int or d['schema_version'] != 1 or
            d['study_id'] != 'shiori-event-compatibility-2026-10-22' or
            d['date'] != '2026-10-22' or d['endpoint'] != 'relevant_original_source_scene_at_1'):
        raise ValueError('Unexpected study identity or endpoint')
    _keys(d['provenance'], PROVENANCE_FIELDS, 'provenance')
    for key, value in d['provenance'].items():
        if not isinstance(value, str) or not re.fullmatch('[a-f0-9]{64}', value):
            raise ValueError('Provenance permits named SHA-256 digests only')
    _keys(d['sample'], SAMPLE_VALUES, 'sample')
    for key, expected in SAMPLE_VALUES.items():
        _integer(d['sample'][key], key)
        if d['sample'][key] != expected:
            raise ValueError(f'Sample disagrees with frozen study design: {key}')
    m = d['method']
    _keys(m, METHOD_TRUE | METHOD_FALSE | {'event_review_prescore_repairs'}, 'method')
    _flags(m, METHOD_TRUE, METHOD_FALSE, 'method')
    _integer(m['event_review_prescore_repairs'], 'event_review_prescore_repairs')
    if m['event_review_prescore_repairs'] > 2:
        raise ValueError('At most two pre-score event-review repairs are allowed')
    _queries(d['per_query'], 'Q', fresh=True)
    _conditions(d['conditions'], d['per_query'], 'fresh conditions')
    k = d['known_regression']
    _keys(k, {'queries', 'positive_queries', 'literal_queries', 'paraphrase_queries', 'confusable_queries', 'absent_queries', 'per_query', 'conditions'}, 'known regression')
    for key in ('queries', 'positive_queries', 'literal_queries', 'paraphrase_queries', 'confusable_queries', 'absent_queries'):
        _integer(k[key], f'known {key}')
        if k[key] != SAMPLE_VALUES[key]:
            raise ValueError('Known regression requires its own frozen 32-query denominators')
    _queries(k['per_query'], 'K', fresh=False)
    _conditions(k['conditions'], k['per_query'], 'known regression conditions')
    v = d['verification']
    _keys(v, VERIFICATION_TRUE | VERIFICATION_FALSE | VERIFICATION_COUNTS, 'verification')
    _flags(v, VERIFICATION_TRUE, VERIFICATION_FALSE, 'verification')
    for key in VERIFICATION_COUNTS:
        _integer(v[key], key)
    for prefix in ('code_engineering', 'synthetic_engineering'):
        if v[prefix + '_passed'] > v[prefix + '_tests']:
            raise ValueError('Engineering passes exceed engineering checks')
    if v['failed_index_artifacts_retained'] != 3:
        raise ValueError('All three failed index artifacts must remain retained')
    if v['native_primary_search_calls'] != 3 * sum(q['retrieval']['native_route_count'] for q in d['per_query']):
        raise ValueError('Primary native calls must count normal and both ablation route executions')
    return d


def load_summary():
    path = ROOT / DATA_FILE
    if not path.is_file():
        raise FileNotFoundError('Audited public summary is unavailable; no study pages were written')
    return validate_summary(json.loads(path.read_text(encoding='utf-8')))


def label(arm, lang):
    return {
        'recovery_raw': T('検索仮説・ゲートなし', 'Recovery retrieval · no gate', lang),
        'strict_source_gate': T('厳格な原文ゲート', 'Strict source gate', lang),
        'event_review_only': T('出来事の適合レビュー', 'Event compatibility review', lang),
        'strict_and_event_review': T('厳格な原文＋出来事レビュー', 'Strict source + event review', lang),
    }[arm]


def outcome(result, positive, lang):
    if not result['search_executed']:
        return T('検索前に停止', 'Stopped before search', lang)
    if not result['returned_candidate']:
        return T('返却候補なし', 'No candidate returned', lang)
    if result['target_hit']:
        return T('対象場面', 'Target scene', lang)
    return T('別場面', 'Wrong scene', lang) if positive else T('対象外候補', 'False candidate', lang)


def results_table(conditions, lang, caption):
    return table(caption, [T('条件', 'Condition', lang), T('対象場面', 'Positive scene hits', lang), T('対象あり・別場面', 'Positive wrong-scene returns', lang), T('文字一致', 'Literal hits', lang), T('言い換え', 'Paraphrase hits', lang), T('紛らわしい対象・誤返却', 'Confusable false returns', lang), T('対象なし・誤返却', 'Absent false returns', lang), T('検索した質問', 'Queries searched', lang)],
        [[label(c['id'], lang), f"{c['positive_hits']} / 16", f"{c['positive_wrong_scene_returns']} / 16", f"{c['literal_hits']} / 4", f"{c['paraphrase_hits']} / 12", f"{c['confusable_false_returns']} / 8", f"{c['absent_false_returns']} / 8", f"{c['native_searches']} / 32"] for c in conditions], 'four-arm-table')


def ablation_table(queries, lang, caption):
    rows = []
    for row in recalculate_ablations(queries):
        variant = 'hops=0' if row['ablation'] == 'hops0' else 'convergence=false'
        rows.append([variant + ' · ' + label(row['id'], lang), f"{row['changed_selections']} / 32", f"{row['positive_hits']} / 16", f"{row['positive_wrong_scene_returns']} / 16", f"{row['confusable_false_returns']} / 8", f"{row['absent_false_returns']} / 8"])
    return table(caption, [T('無効化・条件', 'Ablation and condition', lang), T('最終選択が変化', 'Changed final selections', lang), T('対象場面', 'Positive hits', lang), T('対象あり・別場面', 'Positive wrong-scene returns', lang), T('紛らわしい対象・誤返却', 'Confusable false returns', lang), T('対象なし・誤返却', 'Absent false returns', lang)], rows, 'diagnostic-table')


def event_compatibility(lang, summary=None):
    if lang not in ('ja', 'en'):
        raise ValueError('Supported languages are ja and en')
    d = load_summary() if summary is None else validate_summary(summary)
    s, v, m = d['sample'], d['verification'], d['method']
    q = d['per_query']
    arms = {row['id']: row for row in d['conditions']}
    a, b = arms['strict_source_gate'], arms['strict_and_event_review']
    retained = a['positive_hits'] == b['positive_hits']
    headline = T(f'対象取得{b["positive_hits"]}/16を維持。' if retained else f'対象取得{a["positive_hits"]}/16 → {b["positive_hits"]}/16。', f'{b["positive_hits"]}/16 target hits retained.' if retained else f'Positive hits {a["positive_hits"]}/16 → {b["positive_hits"]}/16.', lang)
    headline += '<br>' + T(f'紛らわしい誤返却{a["confusable_false_returns"]}/8 → {b["confusable_false_returns"]}/8。', f'Confusable false returns {a["confusable_false_returns"]}/8 → {b["confusable_false_returns"]}/8.', lang)
    body = f'''<div class="event-study"><section class="study-hero"><p class="kicker">STUDY / EVENT COMPATIBILITY / v1</p><h1>{headline}</h1><p class="lead">{T(f'新たな実会話4件・新規32問。厳格な原文ゲートから、同じゲートに出来事の適合レビューを加えた条件へ、対象場面の取得は{a["positive_hits"]}/16 → {b["positive_hits"]}/16、紛らわしい対象への誤返却は{a["confusable_false_returns"]}/8 → {b["confusable_false_returns"]}/8、対象なしへの誤返却は{a["absent_false_returns"]}/8 → {b["absent_false_returns"]}/8でした。', f'Four further archived conversations and 32 newly authored queries. From the strict source gate to the same gate plus event compatibility review, positive-scene hits were {a["positive_hits"]}/16 → {b["positive_hits"]}/16; confusable false returns were {a["confusable_false_returns"]}/8 → {b["confusable_false_returns"]}/8 and absent false returns were {a["absent_false_returns"]}/8 → {b["absent_false_returns"]}/8.', lang)}</p><p class="note"><time datetime="{d['date']}">{d['date']}</time> · {T('固定した入力と保存済みの実際のAI出力による記録。閲覧中にAIや検索エンジンは動きません。', 'Recorded results from frozen inputs and saved actual AI outputs. Browsing runs neither an AI nor the retrieval engine.', lang)}</p></section>'''
    body += section('results', '01 / FRESH QUERIES', T('新規32問、全4条件。', 'Fresh 32 queries, all four conditions.', lang), content=results_table(d['conditions'], lang, T('新規評価のみ。既知の回帰問題を含めない。', 'Fresh evaluation only; known regression queries are excluded.', lang)) + f'<p class="note">{T("scene@1は、最終1候補が事前指定した原文場面かを測ります。対象あり16問、対象なし8問、紛らわしい対象8問を別々に報告し、総合点へ合算しません。", "Scene@1 measures whether the final single candidate is a predesignated original-source scene. The 16 positive, eight absent and eight confusable queries have separate denominators; they are not pooled into one score.", lang)}</p>')
    coverage = []
    for key, ja, en in [('original_native_top20_target_present', '元の発話・native上位20件', 'Original-query native top 20'), ('recovery_semantic_native_top20_target_present', '検索仮説・native上位20件', 'Recovery-semantic native top 20'), ('union_target_present', '重複を除いた全候補の合併', 'Full deduplicated candidate union')]:
        coverage.append([T(ja, en, lang), f"{sum(x['retrieval'][key] for x in q)} / 16"])
    cov = table(T('検索経路の対象カバレッジ。最終選択とは異なる。', 'Target coverage in retrieval routes, distinct from final selection.', lang), [T('候補範囲', 'Candidate scope', lang), T('対象を含んだ質問', 'Queries containing a target', lang)], coverage)
    max_union = max(x['retrieval']['unique_union_candidates'] for x in q)
    over20 = sum(x['retrieval']['unique_union_candidates'] > 20 for x in q)
    cov += f'<p>{T(f"各native経路は上位20件までです。経路の合併全体を20件に切り詰めません。実際の全合併の最大候補数は{max_union}件、20件を超えた質問は{over20}/32問でした。カバレッジは選択前に対象候補が存在したことを表し、その候補をゲートが選んだことを表しません。", f"Each native route contributes at most its top 20 candidates. The full route union is not truncated to 20. Its observed maximum was {max_union} candidates; {over20}/32 queries had more than 20. Coverage records target availability before selection; it does not show that a gate selected that target.", lang)}</p>'
    if max_union <= 1:
        cov += f'<div class="boundary-box"><p>{T("今回の新規標本では、各質問の全合併は最大1候補でした。複数の競合する原文場面から適切な1件を選ぶ能力は試していません。網の経路展開が0だった診断と併せ、この標本で動いた範囲に限って解釈します。", "The fresh sample had at most one candidate in each full union. It did not test choosing among multiple competing original scenes. Interpret the result within this limited case, alongside the zero-expansion graph diagnostic.", lang)}</p></div>'
    cov += table(T('全合併に対象があったのに、最終1件が対象にならなかった質問', 'Queries with an available target in the full union but no target at final rank one', lang), [T('条件', 'Condition', lang), T('対象ありの選択未達', 'Available target not selected', lang)], [[label(arm, lang), f"{sum(x['retrieval']['union_target_present'] and not x['conditions'][arm]['target_hit'] for x in q)} / 16"] for arm in ARMS])
    body += section('coverage', '02 / COVERAGE AND SELECTION', T('届いた候補と、選んだ場面を分ける。', 'Separate candidate coverage from scene selection.', lang), content=cov)
    mechanism = cards([
        (T('元の検索を先に実行', 'Retrieve the original query first', lang), T('既存のoriginal-firstの二値・ネットワーク候補取得を変更せず、元の発話と検索仮説のnative経路を合併します。4条件はこの候補列を共有します。', 'The existing original-first binary/network candidate retrieval remains unchanged. Original-query and recovery-semantic native routes form a shared candidate union for the four conditions.', lang)),
        (T('原文と質問から意味を照合', 'Review query meaning against linked originals', lang), T('実際のAIが質問と候補に結び付く原文を読み、出来事・行為・文脈・指示対象・役割・時点・様態の適合を確認しました。単語の一致や二値特徴の有無だけの判定ではありません。', 'An actual AI read each query and the candidate’s linked originals to review event, action, context, referent, role, time and mode compatibility. The review goes beyond word matching or binary-feature overlap.', lang)),
        (T('独立レビューと選択規則', 'Independent review and a fixed selection rule', lang), T(f'レビュー担当にはnativeの順位・点数・経路・厳格ゲートの判定、質問ラベルや種別を隠しました。別の担当が保存物に結び付けて確認し、採点前の修正は{m["event_review_prescore_repairs"]}回でした。通過した最初の候補を元のnative順で選び、点数を混合しません。', f'Native rank, score, route, strict-gate decisions, query labels and query kind were hidden from the review. A separate reviewer checked the bound artifact; there were {m["event_review_prescore_repairs"]} pre-score repairs. Selection takes the first passing candidate in native order, without mixing scores.', lang)),
    ])
    mechanism += f'<div class="boundary-box"><p>{T("これは原文に照らした意味上の適合レビューです。世界で出来事が真に起きたこと、出来事の実世界での同一性、候補を回答へ採用してよいことは確立しません。4条件の比較は、この固定標本での選択規則の記述的比較です。一般的な意味理解や因果的な改善の証明ではありません。", "This is a semantic compatibility review against source text. It does not establish world-event truth, real-world event identity or permission to adopt a candidate into an answer. The four conditions descriptively compare selection rules on this frozen sample; they do not prove general semantic understanding or causal improvement.", lang)}</p></div>'
    body += section('mechanism', '03 / ACTUAL REVIEW', T('検索の後に、原文を読む判断を置く。', 'Add a source-reading decision after retrieval.', lang), content=mechanism)
    counters = [sum(x['retrieval'][key] for x in q) for key in ('graph_expansions', 'graph_edges', 'associated_hits')]
    diagnostics = table(T('通常の共有経路を各質問1回だけ集計', 'Normal shared routes counted once per query', lang), ['Graph expansions', 'Graph edges', 'Associated hits'], [counters])
    diagnostics += ablation_table(q, lang, T('新規32問の実際の無効化診断。変更件数は通常実行との最終選択の比較。', 'Actual ablations on the fresh 32 queries. Changes compare final selections with normal execution.', lang))
    fresh_changes = sum(row['changed_selections'] for row in recalculate_ablations(q))
    if not any(counters) and fresh_changes == 0:
        diagnostics += f'<div class="boundary-box"><p>{T("新規32問では、経路展開・経路辺・関連ヒットはいずれも0でした。網を止めても合流を止めても、全4条件の最終選択はすべて同じです。この新規標本から、網や合流が最終選択を改善した証拠は得られていません。", "The fresh 32-query set had zero graph expansions, edges and associated hits. Disabling traversal or convergence left every final selection unchanged in all four conditions. This fresh sample provides no evidence that traversal or convergence improved final selection.", lang)}</p></div>'
    diagnostics += f'<p class="note">{T("選択一致は、内部の完全な場面IDをnullも含めて比較した真偽値です。場面IDは公開しません。経路の実行カウンタは、選択への寄与、固有の証拠数、保存や検索の速度を表しません。同じ通常経路を4条件で重複加算しません。", "Selection equality was computed internally from complete scene IDs, including null; scene IDs are not public. Route counters do not measure selection contribution, independent evidence or storage/search speed. Shared normal routes are not counted again for each of the four conditions.", lang)}</p>'
    body += section('diagnostics', '04 / NATIVE ABLATIONS', T('網と合流の診断も、実際の結果を残す。', 'Record actual graph and convergence diagnostics.', lang), content=diagnostics)
    known = d['known_regression']
    regression = results_table(known['conditions'], lang, T('既知32問の回帰確認。新規標本ではない。', 'Known 32-query regression check; not a fresh sample.', lang))
    regression += f'<p>{T("K01–K32は以前からある質問です。新規Q01–Q32の取得率や母数へ足しません。", "K01–K32 are previously known queries. Their results are not added to the fresh Q01–Q32 counts or denominators.", lang)}</p>'
    regression += ablation_table(known['per_query'], lang, T('既知32問だけの無効化診断。新規32問の診断とは別。', 'Ablations on the known 32 queries only, separate from the fresh-query diagnostics.', lang))
    known_normal = {row['id']: row for row in known['conditions']}
    known_ablation = {(row['ablation'], row['id']): row for row in recalculate_ablations(known['per_query'])}
    kn = known_normal['event_review_only']['positive_hits']
    kh = known_ablation['hops0', 'event_review_only']['positive_hits']
    kc = known_ablation['without_convergence', 'event_review_only']['positive_hits']
    regression += f'<p>{T(f"既知集合の出来事レビュー単独では、通常の対象取得{kn}/16に対し、網を止めたhops=0は{kh}/16、合流を止めた条件は{kc}/16でした。この差は既知集合での網の診断として扱います。", f"For event review alone on the known set, positive hits were {kn}/16 normally, {kh}/16 with hops=0, and {kc}/16 with convergence disabled. This difference is a graph diagnostic on the known set.", lang)}</p>'
    regression += f'<p class="note">{T("既知集合で網や合流を止めたときの変化は、再利用した質問上の診断です。新規の質問への一般化を示しません。最終場面の一致は内部でnullも含めて比較し、出典IDを公開しません。", "Changes when graph traversal or convergence is disabled on the known set are diagnostics on reused questions. They do not establish generalization to fresh queries. Final-scene equality was compared internally, including null, without publishing source IDs.", lang)}</p>'
    body += section('known-regression', '05 / SEPARATE REGRESSION', T('既知の32問は、新規評価に加えない。', 'Keep the known 32-query regression set separate.', lang), content=regression)
    method = f'<div class="boundary-box"><p>{T(f"保存済み会話{ s['archive_sessions'] }件、除外{s['excluded_sessions']}件、適格{s['eligible_sessions']}件を記録し、新たな4会話から各8件の原文メッセージを採用しました。機械的な件数確認では本文の文字列を復号しました。その後、選んだ本文の意味を読む前に選定を固定しました。原文のみを使う索引レビューで{s['reviewed_features']}特徴・{s['cue_concepts']}概念を確認し、コードの固定前に承認しました。", f"The retained selection record reports {s['archive_sessions']} archived sessions, {s['excluded_sessions']} excluded and {s['eligible_sessions']} eligible. Four further sessions supplied eight whole messages each. Mechanical counting decoded body strings; selection was then durably locked before semantic reading of the selected bodies. Source-only index review approved {s['reviewed_features']} features and {s['cue_concepts']} concepts before code freeze.", lang)}</p><p>{T("質問作成担当には原文を渡し、アルゴリズムの手順書は渡しませんでした。原文だけを使うよう指示しました。新規32問は文字一致4・言い換え12・対象なし8・紛らわしい対象8です。質問順とIDはseedを使って並べ替えました。担当の分離は同じホスト上の指示によるもので、モデルの識別子は記録できませんでした。", "The query author received source material without the algorithm protocol and was instructed to use only that material. The 32 fresh queries comprise four literal, 12 paraphrase, eight absent and eight confusable queries. Query order and IDs were permuted with a seed. Roles were separated by instructions on the same host; model identity was unavailable.", lang)}</p></div>'
    method += f'<div class="boundary-box"><h3>{T("最初の技術的失敗も保持", "The initial technical failure remains retained", lang)}</h3><p>{T(f"最初の索引構築は入力監査のalias不足により、一部DB書込みの後で失敗しました。質問を作る前の失敗物{v['failed_index_artifacts_retained']}件を保持しています。修正した事前検査は、入力不足なら書込み前に失敗します。コードの工学チェックは{v['code_engineering_passed']}/{v['code_engineering_tests']}件、研究手順の人工入力チェックは{v['synthetic_engineering_passed']}/{v['synthetic_engineering_tests']}件成功しました。この2組は別々に記録し、実会話の評価にも合算しません。", f"The first index build failed because an input-audit alias was missing, after partial database writes. All {v['failed_index_artifacts_retained']} failed artifacts remain retained from before query authoring. The corrected preflight fails before writes when required input is missing. Code engineering checks passed {v['code_engineering_passed']}/{v['code_engineering_tests']}; synthetic checks of the research procedure passed {v['synthetic_engineering_passed']}/{v['synthetic_engineering_tests']}. These two sets remain separate and are not pooled with the real-dialogue evaluation.", lang)}</p></div>'
    body += section('method', '06 / METHOD AND ISOLATION', T('固定の順序と、分離の限界。', 'Freeze order and limits of isolation.', lang), content=method)
    perquery = table(T('本文と出典IDを公開しない問別結果', 'Per-query outcomes without query text or source IDs', lang), [T('質問', 'Query', lang), T('種別', 'Category', lang)] + [label(arm, lang) for arm in ARMS], [[x['id'], T({'literal':'文字一致','paraphrase':'言い換え','confusable':'紛らわしい対象','absent':'対象なし'}[x['category']], x['category'], lang)] + [outcome(x['conditions'][arm], x['category'] in ('literal', 'paraphrase'), lang) for arm in ARMS] for x in q], 'per-query-table')
    body += section('per-query', '07 / OPAQUE OUTCOMES', T('問別の選択を、匿名のまま確認する。', 'Inspect each selection with opaque query IDs.', lang), content=f'<details><summary>{T("新規32問の結果を表示", "Show the fresh 32-query outcomes", lang)}</summary>{perquery}</details>')
    routes = sum(x['retrieval']['native_route_count'] for x in q)
    limits = f'<div class="boundary-box"><ul><li>{T("保存した実際のAI出力を再生し、独立した再生でも一致を確認しました。同じ判断が新しいAI生成でも再現するかは試していません。", "Saved actual AI outputs were replayed, with agreement checked by an independent replay. Fresh AI regeneration was not tested.", lang)}</li><li>{T(f"新規評価は通常経路{routes}回と2種類の無効化を含め、primaryのnative検索{v['native_primary_search_calls']}回です。新規評価の準備時再生{v['preparation_replay_native_search_calls']}回と独立再生{v['independent_replay_native_search_calls']}回は分けて記録します。既知回帰もprimary {v['known_regression_native_search_calls']}回、準備時再生{v['known_regression_preparation_replay_native_search_calls']}回、独立再生{v['known_regression_independent_replay_native_search_calls']}回を別々に記録します。さらに最終監査の追加再生として、新規{v['final_audit_additional_native_search_calls']}回・既知回帰{v['known_regression_final_audit_additional_native_search_calls']}回を別に記録します。これらの再生を評価問題や正答数へ加算しません。表の「検索した質問」は質問の件数で、物理的なnative呼出し数ではありません。", f"The fresh evaluation used {routes} normal native routes plus two ablations, totaling {v['native_primary_search_calls']} primary native search calls. Fresh preparation replay ({v['preparation_replay_native_search_calls']}) and independent replay ({v['independent_replay_native_search_calls']}) calls are recorded separately. The known regression set also has separate primary ({v['known_regression_native_search_calls']}), preparation replay ({v['known_regression_preparation_replay_native_search_calls']}) and independent replay ({v['known_regression_independent_replay_native_search_calls']}) call counts. The final audit added a further {v['final_audit_additional_native_search_calls']} fresh-set and {v['known_regression_final_audit_additional_native_search_calls']} known-regression native calls, recorded separately from the earlier replays. Replay counts are not added to evaluation-query or hit counts. “Queries searched” counts queries, not physical native calls.", lang)}</li><li>{T("公開JSONから集計は再計算できます。原文、質問本文、索引語、native AI保存物、正解の出典ID、私的な評価一式は非公開で、公開データだけで原文の意味やエンジン実行を外部監査することはできません。", "Public JSON permits aggregate recalculation. Original conversations, query text, index vocabulary, native AI artifacts, target source IDs and private evaluation artifacts remain private; public data alone does not permit external source auditing or an engine rerun.", lang)}</li><li>{T("世界での出来事の真偽や回答への採用は未検証です。保存・検索の計時、日常会話での自然な想起、生物学的な脳の再現、Emotion、full Wakeも評価していません。", "World-event truth and answer adoption are unverified. Storage/search timing, natural everyday recall, biological brain reproduction, Emotion and full Wake were not evaluated.", lang)}</li></ul></div>'
    limits += f'<details><summary>{T("保持された記録のSHA-256", "Retained record SHA-256 digests", lang)}</summary><dl class="fact-list">' + ''.join(f'<div><dt>{E(key)}</dt><dd><code>{E(value)}</code></dd></div>' for key, value in d['provenance'].items()) + '</dl></details>'
    limits += f'<div class="download-links"><a href="../../{DATA_FILE}" download>{T("公開集計JSONを取得", "Download public summary JSON", lang)}</a></div>'
    body += section('verification', '08 / REPLAY AND LIMITS', T('再生の一致と、まだ測っていないこと。', 'Replay agreement and what remains unmeasured.', lang), content=limits) + '</div>'
    doc = _pages.document(lang, True, T('SHIORI 出来事の適合レビュー・4条件比較', 'SHIORI event compatibility: four conditions', lang), T('新たな実会話4件・32問。候補取得後の出来事適合レビューを4条件で比較し、候補カバレッジ、最終選択、回帰、診断を区別。', 'Four further archived conversations and 32 queries compare post-retrieval event compatibility review in four conditions, separating candidate coverage, final selection, regression and diagnostics.', lang), body, study_path=STUDY, record_date=d['date'])
    return doc.replace('<script src="../../results.js" defer></script>', '<link rel="stylesheet" href="event-compatibility.css">')


def build():
    d = load_summary()
    rendered = {name: event_compatibility(lang, d) + '\n' for lang, name in [('ja', 'index.html'), ('en', 'en.html')]}
    path = ROOT / STUDY
    path.mkdir(parents=True, exist_ok=True)
    for name, html in rendered.items():
        (path / name).write_text(html, encoding='utf-8')


if __name__ == '__main__':
    build()

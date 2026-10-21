"""Render the next study from its audited public summary, never private inputs.

Missing or inconsistent public data is an error. No pending-result page, invented
metric or fallback to a previous study is written. Existing pages are untouched.
"""
from pathlib import Path
from html import escape as E
import importlib.util
import json
import re

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = 'data/shiori-retrieval-hypotheses-2026-10-21.json'
STUDY = 'studies/2026-10-21-retrieval-hypotheses/'
ARMS = ('baseline', 'legacy_gated', 'original_gated',
        'positive_union_gated', 'recovery_raw', 'recovery_gated')
CATEGORIES = ('literal', 'paraphrase', 'confusable', 'absent')
METRICS = ('positive_hits', 'positive_wrong_scene_returns', 'literal_hits', 'paraphrase_hits',
           'confusable_false_returns', 'absent_false_returns',
           'native_searches', 'pre_search_abstentions',
           'graph_expansions', 'graph_edges', 'associated_hits')
SAMPLE_FIELDS = {'sessions', 'source_messages', 'messages_per_session', 'queries',
                 'positive_queries', 'literal_queries', 'paraphrase_queries',
                 'confusable_queries', 'absent_queries', 'reviewed_features',
                 'cue_concepts', 'archive_sessions', 'excluded_sessions',
                 'eligible_sessions'}
VERIFICATION_FIELDS = {
    'saved_actual_ai_outputs_replayed', 'independent_replay_verified',
    'synthetic_engineering_tests', 'synthetic_engineering_passed',
    'pre_body_selection_locked', 'mechanical_metadata_repair_preserved',
    'source_event_identity_verified', 'model_regeneration_tested',
    'timing_measured', 'daily_brain_verified', 'emotion_verified',
    'full_wake_verified', 'external_source_audit_possible_from_public_data',
    'query_author_read_full_protocol', 'role_isolation_instruction_only',
    'model_identity_recorded',
    'semantic_review_repairs', 'pre_score_literal_requirements_removed',
}

# Reuse public presentation helpers without changing the prior-study builder.
_spec = importlib.util.spec_from_file_location('existing_public_pages', ROOT / 'tools/build_pages.py')
_pages = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_pages)
T, section, table, cards = _pages.T, _pages.section, _pages.table, _pages.cards


def _keys(obj, expected, name):
    if not isinstance(obj, dict) or set(obj) != set(expected):
        raise ValueError(f'{name}: unexpected or missing public fields')


def _integer(value, name):
    if type(value) is not int or value < 0:
        raise ValueError(f'{name}: expected a nonnegative integer')


def validate_summary(d):
    """Check the recursive public allowlist and recalculate fresh aggregates."""
    _keys(d, {'schema_version', 'study_id', 'date', 'endpoint', 'provenance',
              'sample', 'conditions', 'per_query', 'known_regression',
              'verification', 'boundaries'}, 'summary')
    if (d['schema_version'] != 1 or
            d['study_id'] != 'shiori-retrieval-hypotheses-2026-10-21' or
            d['date'] != '2026-10-21' or
            d['endpoint'] != 'relevant_original_source_scene_at_1'):
        raise ValueError('Unexpected study identity or endpoint')
    if not isinstance(d['provenance'], dict) or not d['provenance']:
        raise ValueError('Retained public provenance hashes are required')
    for key, value in d['provenance'].items():
        if not re.fullmatch('[a-z][a-z0-9_]*_sha256', key) or not isinstance(value, str) or not re.fullmatch('[a-f0-9]{64}', value):
            raise ValueError('Only named SHA-256 digests are allowed in provenance')
    s = d['sample']
    _keys(s, SAMPLE_FIELDS, 'sample')
    for key, value in s.items():
        _integer(value, key)
    if s['sessions'] != 4 or s['messages_per_session'] != 8 or s['source_messages'] != 32 or s['queries'] != 32:
        raise ValueError('This study requires four sessions, eight messages each, and 32 queries')
    if s['positive_queries'] != s['literal_queries'] + s['paraphrase_queries']:
        raise ValueError('Positive denominator does not match its categories')
    if sum(s[k + '_queries'] for k in CATEGORIES) != s['queries']:
        raise ValueError('Category denominators do not sum to all queries')
    if any(s[k + '_queries'] == 0 for k in CATEGORIES):
        raise ValueError('Every planned query category must be represented')
    if not isinstance(d['conditions'], list) or any(not isinstance(c, dict) for c in d['conditions']) or [c.get('id') for c in d['conditions']] != list(ARMS):
        raise ValueError('All six conditions must be supplied in the fixed order')
    if not isinstance(d['per_query'], list) or any(not isinstance(q, dict) for q in d['per_query']) or [q.get('id') for q in d['per_query']] != [f'Q{i:02}' for i in range(1, 33)]:
        raise ValueError('Fresh queries must use opaque study-local labels Q01–Q32')
    for q in d['per_query']:
        _keys(q, {'id', 'category', 'conditions'}, 'query')
        if q['category'] not in CATEGORIES:
            raise ValueError('Unexpected query category')
        _keys(q['conditions'], ARMS, 'query conditions')
        for result in q['conditions'].values():
            _keys(result, {'target_hit', 'returned_candidate', 'search_executed'}, 'query result')
            if any(type(value) is not bool for value in result.values()):
                raise ValueError('Per-query outcomes must be booleans')
            if result['target_hit'] and (q['category'] not in ('literal', 'paraphrase') or not result['returned_candidate']):
                raise ValueError('A target hit requires a positive query and a returned candidate')
            if result['returned_candidate'] and not result['search_executed']:
                raise ValueError('A returned candidate requires an executed search')
    for category in CATEGORIES:
        if sum(q['category'] == category for q in d['per_query']) != s[category + '_queries']:
            raise ValueError('Per-query category count disagrees with its denominator')
    for c in d['conditions']:
        _keys(c, {'id', *METRICS}, 'condition')
        for metric in METRICS:
            _integer(c[metric], metric)
        aid = c['id']
        expected = {}
        for category in ('literal', 'paraphrase'):
            expected[category + '_hits'] = sum(q['conditions'][aid]['target_hit'] for q in d['per_query'] if q['category'] == category)
        expected['positive_hits'] = expected['literal_hits'] + expected['paraphrase_hits']
        expected['positive_wrong_scene_returns'] = sum(q['conditions'][aid]['returned_candidate'] and not q['conditions'][aid]['target_hit'] for q in d['per_query'] if q['category'] in ('literal', 'paraphrase'))
        for category in ('confusable', 'absent'):
            expected[category + '_false_returns'] = sum(q['conditions'][aid]['returned_candidate'] for q in d['per_query'] if q['category'] == category)
        expected['native_searches'] = sum(q['conditions'][aid]['search_executed'] for q in d['per_query'])
        expected['pre_search_abstentions'] = s['queries'] - expected['native_searches']
        for metric, value in expected.items():
            if c[metric] != value:
                raise ValueError(f'{aid}: {metric} disagrees with per-query outcomes')
    r = d['known_regression']
    _keys(r, {'queries', 'positive_queries', 'confusable_queries', 'conditions'}, 'known regression')
    if (r['queries'], r['positive_queries'], r['confusable_queries']) != (32, 16, 8):
        raise ValueError('Known regression must retain its separate denominators')
    if not isinstance(r['conditions'], list) or any(not isinstance(c, dict) for c in r['conditions']) or [c.get('id') for c in r['conditions']] != list(ARMS):
        raise ValueError('Known regression requires all six conditions')
    for c in r['conditions']:
        _keys(c, {'id', 'positive_hits', 'confusable_false_returns'}, 'known regression condition')
        for metric, denominator in [('positive_hits', 16), ('confusable_false_returns', 8)]:
            _integer(c[metric], metric)
            if c[metric] > denominator:
                raise ValueError('Known regression count exceeds its denominator')
    v = d['verification']
    _keys(v, VERIFICATION_FIELDS, 'verification')
    for key, value in v.items():
        if key in ('synthetic_engineering_tests', 'synthetic_engineering_passed',
                   'semantic_review_repairs', 'pre_score_literal_requirements_removed'):
            _integer(value, key)
        elif type(value) is not bool:
            raise ValueError('Verification flags must be booleans')
    if v['synthetic_engineering_passed'] > v['synthetic_engineering_tests']:
        raise ValueError('Engineering passes exceed checks')
    for key in ('saved_actual_ai_outputs_replayed', 'pre_body_selection_locked',
                'mechanical_metadata_repair_preserved', 'query_author_read_full_protocol',
                'role_isolation_instruction_only'):
        if not v[key]:
            raise ValueError(f'The reported method requires {key}')
    for key in ('source_event_identity_verified', 'model_regeneration_tested',
                'timing_measured', 'daily_brain_verified', 'emotion_verified',
                'full_wake_verified', 'external_source_audit_possible_from_public_data',
                'model_identity_recorded'):
        if v[key]:
            raise ValueError(f'This study does not establish {key}')
    if not isinstance(d['boundaries'], list) or not all(isinstance(x, str) for x in d['boundaries']):
        raise ValueError('Boundaries must be public statements')
    return d


def load_summary():
    path = ROOT / DATA_FILE
    if not path.is_file():
        raise FileNotFoundError('Audited public summary is not available; no study pages were written')
    return validate_summary(json.loads(path.read_text()))


def label(arm, lang):
    return {
        'baseline': T('元の発話で検索', 'Original-query baseline', lang),
        'legacy_gated': T('従来の手掛かり＋ゲート', 'Legacy cues + gate', lang),
        'original_gated': T('元の発話＋ゲート', 'Original query + gate', lang),
        'positive_union_gated': T('元の発話＋肯定手掛かり＋ゲート', 'Original + positive cues + gate', lang),
        'recovery_raw': T('元の発話＋検索仮説', 'Original + search hypotheses', lang),
        'recovery_gated': T('元の発話＋検索仮説＋ゲート', 'Original + hypotheses + gate', lang),
    }[arm]


def chart(d, lang, metric, denominator, title, sid):
    rows = []
    for c in d['conditions']:
        n = c[metric]
        rows.append(f'<li class="chart-row" data-arm="{c["id"]}"><div class="chart-label"><strong>{label(c["id"], lang)}</strong><small>{c["id"]}</small></div><span class="chart-track" aria-hidden="true"><span class="chart-fill" style="width:{n / denominator * 100:.4f}%"></span></span><span class="chart-value">{n} / {denominator}</span></li>')
    return f'<figure class="summary-chart" aria-labelledby="{sid}"><figcaption id="{sid}">{title}</figcaption><ol class="chart-rows">{"".join(rows)}</ol></figure>'


def retrieval_hypotheses(lang, summary=None):
    if lang not in ('ja', 'en'):
        raise ValueError('Supported languages are ja and en')
    d = load_summary() if summary is None else validate_summary(summary)
    s, v = d['sample'], d['verification']
    arms = {c['id']: c for c in d['conditions']}
    legacy, recovery = arms['legacy_gated'], arms['recovery_gated']
    missed = sum(q['category'] in ('literal', 'paraphrase') and not q['conditions']['recovery_gated']['returned_candidate'] for q in d['per_query'])
    failed = missed + recovery['positive_wrong_scene_returns'] + recovery['confusable_false_returns'] + recovery['absent_false_returns']
    body = f'''<div class="retrieval-study"><section class="study-hero"><p class="kicker">STUDY / RETRIEVAL HYPOTHESES / v1</p><h1>{T('取得は増えた。<br>取り違えは残った。','More relevant hits.<br>Mix-ups remained.',lang)}</h1><p class="lead">{T(f'新たな実会話4件・新規32問で6条件を比較。従来の手掛かり＋原文ゲートでは対象場面の取得が{legacy["positive_hits"]}/{s["positive_queries"]}、元の検索を残して検索仮説を加えたゲート条件では{recovery["positive_hits"]}/{s["positive_queries"]}でした。紛らわしい対象への誤返却は{legacy["confusable_false_returns"]}/{s["confusable_queries"]}から{recovery["confusable_false_returns"]}/{s["confusable_queries"]}で変わらず、取り違えは解消していません。', f'Four further real conversations and 32 new queries compared six conditions. Positive-scene hits were {legacy["positive_hits"]}/{s["positive_queries"]} with legacy cues and the source gate, and {recovery["positive_hits"]}/{s["positive_queries"]} when the original route was retained and search hypotheses added before the gate. Confusable false returns stayed at {legacy["confusable_false_returns"]}/{s["confusable_queries"]} versus {recovery["confusable_false_returns"]}/{s["confusable_queries"]}; mix-ups were not resolved.',lang)}</p><p class="note"><time datetime="{d['date']}">{d['date']}</time> · {T('同じ固定DBと保存済みの実際のAI出力を使った比較。閲覧中にAIや検索エンジンは動きません。','The comparisons shared a frozen database and saved actual AI outputs. Browsing runs neither an AI nor the retrieval engine.',lang)}</p></section>'''
    body += f'<div class="finding-callout"><h2>{T("新しいゲート条件でも、期待を満たさない結果が残った。","The new gated condition still failed expected retrieval outcomes.",lang)}</h2><p>{T(f"対象ありで別の場面を返した{recovery['positive_wrong_scene_returns']}問、紛らわしい対象に誤候補を返した{recovery['confusable_false_returns']}問、対象ありで候補を返せなかった{missed}問。計{failed}問の未達です。原文と特徴が適合しても、探している出来事と同じとは限りません。", f"It returned a wrong scene on {recovery['positive_wrong_scene_returns']} positive query, a false candidate on {recovery['confusable_false_returns']} confusable query, and no candidate on {missed} positive query: {failed} failed expectations in total. Compatibility with source text and features does not establish that the intended event was retrieved.",lang)}</p></div>'
    body += f'<div class="finding-callout"><h2>{T("網は動いた。今回の上位1件は変わらなかった。","The graph ran. The selected top-one source did not change.",lang)}</h2><p>{T("独立した診断では、全32問・全6条件で、通常の実行、経路探索を止めた実行（hops=0）、手掛かりの合流を止めた実行（convergence=false）の選択場面がすべて同じでした。この標本では、網や合流による最終1候補の選択への寄与は確認できません。今回の取得増加を、網が効いた証拠や速度改善として扱いません。","Independent diagnostics found the same selected scene for all 32 queries in all six conditions under normal execution, disabled traversal (hops=0), and disabled convergence (convergence=false). No contribution of the graph or convergence to the final top-one selection was observed on this sample. The retrieval increase is not evidence of graph efficacy or a speed improvement.",lang)}</p></div>'

    results = chart(d, lang, 'positive_hits', s['positive_queries'], T('最終1候補が事前指定の対象場面 / 対象あり','Final single candidate matched a predesignated source scene / positive queries',lang) + f' {s["positive_queries"]}', 'positive-chart-title')
    results += chart(d, lang, 'confusable_false_returns', s['confusable_queries'], T('紛らわしい対象に候補を返した / 少ない方がよい','Candidate returned for a confusable target / lower is preferable',lang) + f' · {s["confusable_queries"]}', 'false-chart-title')
    rows = [[label(c['id'], lang), f'{c["positive_hits"]} / {s["positive_queries"]}', f'{c["positive_wrong_scene_returns"]} / {s["positive_queries"]}', f'{c["literal_hits"]} / {s["literal_queries"]}', f'{c["paraphrase_hits"]} / {s["paraphrase_queries"]}', f'{c["confusable_false_returns"]} / {s["confusable_queries"]}', f'{c["absent_false_returns"]} / {s["absent_queries"]}', f'{c["pre_search_abstentions"]} / {s["queries"]}'] for c in d['conditions']]
    results += table(T('新規32問・全6条件。既知の回帰問題は含まない。','Fresh 32 queries, all six conditions. Known regression cases are excluded.',lang), [T('条件','Condition',lang), T('対象場面の取得','Positive scene hits',lang), T('対象ありで別場面を誤返却','Wrong-scene returns on positive queries',lang), T('文字一致','Literal hits',lang), T('言い換え','Paraphrase hits',lang), T('紛らわしい対象への誤返却','Confusable false returns',lang), T('対象なしへの誤返却','Absent false returns',lang), T('検索前に停止','Pre-search abstentions',lang)], rows, 'six-arm-table')
    results += f'<p class="note">{T("評価は事前指定した原文場面へのscene@1です。回答の正確さや出来事そのものの同一性を示しません。異なる母数を総合点にせず、小規模な同一標本内の記述的比較として扱います。","The endpoint is scene@1 against predesignated original-source scenes. It does not establish answer accuracy or source-event identity. Distinct denominators are not combined into one score; these are descriptive comparisons within a small sample.",lang)}</p>'
    results += f'<p class="note">{T(f"診断条件positive_union_gatedは{arms['positive_union_gated']['positive_hits']}/{s['positive_queries']}。この標本では元の経路と肯定手掛かりの結合だけでは従来条件から増えず、否定・仮定・不確実性を検索仮説として残した条件で{recovery['positive_hits']}/{s['positive_queries']}になりました。raw条件の{arms['recovery_raw']['positive_hits']}/{s['positive_queries']}からゲートは正しい候補1件も落としており、検索と原文確認の双方に課題が残ります。", f"The diagnostic positive_union_gated condition scored {arms['positive_union_gated']['positive_hits']}/{s['positive_queries']}. On this sample, joining the original route with positive cues did not increase hits over the legacy condition; retaining negation, hypothetical cues and uncertainty as search hypotheses reached {recovery['positive_hits']}/{s['positive_queries']}. The gate also removed one correct candidate from the raw condition’s {arms['recovery_raw']['positive_hits']}/{s['positive_queries']}; both retrieval and source checking retain limitations.",lang)}</p>'
    body += section('results', '01 / FRESH HELD-OUT QUERIES', T('新しい32問で得た結果。','Results on 32 new queries.',lang), content=results)

    method = cards([
        (T('検索仮説の意味','What a search hypothesis means',lang), T('unknown以外の手掛かりは、否定や仮定を含んでも検索の入口として残します。不確実性だけで検索全体を止めません。検索候補になったことは、記述が事実であることや、答えに採用してよいことを意味しません。','Non-unknown cues can open retrieval even when negated or hypothetical. Uncertainty alone does not stop the whole search. Becoming a search candidate does not make a statement true or authorize its use in an answer.',lang)),
        (T('元の経路と順位を残す','Preserve the original route and order',lang), T('元の発話による検索を残し、その候補を先に置いて追加経路を結合します。経路間のスコア加算は行いません。従来条件は失敗を含めて比較に残し、回復条件だけを示しません。','Original-query retrieval stays available. Its candidates come first when additional routes are joined; scores are not summed across routes. The legacy condition remains in the comparison, including its failures.',lang)),
        (T('2つの診断条件','Two diagnostic conditions',lang), T('original_gatedは元の経路と厳格ゲート、positive_union_gatedは元の経路と肯定手掛かりを結合した厳格ゲートです。元の経路を戻す効果と、否定・仮定・不確実性を検索仮説として残す方針の効果を分けて見ます。','original_gated applies the strict gate to the original route. positive_union_gated joins the original route with positive cues before that gate. They separate restoring the fallback route from retaining negation, hypothetical cues and uncertainty as search hypotheses.',lang)),
        (T('ゲートは緩めない','Keep the strict source gate',lang), T('recovery_rawとrecovery_gatedで、同じ回復検索の候補に対するゲートの有無を比較します。原文リンク、原文内の文字、特徴の整合性を確認する厳格な条件は変更しません。ゲート通過だけでは人物・対象・出来事の同一性も確定しません。','recovery_raw and recovery_gated compare the same recovery retrieval with and without the gate. Strict checks of source links, source text and feature compatibility stay unchanged. Passing the gate alone does not establish person, object or event identity.',lang)),
    ])
    body += section('policy', '02 / SIX COMPARISON CONDITIONS', T('検索の入口と、答えへの採用を分ける。','Separate retrieval leads from answer adoption.',lang), content=method)

    selection = cards([
        (T('原文の意味を読む前に選定を固定','Lock selection before semantic reading',lang), T(f'保存済み{s["archive_sessions"]}セッションのうち、過去の使用・閲覧記録に基づく{s["excluded_sessions"]}件を除外。条件を満たす{s["eligible_sessions"]}候補から、時系列順の先頭4件と各会話の先頭8件を選びました。件数を機械的に確認した後、原文の意味を読む前に選定をファイルへ固定しました。件数確認では本文文字列のデコードが必要でした。公開JSONのpre_body_selection_lockedは、選定した本文の意味を読む前の固定を指します。', f'From {s["archive_sessions"]} archived sessions, {s["excluded_sessions"]} were excluded using retained prior-use and exposure records. The first four of {s["eligible_sessions"]} eligible sessions in chronological order and the first eight whole messages in each were selected. After mechanical counting, selection was durably fixed before semantic reading of selected bodies. Counting required decoding the body strings. The public pre_body_selection_locked flag refers to this pre-semantic lock.',lang)),
        (T('除外メタデータの修復を保持','Retain the exclusion-metadata repair',lang), T('最初の固定では、not_neededという状態フラグをレビュー済みと誤って数え、101件を除外していました。フラグの機械的な分類を修復して除外を91件に直し、選定パケット本文の意味を読む前に有効な選定を固定しました。失敗した固定と修復前後の記録はすべて保持。原文の適性や検索成績による選び直しは行っていません。「未使用」は保持されたローカル記録の範囲です。','The initial lock excluded 101 sessions because a not_needed status flag had been incorrectly classified as reviewed. The mechanical classification was repaired, reducing exclusions to 91, and the effective selection was fixed before semantic reading of selection-packet bodies. All failed-lock and before/after artifacts were retained. Source suitability and retrieval performance were not used to reselect inputs. Unused refers to retained local exposure records.',lang)),
        (T('質問に合わせない索引','Index without query tuning',lang), T(f'実際のAIが原文だけから{s["reviewed_features"]}特徴を作り、レビューを保存しました。検索語彙は{s["cue_concepts"]}概念。索引は質問作成前に固定し、原文・質問・対象指定と保存済みAI出力を全6条件で共用しました。', f'An actual AI authored {s["reviewed_features"]} source-only features and retained review outputs. The retrieval inventory contained {s["cue_concepts"]} concepts. The index was frozen before query authoring; all six conditions shared sources, queries, target labels and saved AI outputs.',lang)),
        (T('役割分離の範囲','Scope of role separation',lang), T('索引、質問・対象指定、手掛かり作成、レビューの役割を指示で分けました。手掛かり作成は原文・対象・検索結果を見ない条件です。質問作成者は許可された手順書の全文を読み、アルゴリズム設計には盲検ではありませんでした。索引・検索結果・既知回帰結果は見ていません。同じホスト上の指示による分離で、アクセス隔離や外部盲検試験ではありません。モデル識別情報は取得できていません。','Indexing, query and target authoring, cue generation and review used separate instructed roles. Cue generation was blind to sources, targets and retrieval results. The query author read the full permitted protocol and was not blind to algorithm design, but did not read the index, retrieval outcomes or known regression results. Roles were separated by instructions on a shared host, without access isolation or external blinding. Model identifiers were unavailable.',lang)),
    ])
    body += section('method', '03 / FROZEN FRESH INPUTS', T('どの原文を、いつ固定したか。','Which sources were frozen, and when.',lang), content=selection)
    repair = f'<div class="boundary-box"><p>{T(f"実際のAIによる最初の意味レビューは、根拠のない厳密な文字列要件{v['pre_score_literal_requirements_removed']}件を棄却しました。作者はその要件だけを取り除き、修正{v['semantic_review_repairs']}回を保存しました。新規32問の検索・採点を一度も行う前の修正です。手掛かり、質問、対象指定、索引、原文ゲートは変更していません。", f"The first actual AI semantic review rejected {v['pre_score_literal_requirements_removed']} arbitrary literal requirements. The author removed only those requirements and retained {v['semantic_review_repairs']} repair round. This occurred before any fresh-query retrieval or scoring. Cues, queries, target labels, the index and the source gate stayed unchanged.",lang)}</p></div>'
    body += section('amendment', 'PRE-SCORE SEMANTIC REVIEW', T('採点前に棄却された要件も残す。','Retain requirements rejected before scoring.',lang), content=repair)

    regression = d['known_regression']
    rows = [[label(c['id'],lang), f'{c["positive_hits"]} / {regression["positive_queries"]}', f'{c["confusable_false_returns"]} / {regression["confusable_queries"]}'] for c in regression['conditions']]
    known = f'<p class="note">{T("前研究の既知32問を、実装の回帰確認として再利用しました。修正の動機になった既知問題であり、新規32問の成績、未使用標本での改善、独立した追試として数えません。","The prior study’s known 32 queries were reused for implementation regression checks. These known cases helped motivate the changes; they are not fresh-query performance, improvement on an unused sample, or an independent replication.",lang)}</p>'
    known += table(T('既知の回帰32問だけの結果 / 新規評価から分離','Known 32-query regression only / separate from fresh evaluation',lang), [T('条件','Condition',lang), T('対象場面の取得','Positive scene hits',lang), T('紛らわしい対象への誤返却','Confusable false returns',lang)], rows)
    known += f'<p class="note"><a href="../2026-10-21-cross-session/{"index.html" if lang == "ja" else "en.html"}">{T("固定された前研究を読む","Read the unchanged prior study",lang)} →</a></p>'
    body += section('regression', '04 / KNOWN REGRESSION ONLY', T('既知問題の確認を、新規成績に混ぜない。','Keep known regression separate from new results.',lang), content=known)

    cat = dict(zip(CATEGORIES, [T('文字一致','Literal',lang), T('言い換え','Paraphrase',lang), T('紛らわしい対象','Confusable',lang), T('対象なし','Absent',lang)]))
    rows = []
    for q in d['per_query']:
        cells = [E(q['id']), cat[q['category']]]
        for aid in ARMS:
            c = q['conditions'][aid]
            if not c['search_executed']:
                outcome = T('検索前に停止','Stopped before search',lang)
            elif c['target_hit']:
                outcome = T('対象場面を取得','Target scene hit',lang)
            elif c['returned_candidate']:
                outcome = T('対象外候補を返却','Non-target candidate returned',lang)
            elif aid == 'recovery_gated' and q['conditions']['recovery_raw']['returned_candidate']:
                outcome = T('候補を棄却','Candidate rejected',lang)
            else:
                outcome = T('返却候補なし','No candidate returned',lang)
            cells.append(outcome)
        rows.append(cells)
    outcomes = table(T('今回専用の匿名ラベルQ01〜Q32 / 全6条件','Study-local opaque labels Q01–Q32 / all six conditions',lang), ['ID', T('種別','Category',lang)] + [label(a,lang) for a in ARMS], rows, 'run-table six-arm-table')
    outcomes += f'<p class="note">{T("「返却候補なし」は、検索で候補がなかった場合と、原文ゲートで返さなかった場合を含みます。回復2条件で検索候補を共有し、raw側が返した候補をgated側が返さなかった場合は「候補を棄却」と表示します。","No candidate returned includes both an empty retrieval and a candidate withheld by the source gate. For the recovery pair sharing retrieval, a candidate returned by raw and withheld by gated is shown as Candidate rejected.",lang)}</p>'
    body += section('queries', '05 / ALL FRESH QUERY OUTCOMES', T('全問の取得・誤返却・停止を残す。','Retain every hit, false return and abstention.',lang), T('質問本文、会話原文、特徴語、出典IDを公開しません。別研究の同じラベルとは対応しません。','Query text, conversations, feature vocabulary and source IDs remain private. Labels do not correspond to matching labels in other studies.',lang), f'<details><summary>{T("新規32問の全結果を見る","View every fresh-query outcome",lang)}</summary>{outcomes}</details>')

    checks = [
        T('同じ保存済みの実際のAI出力を再生して比較しました。AIの出力を再生成して同じ判断になるかは試していません。','Comparisons replayed the same saved actual AI outputs. Regenerating AI interpretations to test their stability was not evaluated.',lang),
        T(f'人工入力による工学チェックは{v["synthetic_engineering_tests"]}件中{v["synthetic_engineering_passed"]}件成功。これらは新規32問や既知32問と異なる検証で、取得率の母数に合算しません。', f'{v["synthetic_engineering_passed"]} of {v["synthetic_engineering_tests"]} synthetic engineering checks passed. They are distinct from both the fresh and known 32-query sets and are not pooled into retrieval rates.',lang),
        T('原文場面の指定と索引は内部確認です。公開JSONだけで第三者が原文の意味、出典の同一性、エンジンの実行を監査することはできません。','Source-scene labels and indexing were checked internally. Public JSON alone does not permit independent auditing of source meaning, source identity or engine execution.',lang),
        T('出来事の同一性、Emotion、full Wakeは未検証です。日常会話での自然な想起、生物学的な脳の再現は未検証です。今回は保存・検索の計時を行っていません。','Event identity, Emotion and full Wake remain unverified. Natural everyday recall and biological brain reproduction were not evaluated. Storage and retrieval were not timed in this study.',lang),
    ]
    checks.insert(1, T('独立した保存済み入力の再生一致を確認しました。','An independent replay checked agreement on the saved inputs.',lang) if v['independent_replay_verified'] else T('保存済み入力の独立した再生一致は、まだ確認されていません。','Agreement under an independent replay of saved inputs has not yet been verified.',lang))
    verify = '<div class="boundary-box"><ul>' + ''.join(f'<li>{x}</li>' for x in checks) + '</ul></div>'
    verify += f'<div class="boundary-box"><h3>{T("経路利用のカウンタと、寄与を分ける。","Separate traversal counters from retrieval contribution.",lang)}</h3><p>{T("以下は各条件が使う通常の検索経路出力の合計です。元の経路や手掛かりの経路を条件間で共有・再利用しているため、全6行を足して独立した実行数や証拠数にはできません。選択された固有場面数、取得精度、計時の値でもありません。経路探索・合流を止めても最終選択が同じだった診断を優先して解釈します。","These counters sum normal retrieval-route outputs used by each condition. Original and cue routes are shared and reused across conditions, so adding the six rows does not give independent runs or evidence counts. They are not unique selected scenes, retrieval accuracy or timing. Interpret them alongside the unchanged selections when traversal or convergence was disabled.",lang)}</p></div>'
    verify += table(T('共有する通常経路のカウンタ / 条件間で合算しない','Shared normal-route counters / do not sum across conditions',lang), [T('条件','Condition',lang), 'Graph expansions', 'Graph edges', 'Associated hits'], [[label(c['id'],lang), c['graph_expansions'], c['graph_edges'], c['associated_hits']] for c in d['conditions']])
    if d['boundaries']:
        verify += '<div class="boundary-box"><h3>' + T('公開集計に付属する評価範囲','Scope statements retained with the public summary',lang) + '</h3><ul>' + ''.join(f'<li>{E(value)}</li>' for value in d['boundaries']) + '</ul></div>'
    verify += f'<details><summary>{T("保持された記録の識別子","Retained record digests",lang)}</summary><dl class="fact-list">' + ''.join(f'<div><dt>{E(k)}</dt><dd><code>{E(value)}</code></dd></div>' for k,value in d['provenance'].items()) + '</dl></details>'
    verify += f'<div class="download-links"><a href="../../{DATA_FILE}" download>{T("公開集計JSONを取得","Download public summary JSON",lang)}</a></div>'
    body += section('verification', '06 / VERIFICATION AND LIMITS', T('再生の一致と、未検証の範囲。','Replay agreement and remaining limits.',lang), content=verify)
    implementation = f'<div class="boundary-box"><p>{T("新しい方針のコードは、非公開の実験ブランチへ明示的に選ぶopt-inの追加として反映しました。従来の方針は既定のままです。実験ブランチへの反映と、この標本の取得結果を、運用環境への導入や日常の性能と混同しません。運用中の記憶DBには導入しておらず、自動的なモデル呼出しやfull Wakeも追加していません。","The new policy code was merged only into the private experimental branch as an explicit opt-in addition. The legacy policy remains the default. Experimental-branch integration and results on this sample do not establish operational deployment or everyday performance. The policy has not been introduced into the operational memory database, and no automatic model caller or full Wake was added.",lang)}</p></div>'
    body += section('implementation', '07 / IMPLEMENTATION STATUS', T('実験への反映と、運用への導入を分ける。','Separate experimental integration from operational deployment.',lang), content=implementation)
    body += '</div>'
    doc = _pages.document(lang, True, T('SHIORI 検索仮説の6条件比較','SHIORI six-condition search-hypothesis study',lang), T('新規実会話4件・32問。元の発話の検索を残し、否定・仮定・不確実性を検索仮説として加える6条件を比較。既知回帰問題と限界を分離。','Four new real conversations and 32 queries compare six retrieval conditions preserving the original query while adding search hypotheses. Known regression results and verification limits are separate.',lang), body, study_path=STUDY, record_date=d['date'])
    # Charts are static. No script or prior-study chart control is required.
    doc = doc.replace('<script src="../../results.js" defer></script>', '<link rel="stylesheet" href="retrieval-hypotheses.css">')
    return doc


def build():
    d = load_summary()
    rendered = {name: retrieval_hypotheses(lang, d) + '\n' for lang, name in [('ja','index.html'), ('en','en.html')]}
    path = ROOT / STUDY
    path.mkdir(parents=True, exist_ok=True)
    for name, html in rendered.items():
        (path / name).write_text(html)


if __name__ == '__main__':
    build()

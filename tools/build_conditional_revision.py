"""Fail-closed public rendering of audited conditional-revision records only.

No private tasks, gold, sources or actor progress are read here. Saved replay
items and new AI choices keep distinct prediction scopes. All public counts and
paired outcomes are recalculated from the complete 21-item export.
"""
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://yuu-honda.github.io/lux-spiria-results/'
DATA_FILE = 'data/conditional-revision-2026-10-27.json'
STUDY = 'studies/2026-10-27-conditional-revision/'
REPLAY = 'experiments/conditional-revision-2026-10-27/'
ZIP_FILE = 'downloads/conditional-revision-2026-10-27.zip'
CODE_SHA256 = '61495538507742ab5c3d55721a4115bf9fb24542b605525c63edc6b8f4cb7297'
PROTOCOL_SHA256 = '3d93a91dbc93b6528ee65179e9f753041ce211ef9a2e073802377d7e0c4c6e8b'
CONDITIONS = {'legacy': 3, 'wrapped': 3, 'repair': 3,
              'raw_observations': 6, 'raw_observations_and_conditional_review': 6}
ARMS = ('raw_observations', 'raw_observations_and_conditional_review')
OLD_IDS = {'P01': 'D01', 'P03': 'D02', 'P05': 'D03'}
CATALOG = {'S01': ('D01', 'legacy_root'), 'S02': ('D01', 'wrapped_v2'),
           'S03': ('D02', 'legacy_root'), 'S04': ('D02', 'wrapped_v2'),
           'S05': ('D03', 'legacy_root'), 'S06': ('D03', 'wrapped_v2')}
LATER = {'F01': 'S01', 'F02': 'S04', 'F03': 'S05',
         'F04': 'S02', 'F05': 'S03', 'F06': 'S06'}
FORMATS = ('legacy_root', 'wrapped_v2')
SOURCE_FILES = {
    'data/shiori-pilot-2026-10-13.json': '5f1a09df554ac6a57b0ead347ae4f3bbd4ec9ed4866fc44e96f82926194f21c7',
    'data/shiori-cross-session-2026-10-21.json': '09f075d9f84bfb336912946b6f268056e2c0b1b8fd6ca8e58eb28d3d1ab34c99',
    'data/working-memory-source-fixed-2026-10-24.json': 'a7ce1a4553cd7b85f0780bf9f178c6940c2300461caaa90ade6025736f80a8b6',
}
SAMPLE = {'public_source_families': 3, 'saved_successful_actions': 3,
          'diagnostic_legacy_replays': 3, 'diagnostic_wrapped_replays': 3,
          'actual_ai_repair_actions': 3, 'new_objectives': 3,
          'formats_per_objective': 2, 'later_tasks_per_arm': 6,
          'later_arms': 2, 'later_actual_actions': 12, 'total_execution_items': 21}
ITEM_FIELDS = {'condition', 'id', 'source', 'origin_alias', 'format',
               'execution_status', 'error', 'validation_status', 'artifact_sha256',
               'prediction', 'prediction_scored', 'prediction_agreement',
               'canonical_characters', 'action_sha256', 'budget_exceeded'}
COUNT_FIELDS = ('items', 'accepted', 'rejected', 'artifacts_written',
                'budget_exceeded', 'execution_errors', 'invalid_actions')
ERROR_TYPES = {'KeyError', 'IndexError', 'TypeError', 'ValueError',
               'ZeroDivisionError', 'OverflowError', 'InvalidAction',
               'ExecutionError', 'ActionError', 'HarnessError', 'OSError',
               'FileNotFoundError', 'PermissionError', 'RuntimeError', 'JSONDecodeError'}
CLASSIFICATIONS = ('both_correct', 'corrected', 'regressed', 'both_wrong')
CHANGE_TYPES = ('conditional_update', 'confirmation', 'deferred')
PACKETS = ('repair_before', 'repair_after', 'later_raw', 'later_review')
SCOPE_TRUE = {'engineered_migration', 'shared_raw_observations',
              'repair_and_review_same_context', 'saved_actions_from_separate_prior_context',
              'all12_later_actions_frozen_before_feedback', 'fixed_task_and_dispatch_order',
              'independent_input_review_approved', 'independent_final_audit_approved'}
SCOPE_FALSE = {'full_current_json_provided', 'fresh_ai_regeneration_in_replay'}
PROVENANCE = {'code_sha256', 'protocol_sha256', 'input_freeze_sha256',
              'source_derivation_sha256', 'saved_action_sha256', 'repair_action_sha256',
              'review_sha256', 'later_action_freeze_sha256', 'results_sha256', 'final_audit_sha256'}
TOP_FIELDS = {'schema_version', 'study_id', 'date', 'sample', 'items', 'counts',
              'paired', 'review', 'packets', 'scope', 'provenance', 'replay'}


def _keys(value, expected, where):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise ValueError(f'{where}: unexpected or missing public fields')


def _integer(value, where, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f'{where}: expected integer at least {minimum}')


def _digest(value, where):
    if not isinstance(value, str) or not re.fullmatch('[a-f0-9]{64}', value):
        raise ValueError(f'{where}: SHA-256 only')


def aggregate_items(items):
    counts = {key: 0 for key in COUNT_FIELDS}
    for item in items:
        counts['items'] += 1
        counts[item['validation_status']] += 1
        counts['artifacts_written'] += int(item['artifact_sha256'] is not None)
        counts['budget_exceeded'] += int(item['budget_exceeded'])
        counts['execution_errors'] += int(item['execution_status'] == 'execution_error')
        counts['invalid_actions'] += int(item['execution_status'] == 'invalid_action')
    return counts


def paired_items(items):
    bound = {(item['condition'], item['id']): item for item in items}
    result = []
    for task, source in LATER.items():
        before, after = (bound[arm, task]['validation_status'] == 'accepted' for arm in ARMS)
        classification = ('both_correct' if before and after else 'corrected' if after else
                          'regressed' if before else 'both_wrong')
        result.append({'id': task, 'format': CATALOG[source][1], 'classification': classification})
    return result


def recalculate(items):
    """Recalculate exported aggregates without writing or authoring meaning."""
    return {'counts': {condition: aggregate_items([item for item in items if item['condition'] == condition])
                       for condition in CONDITIONS}, 'paired': paired_items(items)}


def _items(items):
    if not isinstance(items, list) or len(items) != 21:
        raise ValueError('items: retain all 21 execution items')
    bound = {}
    for item in items:
        _keys(item, ITEM_FIELDS, 'item')
        condition, task = item['condition'], item['id']
        if not isinstance(condition, str) or condition not in CONDITIONS:
            raise ValueError('item: unknown condition')
        if not isinstance(task, str) or task not in (LATER if condition in ARMS else OLD_IDS) or (condition, task) in bound:
            raise ValueError('item: missing/duplicate/unfrozen task binding')
        if condition in ARMS:
            source = LATER[task]; origin, fmt = CATALOG[source]
        else:
            source = origin = OLD_IDS[task]
            fmt = 'legacy_root' if condition == 'legacy' else 'wrapped_v2'
        if (item['source'], item['origin_alias'], item['format']) != (source, origin, fmt):
            raise ValueError('item: frozen source/origin/format binding differs')
        status = item['execution_status']
        if not isinstance(status, str) or status not in ('ok', 'unavailable', 'invalid_action', 'execution_error'):
            raise ValueError('item: unsupported execution status')
        if item['validation_status'] not in ('accepted', 'rejected') or not isinstance(item['validation_status'], str):
            raise ValueError('item: unsupported validation status')
        failed = status in ('invalid_action', 'execution_error')
        if failed:
            _keys(item['error'], {'type', 'sha256'}, 'item error')
            if not isinstance(item['error']['type'], str) or item['error']['type'] not in ERROR_TYPES:
                raise ValueError('item: preserve an allowlisted actual exception class')
            _digest(item['error']['sha256'], 'canonical raw-error digest')
            if item['artifact_sha256'] is not None or item['validation_status'] != 'rejected':
                raise ValueError('item: failed execution has no artifact and is rejected')
        else:
            if item['error'] is not None:
                raise ValueError('item: completed execution must have null error')
            _digest(item['artifact_sha256'], 'actual artifact digest')
        if item['validation_status'] == 'accepted' and status != 'ok':
            raise ValueError('item: supported numeric objectives require a completed artifact')
        if not isinstance(item['prediction'], str) or item['prediction'] not in ('accepted', 'rejected', 'uncertain'):
            raise ValueError('item: unsupported pre-execution prediction')
        scored = condition not in ('legacy', 'wrapped')
        if type(item['prediction_scored']) is not bool or item['prediction_scored'] != scored:
            raise ValueError('item: prior-v1 saved predictions must not be newly scored')
        expected = None if not scored or item['prediction'] == 'uncertain' else item['prediction'] == item['validation_status']
        if expected is None:
            if item['prediction_agreement'] is not None:
                raise ValueError('item: unscored/uncertain prediction requires null agreement')
        elif type(item['prediction_agreement']) is not bool or item['prediction_agreement'] != expected:
            raise ValueError('item: prediction agreement does not recalculate')
        _integer(item['canonical_characters'], 'item canonical characters', 1)
        if type(item['budget_exceeded']) is not bool or item['budget_exceeded'] != (item['canonical_characters'] > 6000):
            raise ValueError('item: actual character cap violation disagrees')
        _digest(item['action_sha256'], 'actual action digest')
        bound[condition, task] = item
    required = {(condition, task) for condition in CONDITIONS for task in (LATER if condition in ARMS else OLD_IDS)}
    if set(bound) != required:
        raise ValueError('items: every frozen execution binding is required')
    for task in OLD_IDS:
        a, b = bound['legacy', task], bound['wrapped', task]
        if any(a[field] != b[field] for field in ('prediction', 'canonical_characters', 'action_sha256')):
            raise ValueError('item: legacy/wrapped diagnostics must reuse identical saved actions')
    return bound


def validate_summary(d):
    _keys(d, TOP_FIELDS, 'summary')
    if type(d['schema_version']) is not int or d['schema_version'] != 1 or d['study_id'] != 'conditional-revision-2026-10-27' or d['date'] != '2026-10-27':
        raise ValueError('Unexpected study identity')
    _keys(d['sample'], SAMPLE, 'sample')
    for key, expected in SAMPLE.items():
        _integer(d['sample'][key], 'sample.' + key)
        if d['sample'][key] != expected:
            raise ValueError('sample: frozen denominators differ')
    _items(d['items'])
    expected = recalculate(d['items'])
    _keys(d['counts'], CONDITIONS, 'counts')
    for condition in CONDITIONS:
        _keys(d['counts'][condition], COUNT_FIELDS, 'condition counts')
        for field in COUNT_FIELDS:
            _integer(d['counts'][condition][field], 'count.' + field)
            if d['counts'][condition][field] != expected['counts'][condition][field]:
                raise ValueError('counts: every metric must recalculate from all 21 items')
    if not isinstance(d['paired'], list) or len(d['paired']) != 6:
        raise ValueError('paired: all six matched later items required')
    seen = set()
    by_id = {row['id']: row for row in expected['paired']}
    for row in d['paired']:
        _keys(row, {'id', 'format', 'classification'}, 'paired row')
        if not isinstance(row['id'], str) or row['id'] not in LATER or row['id'] in seen:
            raise ValueError('paired: duplicate/unknown ID')
        if row != by_id[row['id']]:
            raise ValueError('paired: format and correctness classification must recalculate')
        seen.add(row['id'])
    review = d['review']
    _keys(review, {'change_types', 'legacy_rule_preserved', 'grounded', 'canonical_characters', 'sha256'}, 'review')
    for field in ('change_types', 'legacy_rule_preserved', 'grounded'):
        if not isinstance(review[field], list) or len(review[field]) != 3:
            raise ValueError('review: exactly three actual entries required')
    if any(not isinstance(value, str) or value not in CHANGE_TYPES for value in review['change_types']):
        raise ValueError('review: actual AI classification must use allowlisted types')
    if any(type(value) is not bool for field in ('legacy_rule_preserved', 'grounded') for value in review[field]):
        raise ValueError('review: independent grounding/scope assessments must be boolean')
    _integer(review['canonical_characters'], 'review canonical characters', 1)
    _digest(review['sha256'], 'review digest')
    _keys(d['packets'], PACKETS, 'packets')
    for packet in d['packets'].values():
        _keys(packet, {'raw_sha256', 'canonical_characters'}, 'packet')
        _digest(packet['raw_sha256'], 'packet raw digest')
        _integer(packet['canonical_characters'], 'packet canonical characters', 1)
    _keys(d['scope'], SCOPE_TRUE | SCOPE_FALSE | {'provider_metadata'}, 'scope')
    for field in SCOPE_TRUE | SCOPE_FALSE:
        if type(d['scope'][field]) is not bool or d['scope'][field] != (field in SCOPE_TRUE):
            raise ValueError('scope: frozen role/interface/order/audit boundary differs')
    if d['scope']['provider_metadata'] is not None:
        raise ValueError('scope: unavailable provider metadata remains null')
    _keys(d['provenance'], PROVENANCE, 'provenance')
    for value in d['provenance'].values():
        _digest(value, 'provenance')
    if d['provenance']['code_sha256'] != CODE_SHA256 or d['provenance']['protocol_sha256'] != PROTOCOL_SHA256:
        raise ValueError('provenance: frozen controller/protocol hash differs')
    if review['sha256'] != d['provenance']['review_sha256']:
        raise ValueError('review: record and provenance digests disagree')
    _keys(d['replay'], {'manifest_sha256', 'readme_sha256', 'zip_sha256'}, 'replay')
    for value in d['replay'].values():
        _digest(value, 'replay')
    return d


def load_summary(root=None):
    root = ROOT if root is None else root
    path = root / DATA_FILE
    if not path.is_file():
        raise FileNotFoundError('Audited conditional-revision export unavailable; no publication writes')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate public JSON field')
            result[key] = value
        return result
    def nonfinite(value):
        raise ValueError('Nonfinite public JSON number is forbidden')
    return validate_summary(json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique, parse_constant=nonfinite))


def optional_summary(root=None):
    root = ROOT if root is None else root
    return load_summary(root) if (root / DATA_FILE).is_file() else None


def require_public_inputs(root, d):
    for relative, digest in SOURCE_FILES.items():
        path = root / relative
        if not path.is_file() or sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError('Frozen original public source missing or changed')
    for relative, field in [(REPLAY + 'manifest.json', 'manifest_sha256'),
                            (REPLAY + 'README.md', 'readme_sha256'), (ZIP_FILE, 'zip_sha256')]:
        path = root / relative
        if not path.is_file() or sha256(path.read_bytes()).hexdigest() != d['replay'][field]:
            raise ValueError('Audited replay manifest/README/external ZIP missing or changed')


def t(ja, en, lang):
    return ja if lang == 'ja' else en


def label(condition, lang):
    return {'legacy': t('保存操作・元形式で再実行', 'Saved action · legacy replay', lang),
            'wrapped': t('保存操作・包み替え形式で再実行', 'Saved action · wrapped replay', lang),
            'repair': t('実際のAIによる互換修正', 'Actual AI compatibility repair', lang),
            ARMS[0]: t('同じ生の観測記録', 'Same raw observations', lang),
            ARMS[1]: t('同じ観測記録＋条件付きレビュー', 'Same observations + conditional review', lang)}[condition]


def table(caption, heads, rows, css=''):
    return (f'<div class="table-wrap" role="region" tabindex="0" aria-label="{escape(caption, quote=True)}"><table class="{css}"><caption>{escape(caption)}</caption><thead><tr>' +
            ''.join(f'<th scope="col">{escape(str(value))}</th>' for value in heads) + '</tr></thead><tbody>' +
            ''.join('<tr><th scope="row">' + escape(str(row[0])) + '</th>' + ''.join(f'<td>{escape(str(value))}</td>' for value in row[1:]) + '</tr>' for row in rows) + '</tbody></table></div>')


def section(sid, kicker, title, body):
    return f'<section class="section" id="{sid}" aria-labelledby="{sid}-title"><div class="section-heading"><p class="eyebrow">{kicker}</p><h2 id="{sid}-title">{title}</h2></div>{body}</section>'


def selected(d, condition, fmt=None):
    return [item for item in d['items'] if item['condition'] == condition and (fmt is None or item['format'] == fmt)]


def paired_counts(d, fmt=None):
    return {key: sum(row['classification'] == key for row in d['paired'] if fmt is None or row['format'] == fmt)
            for key in CLASSIFICATIONS}


def finding(d, lang):
    a, b, repair = (d['counts'][condition] for condition in ('legacy', 'wrapped', 'repair'))
    pairs = paired_counts(d)
    text = f'<p>{t(f"同じ保存操作3件の受理は、元形式 {a['accepted']}/3、意図した包み替え形式 {b['accepted']}/3でした。新しく選んだAI修正は {repair['accepted']}/3 が受理されました。", f"The same three saved actions were accepted {a['accepted']}/3 on legacy files and {b['accepted']}/3 after the declared wrapping change. Newly chosen AI repairs were accepted {repair['accepted']}/3.", lang)}</p>'
    text += f'<p>{t(f"同じ後続6項目では、観測記録だけ → 同じ記録＋レビューで修正 {pairs['corrected']}、後退 {pairs['regressed']}でした。6項目は3つの新規目的を2形式で実行したもので、6つの独立した目的ではありません。", f"On the same six later items, raw observations → the same observations plus review corrected {pairs['corrected']} outcomes and regressed {pairs['regressed']}. These are three new objectives executed in two formats, not six independent objectives.", lang)}</p>'
    if pairs['corrected'] == pairs['regressed'] == 0:
        text += f'<p><strong>{t("この標本では、追加レビューによって受理される項目は変わりませんでした。", "On this sample, added review did not change which items were accepted.", lang)}</strong></p>'
    if d['review']['change_types'] == ['confirmation'] * 3:
        text += f'<p class="note">{t("実レビュー3件の分類はすべてconfirmationで、conditional_updateは0件です。保存された外部操作の互換修正と、本人の誤判断後の判断改訂を区別し、観測された分類をそのまま報告します。", "All three actual review entries are classified as confirmation; conditional_update is zero. Repairing a saved external operation is distinct from revising one's own mistaken judgment. The observed classifications are retained.", lang)}</p>'
    return text


def _outcomes(d, lang):
    rows = [[label(condition, lang), f'{d["counts"][condition]["accepted"]} / 3',
             d['counts'][condition]['execution_errors'], d['counts'][condition]['invalid_actions'],
             d['counts'][condition]['artifacts_written']] for condition in ('legacy', 'wrapped', 'repair')]
    result = table(t('旧操作の診断6件と、新しいAI修正3件を区別する。', 'Distinguish six saved-action diagnostics from three new AI repairs.', lang),
                   [t('段階', 'Stage', lang), t('受理', 'Accepted', lang), t('実行エラー', 'Execution errors', lang),
                    t('無効な操作', 'Invalid actions', lang), t('実成果物', 'Written artifacts', lang)], rows)
    result += f'<p class="note">{t("旧操作と予測は以前の別コンテキストで元形式向けに作られました。包み替え後の失敗は、新しいAIの誤答や予測失敗として採点しません。元形式での旧予測も今回の新しい予測成績に加えません。", "The saved actions and predictions came from a different earlier context for v1. Failures after wrapping are not scored as new-AI errors or miscalibration. Even legacy replay predictions are excluded from current prediction scores.", lang)}</p>'
    rows = []
    for arm in ARMS:
        for fmt in FORMATS:
            counts = aggregate_items(selected(d, arm, fmt))
            rows.append([label(arm, lang), fmt, f'{counts["accepted"]} / 3', counts['execution_errors'], counts['invalid_actions']])
    result += table(t('後続：3つの新規目的を各2形式、各条件6項目。', 'Later: three new objectives in two formats, six items per arm.', lang),
                    [t('条件', 'Arm', lang), t('形式', 'Format', lang), t('受理', 'Accepted', lang),
                     t('実行エラー', 'Execution errors', lang), t('無効な操作', 'Invalid actions', lang)], rows, 'cr-wide')
    pairs = []
    for fmt in (None, *FORMATS):
        counts = paired_counts(d, fmt)
        pairs.append([fmt or t('全6項目', 'All six items', lang), *[counts[key] for key in CLASSIFICATIONS]])
    result += table(t('同じ目的・同じ形式で対応づけた観測記録だけ → レビュー追加。', 'Paired same-objective, same-format raw observations → added review.', lang),
                    [t('層', 'Stratum', lang), t('両方受理', 'Both correct', lang), t('修正', 'Corrected', lang),
                     t('後退', 'Regressed', lang), t('両方不一致', 'Both wrong', lang)], pairs)
    objective_rows = []
    bound = {(item['condition'], item['source']): item for item in d['items'] if item['condition'] in ARMS}
    for origin in ('D01', 'D02', 'D03'):
        sources = [source for source, (family, _) in CATALOG.items() if family == origin]
        objective_rows.append([origin, *[bound[arm, source]['validation_status'] for source in sources for arm in ARMS]])
    result += table(t('3つの新規目的ごとの受理。各行は同じ目的を2形式で比較。', 'Acceptance by the three new objectives; each row compares the same objective in two formats.', lang),
                    ['Objective family', 'Legacy / raw', 'Legacy / review', 'Wrapped / raw', 'Wrapped / review'], objective_rows, 'cr-wide')
    return result


def render(lang, summary=None):
    if lang not in ('ja', 'en'):
        raise ValueError('Supported languages are ja and en')
    d = load_summary() if summary is None else validate_summary(summary)
    title = t('条件が変わったら、<br>何を直し、何を残すか。', 'When the format changes,<br>what changes and what stays?', lang)
    body = f'<div class="cr-study"><section class="study-hero"><p class="kicker">STUDY / CONTROLLED CONDITIONAL REVISION / v1</p><h1>{title}</h1><p class="lead">{t("公開済みデータの置き場所をpayloadの下へ移し、保存した読み方を再実行しました。実際のAIが新しい読み方を選び、元の形式では元の方法を保つ、という条件分岐を調べます。変更は意図した表層的なschema変更で、自然障害や信念・概念の学習を検証する課題ではありません。", "We moved previously public data under payload and replayed the saved reading operations. An actual AI chose a new reading method while retaining the old method for the original format. This deliberately engineered surface-schema change tests conditional compatibility, not a natural outage, belief revision or concept learning.", lang)}</p><p class="note">2026-10-27 · {t("保存済み実行記録。閲覧中にAIや実行エンジンは動きません。", "Stored execution record. Browsing runs neither an AI nor the execution engine.", lang)}</p></section>'
    purpose = f'<div class="boundary-box"><p>{t("主比較は、同じ生の観測記録 → 同じ記録＋AIの条件付きレビューです。両条件には旧目標・操作、実際の旧形式と包み替え形式の結果、schema観測、AI修正と実結果を同じように渡します。レビューだけが追加され、フィードバック有無の比較ではありません。", "The primary comparison is identical raw observations → the same observations plus an AI conditional review. Both arms receive old goals/actions, actual legacy/wrapped results, schema observations, AI repairs and their actual results. Only review access is added; this is not feedback versus no feedback.", lang)}</p></div>'
    body += section('purpose', '01 / QUESTION AND FINDING', t('互換修正と、本人の判断改訂を分ける。', 'Separate compatibility repair from revising one’s own judgment.', lang), purpose + finding(d, lang))
    migration = '<div class="cr-formats"><div><h3>legacy_root</h3><p>' + t('変更しない公開原本のコピー', 'Unchanged complete public-file copy', lang) + '</p></div><span aria-hidden="true">→</span><div><h3>artifact-container.v2</h3><p><code>payload</code> ' + t('の下へ同じparsed原本を移す', 'contains the same parsed original', lang) + '</p></div></div>'
    migration += f'<p>{t("包み替えはschema_versionとpayloadだけを持つ、事前に宣言した形式変更です。payload内の型・値は元と同じで、原本のバイト列は変更しません。旧形式で正しかったパスが新形式で使えないかを意図して検査します。自然に起きた障害や、新しい実会話の出来事として扱いません。", "The declared transformation has only schema_version and payload. Payload types and values equal the original, whose raw bytes remain unchanged. The test deliberately checks whether a valid legacy path fails in the new format. It is not a naturally occurring outage or a new dialogue episode.", lang)}</p>'
    migration += f'<p>{t("アクターは完全な現在のJSONを受け取りません。与えるのはsource handleと、実ファイルから作ったschema観測です。キーと配列順を保ち、数値などを型マーカーに置換し、条件のid文字列だけを残し、per_query/provenanceは省略を明示します。両条件へ同じ観測を渡します。形式の説明と旧形式を維持する指示があるため、適切な条件分岐を、自発的な概念学習とは呼びません。", "Actors do not receive full current JSON. They receive source handles and actual-file schema observations: keys/array order remain, scalars become type markers, only condition id strings remain, and per_query/provenance omissions are explicit. Both arms receive identical observations. Format descriptions and legacy-preservation instructions are supplied; appropriate conditional branching is not spontaneous conceptual learning.", lang)}</p>'
    body += section('migration', '02 / DECLARED FORMAT CHANGE', t('変えた条件と、保持した原本を明示する。', 'Declare the changed condition and preserved original.', lang), migration)
    sequence = [t('旧3操作を元形式と包み替え形式で各1回実行し、全6結果を保持。', 'Execute three saved operations once per format and retain all six results.', lang),
                t('新しいAIの1コンテキストが3修正と予測を選び、実行前に固定。', 'One fresh AI context chooses three repairs and predictions, frozen before execution.', lang),
                t('実際に修正3件を実行し、その結果だけを同じ修正コンテキストへ返す。', 'Execute all three repairs and return only actual results to the same repair context.', lang),
                t('同じコンテキストが条件付きレビュー3件を記録し、分類をそのまま保持。', 'That same context records three conditional-review entries; retain its actual classifications.', lang),
                t('別の新しい2コンテキストが共通の6課題に対する操作を選び、全12行動を結果の前に固定。', 'Two other fresh contexts choose operations for the same six frozen tasks; freeze all 12 before feedback.', lang)]
    flow = '<ol class="cr-sequence">' + ''.join(f'<li>{text}</li>' for text in sequence) + '</ol>'
    flow += f'<p>{t("合計21実行項目は、保存操作の再実行6＋新しいAI修正3＋後続12です。21回の新しいAI判断やprovider要求を意味しません。以前の保存操作は別のコンテキストで作られ、今回の修正選択と事後レビューだけが同じ新しいコンテキストの2ターンです。修正・レビューと後続操作の担当範囲では3コンテキスト・4ターンで、課題作成者・査読者・監査者はこの数に含めません。provider要求数や連続したモデル同一性は未確認です。", "The 21 execution items are six saved replays + three new AI repairs + 12 later actions, not 21 fresh AI decisions or provider requests. Saved actions came from a separate earlier context; only current repair choice and post-outcome review share one new context across two turns. Repair/review and later-operation roles use three contexts and four turns, excluding task authors, reviewers and auditors. Provider request counts and continuous model identity are unverified.", lang)}</p>'
    flow += f'<p class="note">{t("後続順はF01–F06で共通、開始順は観測記録だけ、次にレビュー追加です。条件順やprovider・時刻の効果は制御していません。意味を変更する再試行、得点後の課題やgold変更、失敗項目の除外は行いません。", "Later order is F01–F06 in both arms; dispatch is raw observations, then added review. Order, provider and time effects are uncontrolled. There are no semantic retries, post-score task/gold changes or failed-item exclusions.", lang)}</p>'
    body += section('sequence', '03 / ROLES AND REAL EXECUTION', t('選択、実行、結果後のレビューを区別する。', 'Distinguish choice, execution and post-outcome review.', lang), flow)
    body += section('results', '04 / ALL EXECUTION RESULTS', t('元形式と新形式を、別々に読む。', 'Read legacy and wrapped outcomes separately.', lang), _outcomes(d, lang))
    rows = []
    for index, change in enumerate(d['review']['change_types']):
        rows.append([index + 1, change, int(d['review']['grounded'][index]), int(d['review']['legacy_rule_preserved'][index])])
    review = table(t('実際のAI分類と、独立した原文根拠・旧形式範囲の監査。1=確認、0=確認できず。', 'Actual AI classifications and independent grounding/legacy-scope audit. 1=verified, 0=not verified.', lang),
                   [t('項目', 'Entry', lang), 'Change type', t('根拠', 'Grounded', lang), t('旧規則の範囲保持', 'Legacy rule preserved', lang)], rows)
    review += f'<p>{t("conditional_update・confirmation・deferredは本人の実際の分類です。分類をコードが作ったり、confirmationを修正成功へ読み替えたりしません。外部に保存する記録であり、モデルの重み学習・遅延保持・心理的な学習の数値にはしません。", "conditional_update, confirmation and deferred are the actor’s actual classifications. Code does not author them or reinterpret confirmation as judgment revision. This external record is not a numerical measure of model-weight learning, delayed retention or psychological learning.", lang)}</p>'
    review += f'<p>{t(f"レビュー全体は{d['review']['canonical_characters']}/6000 canonical文字、上限超過は{int(d['review']['canonical_characters'] > 6000)}件です。", f"The complete review has {d['review']['canonical_characters']}/6000 canonical characters, with {int(d['review']['canonical_characters'] > 6000)} cap violations.", lang)}</p>'
    packet_labels = {'repair_before': t('修正・同じcontextのターン1', 'Repair · shared-context turn 1', lang),
                     'repair_after': t('レビュー・同じcontextのターン2', 'Review · shared-context turn 2', lang),
                     'later_raw': label(ARMS[0], lang), 'later_review': label(ARMS[1], lang)}
    review += table(t('実際に渡したpacketのcanonical文字数と生バイト列hash', 'Canonical characters and raw-byte digests of actual input packets', lang),
                    [t('役割', 'Role', lang), t('canonical入力文字数', 'Canonical input characters', lang), 'Raw SHA-256'],
                    [[packet_labels[key], d['packets'][key]['canonical_characters'], d['packets'][key]['raw_sha256']] for key in PACKETS], 'cr-digests')
    output_rows = []
    for condition in CONDITIONS:
        items = selected(d, condition)
        output_rows.append([label(condition, lang), len(items), sum(item['canonical_characters'] for item in items),
                            max(item['canonical_characters'] for item in items), sum(item['budget_exceeded'] for item in items)])
    review += table(t('実行項目ごとの保存操作文字数。旧操作の再利用は新しい生成ではない。', 'Saved-action characters per execution item; reusing an old action is not new generation.', lang),
                    [t('条件', 'Condition', lang), t('項目', 'Items', lang), t('合計', 'Sum', lang), t('最大 / 上限6000', 'Maximum / cap6000', lang), t('超過', 'Overruns', lang)], output_rows, 'cr-wide')
    review += f'<p class="note">{t("canonical JSONはUnicodeを保ち、キー順と整形空白をそろえ、文字列本文は変更しません。入力長は実際に異なります。同じ行動機会と上限・証拠でも同じ計算量とは言えず、上限超過だけで成果物を不正解にしません。モデル名・設定・要求数・token計算量は未取得でnullです。", "Canonical JSON retains Unicode and standardizes keys/formatting without changing string text. Actual input lengths differ. Shared opportunities, caps and evidence do not establish equal compute; cap overrun alone does not make an artifact incorrect. Model identity, settings, request counts and token compute were unavailable and remain null.", lang)}</p>'
    body += section('review-costs', '05 / REVIEW AND COSTS', t('確認・更新・保留を、実際の分類で残す。', 'Retain actual confirmation, update and deferral labels.', lang), review)
    item_rows = []
    for condition in CONDITIONS:
        for item in sorted(selected(d, condition), key=lambda row: row['id']):
            item_rows.append([label(condition, lang), item['id'], item['source'], item['origin_alias'], item['format'],
                              item['execution_status'], item['validation_status'], item['error']['type'] if item['error'] else '—',
                              item['prediction'], int(item['prediction_scored']),
                              '—' if item['prediction_agreement'] is None else int(item['prediction_agreement']), item['canonical_characters']])
    items = '<details><summary>' + t('全21項目の状態・予測・文字数', 'All 21 statuses, predictions and character counts', lang) + '</summary>'
    items += table(t('保存操作の予測は採点0、agreementはnull。新しい修正・後続予測だけを採点。', 'Saved predictions have scored=0 and null agreement; only current repair/later predictions are scored.', lang),
                   ['Condition', 'ID', 'Source', 'Origin', 'Format', 'Execution', 'Validation', 'Error type', 'Prediction', 'Scored', 'Agreement', 'Characters'], item_rows, 'cr-items') + '</details>'
    body += section('items', '06 / RETAINED ITEM RECORDS', t('失敗と、採点しない旧予測も保持する。', 'Retain failures and excluded prior predictions.', lang), items)
    limits = f'<div class="boundary-box"><p>{t("3つの公開出典群、3つの新規目的、各2形式という設計課題の記述的試験です。型と値の機械的な検証であり、コードが自然言語の理解や学習を意味採点したものではありません。旧形式の失敗は別に保持しますが、出力の誤りだけで主観的な過剰一般化の原因は判定できません。", "This is a descriptive engineered task over three public source families and three new objectives in two formats. Validation mechanically compares types and values; code does not grade natural-language understanding or learning. Legacy failures are retained separately, but incorrect output alone cannot establish subjective overgeneralization.", lang)}</p></div>'
    limits += f'<p>{t("元の数値は過去に公開されており、事前接触や訓練での露出は除外できません。今回の入力はschema観測＋handleに制限した人工的なinterfaceです。役割は同じhost上で指示により分離し、OS隔離やprovider同一性は保証しません。自然な想起、自発的概念獲得、モデル重み学習、native ChatGPT、全LRE Wake、SHIORIの網・二値速度、Emotion、生物学的な脳・AGI・意識は検証していません。", "Original values were previously public, so prior exposure or training cannot be excluded. This is an artificial interface restricted to schema observations and handles. Roles shared a host with instruction separation, not OS isolation or authenticated provider identity. Natural recall, spontaneous concept acquisition, model-weight learning, native ChatGPT, full LRE Wake, SHIORI graph/binary speed, Emotion, biological brains, AGI and consciousness were not tested.", lang)}</p>'
    limits += f'<p><a href="../../{DATA_FILE}">{t("全項目・集計JSON", "All items and aggregate JSON", lang)}</a></p><details><summary>{t("監査用hash", "Audit digests", lang)}</summary>' + table('SHA-256', ['Artifact', 'SHA-256'], [[key, d['provenance'][key]] for key in sorted(PROVENANCE)], 'cr-digests') + '</details>'
    body += section('limits', '07 / LIMITS', t('互換修正の観測を、学習の証明へ拡張しない。', 'Keep compatibility observations within their scope.', lang), limits)
    replay = f'<p>{t("公開済みの原本、宣言した包み替え、保存操作、新しいAI選択、実出力、レビューとコードを公開して、保存された処理を決定的に再実行します。新しいAIの判断を生成し直す処理ではありません。以前の7研究・データ・リプレイ・4つのストーリーの履歴は変更しません。", "Public originals, the declared wrapper, saved operations, new AI choices, actual outputs, review and code support deterministic saved-action replay. It does not regenerate fresh AI decisions. The seven earlier studies/data/replay and four overview stories retain their history.", lang)}</p>'
    replay += f'<div class="download-links"><a href="../../{REPLAY}README.md">{t("公開リプレイ手順", "Public replay instructions", lang)} ↗</a><a href="../../{ZIP_FILE}" download>ZIP ↓</a></div>'
    body += section('public-replay', '08 / PUBLIC REPLAY', t('保存された実行を、公開データで再確認する。', 'Recheck saved execution against public data.', lang), replay)
    return _document(lang, body + '</div>')


def _document(lang, body):
    title = t('形式変更と条件付きの互換修正', 'Format change and conditional compatibility repair', lang)
    description = t('意図した形式変更、保存操作6再実行、実際のAI修正3、同じ新規目的の後続12。全21項目とレビュー・限界・公開リプレイ。', 'Declared migration, six saved replays, three actual AI repairs and 12 later actions on matched objectives: all 21 items, review, limits and public replay.', lang)
    canonical = BASE + STUDY + ('' if lang == 'ja' else 'en.html')
    results = '../../results.html' if lang == 'ja' else '../../results.en.html'
    home = '../../index.html' if lang == 'ja' else '../../index.en.html'
    switch = ''.join(f'<a href="{href}" lang="{code}" hreflang="{code}"' + (' aria-current="page"' if lang == code else '') + f'>{name}</a>' for href, code, name in [('index.html', 'ja', '日本語'), ('en.html', 'en', 'EN')])
    return f'''<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title} — LUX SPIRIA Results</title><meta name="description" content="{description}">
<link rel="canonical" href="{canonical}"><link rel="alternate" hreflang="ja" href="{BASE+STUDY}"><link rel="alternate" hreflang="en" href="{BASE+STUDY}en.html"><link rel="alternate" hreflang="x-default" href="{BASE+STUDY}"><meta name="theme-color" content="#090d12"><meta property="og:type" content="website"><meta property="og:title" content="{title} — LUX SPIRIA Results"><meta property="og:description" content="{description}"><meta property="og:url" content="{canonical}"><meta property="og:image" content="{BASE}assets/lux-symbol.png"><link rel="icon" type="image/png" sizes="32x32" href="../../assets/favicon-32.png"><link rel="apple-touch-icon" sizes="180x180" href="../../assets/apple-touch-icon.png"><link rel="manifest" href="../../{'site' if lang=='ja' else 'site.en'}.webmanifest"><link rel="stylesheet" href="../../site.css"><link rel="stylesheet" href="../../theme-dark.css"><link rel="stylesheet" href="conditional-revision.css"></head>
<body><a class="skip-link" href="#main">{t('本文へ','Skip to content',lang)}</a><div class="page"><header class="masthead"><a class="brand" href="{results}" aria-label="LUX SPIRIA Results"><img src="../../assets/lux-symbol.png" alt="" width="44" height="44"><span class="brand-wordmark">LUX SPIRIA<span class="brand-subtitle">RESEARCH RESULTS</span></span></a><nav aria-label="{t('主なページ','Main navigation',lang)}"><a href="{results}#studies">{t('研究結果','Studies',lang)}</a><a href="#limits">{t('限界','Limits',lang)}</a><a href="{home}">{t('全体像','Overview',lang)}</a><span class="lang">{switch}</span></nav></header><main id="main">{body}</main><footer class="footer"><nav aria-label="{t('資料と規約','Resources and terms',lang)}"><a href="{home}">LUX SPIRIA</a><a href="../../LICENSE">License / LSP-1.0</a><a href="https://github.com/Yuu-Honda/lux-spiria-results">GitHub ↗</a></nav><small>RESULT RECORD / 2026-10-27 · v1</small></footer></div></body></html>'''


def build():
    d = load_summary(); require_public_inputs(ROOT, d)
    pages = {'index.html': render('ja', d), 'en.html': render('en', d)}
    destination = ROOT / STUDY
    destination.mkdir(parents=True, exist_ok=True)
    for name, text in pages.items():
        (destination / name).write_text(text, encoding='utf-8')
    return pages


if __name__ == '__main__':
    try:
        build()
    except (FileNotFoundError, ValueError) as error:
        raise SystemExit(str(error)) from error

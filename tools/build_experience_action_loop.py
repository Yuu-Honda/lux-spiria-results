"""Render an audited public export; absent data creates no study or result."""
import argparse
from hashlib import sha256
from html import escape
import importlib.util
import io
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://yuu-honda.github.io/lux-spiria-results/'
DATA_FILE = 'data/experience-action-loop-2026-10-30.json'
STUDY = 'studies/2026-10-30-experience-action-loop/'
REPLAY = 'experiments/experience-action-loop-2026-10-30/'
ZIP_FILE = 'downloads/experience-action-loop-2026-10-30.zip'
_spec = importlib.util.spec_from_file_location('experience_action_public_schema', ROOT / 'tools/experience_action_schema.py')
schema = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(schema)
validate_summary = schema.validate_summary
ARMS, PHASES = schema.ARMS, schema.PHASES
CSS = '''.eal-study{min-width:0}.eal-study h1{text-wrap:balance}.eal-study .section{margin-block:3rem}.eal-study .lead{max-width:65rem}.eal-study .table-wrap{max-width:100%;overflow:auto;overscroll-behavior-x:contain;border:1px solid var(--line);border-radius:10px}.eal-study table{border-collapse:collapse;min-width:740px;width:100%}.eal-study caption{padding:1rem;text-align:left;color:#bdcad7;white-space:normal}.eal-study th,.eal-study td{padding:.8rem;text-align:left;vertical-align:top;border-bottom:1px solid var(--line)}.eal-study tbody tr:last-child>*{border-bottom:0}.eal-study .eal-scroll-hint{font-size:.85rem;color:#b5c3d0;margin:.6rem 0;max-width:75ch}.eal-study details{margin:1rem 0;border:1px solid var(--line);border-radius:8px;padding:.75rem 1rem;min-width:0}.eal-study summary{cursor:pointer;overflow-wrap:anywhere}.eal-study p,.eal-study li,.eal-study code,.eal-study td,.eal-study th{overflow-wrap:anywhere}.eal-study pre{margin:.8rem 0;white-space:pre-wrap;overflow-wrap:anywhere;word-break:break-word;font:.8rem/1.7 var(--mono);color:#d9e4ef;background:#101923;padding:1rem;max-width:100%;border-radius:6px}.eal-study .download-links{display:flex;flex-wrap:wrap;gap:1rem}.eal-study .eal-note{color:#bac7d5;margin:.9rem 0}.eal-study .eal-digests td{font: .8rem/1.7 var(--mono);word-break:break-all}.eal-study .eal-source-id{font: .85rem/1.7 var(--mono)}.eal-study .boundary-box p+p{margin-top:1rem}@media(max-width:700px){.eal-study .section{margin-block:2rem}.eal-study details{padding:.65rem}.eal-study caption{max-width:calc(100vw - 4rem)}.eal-study table{min-width:680px}}'''


def t(ja, en, lang):
    return ja if lang == 'ja' else en


def label(arm, lang):
    return {'full': t('全接続', 'Full loop', lang),
        'hops0': t('経路0段', 'Zero hops', lang),
        'no_writeback': t('新判断の再保存なし', 'No new-judgment writeback', lang),
        'no_history': t('過去記録なし', 'No history', lang)}[arm]


def phase_label(phase, lang):
    return {'R': t('R / 変更後の条件', 'R / changed conditions', lang),
        'L': t('L / 旧条件へ戻る', 'L / return to legacy conditions', lang),
        'N': t('N / 未観測の条件', 'N / unobserved conditions', lang)}[phase]


def boundary(lang):
    return t('isolated native componentsでの人工課題です。全Wake・Emotion・脳・AGI・自然会話・重み学習を検証していません。共有FS上の指示による読取allowlistであり、OS隔離ではありません。',
        'Engineered tasks use isolated native components. Full Wake, Emotion, brains, AGI, natural conversation and weight learning were not evaluated. Roles use instruction-based read allowlists on a shared filesystem, not OS isolation.', lang)


def aggregate(d, phase, arm):
    return next(row for row in d['aggregates'] if (row['phase'], row['arm']) == (phase, arm))


def finding(d, lang):
    full = [aggregate(d, p, 'full')['artifact_accepted'] for p in PHASES]
    raw = [aggregate(d, p, 'no_writeback')['artifact_accepted'] for p in PHASES]
    if full == raw:
        return t('全接続と新判断の再保存なしは、各phaseの受理数が同じでした。新判断が再び返った事実と、その追加利益は分けます。raw evidenceが十分な範囲で、新判断による追加の受理改善は示していません。',
            'Full loop and no new-judgment writeback had equal acceptance counts in each phase. Returning a new judgment and gaining an additional benefit are separate outcomes. These results do not show additional acceptance gains from a new judgment where raw evidence was sufficient.', lang)
    return t('全接続と新判断の再保存なしの受理数はphaseごとに併記します。新判断が再び返っただけで追加利益とは呼びません。この小規模な人工課題の差から、一般的な学習効果や自然会話への利益は導きません。',
        'Acceptance counts for full loop and no new-judgment writeback are shown by phase. A returned new judgment alone is not an additional benefit. Differences in these small engineered tasks do not establish general learning or natural-conversation benefits.', lang)


def hero_finding(d, lang):
    full = [r for r in d['rows'] if r['phase'] in ('R', 'L') and r['arm'] == 'full']
    raw = [r for r in d['rows'] if r['phase'] in ('R', 'L') and r['arm'] == 'no_writeback']
    a, b = sum(r['artifact_accepted'] for r in full), sum(r['artifact_accepted'] for r in raw)
    if a == len(full) and b == len(raw):
        text = t(f'全接続と、新しい判断を加えない条件は、新旧の課題でそれぞれ{len(full)}件すべて受理されました。',
            f'Both the full loop and the condition without new judgments produced accepted results for all {len(full)} tasks covering the old and changed conditions.', lang)
    else:
        text = t(f'新旧の課題で、全接続は{a}/{len(full)}件、新しい判断を加えない条件は{b}/{len(raw)}件が受理されました。',
            f'Across old and changed conditions, accepted results were {a}/{len(full)} with the full loop and {b}/{len(raw)} without new judgments.', lang)
    if a == b:
        text += t(' 同じ成績だったため、新しい判断を追加する効果は確認できていません。',
            ' With equal results, no additional benefit from adding the new judgment was established.', lang)
    else:
        text += t(' 新しい判断が返ることと、追加の効果があることは分けて評価します。',
            ' Returning a new judgment and gaining an additional benefit are assessed separately.', lang)
    return text


def eligible_source_note(d, lang):
    """Explain the narrow original-source contract without recoding false rows."""
    failed = [r for r in d['rows'] if not r['all_quotes_exact']]
    note = t(f'適格な原出典の確認は{len(d["rows"]) - len(failed)}/{len(d["rows"])}件がtrue、{len(failed)}件がfalseでした。',
        f'The eligible original-source check is true for {len(d["rows"]) - len(failed)}/{len(d["rows"])} rows and false for {len(failed)} row{"s" if len(failed) != 1 else ""}.', lang)
    if failed:
        notices = [r for r in failed if all(e['source_id'] == 'QUERY_RESULT.json'
            for e, exact in zip(r['action']['evidence'], r['exact_quote_checks']) if not exact)]
        if len(notices) == len(failed):
            note += t(' falseの行は、実際に返されたunavailability通知を引用しています。通知文自体が実packetと一致することは独立監査で確認しました。このcheckは、予登録された原tool出力／native judgmentという適格なsource型から外れるためfalseです。架空引用や通知文の不一致を示す値ではありません。棄権の意味的妥当性は別に監査します。',
                ' The false rows quote actual returned unavailability notices. Independent audit confirmed that the notice text matches the actual packet. The check is false because a notice falls outside the preregistered eligible source types of original tool output and native judgment. It does not indicate fabricated quotations or mismatched notice text. The semantic appropriateness of abstention is audited separately.', lang)
        else:
            note += t(' falseは、予登録された原tool出力／native judgmentの出典契約を満たさない結果です。それだけで架空引用と判定する値ではありません。実通知の引用、本文一致、棄権の意味的妥当性は分けて監査します。',
                ' False means the preregistered original-tool/native-judgment source contract is not satisfied. It does not by itself classify a quotation as fabricated. Actual notice quotations, text matching and the semantic appropriateness of abstention are audited separately.', lang)
    return note


def read_export(root=ROOT, source=None):
    path = root / DATA_FILE if source is None else Path(source)
    if source is None and not path.exists() and not path.is_symlink():
        return None
    if path.is_symlink() or not path.is_file():
        raise ValueError('Audited public export must be an existing regular file')
    raw = path.read_bytes()
    return validate_summary(schema.parse_json(raw)), raw


def optional_summary(root=ROOT, source=None):
    export = read_export(root, source)
    return None if export is None else export[0]


def table(caption, headers, rows, lang, cls=''):
    # Every cell is plain public text; escaping happens at this boundary.
    hint = t('表は横へスクロールできます。キーボードでも表の領域へ移動できます。',
             'Scroll horizontally for every column. The table region is keyboard focusable.', lang)
    return '<p class="eal-scroll-hint">' + hint + '</p><div class="table-wrap" role="region" tabindex="0" aria-label="' + escape(caption, quote=True) + '"><table class="' + cls + '"><caption>' + escape(caption) + '</caption><thead><tr>' + ''.join('<th scope="col">' + escape(str(h)) + '</th>' for h in headers) + '</tr></thead><tbody>' + ''.join('<tr><th scope="row">' + escape(str(row[0])) + '</th>' + ''.join('<td>' + escape(str(cell)) + '</td>' for cell in row[1:]) + '</tr>' for row in rows) + '</tbody></table></div>'


def section(identity, title, body):
    return f'<section class="section" id="{identity}" aria-labelledby="{identity}-title"><div class="section-heading"><h2 id="{identity}-title">{title}</h2></div>{body}</section>'


def details(title, value):
    return '<details><summary>' + escape(title) + '</summary><pre>' + escape(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)) + '</pre></details>'


def render(lang, d):
    validate_summary(d)
    title = t('過去の経験から、次の作業を選べるか。', 'Can past experience guide the next task?', lang)
    description = t('JSON・HTML・ZIPを実際に作る課題を用意し、36の新しいAIコンテキストで比較しました。変更後の条件、以前の条件、未経験の条件を区別して作業できるかを調べました。',
        'We set up tasks that actually create JSON, HTML and ZIP files, then compared choices made in 36 fresh AI contexts. We tested whether they could distinguish changed conditions, earlier conditions and conditions they had never encountered.', lang)
    body = '<div class="eal-study"><section class="study-hero"><p class="eyebrow">EXPERIENCE → CONDITIONAL JUDGMENT → RECALL → ACTION</p><time datetime="2026-10-30">2026-10-30</time><h1>' + title + '</h1><p class="lead">' + description + '</p></section>'
    body += '<div class="finding-callout"><p>' + hero_finding(d, lang) + '</p></div>'
    design = '<p>' + t('実tool経験をLREの条件付き判断として保持し、SHIORIの網を通して新しいAI contextへ返し、そのAIが1回の実操作を選ぶ。変更後に得た新判断も再索引し、次に再び返るかを調べました。',
        'Actual tool experience is retained as a conditional LRE judgment, returned through a SHIORI network to a fresh AI context, and used to choose one real operation. New judgments after the change are also reindexed and checked for later return.', lang) + '</p>'
    design += '<p>' + t('独立に設計したhistoryは3つです。JSON・HTML・ZIPは同じordering-policy機構を形式を変えて繰り返したもので、3種類の異なる認知能力ではありません。教師6context、意味reviewer 3context、probe 36contextを区別します。各phaseは4条件×3historyの全12選択を実行前に固定し、その後各1回だけ実操作。probeの修正や実行結果を見た選び直しはありません。',
        'There are three independently engineered histories. JSON, HTML and ZIP repeat the same ordering-policy mechanism in different formats; they are not three distinct cognitive abilities. Six teacher, three semantic-reviewer and 36 probe contexts are separate units. Each phase freezes all twelve choices across four arms × three histories before one real operation per item. Probes have no repair or outcome-driven reselection.', lang) + '</p>'
    arms = [[label(a, lang), {
        'full': t('過去tool記録・旧判断・新判断・網の経路', 'Historical tool evidence, old/new judgments and graph paths', lang),
        'hops0': t('同じ記録、経路展開0段', 'Same history with zero-hop retrieval', lang),
        'no_writeback': t('raw経験と旧判断を保持、新判断を再保存しない', 'Raw experience and old judgments; no new-judgment writeback', lang),
        'no_history': t('過去記録を返さない', 'No returned historical evidence', lang)}[a]] for a in ARMS]
    design += table(t('4つの比較条件', 'Four comparison arms', lang), ['Arm', t('渡すもの', 'Available evidence', lang)], arms, lang)
    design += '<p class="eal-note">' + t('Rは変更後、Lは旧条件への戻り、Nは観測したことのないopaque profileです。未観測条件での適切な棄権は、文字列引用の一致とは別に独立監査が確認します。',
        'R uses changed conditions, L returns to legacy conditions, and N uses an unobserved opaque profile. Independent audit assesses whether abstention is appropriate in unobserved conditions, separately from exact quotation checks.', lang) + '</p>'
    design += '<p>' + t('語彙はauthor AIが選び、独立AIがreviewしました。fullとno_writebackは新episodeの有無でgraph degreeやscoreも変わり得るため、新判断を追加で利用可能にする比較として読みます。scoreは検索候補の順位値で、確信度や独立証拠の確率ではありません。全会話の自動capture・汎用日本語理解・productionへの統合は検証していません。',
        'An author AI chose the vocabulary and an independent AI reviewed it. Adding a new episode can also change graph degree and scores, so full versus no_writeback compares incremental availability of new judgments. Scores rank retrieval candidates; they are not confidence or probabilities of independent evidence. Automatic capture of all conversation, general Japanese understanding and production integration were not evaluated.', lang) + '</p>'
    body += section('design', t('経験・判断・経路・行動をつなぐ。', 'Connect experience, judgment, paths and action.', lang), design)
    rows = [[phase_label(r['phase'], lang), label(r['arm'], lang), f"{r['artifact_accepted']}/{r['n']}", r['builds'], r['abstentions'], r['rejected_artifacts'], r['operation_errors'], r['queries'], r['indirect_return_queries'], r['new_judgment_return_queries']] for r in d['aggregates']]
    results = table(t('各phase・各条件は3件。受理と棄権を別に表示。', 'Three items per phase/arm; acceptance and abstention remain separate.', lang),
        ['Phase', 'Arm', t('受理', 'Accepted', lang), 'Build', t('棄権', 'Abstain', lang), t('棄却artifact', 'Rejected artifact', lang), 'Op error', 'Query', t('直接一致0の経路返却', 'Indirect return', lang), t('新判断返却', 'New judgment returned', lang)], rows, lang)
    results += '<p>' + finding(d, lang) + '</p><p class="eal-note">' + t('exit 0、artifact受理、適格な原出典の確認、判断の適用可能性は別のものです。JSONのall_quotes_exactは公開21source本文への包含一致という狭いcheckです。棄権でevidenceが空なら空配列の規則でtrueになりますが、根拠が十分な成功を意味しません。query bytes/文字数は返却packetの量で、token・compute・速度・費用ではありません。',
        'Exit zero, artifact acceptance, eligible original-source checks and judgment applicability are distinct. The JSON field all_quotes_exact is a narrow containment check against the 21 disclosed source texts. An abstention with empty evidence is true by the empty-list rule; this does not mean sufficient supporting evidence. Query bytes/characters measure returned packets, not tokens, compute, speed or spending.', lang) + '</p>'
    usage = schema.evidence_usage(d)
    usage_rows = [
        [t('全接続で新判断が返却された項目', 'Full-loop items returning a new judgment', lang), f"{usage['full_new_judgment_return_rows']}/{usage['full_rows']}"],
        [t('非空で適格な原出典を引用した行', 'Rows with nonempty eligible original-source evidence', lang), usage['eligible_nonempty_rows']],
        [t('evidenceが空の行（checkはtrue）', 'Rows with empty evidence (check is true)', lang), usage['empty_evidence_rows']],
        [t('型外の実通知を引用した行（checkはfalse）', 'Rows citing out-of-type actual notices (check is false)', lang), usage['out_of_type_notice_rows']],
        [t('その他の原出典契約false行', 'Other rows failing the original-source contract', lang), usage['other_source_contract_false_rows']],
        [t('適格な原toolの逐語引用', 'Eligible original-tool verbatim quotations', lang), usage['eligible_tool_verbatim_quotes']],
        [t('適格なnative判断の逐語引用', 'Eligible native-judgment verbatim quotations', lang), usage['eligible_native_judgment_verbatim_quotes']],
        [t('適格なnative判断を引用した行', 'Rows citing an eligible native judgment', lang), usage['native_judgment_citing_rows']]]
    results += table(t('新判断が利用可能になることと、行動の根拠への採用を分ける。公開21sourceと36行だけから再計算。',
        'Separate availability of a new judgment from its adoption as action evidence. Recalculated from 21 public sources and 36 rows only.', lang), [t('観測', 'Observation', lang), t('件数', 'Count', lang)], usage_rows, lang)
    if usage['eligible_native_judgment_verbatim_quotes'] == 0:
        results += '<p>' + t('新判断は返却されて利用可能になりましたが、probeのevidenceにnative判断を逐語引用した項目はありません。新判断を採用・活用したことまでは確認していません。原toolのraw原文を使う条件でも同じ受理数で、新判断の追加利益は未確認です。',
            'New judgments were returned and available, but no probe evidence quoted a native judgment verbatim. Adoption or use of the new judgment was not established. Conditions using raw original-tool evidence had the same acceptance counts; an additional benefit from the new judgment remains unconfirmed.', lang) + '</p>'
    body += section('results', t('全12条件集計を残す。', 'Retain all twelve phase/arm aggregates.', lang), results)
    records = []
    for r in d['rows']:
        records.append([r['assignment_id'], r['world'], r['phase'], label(r['arm'], lang), r['profile'], r['action']['decision'], r['action']['recipe'] or '—', r['action']['prediction'], r['exit_code'], r['artifact_accepted'], r['abstained'], r['query_status'], r['new_judgment_returned'], r['all_quotes_exact']])
    all_rows = table(t('除外なしの全36選択と実結果', 'All 36 choices and actual outcomes, with no exclusions', lang), ['ID', 'History', 'Phase', 'Arm', 'Profile', 'Decision', 'Recipe', 'Prediction', 'Exit', 'Accepted', 'Abstain', 'Query', 'New J', t('適格な原出典の確認', 'Eligible original-source check', lang)], records, lang)
    all_rows += '<p class="eal-note">' + eligible_source_note(d, lang) + '</p>'
    quote_failures = [r['assignment_id'] for r in d['rows'] if not r['all_quotes_exact']]
    if quote_failures:
        all_rows += '<p class="eal-note">' + t('原出典の契約から外れた行も、falseのまま保持します：', 'Rows outside the eligible original-source contract remain retained as false: ', lang) + escape(', '.join(quote_failures)) + '</p>'
    for r in d['rows']:
        all_rows += details(r['assignment_id'] + ' / ' + phase_label(r['phase'], lang) + ' / ' + label(r['arm'], lang), r)
    body += section('all-choices', t('選択の理由と証拠も、全36件。', 'Every choice, reason and evidence: all 36 items.', lang), all_rows)
    paths = '<p>' + t('各hitのmatched_cuesとsupport.pathは上の項目詳細にそのまま保持します。下にも実際に返った経路だけを表示します。有限aliasから共有componentへ辿るよう設計した網であり、自由な意味理解の証明ではありません。type=shared_feature_not_causalは共有特徴リンクで、因果経路を意味しません。直接一致0での返却と、最終artifactの改善を混同しません。',
        'Every hit’s matched_cues and support.path are retained in the item details above. The table below shows only paths actually returned. This engineered network connects finite aliases through shared components; it does not establish unrestricted semantic comprehension. type=shared_feature_not_causal denotes a shared-feature link, not a causal path. Indirect return and final artifact improvement are separate outcomes.', lang) + '</p>'
    path_rows = []
    for r in d['rows']:
        for h in r['hits']:
            for s in h['support']:
                if s['path']:
                    path_rows.append([r['assignment_id'], h['episode_id'], h['source_kind'], len(h['matched_cues']), h['indirect_zero_direct_match'], schema.canonical(s['cue']), schema.canonical(s['path'])])
    paths += '<details><summary>' + t('全経路の記録を見る', 'View all recorded paths', lang) + '</summary>' + table(t('実際のsupport path。経路がないhitも項目詳細に保持。', 'Actual support paths; hits without paths remain in the item details.', lang), ['ID', 'Episode', 'Source kind', 'Direct matches', 'Indirect', 'Cue', 'Path'], path_rows, lang) + '</details>'
    body += section('graph-paths', t('経路の返却と、新判断の再返却。', 'Graph return and return of a new judgment.', lang), paths)
    teachers = '<p>' + t('legacy/currentの教師contextをhistoryごとに1つずつ保持します。実AIが書いた判断はtoolの原出力とは別の解釈であり、同じ出来事を独立した2経験へ数えません。',
        'One legacy and one current teacher context are retained per history. Actual AI judgments interpret tool outputs; a receipt and its interpretation of the same event are not two independent experiences.', lang) + '</p>'
    for teacher in d['teachers']:
        teachers += details(teacher['world'] + ' / ' + teacher['stage'] + ' / ' + teacher['profile'], teacher)
    body += section('teachers', t('6つの教師contextと条件付き判断。', 'Six teacher contexts and conditional judgments.', lang), teachers)
    sources = '<p>' + t('この人工課題の実tool出力と実AI判断だけを、21件の重複しない公開messageとして保存しました。非公開repositoryのsource documentや会話原文は含みません。引用はこの本文との包含一致を検算できます。',
        'These 21 deduplicated public messages contain only actual tool outputs and actual AI judgments from this engineered task. They exclude private-repository source documents and conversations. Quotation containment can be checked against these disclosed texts.', lang) + '</p>'
    sources += '<p>' + t('verifierはrawのobs-*とtool:obs-*、cand-*とjudgment:cand-*を同じ出典の別名として照合します。これはlookup時だけの正規化で、保存ACTIONのsource_idや元bytes・hashを書き換えません。',
        'The verifier maps raw obs-* and tool:obs-*, and cand-* and judgment:cand-*, to aliases of the same source. This normalization is for lookup only; saved ACTION source IDs, original bytes and hashes are not rewritten.', lang) + '</p>'
    for source in d['source_messages']:
        sources += '<details><summary><span class="eal-source-id">' + escape(source['id']) + '</span> / ' + escape(source['source_kind']) + '</summary><p class="eal-source-id">SHA256: ' + source['text_sha256'] + '</p><pre>' + escape(source['text']) + '</pre></details>'
    body += section('public-evidence', t('公開した実evidence本文。', 'Disclosed actual evidence texts.', lang), sources)
    operations = table(t('重複を除いた原observation。36のprobe成績とは別の操作数。', 'Deduplicated original observations; operation counts are separate from 36 probe outcomes.', lang), ['Operation', 'Count'], sorted(d['unique_operation_counts'].items()), lang)
    operations += '<p>' + t('synthetic engineering checksは21件・失敗0・error 0です。研究の36件へ合算しません。', 'There are 21 synthetic engineering checks, zero failures and zero errors. They are not pooled with the 36 research items.', lang) + '</p>'
    body += section('engineering', t('操作の件数と、人工チェックを分ける。', 'Separate operations from synthetic checks.', lang), operations)
    limits = '<div class="boundary-box"><p>' + boundary(lang) + '</p><p>' + t('3つのhistoryは人工設計で、同じ機構を形式を変えて反復しています。独立した多数の現実経験や日常会話への一般化ではありません。provider・model・settings・token・computeはすべて未確認のnullです。新判断を保存・再索引・再想起できたことから、重みの更新や同じ主体の心理的保持を導きません。',
        'The three engineered histories repeat one mechanism across formats. They do not generalize to many independent real experiences or everyday conversation. Provider, model, settings, tokens and compute are all unverified and null. Saving, reindexing and recalling a new judgment do not establish weight updates or one subject’s psychological retention.', lang) + '</p><p>' + t('hashはlocal記録の整合性識別子で、外部署名やhardware attestationではありません。公開verifierは開示された算術・本文hash・引用包含を検算します。非公開native操作や全claimを独立に証明するものではありません。過去11研究と4つのスクロールstoryは公開時のbytesを保持します。',
        'Hashes identify local record integrity; they are not external signatures or hardware attestation. The public verifier checks disclosed arithmetic, text hashes and quotation containment. It cannot independently prove undisclosed native operations or every claim. Eleven earlier studies and four scroll stories retain their published bytes.', lang) + '</p></div>'
    limits += details(t('独立監査・公開保護・追加boundary', 'Independent audit, publication protection and further boundaries', lang), {k: d[k] for k in ('audit', 'protection', 'boundary', 'boundaries', 'provider_metadata')})
    limits += table(t('監査・凍結記録の識別hash', 'Integrity digests for audit and frozen records', lang), ['Record', 'SHA256'], [('protocol_sha256', d['protocol_sha256']), *sorted(d['hashes'].items())], lang, 'eal-digests')
    body += section('limits', t('この試験で言える範囲。', 'What this trial can establish.', lang), limits)
    downloads = '<p>' + t('公開JSONと小さなsaved-evidence verifierだけを配布します。private vendor source・native state・非公開source documentは含みません。native実行や新しいAI選択を再現するpackageではありません。',
        'Downloads contain the public JSON and a small saved-evidence verifier. They exclude private vendor source, native state and private source documents. This package cannot rerun native execution or regenerate fresh AI choices.', lang) + '</p><div class="download-links"><a href="../../' + DATA_FILE + '" download>' + t('公開JSON', 'Public JSON', lang) + '</a><a href="../../' + REPLAY + 'README.md">' + t('検算の説明', 'Verification instructions', lang) + '</a><a href="../../' + ZIP_FILE + '" download>Saved-evidence verifier ZIP ↓</a></div>'
    body += section('downloads', t('公開evidenceを検算する。', 'Verify the disclosed evidence.', lang), downloads) + '</div>'
    home = '../../index.html' if lang == 'ja' else '../../index.en.html'
    results = '../../results.html' if lang == 'ja' else '../../results.en.html'
    canonical = BASE + STUDY + ('' if lang == 'ja' else 'en.html')
    switch = '<a href="index.html" lang="ja" hreflang="ja"' + (' aria-current="page"' if lang == 'ja' else '') + '>日本語</a><a href="en.html" lang="en" hreflang="en"' + (' aria-current="page"' if lang == 'en' else '') + '>EN</a>'
    return f'''<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title} — LUX SPIRIA Results</title><meta name="description" content="{escape(description, quote=True)}"><link rel="canonical" href="{canonical}"><link rel="alternate" hreflang="ja" href="{BASE+STUDY}"><link rel="alternate" hreflang="en" href="{BASE+STUDY}en.html"><link rel="alternate" hreflang="x-default" href="{BASE+STUDY}"><meta name="theme-color" content="#090d12"><link rel="icon" type="image/png" sizes="32x32" href="../../assets/favicon-32.png"><link rel="apple-touch-icon" sizes="180x180" href="../../assets/apple-touch-icon.png"><link rel="manifest" href="../../{'site' if lang=='ja' else 'site.en'}.webmanifest"><link rel="stylesheet" href="../../site.css"><link rel="stylesheet" href="../../theme-dark.css"><link rel="stylesheet" href="experience-action-loop.css"></head><body><a class="skip-link" href="#main">{t('本文へ', 'Skip to content', lang)}</a><div class="page"><header class="masthead"><a class="brand" href="{results}"><img src="../../assets/lux-symbol.png" alt="" width="44" height="44"><span class="brand-wordmark">LUX SPIRIA<span class="brand-subtitle">RESEARCH RESULTS</span></span></a><nav aria-label="{t('主なページ', 'Main navigation', lang)}"><a href="{results}#studies">{t('研究結果', 'Studies', lang)}</a><a href="#all-choices">{t('全36選択', 'All 36 choices', lang)}</a><a href="{home}">{t('全体像', 'Overview', lang)}</a><span class="lang">{switch}</span></nav></header><main id="main">{body}</main><footer class="footer"><nav aria-label="{t('資料', 'Resources', lang)}"><a href="{home}">LUX SPIRIA</a><a href="../../LICENSE">License / LSP-1.0</a><a href="https://github.com/Yuu-Honda/lux-spiria-results">GitHub ↗</a></nav><small>EXPERIENCE–ACTION LOOP / 2026-10-30</small></footer></div></body></html>'''


def public_bundle(d, raw):
    validate_summary(d)
    readme = b'''# Saved-evidence verifier: experience-action loop, 2026-10-30

Python 3 standard library only. Run `python3 -B verify.py evidence.json`.
The four-file package contains this README, evidence.json, verify.py and
MANIFEST.json. It contains no private vendor code, native state, private source
documents or credentials. This is not a native replay or fresh AI regeneration.

The verifier checks the strict public schema, all 36 choices and twelve
aggregates, disclosed source-text SHA256, eligible-source quote flags, profile bindings,
graph path flags and new-judgment-return flags. Empty-evidence abstention passes
the empty-list quote check; this is not sufficient evidence or semantic success.
The check concerns preregistered original tool/native-judgment source types.
An actual returned unavailability notice can match its packet while falling
outside that eligible-source contract. A false flag does not by itself mean a
fabricated quotation. Packet matching and appropriate abstention are separate
independent-audit questions; the original false outcomes remain unchanged.
Raw obs-* and tool:obs-* are lookup aliases of the same original tool source;
cand-* and judgment:cand-* likewise identify the same native judgment. This
normalizes source lookup only. Saved ACTION source_id values, bytes and hashes
are never rewritten. The verifier also reports nonempty eligible rows, empty
evidence rows, out-of-type notices and tool/native-judgment citation counts.
New-judgment return means availability, not demonstrated adoption or benefit.
Independent audit assesses applicability, artifacts and protection separately.
The JSON contains that audit's scope and digest. The verifier does not repeat
that audit or independently establish undisclosed operations or all claims.

JSON/HTML/ZIP histories repeat one engineered ordering-policy mechanism.
New-judgment return and its additional benefit are distinct. Shared-feature
links (shared_feature_not_causal) are not causal paths. The 21 synthetic checks
are separate from the 36 actual probe contexts. Provider/model/settings/token/
compute metadata is unverified and null. Roles use read allowlists on a shared
filesystem, not OS isolation. Full Wake, Emotion, brains, AGI, natural
conversation and weight learning were not evaluated. Hashes identify local
integrity, not external signatures or hardware attestation.

Read the dated Japanese/English study for every retained outcome and limitation.
The repository LICENSE applies; this grants no license to private dependencies.
'''
    files = {'README.md': readme, 'evidence.json': raw,
        'verify.py': (ROOT / 'tools/experience_action_schema.py').read_bytes()}
    manifest = {'schema_version': 1, 'files': {name: {'sha256': sha256(value).hexdigest(), 'bytes': len(value)} for name, value in sorted(files.items())}}
    files['MANIFEST.json'] = (schema.canonical(manifest) + '\n').encode('utf-8')
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name, value in sorted(files.items()):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0)); info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3; info.external_attr = 0o100644 << 16
            z.writestr(info, value, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return files, archive.getvalue()


def build_plan(root=ROOT, source=None):
    spec = importlib.util.spec_from_file_location('experience_action_publication_command', ROOT / 'tools/experience_action_publication.py')
    publication = importlib.util.module_from_spec(spec); spec.loader.exec_module(publication)
    return publication.prepare_updates(root, source)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--experience-action-loop', type=Path, help='Independently audited public export only')
    args = parser.parse_args(argv)
    updates = build_plan(ROOT, args.experience_action_loop)
    for relative, raw in updates.items():
        path = ROOT / relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
    print('Built audited experience-action publication.' if updates else 'No audited experience-action export; no publication writes.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, UnicodeError) as error:
        raise SystemExit(str(error)) from error

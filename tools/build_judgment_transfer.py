"""Render only a strictly validated, independently audited public export.

No input means no publication writes. This module never opens research roots,
executes trials, calls an AI, or accesses native LRE state.
"""
import argparse
from html import escape
import importlib.util
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://yuu-honda.github.io/lux-spiria-results/'
DATA_FILE = 'data/judgment-transfer-2026-11-03.json'
STUDY = 'studies/2026-11-03-judgment-transfer/'
REPLAY = 'experiments/judgment-transfer-2026-11-03/'
ZIP_FILE = 'downloads/judgment-transfer-2026-11-03.zip'
_spec = importlib.util.spec_from_file_location('judgment_transfer_public_schema', ROOT / 'tools/judgment_transfer_schema.py')
schema = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(schema)
validate_summary = schema.validate_summary
ARMS, PHASES = schema.ARMS, schema.PHASES

CSS = '''.jt-study{min-width:0}.jt-study h1{text-wrap:balance}.jt-study .lead{max-width:65rem}.jt-study .section{margin-block:3rem}.jt-study p,.jt-study li,.jt-study th,.jt-study td,.jt-study summary{overflow-wrap:anywhere}.jt-study .table-wrap{max-width:100%;overflow:auto;overscroll-behavior-x:contain;border:1px solid var(--line);border-radius:10px}.jt-study table{width:100%;min-width:780px;border-collapse:collapse}.jt-study caption{text-align:left;padding:1rem;color:#c2cfdd;white-space:normal}.jt-study th,.jt-study td{text-align:left;vertical-align:top;padding:.8rem;border-bottom:1px solid var(--line)}.jt-study tbody tr:last-child>*{border-bottom:0}.jt-study .scroll-hint{font-size:.85rem;color:#b5c3d0;margin:.6rem 0}.jt-study details{min-width:0;border:1px solid var(--line);border-radius:8px;padding:.8rem 1rem;margin:1rem 0}.jt-study summary{cursor:pointer}.jt-study pre{max-width:100%;margin:.8rem 0;white-space:pre-wrap;overflow-wrap:anywhere;word-break:break-word;background:#101923;color:#d9e4ef;padding:1rem;font:.8rem/1.7 var(--mono);border-radius:6px}.jt-study .download-links{display:flex;gap:1rem;flex-wrap:wrap}.jt-study .boundary-box p+p{margin-top:1rem}.jt-study .digest{font:.8rem/1.7 var(--mono);word-break:break-all}.jt-study .jt-metrics{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1rem;margin:1.5rem 0}.jt-study .jt-metrics>div{display:flex;flex-direction:column;justify-content:space-between;gap:.7rem;border:1px solid var(--line);border-radius:10px;padding:1.1rem;background:#101923}.jt-study .jt-metrics dt{font-size:.9rem;color:#c2cfdd}.jt-study .jt-metrics dd{margin:0;color:#fff;font:600 clamp(1.7rem,3vw,2.4rem)/1.2 var(--mono)}.jt-study .jt-ceiling{max-width:75ch;border-left:3px solid #aabed0;padding:.4rem 0 .4rem 1rem;color:#d3dfec}.jt-study .jt-io-summary{font-size:1.05rem;line-height:1.9;max-width:75ch}.jt-study .jt-exception{color:#d4c8a8}@media(max-width:700px){.jt-study .section{margin-block:2rem}.jt-study details{padding:.65rem}.jt-study caption{max-width:calc(100vw - 4rem)}.jt-study .jt-metrics{grid-template-columns:1fr}.jt-study .jt-metrics>div{flex-direction:row;align-items:center}.jt-study .jt-metrics dt{max-width:65%}.jt-study .jt-metrics dd{white-space:nowrap}}'''


def t(ja, en, lang):
    return ja if lang == 'ja' else en


def label(arm, lang):
    return {'raw_only': t('原記録を必要に応じて読む', 'Read originals on request', lang),
        'raw_plus_judgment': t('原記録＋保存した判断', 'Originals + saved judgment', lang),
        'all_raw_upfront': t('原記録を最初から全部読む', 'All originals upfront', lang)}[arm]


def phase_label(phase, lang):
    return {'same_version': t('同じversion', 'Same version', lang),
        'changed_version': t('変更後のversion', 'Changed version', lang)}[phase]


def read_export(root=ROOT, source=None):
    path = root / DATA_FILE if source is None else Path(source)
    if source is None and not path.exists() and not path.is_symlink():
        return None
    if path.is_symlink() or not path.is_file():
        raise ValueError('Audited public export must be a regular file')
    raw = path.read_bytes()
    return validate_summary(schema.parse_json(raw)), raw


def optional_summary(root=ROOT, source=None):
    result = read_export(root, source)
    return None if result is None else result[0]


def aggregate(d, phase, arm, mechanism='all'):
    return next(r for r in d['aggregates'] if (r['phase'], r['arm'], r['mechanism']) == (phase, arm, mechanism))


def finding(d, lang):
    raw = aggregate(d, 'same_version', 'raw_only')['accepted']
    judgment = aggregate(d, 'same_version', 'raw_plus_judgment')['accepted']
    text = t(f'同じversionの新しい課題では、原記録のみが{raw}/6件、保存した判断を加えた条件が{judgment}/6件受理されました。',
        f'On new tasks using the same version, {raw}/6 results were accepted with originals alone and {judgment}/6 with a saved judgment added.', lang)
    if raw == judgment:
        text += t(' 受理数が同じだったため、判断を加える主効果は確認できていません。',
            ' With equal acceptance counts, the primary benefit of adding a judgment remains unconfirmed.', lang)
    else:
        text += t(' この差は6つの人工historyを対応させた記述的比較です。',
            ' This difference is a descriptive comparison of six matched engineered histories.', lang)
    return text


def diagnostic_ceiling(d, lang):
    calls = d['process_counts']['diagnostic_workers']
    return t(f'全probeには、現在の3つの操作すべての実出力を、toy入力で一度に見られる診断を用意しました。実際に{calls}/{len(d["rows"])}件が診断を使っています。この出力だけでも正しい操作を識別できる可能性があり、保存した判断による成功率の上乗せは切り分けられていません。',
        f'Every probe could inspect actual outputs of all three current operations in one diagnostic on toy input; {calls}/{len(d["rows"])} used it. The correct operation may be identifiable from that diagnostic alone, so this study does not isolate a judgment-based accuracy gain.', lang)


def io_finding(d, lang):
    descriptions = []
    for phase in PHASES:
        raw, judgment = (aggregate(d, phase, arm) for arm in ('raw_only', 'raw_plus_judgment'))
        descriptions.append(t(f'{phase_label(phase, lang)}では追加取得が{raw["io"]["requested_original_reads"]}回 → {judgment["io"]["requested_original_reads"]}回、最初の課題＋feedbackの合計が{raw["io"]["total_transferred_packet_bytes"]:,} → {judgment["io"]["total_transferred_packet_bytes"]:,} bytesでした。',
            f'{phase_label(phase, lang)}: requested original reads {raw["io"]["requested_original_reads"]} → {judgment["io"]["requested_original_reads"]}; initial task + feedback {raw["io"]["total_transferred_packet_bytes"]:,} → {judgment["io"]["total_transferred_packet_bytes"]:,} bytes.', lang))
    return t('原記録のみ → 原記録＋判断の順で、', 'From originals alone → originals + judgment: ', lang) + ' '.join(descriptions)


def io_exceptions(d, lang):
    descriptions = []
    for pair in d['matched_pairs']:
        if pair['total_packet_byte_difference'] <= 0:
            continue
        raw, judgment = (next(r for r in d['rows'] if r['phase'] == pair['phase'] and r['world_id'] == pair['world_id'] and r['arm'] == arm) for arm in ('raw_only', 'raw_plus_judgment'))
        descriptions.append(t(f'{pair["world_id"]}（{phase_label(pair["phase"], lang)}）は追加取得が{raw["io"]["requested_original_reads"]}回 → {judgment["io"]["requested_original_reads"]}回で、判断ありのpacketは{pair["total_packet_byte_difference"]:,} bytes多くなりました。',
            f'{pair["world_id"]} ({phase_label(pair["phase"], lang)}): requested reads {raw["io"]["requested_original_reads"]} → {judgment["io"]["requested_original_reads"]}, while the judgment arm delivered {pair["total_packet_byte_difference"]:,} more packet bytes.', lang))
    return t('集計が小さくても、全historyで小さかったとは限りません。', 'A smaller aggregate does not mean every history was smaller. ', lang) + ' '.join(descriptions) if descriptions else ''


def boundary(lang):
    return t('2つの機構を各3historyで調べた小規模な人工課題です。全Wake・Emotion・AGI・脳・自然会話・重み学習の試験ではありません。',
        'This small engineered trial covers two mechanisms with three histories each. It does not evaluate full Wake, Emotion, AGI, brains, natural conversation or weight learning.', lang)


def table(caption, headers, rows, lang):
    return '<p class="scroll-hint">' + t('表は横へスクロールできます。表の領域はキーボードでも選択できます。', 'Scroll horizontally for every column. The table region is keyboard focusable.', lang) + '</p><div class="table-wrap" role="region" tabindex="0" aria-label="' + escape(caption, quote=True) + '"><table><caption>' + escape(caption) + '</caption><thead><tr>' + ''.join('<th scope="col">' + escape(str(h)) + '</th>' for h in headers) + '</tr></thead><tbody>' + ''.join('<tr><th scope="row">' + escape(str(row[0])) + '</th>' + ''.join('<td>' + escape(str(v)) + '</td>' for v in row[1:]) + '</tr>' for row in rows) + '</tbody></table></div>'


def details(title, value):
    return '<details><summary>' + escape(title) + '</summary><pre>' + escape(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)) + '</pre></details>'


def section(identity, title, body):
    return '<section class="section" id="' + identity + '" aria-labelledby="' + identity + '-title"><div class="section-heading"><h2 id="' + identity + '-title">' + title + '</h2></div>' + body + '</section>'


def render(lang, d, replay=False):
    validate_summary(d)
    title = t('保存した判断は、次の作業に役立つか。', 'Does a saved judgment help with the next task?', lang)
    description = t('AIが作業結果から書いた判断を、次の作業に渡すと何が変わるか。識別子をまとめる課題と、途中状態からのSQLite取込で比べました。',
        'What changes when an AI’s judgment about earlier work is passed to the next task? We compared identifier grouping and SQLite imports from staged partial states.', lang)
    accepted, diagnostic = sum(r['accepted'] for r in d['rows']), d['process_counts']['diagnostic_workers']
    metrics = '<dl class="jt-metrics"><div><dt>' + t('成功した最終操作', 'Accepted final operations', lang) + '</dt><dd>' + f'{accepted} / {len(d["rows"])}' + '</dd></div><div><dt>' + t('現在の操作を診断', 'Used the current diagnostic', lang) + '</dt><dd>' + f'{diagnostic} / {len(d["rows"])}' + '</dd></div><div><dt>' + t('主比較：判断追加による受理数の差', 'Primary: paired acceptance difference', lang) + '</dt><dd>' + str(d['primary_paired_accepted_difference']) + ' / 6</dd></div></dl>'
    body = '<div class="jt-study"><section class="study-hero"><p class="eyebrow">JUDGMENT TRANSFER / ENGINEERED TASKS</p><time datetime="2026-11-03">2026-11-03</time><h1>' + title + '</h1><p class="lead">' + description + '</p>' + metrics + '</section><div class="finding-callout"><p>' + finding(d, lang) + '</p></div><p class="jt-ceiling">' + diagnostic_ceiling(d, lang) + '</p>'
    design = '<p>' + t('6つの人工historyは、A：どの識別子を同一とみなしてまとめるか、B：途中状態からのSQLite取込を各3件です。Bの途中状態は設計した入力で、過去のprocess crashを観測したものではありません。操作名は意味が推測できないIDにし、3つの操作の挙動は作業結果や診断から確かめます。教師役のAIが各3課題を2回、合計36回実行し、作業結果から自分で書いた判断をnative LREに保存・review・readbackしました。その後、新しい36のAI contextで比較しました。保存された文章を次に渡す試験で、モデルの重みを更新する学習ではありません。',
        'Six engineered histories cover A: deciding which identifiers count as the same, and B: SQLite imports from staged partial states, three each. The partial states are engineered inputs, rather than observed process crashes. Operations have opaque IDs; their behavior must be checked through work results or diagnostics. Teacher AIs each ran three cases twice, totaling 36 training calls, then authored judgments from the results for native LRE capture, review and readback. We compared 36 fresh AI contexts afterward. This transfers saved text; model weights are not updated.', lang) + '</p><p>' + t('同じversion／変更後versionの各phaseで、3条件×6historyの18個の初期POLICYをすべて固定。その後、同じ6原記録への取得権と1回のcurrent toy診断を提供し、同じcontextの18個のFINALをすべて固定してから、各1回のtarget実操作または棄権を記録しました。',
        'Each same-version/changed-version phase froze all 18 initial POLICY choices across three arms × six histories. The same six-original access rights and one current toy diagnostic were then available. All 18 FINAL choices in those same contexts froze before one target operation or abstention per item.', lang) + '</p>'
    design += table(t('同じ原記録の順序と取得権を持つ3条件', 'Three arms with the same source order and access rights', lang), ['Arm', t('最初に渡す内容', 'Initial evidence', lang)], [[label('raw_only', lang), t('6原記録のcatalog。本文は要求分を返す。', 'Catalog of six originals; requested texts returned.', lang)], [label('raw_plus_judgment', lang), t('同じcatalog＋実保存判断とnative status。', 'Same catalog + actual saved judgment and native status.', lang)], [label('all_raw_upfront', lang), t('6原記録の全本文。診断比較であり数学的上限ではない。', 'All six original texts. Diagnostic comparison, not a mathematical upper bound.', lang)]], lang)
    design += '<p>' + t('retainedとdeferredの両statusをそのままtreatmentに渡します。比較対象は判断本文＋statusの利用可能性で、retainedだけの効果ではありません。SHIORIのrankingは使わず、判断候補とnative状態の利用可能性に比較を絞りました。',
        'Both retained and deferred statuses are passed through unchanged. The treatment is availability of judgment text + status, rather than an effect of retained judgments alone. SHIORI ranking is not used; the comparison isolates availability of a judgment candidate and its native disposition.', lang) + '</p>'
    body += section('design', t('経験と判断を分けて比べる。', 'Compare experience and judgment separately.', lang), design)
    pairs = [p for p in d['matched_pairs'] if p['phase'] == 'same_version']
    main = table(t('主比較：同じversionでの6対応pair。1=受理、0=未受理。差は判断あり−原記録のみ。', 'Primary comparison: six same-version matched pairs. 1=accepted; 0=not accepted. Difference is judgment minus originals alone.', lang), [t('人工history', 'History', lang), t('機構', 'Mechanism', lang), t('原記録のみ', 'Originals alone', lang), t('原記録＋判断', 'Originals + judgment', lang), t('全原記録を最初に', 'All originals upfront', lang), t('受理数の差', 'Difference', lang)], [[p['world_id'], p['mechanism'], int(p['raw_only_accepted']), int(p['judgment_accepted']), int(next(r['accepted'] for r in d['rows'] if r['world_id'] == p['world_id'] and r['phase'] == 'same_version' and r['arm'] == 'all_raw_upfront')), p['accepted_difference']] for p in pairs], lang)
    main += '<p>' + finding(d, lang) + '</p><p class="jt-ceiling">' + diagnostic_ceiling(d, lang) + '</p>'
    body += section('primary', t('主効果は、成功した実操作の差。', 'The primary outcome is accepted real operations.', lang), main)
    result_rows = [[phase_label(r['phase'], lang), label(r['arm'], lang), r['mechanism'], f"{r['accepted']}/{r['n']}", r['abstentions'], r['state_valid'], r['operation_completed'], r['operation_failures'], r['worker_errors'], r['provisional_old_only'], r['old_only_choices'], r['changed_after_feedback']] for r in d['aggregates']]
    compact_results = [[phase_label(r['phase'], lang), label(r['arm'], lang), f"{r['accepted']}/{r['n']}", r['abstentions'], r['provisional_old_only'], r['old_only_choices'], r['changed_after_feedback']] for r in d['aggregates'] if r['mechanism'] == 'all']
    results = table(t('全6条件：受理・棄権・旧versionだけで正しい操作の選択。', 'All six conditions: acceptance, abstention and stale-only operation choices.', lang), [t('version', 'Version', lang), t('条件', 'Arm', lang), t('受理', 'Accepted', lang), t('棄権', 'Abstain', lang), t('初期の旧操作', 'Initial stale-only', lang), t('最終の旧操作', 'Final stale-only', lang), t('非null初期操作の変更', 'Changed nonnull initial choice', lang)], compact_results, lang)
    results += '<details><summary>' + t('機構A/B・失敗を含む全18集計を表示', 'Show all 18 mechanism aggregates, including failures', lang) + '</summary>' + table(t('全phase・条件・機構集計。allは6件、A/Bは各3件。', 'Every phase/arm/mechanism aggregate. all has six items; A/B have three each.', lang), ['Phase', 'Arm', 'Mechanism', 'Accepted', 'Abstain', 'Valid state', 'Completed', 'Op failure', 'Worker error', 'Initial stale-only', 'Final stale-only', 'Changed choice'], result_rows, lang) + '</details>'
    results += '<p>' + t('変更後versionでは、旧versionだけで正しい操作を選んだか、診断を要求したか、最終的に成功したかを別に示します。「操作の変更」は、初期に選んだ操作が非nullの場合だけを数えます。初期nullから最終操作を選ぶことは数えないため、原記録のみの変更0は「feedbackを使わなかった」という意味ではありません。初期の選択、最終選択、stateが正しいこと、操作完了、受理は別の指標です。',
        'For the changed version, stale-only choices, diagnostic requests and final success are separate measures. “Changed choice” counts only a change from a nonnull initial operation. Choosing a final operation after an initial null is excluded, so zero changes in originals alone does not mean feedback was unused. Initial/final choice, valid state, operation completion and acceptance are distinct outcomes.', lang) + '</p>'
    body += section('results', t('変更後の選択と結果も見る。', 'Inspect choices and outcomes after the change.', lang), results)
    io_rows = [[phase_label(r['phase'], lang), label(r['arm'], lang), r['mechanism'], *[r['io'][key] for key in schema.IO_FIELDS]] for r in d['aggregates']]
    compact_io = [[phase_label(r['phase'], lang), label(r['arm'], lang), r['io']['initial_original_count'], r['io']['requested_original_reads'], r['io']['diagnostic_calls'], f"{r['io']['total_transferred_packet_bytes']:,}"] for r in d['aggregates'] if r['mechanism'] == 'all']
    io = '<p class="jt-io-summary">' + io_finding(d, lang) + '</p>'
    if io_exceptions(d, lang):
        io += '<p class="jt-exception">' + io_exceptions(d, lang) + '</p>'
    io += table(t('各条件6件の合計。最初に渡した原記録と追加取得を分ける。', 'Totals for six items per arm. Initial originals and additional requests are separate.', lang), [t('version', 'Version', lang), t('条件', 'Arm', lang), t('最初の原記録', 'Initial originals', lang), t('追加取得', 'Requested reads', lang), t('診断', 'Diagnostics', lang), t('課題＋feedback bytes', 'Task + feedback bytes', lang)], compact_io, lang)
    io += '<details><summary>' + t('全21 I/O指標・機構A/Bの集計を表示', 'Show all 21 I/O measures and A/B aggregates', lang) + '</summary>' + table(t('副指標：公開したI/O。判断構築・学習costの償却は含まない。', 'Secondary measures: disclosed I/O. Judgment construction/training amortization is excluded.', lang), ['Phase', 'Arm', 'Mechanism', *schema.IO_FIELDS], io_rows, lang) + '</details>'
    io += details(t('全12対応pairのI/O差（判断あり−原記録のみ）', 'I/O differences for all twelve matched pairs (judgment minus originals alone)', lang), d['matched_pairs'])
    io += '<p>' + t('read・診断回数やinitial＋feedback packet bytesは、モデルに渡した情報量の副指標です。backendの整合性checkによるdisk read総量ではありません。主効果が同点なら、これだけで成功率改善とは呼びません。同じ成功数でもtoken・compute・速度・費用の削減は未測定です。',
        'Read/diagnostic counts and initial + feedback packet bytes are secondary measures of delivered model evidence, rather than total backend integrity disk reads. When the primary outcome ties, these do not establish improved success. Even with equal success counts, token, compute, speed and cost savings remain unmeasured.', lang) + '</p>'
    body += section('io', t('成功と、読んだ量を分ける。', 'Separate success from delivered evidence volume.', lang), io)
    records = table(t('全36POLICY / FINALと実結果。除外・引用修復なし。', 'All 36 POLICY / FINAL choices and actual outcomes. No exclusions or quotation repairs.', lang), ['ID', 'History', 'Phase', 'Arm', 'Initial operation', 'Diagnostic', 'Final decision', 'Final operation', 'Accepted', 'Citation status'], [[r['assignment_id'], r['world_id'], r['phase'], r['arm'], r['policy']['provisional_operation'], r['policy']['calibration'], r['final']['decision'], r['final']['operation'], r['accepted'], r['citation_status']] for r in d['rows']], lang)
    records += '<p>' + t('引用は任意です。evidenceが空ならcitation_statusはnoneのままです。誤引用や利用できないsourceはfalseのまま保持し、操作成功と別に扱います。逐語一致は判断の意味的な正しさを証明しません。各詳細に実際の理由・prediction・型付き引用・checkを保持します。',
        'Citations are optional. Empty evidence remains citation_status none. Incorrect quotations or unavailable sources remain false and are separate from operation success. Exact wording does not establish semantic correctness. Each detail retains actual reasons, predictions, typed quotations and checks.', lang) + '</p>'
    for r in d['rows']:
        records += details(r['assignment_id'] + ' / ' + r['phase'] + ' / ' + r['arm'], r)
    body += section('all-choices', t('選択理由も、全36件を公開する。', 'Disclose every choice and reason: all 36.', lang), records)
    rounds = [sum(r['accepted'] for r in d['teacher_rounds'] if r['round'] == rnd) for rnd in (1, 2)]
    teachers = '<p>' + t(f'教師役の受理数は1回目{rounds[0]}/18 → 2回目{rounds[1]}/18でした。同じ練習課題を繰り返した成績で、新しい課題への転移や重み更新の証拠ではありません。', f'Teacher acceptance was {rounds[0]}/18 in round one → {rounds[1]}/18 in round two. These repeat the same practice cases; the change does not establish transfer to new tasks or weight updates.', lang) + '</p>'
    quote_counts = {phase: sum(r['exact_judgment_citations'] for r in d['rows'] if r['phase'] == phase) for phase in PHASES}
    retained = sum(j['native_status'] == 'retained' for j in d['teacher_judgments'])
    deferred = sum(j['native_status'] == 'deferred' for j in d['teacher_judgments'])
    teachers += '<p>' + t(f'今回の実statusはretained（保持）{retained}件・deferred（保留）{deferred}件です。これはAI自身のreviewによる扱いで、判断本文が正しいことの証明ではありません。最終evidenceで保存判断を逐語引用した件数は、同じversionで{quote_counts["same_version"]}件、変更後で{quote_counts["changed_version"]}件でした。引用の一致は、判断が選択を引き起こしたことや、引用しなかった判断を使わなかったことを証明しません。', f'Actual native statuses are retained {retained}, deferred {deferred}. This is the AI’s self-review disposition, not proof that its text is correct. Exact saved-judgment quotations in final evidence: {quote_counts["same_version"]} in the same version and {quote_counts["changed_version"]} after the change. A matching quotation does not establish that the judgment caused a choice; absence of a quotation does not establish non-use.', lang) + '</p>'
    teachers += details(t('全12教師roundの実受理数（36実training calls）', 'Actual acceptance in all 12 teacher rounds (36 training calls)', lang), d['teacher_rounds'])
    for item in d['teacher_judgments']:
        teachers += details(item['world_id'] + ' / native ' + item['native_status'], item)
    body += section('teachers', t('教師の判断とnative statusをそのまま残す。', 'Retain teacher judgments and native statuses.', lang), teachers)
    sources = '<p>' + t('この人工課題の原記録、判断、配布packetだけを公開します。本文hashと型付き引用は公開verifierで検算できます。',
        'Only originals, judgments and delivered packets from this engineered task are disclosed. The public verifier checks text hashes and typed quotations.', lang) + '</p>'
    for item in d['source_messages']:
        sources += details(item['id'] + ' / ' + item['source_kind'], item)
    sources += details(t('6つの人工world config', 'Six engineered world configurations', lang), d['worlds'])
    body += section('evidence', t('作業記録と、設計した課題を確かめる。', 'Inspect work records and engineered tasks.', lang), sources)
    limits = '<div class="boundary-box"><p>' + boundary(lang) + '</p><p>' + t('単一seedで作った6historyを各条件で対応させています。36の独立した経験ではありません。Aのheld-outは同じ8key関係で数値とIDを差し替えたもので、新構造への一般化ではありません。',
        'The arms are matched over six histories generated with one seed. These are not 36 independent experiences. A held-out cases replace numbers and IDs within the same eight-key relations; they do not test generalization to new structures.', lang) + '</p><p>' + t('provider・model・settings・tokens・computeは未確認のnullです。共有FS上の指示allowlistでありOS隔離ではありません。hashはlocal記録の整合性識別子で、外部署名やhardware attestationではありません。以前の12研究・data・replay・ZIPと4つのscroll storyは保持します。',
        'Provider, model, settings, tokens and compute remain unverified and null. Roles use instruction-based allowlists on a shared filesystem, not OS isolation. Hashes identify local record integrity, not external signatures or hardware attestation. Twelve prior studies, their data/replay/ZIP files and four scroll stories are preserved.', lang) + '</p></div>'
    limits += details(t('独立監査と公開範囲', 'Independent audit and publication boundaries', lang), {k: d[k] for k in ('audit', 'protection', 'boundary', 'boundaries', 'provider_metadata', 'hashes')})
    body += section('limits', t('この試験が確かめた範囲。', 'What this trial tested.', lang), limits)
    downloads = '<p>' + t('公開JSONは保存済み結果です。閲覧中に研究を実行しません。検算は開示した記録の整合性を確かめるもので、非公開native操作の再実行や新しいAI選択ではありません。',
        'The public JSON contains saved results. Browsing does not run the study. Verification checks disclosed records; it does not rerun private native operations or make fresh AI choices.', lang) + '</p><div class="download-links"><a href="../../' + DATA_FILE + '" download>' + t('公開JSON', 'Public JSON', lang) + '</a>'
    if replay:
        downloads += '<a href="../../' + REPLAY + 'README.md">' + t('保存操作replayの説明', 'Saved-operation replay instructions', lang) + '</a><a href="../../' + ZIP_FILE + '" download>Saved-work replay ZIP ↓</a>'
    else:
        downloads += '<a href="../../' + REPLAY + 'README.md">' + t('保存evidence検算の説明', 'Saved-evidence verification instructions', lang) + '</a><a href="../../' + ZIP_FILE + '" download>Saved-evidence verifier ZIP ↓</a>'
    body += section('downloads', t('保存した結果を検算する。', 'Verify the saved results.', lang), downloads + '</div>') + '</div>'
    home = '../../index.html' if lang == 'ja' else '../../index.en.html'
    results = '../../results.html' if lang == 'ja' else '../../results.en.html'
    canonical = BASE + STUDY + ('' if lang == 'ja' else 'en.html')
    switch = '<a href="index.html" lang="ja" hreflang="ja"' + (' aria-current="page"' if lang == 'ja' else '') + '>日本語</a><a href="en.html" lang="en" hreflang="en"' + (' aria-current="page"' if lang == 'en' else '') + '>EN</a>'
    return f'''<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title} — LUX SPIRIA Results</title><meta name="description" content="{escape(description, quote=True)}"><link rel="canonical" href="{canonical}"><link rel="alternate" hreflang="ja" href="{BASE+STUDY}"><link rel="alternate" hreflang="en" href="{BASE+STUDY}en.html"><link rel="alternate" hreflang="x-default" href="{BASE+STUDY}"><meta name="theme-color" content="#090d12"><link rel="icon" type="image/png" sizes="32x32" href="../../assets/favicon-32.png"><link rel="apple-touch-icon" sizes="180x180" href="../../assets/apple-touch-icon.png"><link rel="stylesheet" href="../../site.css"><link rel="stylesheet" href="../../theme-dark.css"><link rel="stylesheet" href="judgment-transfer.css"></head><body><a class="skip-link" href="#main">{t('本文へ', 'Skip to content', lang)}</a><div class="page"><header class="masthead"><a class="brand" href="{results}"><img src="../../assets/lux-symbol.png" alt="" width="44" height="44"><span class="brand-wordmark">LUX SPIRIA<span class="brand-subtitle">RESEARCH RESULTS</span></span></a><nav aria-label="{t('主なページ', 'Main navigation', lang)}"><a href="{results}#studies">{t('研究結果', 'Studies', lang)}</a><a href="#all-choices">{t('全36選択', 'All 36 choices', lang)}</a><a href="{home}">{t('全体像', 'Overview', lang)}</a><span class="lang">{switch}</span></nav></header><main id="main">{body}</main><footer class="footer"><nav aria-label="{t('資料', 'Resources', lang)}"><a href="{home}">LUX SPIRIA</a><a href="../../LICENSE">License / LSP-1.0</a><a href="https://github.com/Yuu-Honda/lux-spiria-results">GitHub ↗</a></nav><small>JUDGMENT TRANSFER / 2026-11-03</small></footer></div></body></html>'''


def build_plan(root=ROOT, source=None, replay=None):
    spec = importlib.util.spec_from_file_location('judgment_transfer_publication_command', ROOT / 'tools/judgment_transfer_publication.py')
    publication = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(publication)
    return publication.prepare_updates(root, source, replay)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--judgment-transfer', type=Path, help='Independently audited public export only')
    parser.add_argument('--judgment-transfer-replay', type=Path, help='Audited own-authored saved-work replay package')
    args = parser.parse_args(argv)
    updates = build_plan(ROOT, args.judgment_transfer, args.judgment_transfer_replay)
    for relative, raw in updates.items():
        path = ROOT / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    print('Built audited judgment-transfer publication.' if updates else 'No audited judgment-transfer export; no publication writes.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, UnicodeError) as error:
        raise SystemExit(str(error)) from error

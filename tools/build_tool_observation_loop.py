"""Build an optional audited functional pilot; no export means no new output."""
import argparse
from html import escape
import importlib.util
import io
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://yuu-honda.github.io/lux-spiria-results/'
DATA_FILE = 'data/tool-observation-loop-2026-10-28.json'
STUDY = 'studies/2026-10-28-tool-observation-loop/'
REPLAY = 'experiments/tool-observation-loop-2026-10-28/'
ZIP_FILE = 'downloads/tool-observation-loop-2026-10-28.zip'
_spec = importlib.util.spec_from_file_location('tool_observation_public_schema', ROOT / 'tools/tool_observation_schema.py')
schema = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(schema)
validate_summary = schema.validate_summary
aggregate_operations = schema.aggregate_operations

CSS = '''.tol-study{max-width:1200px;margin:auto}.tol-study .lead{max-width:900px}.tol-study .section{padding:2.4rem 0}.tol-study .table-wrap{max-width:100%;overflow:auto;overscroll-behavior-x:contain;border:1px solid #34434d;border-radius:12px}.tol-study table{border-collapse:collapse;min-width:660px;width:100%}.tol-study th,.tol-study td{padding:.8rem;text-align:left;border-bottom:1px solid #34434d;vertical-align:top}.tol-study caption{text-align:left;padding:1rem;color:#b8c7cf}.tol-study .tol-caption{display:block;max-width:calc(100vw - 6rem);white-space:normal;overflow-wrap:anywhere}.tol-study .tol-scroll-hint{font-size:.85rem;color:#b8c7cf;margin:.6rem 0;max-width:70ch}.tol-study .tol-trace{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.8rem;list-style:none;padding:0}.tol-study .tol-trace li{padding:1rem;border:1px solid #34434d;border-radius:12px;background:#101a21}.tol-study .tol-trace strong{display:block;color:#9bdfc4}.tol-study code{overflow-wrap:anywhere}.tol-study .boundary-box{margin:1rem 0}.tol-study details{margin:1rem 0}.tol-study summary{cursor:pointer;padding:.8rem}.tol-study .tol-digests td{word-break:break-all;font-family:monospace}.tol-study .note{color:#b8c7cf}.tol-study .download-links{display:flex;flex-wrap:wrap;gap:1rem}@media(max-width:700px){.tol-study .tol-trace{grid-template-columns:1fr 1fr}.tol-study .section{padding:1.6rem 0}}@media(prefers-reduced-motion:reduce){.tol-study *{scroll-behavior:auto}}'''


def t(ja, en, lang):
    return ja if lang == 'ja' else en


def load_summary(path=None):
    return schema.read_summary(ROOT / DATA_FILE if path is None else path)


def read_export(root=ROOT, source=None):
    path = root / DATA_FILE if source is None else Path(source)
    if not path.exists() and source is None:
        return None
    if not path.is_file() or path.is_symlink():
        raise ValueError('Audited public export must be an existing regular file; no publication writes')
    raw = path.read_bytes()
    return schema.validate_summary(schema.parse_json(raw)), raw


def optional_summary(root=ROOT, source=None):
    export = read_export(root, source)
    return None if export is None else export[0]


def outcome(value, lang):
    return t('未計測', 'Unmeasured', lang) if value is None else t('確認', 'Verified', lang) if value else t('確認できず', 'Not verified', lang)


def native_state(value, lang):
    return t('未計測', 'Unmeasured', lang) if value is None else t('変更なし', 'Unchanged', lang) if value else t('変更あり', 'Changed', lang)


def table(caption, headings, rows, css='', lang='en'):
    hint = t('横に長い表は、表の中を左右にスクロールできます。キーボードでは表にフォーカスして左右キーを使えます。', 'Wide tables scroll horizontally. Focus the table region and use the arrow keys.', lang)
    return '<p class="tol-scroll-hint">' + hint + '</p><div class="table-wrap" role="region" tabindex="0" aria-label="' + escape(caption, quote=True) + '"><table class="' + css + '"><caption><span class="tol-caption">' + escape(caption) + '</span></caption><thead><tr>' + ''.join('<th scope="col">' + escape(str(x)) + '</th>' for x in headings) + '</tr></thead><tbody>' + ''.join('<tr><th scope="row">' + escape(str(row[0])) + '</th>' + ''.join('<td>' + escape(str(x)) + '</td>' for x in row[1:]) + '</tr>' for row in rows) + '</tbody></table></div>'


def section(identity, title, body):
    return f'<section class="section" id="{identity}" aria-labelledby="{identity}-title"><div class="section-heading"><h2 id="{identity}-title">{title}</h2></div>{body}</section>'


def boundary(lang):
    return t('これは隔離したnativeインスタンスの機能接続pilotです。完全なnative実行リプレイや、新しいAI判断の再生成ではありません。精度向上・学習・心理的保持・SHIORI速度・full Wake・生物学的な脳は検証していません。', 'This is a functional integration pilot in isolated native instances. Complete native execution replay and fresh AI regeneration are unavailable. Accuracy gains, learning, psychological retention, SHIORI speed, full Wake and biological brains were not tested.', lang)


def achieved(d):
    operations = {row['ordinal']: row for row in d['operations']}
    exact = sum(all(row[field] is True for field in ('tool_source_return', 'judgment_return', 'exact_input_match', 'exact_stdout_match', 'exact_stderr_match')) for row in d['contexts'])
    reads = sum(row['first_operation'] is not None and operations[row['first_operation']]['operation'] == 'lre_read' and row['exit_code'] == 0 for row in d['contexts'])
    return exact, reads


def render(lang, d):
    if lang not in ('ja', 'en'):
        raise ValueError('Supported languages are ja and en')
    validate_summary(d); counts = d['counts']; sources = d['source_counts']; exact, reads = achieved(d)
    title = t('ツールの実記録を、次の操作へつなぐ。', 'Connect actual tool evidence to a subsequent operation.', lang)
    body = '<div class="tol-study"><section class="study-hero"><p class="kicker">FUNCTIONAL INTEGRATION PILOT / 2026-10-28</p><h1>' + title + '</h1><p class="lead">' + t(f'限定した3条件のうち{exact}/3で、手掛かり検索から過去のAI判断と元のtool input/stdout/stderrを返し、原記録との一致を確認しました。続く実操作として、現在のnative状態を読むlre_readが{reads}/3でexit 0でした。', f'In {exact}/3 bounded checks, cued recall returned a historical AI judgment and the original tool input/stdout/stderr with exact evidence matching. Subsequent lre_read operations to read current native state exited zero in {reads}/3 checks.', lang) + '</p><p>' + t('実tool原記録とAIの解釈は別の出典型として扱います。これは接続の機能確認で、成績向上や自然な記憶を示す比較ではありません。', 'Original tool observations and AI interpretations retain separate source types. This checks a functional connection; it is not an accuracy-benefit or natural-memory comparison.', lang) + '</p><p class="note">' + boundary(lang) + '</p></section>'
    finding = '<p>' + t('過去の判断を直接渡す代わりに、有限の手掛かりからnative SHIORIで検索し、元のtool原記録と判断を型を分けて返しました。次に選ばれた操作の名前と終了状態を、各条件の表に残します。', 'Native SHIORI recalled from a finite cue vocabulary, then returned original tool evidence separately from judgment. Each context table identifies the subsequent operation actually chosen and its exit status.', lang) + '</p>'
    finding += f'<p>{t("記録されたnative subprocess操作", "Recorded native subprocess operations", lang)}: <strong>{counts["operations"]}</strong> · exit 0: <strong>{counts["exit_zero"]}</strong> · nonzero: <strong>{counts["exit_nonzero"]}</strong>.</p>'
    finding += '<p>' + t('exit 0はそのprocessの終了状態で、意味的な成功・回答の十分性・記憶の成長を自動的に示しません。操作の件数を独立した経験やAI/provider要求数へ読み替えません。', 'Exit zero is a process status; it does not automatically establish semantic success, answer adequacy or memory growth. Operation counts are not independent experiences or AI/provider request counts.', lang) + '</p>'
    finding += f'<p>{t("意味索引に入った出典の型別件数", "Typed sources in the semantic index", lang)}: tool_observation {sources["tool_observations"]}; actual_ai_judgment {sources["actual_ai_judgments"]}; {t("独立したtool event", "independent tool events", lang)} {sources["independent_events"]}. ' + t('これは全invocation観察の件数ではありません。同じeventのツール原記録とAI解釈は、別々の経験2件として数えません。後で追加した条件付きnative判断がすべて索引に入るとは限りません。', 'This is not the count of all invocation observations. A tool receipt and its AI interpretation of the same event are not two independent experiences. Later condition-bound native judgments are not necessarily indexed.', lang) + '</p>'
    body += section('finding', t('3つの確認で、何をつないだか。', 'What the three checks connected.', lang), finding)
    trace = [('01', t('実行前の予測・計画', 'Pre-execution prediction and plan', lang)), ('02', t('実tool記録と別のAI判断', 'Actual tool observation and separate AI judgment', lang)), ('03', t('native保存・review・手掛かり検索', 'Native capture, review and cued recall', lang)), ('04', t('原記録を返し、次の操作へ', 'Return original evidence and perform the next operation', lang))]
    flow = '<p>' + t('下は保存済み記録の読み順です。このページでnative処理を動かすものではありません。各段階の実測は下表に残します。', 'This is the reading order for a recorded trace. This page does not execute native operations. Actual measurements remain in the tables below.', lang) + '</p><ol class="tol-trace">' + ''.join(f'<li><strong>{n}</strong>{label}</li>' for n, label in trace) + '</ol>'
    body += section('recorded-trace', t('記録された接続をたどる。', 'Follow the recorded connection.', lang), flow)
    operations_by_id = {row['ordinal']: row for row in d['operations']}
    rows = [[r['id'], r['condition'], '—' if r['first_operation'] is None else 'O' + str(r['first_operation']).zfill(3) + ' · ' + operations_by_id[r['first_operation']]['operation'], '—' if r['exit_code'] is None else r['exit_code'], outcome(r['tool_source_return'], lang), outcome(r['judgment_return'], lang), outcome(r['old_retained_preserved'], lang)] for r in d['contexts']]
    contexts = table(t('3つの限定したcontext check。独立した大標本比較ではありません。', 'Three bounded context checks, not a large independent comparison.', lang), ['ID', 'Condition', 'First operation', 'Exit', 'Tool source', 'Judgment', 'Earlier retained'], rows, lang=lang)
    rows = [[r['id'], outcome(r['exact_input_match'], lang), outcome(r['exact_stdout_match'], lang), outcome(r['exact_stderr_match'], lang), '—' if r['graph_support_path_count'] is None else r['graph_support_path_count'], outcome(r['hops0_same_hits'], lang), outcome(r['convergence_off_same_hits'], lang)] for r in d['contexts']]
    contexts += table(t('原記録の一致と経路診断は、次の操作結果と別に読む。', 'Exact evidence matching and path diagnostics are separate from subsequent operation outcomes.', lang), ['ID', 'Input exact', 'Stdout exact', 'Stderr exact', 'Support paths', 'Hops 0: same hits', 'Convergence off: same hits'], rows, lang=lang)
    rows = [[r['id'], '—' if r['matched_cue_count'] is None else r['matched_cue_count'], *['—' if r[field] is None else r[field] for field in ('top_score', 'hops0_top_score', 'convergence_off_top_score')]] for r in d['contexts']]
    contexts += table(t('同じhitsとは順序付きepisode identityの一致で、scoreの一致ではありません。scoreはconfidenceではなく順位値です。', 'Same hits means ordered episode identity, excluding scores. Scores are ranking values, not confidence.', lang), ['ID', 'Matched cues', 'Top score', 'Hops 0 top score', 'Convergence off top score'], rows, lang=lang)
    contexts += '<p>' + t('変更contextは明示した人工的介入です。旧判断を消して全体へ一般化せず、新しい条件付き判断を追加して戻り条件を確認します。経路が動いたことやhitsの一致だけを、網の因果効果・速度改善へ広げません。', 'The changed context is an explicit engineered intervention. Earlier judgments are retained while a condition-bound judgment is appended and legacy return is checked. Executed paths or matching hits alone do not establish a graph contribution or speed improvement.', lang) + '</p>'
    contexts += '<p>' + t('continuationは、sourceへの対応表・本文・IDを含まない8つのreview済みラベルという有限の手掛かり語彙から選びます。自然言語全般の理解試験ではありません。複数cueの直接集約はscoreを変え得ますが、cueを独立した事実や間接graphの寄与として数えません。', 'Continuations select from a disclosed finite vocabulary of eight reviewed cue labels without source mappings, bodies or IDs. This is not a test of unconstrained language comprehension. Direct cue aggregation can change a score; cues are not independent facts or evidence of indirect graph contribution.', lang) + '</p>'
    contexts += '<p>' + t('変更copyで新しい条件付き判断をnative LREへ保存しましたが、その新判断は索引化も、その後の検索もしていません。反復的な学習loopが成立した証拠とは扱いません。', 'A new condition-bound judgment was saved in native LRE in the changed copy, but that new judgment was neither indexed nor subsequently recalled. This does not establish recurrent learning.', lang) + '</p>'
    body += section('contexts', t('変更と、元の条件への戻りを確認する。', 'Check changed context and return to earlier conditions.', lang), contexts)
    rows = [['O' + str(r['ordinal']).zfill(3), r['phase'], r['operation'], r['exit_code'], outcome(r['plan_before_execution'], lang), native_state(r['native_state_unchanged'], lang), r['revision']] for r in d['operations']]
    operations = table(t('失敗を含む全actual操作。native状態の未計測はnullとして残す。', 'Every actual operation, including failures; unmeasured native-state equality remains null.', lang), ['ID', 'Phase', 'Operation', 'Exit', 'Plan before execution', t('native状態', 'Native state', lang), 'Revision'], rows, lang=lang)
    operations += '<details><summary>' + t('操作時計と原manifestのhash', 'Operation clocks and original manifest digests', lang) + '</summary>' + table('UTC / SHA256', ['ID', 'Started', 'Finished', 'Manifest SHA256'], [['O' + str(r['ordinal']).zfill(3), r['started_at_utc'], r['finished_at_utc'], r['manifest_sha256']] for r in d['operations']], 'tol-digests', lang=lang) + '</details>'
    body += section('operations', t('操作の実記録を残す。', 'Retain the actual operation record.', lang), operations)
    engineering = table(t('人工fixtureによる工学検証。actual pilot結果に合算しない。', 'Synthetic engineering checks; do not pool with actual pilot outcomes.', lang), ['Round', 'Tests', 'Workers', 'Failures', 'Errors'], [[r['round'], r['tests'], r['worker_invocations'], r['failures'], r['errors']] for r in sorted(d['engineering'], key=lambda x: x['round'])], lang=lang)
    engineering += '<p>' + t('最初のinitializeはrevision 1で実行されました。元inputの返却を追加したreview済みrevision 2への修正は、意味索引・continuationの前に固定されました。最初の実行を捨てたり、pilotをやり直したりしていません。', 'The initial initialize operation used revision 1. The reviewed revision 2 correction added original-input return before semantic indexing and continuation. The initial run was retained; the pilot was not discarded or restarted.', lang) + '</p>'
    engineering += '<p>' + t('索引前の診断queryには実際の事前計画がありましたが、native呼出し前の独立したcue-span/review artifactがありませんでした。これは採点したcontinuationではありません。3つのcontinuationの手掛かり選択には呼出し前のhashで結んだspan/review記録を用い、この違いを全工程の一律遵守とは呼びません。', 'The pre-index diagnostic query had an actual prospective plan but lacked a separate cue-span/review artifact before the native call. It was not a scored continuation. The three continuation cue choices use hash-bound span/review records before their calls; this difference prevents a claim of universal protocol compliance.', lang) + '</p>'
    body += section('engineering', t('工学検証とpilotの境界を残す。', 'Retain engineering and pilot boundaries.', lang), engineering)
    privacy = '<p>' + t('人間の私的会話や過去のprivate会話を取得・利用していません。公開物は操作・型・終了・時計・件数・hashに限定します。tool input/stdout/stderr本文、AI判断本文、vendor code、native DB/state、意味feature・cue・trace本文、実行者IDとlocal pathは含みません。provider/model/settings/token/compute情報は未確認のnullです。', 'No human or private conversation content was fetched or used. Public data is limited to operation types, exit codes, clocks, counts and digests. Tool input/stdout/stderr bodies, AI judgment text, vendor code, native databases/state, feature/cue/trace bodies, actor IDs and local paths are excluded. Provider/model/settings/token/compute metadata remains unverified and null.', lang) + '</p><p>' + boundary(lang) + '</p>'
    privacy += '<p>' + t('以前の24時間試験は別の凍結研究です。その記録・課題・automationにこのpilotを混ぜず、直後公開物の未収集状態と過去9研究・4つの概要animationを保持します。', 'The earlier 24-hour endpoint is a separate frozen study. This pilot does not enter its actors, memory, tasks or automation. Its immediate publication keeps its pending state; all nine previous studies and four overview animations are preserved.', lang) + '</p>'
    privacy += '<details><summary>' + t('監査とコードの識別hash', 'Audit and code identity digests', lang) + '</summary>' + table('SHA256', ['Artifact', 'SHA256'], [[k, d['provenance'][k]] for k in sorted(d['provenance'])], 'tol-digests', lang=lang) + '</details>'
    body += section('limits', t('公開範囲と、未検証のこと。', 'Public scope and what remains untested.', lang), privacy)
    verification = '<p>' + t('公開verifierは、開示したJSONの厳格なschema・集計とpackageのhash/byteを再計算します。非公開native操作を再構成せず、exportの意味的主張を独立に証明するものでもありません。hashはlocal記録の識別で、外部署名やhardware attestationではありません。', 'The public verifier recalculates the disclosed JSON schema, aggregates and package hashes/bytes. It cannot reconstruct undisclosed native operations or independently prove exported claims. Digests identify local records; they are not external signatures or hardware attestation.', lang) + '</p><div class="download-links"><a href="../../' + DATA_FILE + '">' + t('公開JSON', 'Public JSON', lang) + '</a><a href="../../' + REPLAY + 'README.md">' + t('保存evidenceの検証手順', 'Saved-evidence verification', lang) + '</a><a href="../../' + ZIP_FILE + '" download>ZIP ↓</a></div>'
    body += section('verification', t('開示した記録を検算する。', 'Verify the disclosed record.', lang), verification)
    results = '../../results.html' if lang == 'ja' else '../../results.en.html';home = '../../index.html' if lang == 'ja' else '../../index.en.html'
    switch = '<a href="index.html" lang="ja" hreflang="ja"' + (' aria-current="page"' if lang == 'ja' else '') + '>日本語</a><a href="en.html" lang="en" hreflang="en"' + (' aria-current="page"' if lang == 'en' else '') + '>EN</a>'
    canonical = BASE + STUDY + ('' if lang == 'ja' else 'en.html')
    manifest = 'site.webmanifest' if lang == 'ja' else 'site.en.webmanifest'
    desc = t('実tool原記録とAI判断を分けたnative LRE/SHIORI接続pilot。3context、全操作、工学検証と再現範囲を記録。', 'A native LRE/SHIORI integration pilot separating actual tool evidence from AI judgments. Three contexts, all operations, engineering checks and reproducibility limits.', lang)
    return f'<!doctype html>\n<html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title} — LUX SPIRIA Results</title><meta name="description" content="{desc}"><link rel="canonical" href="{canonical}"><link rel="alternate" hreflang="ja" href="{BASE+STUDY}"><link rel="alternate" hreflang="en" href="{BASE+STUDY}en.html"><meta name="theme-color" content="#090d12"><link rel="icon" type="image/png" sizes="32x32" href="../../assets/favicon-32.png"><link rel="apple-touch-icon" sizes="180x180" href="../../assets/apple-touch-icon.png"><link rel="manifest" href="../../{manifest}"><link rel="stylesheet" href="../../site.css"><link rel="stylesheet" href="../../theme-dark.css"><link rel="stylesheet" href="tool-observation-loop.css"></head><body><a class="skip-link" href="#main">{t("本文へ", "Skip to content", lang)}</a><div class="page"><header class="masthead"><a class="brand" href="{results}"><img src="../../assets/lux-symbol.png" alt="" width="44" height="44"><span class="brand-wordmark">LUX SPIRIA<span class="brand-subtitle">RESEARCH RESULTS</span></span></a><nav aria-label="{t("主なページ", "Main navigation", lang)}"><a href="{results}#studies">{t("研究結果", "Studies", lang)}</a><a href="#contexts">{t("3条件", "Three contexts", lang)}</a><a href="{home}">{t("全体像", "Overview", lang)}</a><span class="lang">{switch}</span></nav></header><main id="main">{body}</div></main><footer class="footer"><nav aria-label="{t("資料", "Resources", lang)}"><a href="{home}">LUX SPIRIA</a><a href="../../LICENSE">License / LSP-1.0</a><a href="https://github.com/Yuu-Honda/lux-spiria-results">GitHub ↗</a></nav><small>RECORDED FUNCTIONAL PILOT / 2026-10-28</small></footer></div></body></html>'


def evidence_package(d, raw):
    validate_summary(d)
    if schema.validate_summary(schema.parse_json(raw)) != d:
        raise ValueError('Evidence bytes must be the exact validated public summary')
    readme = '''# Saved-evidence verification — 2026-10-28

This four-file package verifies disclosed tool-observation pilot metadata only.
It does not contain private native code/state, tool or judgment bodies, cues,
features, actor IDs, or a complete native execution replay.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B verify.py
```

The verifier checks exact uppercase MANIFEST.json, the complete four-file
inventory, every other file's SHA256 and byte size, the strict evidence schema,
context/operation bindings and disclosed arithmetic. It performs no native
operation and generates no new AI judgment. These checks cannot reconstruct
undisclosed operations or independently prove exported claims. Hashes identify
local records; they are not external signatures or hardware attestation.

Actual pilot results and the two synthetic engineering rounds are separate.
The initial initialize used revision 1; the reviewed original-input-return
correction used revision 2 before semantic indexing/continuation. No run was
discarded or restarted. A pre-index diagnostic had a prospective plan but no
separate pre-call cue-span/review artifact; it was not a scored continuation.
The continuation cue choices use hash-bound pre-call span/review records.
One tool event and its AI interpretation are not two independent experiences.
The new changed-copy judgment was saved in native LRE but was not indexed or
subsequently recalled; this does not establish recurrent learning.
No human/private conversation was fetched or used. The previous delayed study
is separate and unchanged. Provider/model metadata is unverified and null.

The existing project LICENSE applies; this package grants no new license to
private native dependencies. Read the dated JA/EN study for all limits.
'''.encode('utf-8')
    files = {'README.md': readme, 'evidence.json': raw, 'verify.py': (ROOT / 'tools/tool_observation_schema.py').read_bytes()}
    manifest = {'schema_version': 1, 'files': {name: {'sha256': schema.sha256(value), 'bytes': len(value)} for name, value in sorted(files.items())}}
    files['MANIFEST.json'] = (json.dumps(manifest, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name, value in sorted(files.items()):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0)); info.compress_type = zipfile.ZIP_DEFLATED; info.create_system = 3; info.external_attr = 0o100644 << 16
            z.writestr(info, value, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return files, archive.getvalue()


def build_plan(root=ROOT, source=None):
    spec = importlib.util.spec_from_file_location('tool_observation_publication_command', ROOT / 'tools/tool_observation_loop_publication.py')
    publication = importlib.util.module_from_spec(spec); spec.loader.exec_module(publication)
    return publication.prepare_updates(root, source)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tool-observation-loop', type=Path, help='Audited external public-export-v1.json')
    args = parser.parse_args(argv)
    updates = build_plan(ROOT, args.tool_observation_loop)
    for relative, raw in updates.items():
        path = ROOT / relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
    print('Built audited tool-observation publication.' if updates else 'No audited tool-observation export; no publication writes.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, UnicodeError) as error:
        raise SystemExit(str(error)) from error

"""Build public pages using only public, allowlisted summaries. Python 3 stdlib."""
from pathlib import Path
import json
from html import escape as E
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = 'data/shiori-pilot-2026-10-13.json'
D = json.loads((ROOT / DATA_FILE).read_text())
BASE = 'https://yuu-honda.github.io/lux-spiria-results/'
HUB = BASE
STUDY = 'studies/2026-10-13-shiori-pilot/'
CIDS = [c['id'] for c in D['conditions']]
NEW_DATA_FILE = 'data/shiori-cross-session-2026-10-21.json'
NEW_D = json.loads((ROOT / NEW_DATA_FILE).read_text())
NEW_STUDY = 'studies/2026-10-21-cross-session/'
LATEST_DATA_FILE = 'data/shiori-retrieval-hypotheses-2026-10-21.json'
LATEST_D = json.loads((ROOT / LATEST_DATA_FILE).read_text()) if (ROOT / LATEST_DATA_FILE).is_file() else None
LATEST_STUDY = 'studies/2026-10-21-retrieval-hypotheses/'
EVENT_DATA_FILE = 'data/shiori-event-compatibility-2026-10-22.json'
EVENT_D = json.loads((ROOT / EVENT_DATA_FILE).read_text()) if (ROOT / EVENT_DATA_FILE).is_file() else None
EVENT_STUDY = 'studies/2026-10-22-event-compatibility/'
_adoption_spec = importlib.util.spec_from_file_location('event_adoption_publication', ROOT / 'tools/event_adoption_publication.py')
ADOPTION_PUBLICATION = importlib.util.module_from_spec(_adoption_spec)
_adoption_spec.loader.exec_module(ADOPTION_PUBLICATION)
ADOPTION_D = ADOPTION_PUBLICATION.optional_summary(ROOT)
_working_spec = importlib.util.spec_from_file_location('working_memory_publication', ROOT / 'tools/working_memory_publication.py')
WORKING_PUBLICATION = importlib.util.module_from_spec(_working_spec)
_working_spec.loader.exec_module(WORKING_PUBLICATION)
WORKING_D = WORKING_PUBLICATION.optional_summary(ROOT)
_action_spec = importlib.util.spec_from_file_location('action_feedback_publication', ROOT / 'tools/action_feedback_publication.py')
ACTION_PUBLICATION = importlib.util.module_from_spec(_action_spec)
_action_spec.loader.exec_module(ACTION_PUBLICATION)
ACTION_D = ACTION_PUBLICATION.optional_summary(ROOT)

def T(ja, en, lang): return ja if lang == 'ja' else en

def label(cid, lang):
    return {'direct_max': T('直接照合・最大値', 'Direct · best cue', lang),
            'direct_sum': T('直接照合・合流', 'Direct · cue aggregation', lang),
            'path_max': T('1段の経路・最大値', 'One hop · best cue', lang),
            'path_sum': T('1段の経路・合流', 'One hop · cue aggregation', lang)}[cid]

def category(cid, lang):
    return {'direct_source_question': T('直接', 'Direct', lang),
            'paraphrase_question': T('言い換え', 'Paraphrase', lang),
            'two_clue_question': T('二手掛かり', 'Two clues', lang),
            'no_answer_control': T('対象なし', 'No target', lang)}[cid]

def section(sid, eyebrow, title, desc='', content=''):
    return f'<section class="section" id="{sid}" aria-labelledby="{sid}-title"><div class="section-heading"><p class="eyebrow">{eyebrow}</p><h2 id="{sid}-title">{title}</h2>' + (f'<p>{desc}</p>' if desc else '') + f'</div>{content}</section>'

def table(caption, heads, rows, cls=''):
    return '<div class="table-wrap" role="region" aria-label="' + E(caption) + '" tabindex="0"><table class="' + cls + '"><caption>' + caption + '</caption><thead><tr>' + ''.join(f'<th scope="col">{h}</th>' for h in heads) + '</tr></thead><tbody>' + ''.join('<tr><th scope="row">'+str(r[0])+'</th>'+''.join(f'<td>{v}</td>' for v in r[1:])+'</tr>' for r in rows) + '</tbody></table></div>'

def cards(items):
    return '<div class="method-grid">'+''.join(f'<article><h3>{h}</h3><p>{p}</p></article>' for h,p in items)+'</div>'

def document(lang, study, title, description, body, *, study_path=STUDY, record_date=None):
    prefix = '../../' if study else ''
    home = prefix + ('results.html' if lang == 'ja' else 'results.en.html')
    ja = BASE + (study_path if study else 'results.html')
    en = ja + 'en.html' if study else BASE + 'results.en.html'
    canonical = ja if lang == 'ja' else en
    ja_switch = 'index.html' if study else 'results.html'
    en_switch = 'en.html' if study else 'results.en.html'
    hub = HUB + ('' if lang == 'ja' else 'index.en.html')
    nav = f'<a href="{home}#studies">{T("研究結果", "Studies", lang)}</a><a href="{home}#scope">{T("公開範囲", "Public scope", lang)}</a><a href="{hub}">{T("研究の全体像", "Project overview", lang)} ↗</a>'
    languages = f'<span class="lang" aria-label="{T("表示言語", "Language", lang)}"><a href="{ja_switch}" lang="ja" hreflang="ja"'+(' aria-current="page"' if lang=='ja' else '')+f'>日本語</a><span aria-hidden="true">/</span><a href="{en_switch}" lang="en" hreflang="en"'+(' aria-current="page"' if lang=='en' else '')+'>EN</a></span>'
    return f'''<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — LUX SPIRIA Results</title><meta name="description" content="{E(description, quote=True)}">
<link rel="canonical" href="{canonical}"><link rel="alternate" hreflang="ja" href="{ja}"><link rel="alternate" hreflang="en" href="{en}"><link rel="alternate" hreflang="x-default" href="{ja}">
<meta name="theme-color" content="#090d12"><meta name="apple-mobile-web-app-title" content="LUX Results">
<meta property="og:type" content="website"><meta property="og:title" content="{E(title, quote=True)} — LUX SPIRIA Results"><meta property="og:description" content="{E(description, quote=True)}"><meta property="og:url" content="{canonical}"><meta property="og:image" content="{BASE}assets/lux-symbol.png">
<link rel="icon" type="image/png" sizes="32x32" href="{prefix}assets/favicon-32.png"><link rel="apple-touch-icon" sizes="180x180" href="{prefix}assets/apple-touch-icon.png"><link rel="manifest" href="{prefix}{'site' if lang=='ja' else 'site.en'}.webmanifest"><link rel="stylesheet" href="{prefix}site.css"><script src="{prefix}results.js" defer></script>
</head><body><a class="skip-link" href="#main">{T('本文へ', 'Skip to content', lang)}</a><div class="page">
<header class="masthead"><a class="brand" href="{home}" aria-label="LUX SPIRIA Results"><img src="{prefix}assets/lux-symbol.png" alt="" width="44" height="44"><span class="brand-wordmark">LUX SPIRIA<span class="brand-subtitle">RESEARCH RESULTS</span></span></a><nav aria-label="{T('主なページ', 'Main navigation', lang)}">{nav}{languages}</nav></header>
<main id="main">{body}</main>
<footer class="footer"><nav aria-label="{T('資料と規約','Resources and terms',lang)}"><a href="{hub}">LUX SPIRIA ↗</a><a href="{prefix}LICENSE">License / LSP-1.0</a><a href="https://github.com/Yuu-Honda/lux-spiria-results">GitHub ↗</a></nav><small>RESULT RECORD / {record_date or D['date']} · v1</small></footer>
</div></body></html>'''

def scope(lang):
    return section('scope', 'PUBLIC SCOPE', T('公開するもの、保持するもの。','What is public, what is retained.',lang),
        T('概要・結果・歴史を、それぞれ追跡できる形に分けています。','Overview, results and history remain separately traceable.',lang), cards([
        (T('このResults','This Results site',lang),T('固定した手順、全条件の集計、匿名化した問別結果、実行確認と限界を公開します。画面は保存済み結果の表示です。閲覧中にSHIORIやAIを実行しません。','Publishes the frozen procedure, all condition aggregates, opaque per-query results, verification and limitations. These pages display stored results; they do not run SHIORI or an AI while you browse.',lang)),
        (T('非公開の研究一式','Private research bundle',lang),T('会話原文・質問本文・出典ID・特徴語・SQLite・実験用コードと詳細ログは非公開で保持します。公開集計は再計算できますが、第三者が公開ファイルだけで原文照合やエンジン再実行を行うことはできません。','Original conversations, question text, source IDs, feature terms, SQLite, experiment code and detailed logs remain private. Public aggregates can be recalculated; source auditing and engine reruns cannot be performed from public files alone.',lang)),
        (T('LUX SPIRIAの研究史','LUX SPIRIA history',lang),T('起点の問い、過去の観測、README、releaseは元のプロジェクトに保持します。新しい実験結果で過去を書き換えません。','The originating questions, past observations, README and releases remain in the original project. New experiments do not rewrite past records.',lang)),
        (T('今回まだ測っていないもの','Not evaluated in this study',lang),T('LREの全Wake、Emotionの効果、応答生成、日常会話での自然な想起、人格連続性は今回の評価対象に含みません。','Full LRE Wake, Emotion effects, response generation, natural everyday recall and personality continuity were not evaluated.',lang))]))

def landing(lang):
    if LATEST_D is None or EVENT_D is None:
        raise FileNotFoundError('Audited latest public summary is not available; no listings were written')
    studyurl = STUDY + ('index.html' if lang=='ja' else 'en.html')
    body = f'''<section class="results-hero"><p class="eyebrow">LUX SPIRIA / RESEARCH RESULTS</p><h1>{T('問いと手順を固定し、<br>結果を残す。','Fix the question.<br>Keep the result.',lang)}</h1><p class="lead">{T('記憶・感情・変化・想起・連続性。その研究で実際に何を動かし、何が起き、どこまで確かめたかを残す場所です。','Memory, affect, change, recall and continuity. A record of what was actually run, what happened, and how far verification reaches.',lang)}</p></section>
<div class="status-strip"><span>{T('実行済み結果を公開 · 小規模な探索的試験','Recorded execution · small exploratory pilot',lang)}</span><small>UPDATED / {EVENT_D['date']}</small></div>
<div class="hero-metrics"><div class="metric"><strong>04</strong><span>{T('公開研究','Published studies',lang)}</span><small>2026-10-13 / 2026-10-22</small></div><div class="metric"><strong>{EVENT_D['sample']['sessions']}</strong><span>{T('最新試験の実会話','Real sessions in latest study',lang)}</span><small>{T('各8件・計32原文メッセージ','Eight messages each · 32 source messages',lang)}</small></div><div class="metric"><strong>{EVENT_D['sample']['queries']}</strong><span>{T('最新試験の質問','Queries in latest study',lang)}</span><small>{T('対象あり16・対象なし8・紛らわしい8','16 positive · 8 absent · 8 confusable',lang)}</small></div></div>'''
    card = f'''<article class="study-card"><span class="study-status">RUN 001 / EXPLORATORY PILOT</span><time datetime="{D['date']}">{D['date']}</time><h3><a href="{studyurl}">{T('SHIORI、手掛かりと経路の比較。','SHIORI: cues, paths and retrieval.',lang)} ↗</a></h3><p>{T('実会話を固定し、直接照合と1段の経路、最大値と手掛かりの合流を4条件で比較。索引のレビュー依存と、言い換えで入口が作れなかった失敗も記録しました。','A frozen real-dialogue sample compared direct versus one-hop retrieval and best-cue versus cue aggregation across four conditions. The record includes review-dependent indexing and failures to form cues for paraphrases.',lang)}</p><div class="study-stats"><span><strong>4</strong>{T('比較条件','conditions',lang)}</span><span><strong>0 → 203</strong>{T('標準解析 → レビュー後の延べ特徴数','default → reviewed feature occurrences',lang)}</span><span><strong>0 / 8</strong>{T('言い換えの対象到達','paraphrase target hits',lang)}</span></div></article>'''
    newurl = NEW_STUDY + ('index.html' if lang == 'ja' else 'en.html')
    latest = f'''<article class="study-card"><span class="study-status">STUDY / CROSS-SESSION REPLICATION</span><time datetime="{NEW_D['date']}">{NEW_D['date']}</time><h3><a href="{newurl}">{T('誤接続は減った。取得改善は再現しなかった。','Fewer false returns. No replicated retrieval gain.',lang)} ↗</a></h3><p>{T('別の実会話4件・32問で、元の発話による検索、AIが作る手掛かり、原文確認ゲートを比較。紛らわしい対象への誤接続は減りましたが、検索前の停止と厳しすぎる照合で、必要な記憶も落としました。最初の技術的失敗と、別条件での修正後の結果を併記しています。','Four further real conversations and 32 queries compared original-query retrieval, AI-authored cues and a source gate. Confusable false returns fell, but pre-search abstention and overly strict matching also lost relevant records. The initial technical failure and the separately amended scored condition are both retained.',lang)}</p><div class="study-stats"><span><strong>7/16 → 5/16</strong>{T('対象場面の取得','positive scene hits',lang)}</span><span><strong>6/8 → 0/8</strong>{T('紛らわしい候補の返却','confusable false returns',lang)}</span><span><strong>0</strong>{T('全条件の連想経路展開','graph expansions in every condition',lang)}</span></div></article>'''
    newesturl = LATEST_STUDY + ('index.html' if lang == 'ja' else 'en.html')
    current = {c['id']:c for c in LATEST_D['conditions']}
    a, b = current['legacy_gated'], current['recovery_gated']
    newest = f'''<article class="study-card"><span class="study-status">STUDY / RETRIEVAL HYPOTHESES</span><time datetime="{LATEST_D['date']}">{LATEST_D['date']}</time><h3><a href="{newesturl}">{T('取得は増えた。取り違えは残った。','More relevant hits. Mix-ups remained.',lang)} ↗</a></h3><p>{T('さらに別の実会話4件・新規32問で、元の検索を残し、否定・仮定・不確実性を検索仮説として加える6条件を比較。原文ゲートは同じ厳格な条件です。改善方式でも、対象ありの別場面誤返却1問、紛らわしい対象への誤返却1問、対象ありの未取得1問が残りました。','Four further conversations and 32 new queries compared six conditions preserving original-query retrieval while adding negation, hypothetical cues and uncertainty as search hypotheses. The strict source gate stayed unchanged. The recovery policy still returned one wrong positive scene, returned one confusable false candidate, and missed one positive query.',lang)}</p><p>{T('網と合流は実行されましたが、独立診断では全32問・全6条件で無効化しても最終選択が同じでした。今回の取得増加を網の寄与や速度改善とは扱いません。','Traversal and convergence ran, but independent diagnostics found unchanged final selections when either was disabled, for all 32 queries in all six conditions. The retrieval increase does not demonstrate a graph contribution or a speed improvement.',lang)}</p><div class="study-stats"><span><strong>{a['positive_hits']}/16 → {b['positive_hits']}/16</strong>{T('従来方式 → 改善方式の対象取得（同じ原文ゲート）','legacy → recovery positive hits (same source gate)',lang)}</span><span><strong>{a['confusable_false_returns']}/8 → {b['confusable_false_returns']}/8</strong>{T('紛らわしい対象への誤返却','confusable false returns',lang)}</span><span><strong>{b['positive_wrong_scene_returns']}/16</strong>{T('改善方式の別場面誤返却','recovery wrong positive scenes',lang)}</span></div></article>'''
    eventurl = EVENT_STUDY + ('index.html' if lang == 'ja' else 'en.html')
    event_arms = {c['id']: c for c in EVENT_D['conditions']}
    strict, reviewed = event_arms['strict_source_gate'], event_arms['strict_and_event_review']
    expansions = sum(q['retrieval']['graph_expansions'] for q in EVENT_D['per_query'])
    selection_changes = sum(not q['ablations'][variant][arm]['same_selection_as_normal'] for q in EVENT_D['per_query'] for variant in ('hops0', 'without_convergence') for arm in event_arms)
    graph_note = T(f'新規32問の経路展開は{expansions}件。網・合流の無効化で最終選択が変わった問・条件・診断の組合せは{selection_changes}件でした。', f'The fresh set had {expansions} graph expansions and {selection_changes} changed query-condition-diagnostic selections when traversal or convergence was disabled.', lang)
    event = f'''<article class="study-card"><span class="study-status">STUDY / EVENT COMPATIBILITY</span><time datetime="{EVENT_D['date']}">{EVENT_D['date']}</time><h3><a href="{eventurl}">{T(f'対象取得{reviewed["positive_hits"]}/16。誤候補を原文で確かめた。',f'{reviewed["positive_hits"]}/16 target hits. False candidates checked against source.',lang)} ↗</a></h3><p>{T('新たな実会話4件・32問で、同じ検索候補に厳格な原文ゲート、出来事の適合レビュー、両方を加える4条件を比較。AIが質問と候補の原文を読み、行為・文脈・指示対象・役割・時点・様態を照合しました。','Four further archived conversations and 32 new queries compared four conditions using the same retrieved candidates: no gate, the strict source gate, event compatibility review, and both. An AI read queries and linked originals to check action, context, referent, role, time and mode.',lang)}</p><div class="study-stats"><span><strong>{strict['positive_hits']}/16 → {reviewed['positive_hits']}/16</strong>{T('厳格な原文ゲート → 同ゲート＋出来事レビューの対象取得','strict source gate → same gate + event review: positive hits',lang)}</span><span><strong>{strict['confusable_false_returns']}/8 → {reviewed['confusable_false_returns']}/8</strong>{T('紛らわしい対象への誤返却','confusable false returns',lang)}</span><span><strong>{strict['absent_false_returns']}/8 → {reviewed['absent_false_returns']}/8</strong>{T('対象なしへの誤返却','absent false returns',lang)}</span></div><p>{graph_note} {T('既知32問の回帰とその網の診断は別に報告します。世界での真偽や回答への採用を検証した結果ではありません。','The known 32-query regression set and its graph diagnostics are reported separately. These results do not establish world-event truth or answer adoption.',lang)}</p></article>'''
    body += section('studies', '01 / STUDIES', T('実験の記録。','Study records.',lang), T('成功した条件だけでなく、失敗した入力と再現の範囲も残します。','Successes, failed inputs and the scope of reproduction are recorded together.',lang),event + newest + latest + card)
    body += section('method', '02 / METHOD', T('結果の手前に、手順を置く。','The procedure comes before the result.',lang), content=cards([
        (T('入力を固定する','Freeze the inputs',lang),T('原文、索引、質問、対象となる出典を検索実行前に固定。検索結果を見てから都合よく手掛かりや正解を変えません。','Freeze the source, index, questions and target sources before retrieval. Do not tune cues or targets after seeing the result.',lang)),
        (T('比較条件を全部出す','Show every condition',lang),T('各試験の全比較条件を公開。対象到達、誤接続、検索前の停止を分け、経路や速度の効果は実際に測った試験でのみ報告します。','Publish every comparison condition in each study. Separate target hits, false returns and pre-search abstention; report path and speed effects only when actually measured.',lang))]))
    body += scope(lang)
    html = document(lang,False,T('研究結果','Research results',lang),T('LUX SPIRIAの実行済み研究結果。方法、全条件比較、失敗、再現確認と限界。','Recorded LUX SPIRIA research: methods, all-condition comparisons, failures, verification and limitations.',lang),body,record_date=EVENT_D['date'])
    html = ADOPTION_PUBLICATION.integrate_listing(html, lang, ADOPTION_D)
    html = WORKING_PUBLICATION.integrate_listing(html, lang, WORKING_D)
    return ACTION_PUBLICATION.integrate_listing(html, lang, ACTION_D)

def study(lang):
    body = f'''<section class="study-hero"><p class="kicker">RUN 001 / RETROSPECTIVE PILOT / v1</p><h1>{T('SHIORI、手掛かりと<br>経路の比較。','SHIORI: cues, paths<br>and retrieval.',lang)}</h1><p class="lead">{T('実会話42メッセージを保存し、レビュー済みの意味特徴を延べ203件で索引を作成。別工程で作った24問を固定し、4条件で検索しました。','42 real-dialogue messages were captured and indexed with 203 reviewed semantic-feature occurrences. 24 queries authored in a separate step were frozen and tested under four retrieval conditions.',lang)}</p><p class="note"><time datetime="{D['date']}">{D['date']}</time> · {T('保存済みの実行結果。閲覧中のエンジン実行ではありません。','Stored execution results; no engine runs while you browse.',lang)}</p></section>
<div class="finding-callout"><h2>{T('入口がないと、経路を辿れない。','Without a cue, there is no path to follow.',lang)}</h2><p>{T('言い換え8問は、全条件で手掛かり0・候補0でした。一方、手掛かりの合流は直接照合だけでも上位3件への対象到達を5問増やしました。1段の経路を加えた増分は、上位5件で1問でした。','All eight paraphrase queries produced zero cues and zero candidates in every condition. Cue aggregation added five top-three target hits even without hops. One-hop traversal added one top-five hit.',lang)}</p></div>'''
    chartrows=[]
    for c in D['conditions']:
        h=c['target_hits']
        chartrows.append(f'<li class="chart-row" data-condition="{c["id"]}" data-at-1="{h["at_1"]}" data-at-3="{h["at_3"]}" data-at-5="{h["at_5"]}"><div class="chart-label"><strong>{label(c["id"],lang)}</strong><small>{c["id"]}</small></div><span class="chart-track" aria-hidden="true"><span class="chart-fill" style="width:{h["at_5"]/22*100:.4f}%"></span></span><span class="chart-value">{h["at_5"]} / 22</span></li>')
    chart=f'''<figure class="summary-chart"><figcaption id="hit-caption">{T('上位5件に対象出典が入った質問数 / 対象あり22問','Queries with a target source in the top 5 / 22 target-bearing queries',lang)}</figcaption><label class="metric-control" for="hit-cutoff">{T('表示する集計','Display aggregate',lang)} <select id="hit-cutoff" data-chart-cutoff aria-controls="hit-bars"><option value="5" selected>Top 5</option><option value="3">Top 3</option><option value="1">Top 1</option></select></label><ol id="hit-bars" class="chart-rows">{''.join(chartrows)}</ol><p class="note" data-chart-announcement aria-live="polite"></p></figure>'''
    rows=[[label(c['id'],lang),str(c['target_hits']['at_1']),str(c['target_hits']['at_3']),str(c['target_hits']['at_5']),f'{c["mrr_at_5"]:.4f}'] for c in D['conditions']]
    chart+=table(T('全条件・対象あり22問の結果','All conditions · 22 target-bearing queries',lang),[T('条件','Condition',lang),'Top 1','Top 3','Top 5','MRR@5'],rows)
    chart+=f'<p class="note">{T("対象到達は、実行前に指定した出典のいずれかが返ったことです。会話理解や回答の正確さではありません。MRR@5は最初の対象順位の逆数の平均（上位5件になければ0）。同点はepisode root hash順で、上位5件の外に続く同点は測っていません。","A hit means retrieval of a predesignated target source. It does not measure comprehension or answer correctness. MRR@5 averages the reciprocal rank of the first target, assigning zero beyond five. Ties use episode-root-hash order; ties beyond the returned five were not measured.",lang)}</p>'
    chart+=cards([
        (T('合流の増分','Aggregation increment',lang),T('上位3件で5問増加、減少0。Q04・Q08・Q17・Q20・Q21。これは同じ試験内の記述的な差で、独立した証拠や統計的有意性の証明ではありません。','Five additional top-three hits, no losses: Q04, Q08, Q17, Q20 and Q21. This is a descriptive within-sample difference, not independent evidence or a claim of statistical significance.',lang)),
        (T('経路の増分','Hop increment',lang),T('上位3件の増加0。上位5件ではQ19だけが追加され、順位4でした。単一の手掛かりからの経路であり、複数手掛かりの合流による到達ではありません。','No additional top-three hits. Q19 alone was added at top five, at rank four. It followed a single-cue path, rather than multiple-cue convergence.',lang))])
    body+=section('results','01 / ALL CONDITIONS',T('何が届き、何が届かなかったか。','What was reached, what was missed.',lang),T('母数22。対象なしの2問は、到達率の母数に含めません。','Denominator: 22. The two no-target controls are excluded from target-hit rates.',lang),chart)
    catrows=[]
    for cat in ('direct_source_question','paraphrase_question','two_clue_question'):
        qs=[q for q in D['per_query'] if q['category']==cat]
        hits=lambda k:sum(q['conditions']['path_sum']['target_rank_at_5'] is not None and q['conditions']['path_sum']['target_rank_at_5']<=k for q in qs)
        catrows.append([category(cat,lang),len(qs),hits(3),hits(5)])
    content=table(T('1段の経路＋合流：質問種別ごとの対象到達','One hop + aggregation: target hits by query category',lang),[T('種別','Category',lang),T('問数','Queries',lang),'Top 3','Top 5'],catrows)
    content+=f'<div class="boundary-box"><ul><li>{T("標準解析で意味特徴は0件。延べ203件は、原文だけを読むAIによるレビューで作りました。検索を繰り返して自動学習した結果ではありません。","Default preparation produced zero semantic features. The 203 feature occurrences came from source-only AI-assisted review, not automatic learning through repeated retrieval.",lang)}</li><li>{T("Q09〜Q16は手掛かりも候補も0。unknownの出力も0でしたが、理解済みを意味しません。解析器は未知表現を網羅して列挙しません。","Q09–Q16 had zero cues and candidates. A zero unknown count does not mean comprehension; the parser does not enumerate every unrecognized expression.",lang)}</li><li>{T("対象なし2問も2問とも候補を返しました。検索候補が出たことと、回答可能であることは別です。今回はAIの回答を生成していません。","Both no-target controls returned candidates. Candidate retrieval does not establish answerability. No model answers were generated.",lang)}</li></ul></div>'
    body+=section('failures','02 / FAILURE ANALYSIS',T('索引と解析の限界が見えた。','Indexing and parsing limits became visible.',lang),content=content)
    method=cards([
        (T('01 原文を選ぶ','01 Select source',lang),T('2025-02-27の保存済み会話1セッション。exportの47レコードからsystem 2件と空のAI発話3件を除き、ユーザー21件・AI21件を保存。途中で切れたAI発話1件は補完せず保持しました。','One archived conversation dated 2025-02-27. Of 47 export records, two system records and three empty AI messages were excluded, leaving 21 user and 21 AI messages. One truncated AI message was retained without completion.',lang)),
        (T('02 索引を固定する','02 Freeze indexing',lang),T('1メッセージを1episodeとして原文を保存。原文だけから特徴をレビューし、質問作成前に索引を固定しました。質問を索引作成者には渡していません。','Each message became one episode. Features were reviewed from source alone and frozen before query authoring. The indexer was not given the queries.',lang)),
        (T('03 質問と対象を固定する','03 Freeze queries and targets',lang),T('別工程で直接8・言い換え8・二手掛かり6・対象なし2問を作成。対象出典を検索前に照合しました。ローカルの手順固定であり、外部機関への事前登録ではありません。','A separate step authored eight direct, eight paraphrase, six two-clue and two no-target queries. Target sources were audited before retrieval. This was a local protocol freeze, not external preregistration.',lang)),
        (T('04 全条件を実行する','04 Run all conditions',lang),T('経路0段/1段 × 手掛かり最大値/合流の2×2比較。各手掛かりの最良寄与を足す合流方式を使用。bitmap、上位5件、hub_limit 32、literal補助検索なしで固定しました。','A 2×2 comparison: zero/one hop × best cue/cue aggregation. Aggregation sums the best contribution per cue. Main runs fixed bitmap, limit five, hub_limit 32, and no lexical fallback.',lang))])
    method+=f'<p class="note">{T("保存候補の絞り込みと、2問の対象・表現の修正は初回検索前に記録し、旧版も保持しました。結果を見た後の索引・質問調整はしていません。既存13抜粋との非重複は原文hashと場面で確認しました。日時による独立照合ではありません。","Source selection and two query/target corrections were recorded before the first retrieval; earlier versions were retained. No index or query tuning followed results. Non-overlap with an earlier 13-excerpt sample was checked using text hashes and scenes, not an independent timestamp comparison.",lang)}</p>'
    method+=f'<p class="note">{T("保存と検索は同じcue parser関数を使います。ただし検索時の語彙はレビュー済み特徴で拡張され、標準保存解析時とは異なります。作業分担は同じチーム内のAI補助であり、外部研究者による独立した盲検評価ではありません。","Preparation and recall use the same cue-parser function, but the recall lexicon is expanded by reviewed features and differs from default preparation. Role separation used AI assistance within the same team; it was not independent external blind review.",lang)}</p>'
    body+=section('method','03 / FROZEN METHOD',T('何を固定して、比較したか。','What was fixed for comparison.',lang),content=method)
    rows=[]
    for q in D['per_query']:
        values=[]
        for cid in CIDS:
            rank=q['conditions'][cid]['target_rank_at_5']
            values.append(f'<span class="rank-value">{rank}</span>' if rank else f'<span class="rank-miss">{T("対象なし" if q["category"]=="no_answer_control" else "未到達", "No target" if q["category"]=="no_answer_control" else "Miss",lang)}</span>')
        rows.append([q['id'],category(q['category'],lang)]+values)
    content=table(T('24問の匿名順位：上位5件内の最初の対象','Opaque ranks for 24 queries: first target within top five',lang),['ID',T('種別','Category',lang)]+[label(c,lang) for c in CIDS],rows,'run-table')
    content+=f'<p class="note">{T("Q01〜Q24は今回専用の公開ラベルです。問い本文、原文、出典ID、特徴語は公開しません。全条件の候補数・手掛かり数・同点有無は公開JSONにあります。対象指定は十分な出典を選ぶ方式で、関連する全出典の網羅ではありません。","Q01–Q24 are public labels created for this study. Question text, source text, source IDs and feature terms remain private. Candidate counts, cue counts and within-top-five ties for every condition are in the public JSON. Targets identify sufficient sources, not an exhaustive set of relevant records.",lang)}</p>'
    body+=section('queries','04 / PER-QUERY RESULTS',T('集計の内訳も残す。','Keep the individual outcomes.',lang),content=content)
    timingrows=[[label(r['condition'],lang),r['method'],f'{r["median_ms"]:.4f}',f'{r["p95_ms"]:.4f}',r['n']] for r in D['timing']['samples']]
    timing=table(T('初回実行のwarm recall計時 / ms','Warm recall timing from the first run / ms',lang),[T('条件','Condition',lang),T('方式','Method',lang),T('中央値 ms','Median ms',lang),'p95 ms','n'],timingrows)
    timing+=f'<p class="note">{T("24問×21反復、条件・方式ごとに504サンプル。手掛かり0の質問も含みます。条件と方式の順序を回転して計時。query解析を含み、原文取得・JSON化・DB構築・モデル実行・レビュー時間を含みません。Memory読み込みでは全方式の索引を構築します。","24 queries × 21 repetitions gives 504 samples per condition and method, including zero-cue queries. Timing order was rotated across conditions and methods. Timing includes query parsing, excludes raw-source lookup, serialization, DB construction, model execution and review. Memory loading builds all indexes.",lang)}</p>'
    timing+=f'<div class="boundary-box"><p>{T("42メッセージのこの試験では、二進数・tag・bitmap間の大きな速度優位は示せません。従来の全文検索や旧保存系との速度比較でもありません。別プロセスで確認したのは結果の一致で、計時値の一致ではありません。","This 42-message test does not establish a large speed advantage between binary, tag and bitmap retrieval, or a speedup over full-text search or older storage systems. Cross-process checks reproduced retrieval results, not timing values.",lang)}</p></div>'
    body+=section('timing','05 / MEASURED RUNTIME',T('速度は、測った範囲で読む。','Read timing within its measured scope.',lang),content=timing)
    checks=[T('保存した42件を原文と完全照合','All 42 captured messages matched source rereads',lang),T('24問×4条件の96組で、binary / tags / bitmapの結果・score・evidence一致','Results, scores and evidence matched across binary / tags / bitmap in all 96 query-condition cases',lang),T('検索前後でDB hashが変わらない','Database hash unchanged by retrieval',lang),T('同じDBを再度開いて同じ結果','Reopening the same database returned the same results',lang),T('別Pythonプロセス・新DB・hash seed 0/17で結果と集計が一致','Fresh Python processes and databases with hash seeds 0/17 reproduced results and metrics',lang),T('別検算でhit数とMRRを再計算して一致','Separate recalculation matched hit counts and MRR',lang),T('再実行wrapperで再構築と参照結果一致を確認','A reproduction wrapper verified rebuilding and equality with reference results',lang)]
    verify='<div class="boundary-box"><ul>'+''.join(f'<li>{s}</li>' for s in checks)+'</ul></div>'
    verify+=f'<p class="note">{T("ここでの再実行確認は、非公開の同じ固定入力を用いた内部確認です。公開JSONで集計は追跡できますが、第三者が原文や意味索引の妥当性を独立検証できる公開データセットではありません。","These are internal reproduction checks using the same private frozen inputs. Aggregates are traceable from public JSON; this is not a public dataset enabling independent source or semantic-index validation.",lang)}</p>'
    verify+=f'<details><summary>{T("実装と入力固定の識別子","Implementation and freeze identifiers",lang)}</summary><div class="source-note"><p>{T("実験版SHIORI v0.2の固定snapshotを使用。LRE mainの正本機構とは分離されたdraft prototypeです。","A pinned experimental SHIORI v0.2 snapshot was used, separate from canonical LRE main, as a draft prototype.",lang)}</p><p>Engine commit: <code>{D["provenance"]["engine_commit"]}</code></p><p>Frozen manifest SHA-256: <code>{D["provenance"]["freeze_sha256"]}</code></p><p>Experiment manifest SHA-256: <code>{D["provenance"]["experiment_manifest_sha256"]}</code></p><p>{T("hashは保持した一式の識別子です。それ自体で科学的妥当性や公開再現性を証明しません。","Hashes identify retained bundles; they do not by themselves establish scientific validity or public reproducibility.",lang)}</p></div></details>'
    body+=section('verification','06 / VERIFICATION',T('何を再実行して確かめたか。','What reruns actually verified.',lang),content=verify)
    limits=[T('選択した実会話1件・研究者が作った24問の探索試験。日常会話全体の精度や統計的有意性へ一般化しません。','An exploratory test on one selected conversation and 24 researcher-authored queries. It does not estimate everyday conversation accuracy or statistical significance.',lang),T('原文は「何が語られたか」の記録です。そこで語られた製品や外部事実の正しさを独立に検証したものではありません。','The transcript records what was said; it does not independently establish the truth of product claims or external facts in that conversation.',lang),T('レビュー依存の索引、限定的なparser、上位5件の同点が残ります。人格連続性・主観的感情・自然な想起の因果効果はこの結果から導きません。','Review-dependent indexing, bounded parsing and top-five ties remain. These results do not establish personality continuity, subjective affect or a causal effect on natural recall.',lang),T('LREの全Wake、Emotion、SHIORIとの自動統合、AIの応答生成は実行していません。','Full LRE Wake, Emotion, automatic SHIORI integration and AI response generation were not run.',lang)]
    content='<div class="boundary-box"><ul>'+''.join(f'<li>{l}</li>' for l in limits)+'</ul></div>'
    content+=f'<div class="download-links"><a href="../../{DATA_FILE}" download>{T("公開集計JSONを取得","Download public summary JSON",lang)}</a><a href="../../{ "results.html" if lang=="ja" else "results.en.html"}#scope">{T("公開範囲を確認","Read public scope",lang)} →</a></div>'
    body+=section('limits','07 / LIMITATIONS',T('示したことと、まだ示していないこと。','What is shown, and what remains untested.',lang),content=content)
    return document(lang,True,T('SHIORI実会話パイロット','SHIORI real-record pilot',lang),T('実会話42件・24問・4条件。手掛かりの合流、経路探索、失敗、速度、内部再実行確認の記録。','42 real messages, 24 queries, four conditions: cue aggregation, path traversal, failures, timing and internal reproduction checks.',lang),body)

def cross_label(cid, lang):
    return {
        'baseline': T('元の発話で検索', 'Original-query baseline', lang),
        'raw_semantic': T('AIの手掛かりで検索', 'AI cues before source gate', lang),
        'gated_semantic': T('AIの手掛かり＋原文ゲート', 'AI cues + source gate', lang),
    }[cid]


def cross_chart(lang, key, denominator, title, chart_id):
    rows = []
    for c in NEW_D['conditions']:
        count = c[key]
        rows.append(f'<li class="chart-row" data-arm="{c["id"]}"><div class="chart-label"><strong>{cross_label(c["id"], lang)}</strong><small>{c["id"]}</small></div><span class="chart-track" aria-hidden="true"><span class="chart-fill" style="width:{count / denominator * 100:.4f}%"></span></span><span class="chart-value">{count} / {denominator}</span></li>')
    return f'<figure class="summary-chart" aria-labelledby="{chart_id}"><figcaption id="{chart_id}">{title}</figcaption><ol class="chart-rows">{"".join(rows)}</ol></figure>'


def cross_session(lang):
    d = NEW_D
    body = f'''<section class="study-hero"><p class="kicker">STUDY / CROSS-SESSION REPLICATION / v1</p><h1>{T('誤接続は減った。<br>取得も減った。','Fewer false returns.<br>Fewer relevant hits.',lang)}</h1><p class="lead">{T('別の実会話4件・32問で、AIが作る検索の手掛かりと、戻った原文を確認するゲートを比較しました。必要な場面の取得は7/16から5/16へ低下。紛らわしい対象への誤接続は6/8から0/8へ減りました。','Four further real conversations and 32 queries tested AI-authored retrieval cues and a gate checking returned sources. Relevant-scene hits fell from 7/16 to 5/16. Confusable false returns fell from 6/8 to 0/8.',lang)}</p><p class="note"><time datetime="{d['date']}">{d['date']}</time> · {T('修正条件で得た保存済みの実行結果。閲覧中にエンジンやAIを動かしません。','Stored results from a technically amended condition. Browsing does not run the engine or an AI.',lang)}</p></section>
<div class="finding-callout"><h2>{T('取り違えを減らしても、取り出せなければ十分ではない。','Fewer mix-ups are not enough if relevant records are lost.',lang)}</h2><p>{T('以前の小規模試験で見えた取得改善は、この別会話の試験では再現しませんでした。今回確認できたのは、誤候補の削減と、検索を止めすぎる問題が同時にあることです。','The retrieval gain observed in an earlier small trial did not replicate on these further conversations. This study found both fewer false candidates and excessive suppression of retrieval.',lang)}</p></div>'''

    results = cross_chart(lang, 'positive_hits', d['sample']['positive_queries'], T('最終的に返した1件が対象場面 / 対象あり16問','Final single candidate matched target scene / 16 positive queries',lang), 'positive-chart-title')
    results += cross_chart(lang, 'confusable_false_returns', d['sample']['confusable_queries'], T('紛らわしい対象に候補を返した / 8問','Candidate returned for a confusable target / 8 queries',lang), 'false-chart-title')
    rows = [[cross_label(c['id'],lang), f'{c["positive_hits"]} / 16', f'{c["literal_hits"]} / 4', f'{c["paraphrase_hits"]} / 12', f'{c["confusable_false_returns"]} / 8', f'{c["absent_false_returns"]} / 8', f'{c["pre_search_abstentions"]} / 32'] for c in d['conditions']]
    results += table(T('全3条件：異なる母数を混ぜずに比較','All three conditions: distinct denominators',lang), [T('条件','Condition',lang),T('対象場面の取得','Positive scene hits',lang),T('文字一致の取得','Literal hits',lang),T('言い換えの取得','Paraphrase hits',lang),T('紛らわしい対象への誤返却','Confusable false returns',lang),T('対象なしへの誤返却','Absent false returns',lang),T('検索前に停止','Pre-search abstentions',lang)], rows)
    results += f'<p class="note">{T("評価対象は、最終的に選んで返した1件が、事前に指定した原文場面か（scene@1）です。回答の正確さや、人のように思い出したかは評価していません。棒はそれぞれ別の母数を示し、上昇・低下を一つの総合点へまとめません。原文の出来事そのものの同一性も、この数値だけでは確定しません。","The endpoint is whether the final single selected candidate matches a predesignated original-source scene (scene@1). Answer correctness and human-like recollection were not evaluated. The charts have different denominators; rises and falls are not combined into an overall score. These numbers alone do not establish source-event identity.",lang)}</p>'
    results += f'<p class="note">{T("原文ゲートは、実際のAIが保存した要件に対し、原文リンク、原文内の文字、特徴の整合性をコードで確認します。検索のたびにAIが意味を再レビューする仕組みではありません。この確認だけで、同じ人物・対象・出来事への到達が確定するわけではありません。","The source gate uses code to check original-source links, source text and feature compatibility against requirements saved by an actual AI. It does not perform a new AI semantic review for each query. These checks do not establish that the same person, object or event has been reached.",lang)}</p>'
    body += section('results','01 / ALL THREE CONDITIONS',T('届いた記憶と、返してしまった候補。','Relevant scenes and false candidates.',lang),content=results)

    failures = cards([
        (T('検索前に23/32問を止めた','23/32 queries stopped before search',lang),T('AIの手掛かりを使う両条件では、対象あり16問のうち10問も検索前に停止しました。内訳は、否定・不明状態の手掛かり7問、不確実性2問、手掛かりなし1問です。失敗した過去や仮定を含む相談まで探せなくなるため、局所的な否定や不確実性で検索全体を止める設計に課題があります。','Both AI-cue conditions abstained before search on 10 of 16 positive queries: seven for nonpositive or unknown cue state, two for uncertainty and one for no cues. Past failures and hypothetical consultations can still have relevant records. Local negation or uncertainty should not automatically close the whole retrieval route.',lang)),
        (T('ゲートは誤候補3件と正解1件を落とした','The gate removed three false and one correct candidate',lang),T('検索された9候補のうち4件を棄却。3件は紛らわしい対象への誤候補でしたが、1件は正しい場面でした。一般的な言い換えにも厳密な文字の存在を要求し、正しい候補を落としました。言い換えと、人物・対象・出来事の同一性を分けて扱う必要があります。','Of nine retrieved candidates, four were rejected: three confusable false candidates and one correct scene. Requiring an exact textual form for a generic paraphrase lost a relevant record. Paraphrase matching needs to be distinguished from person, object and event identity.',lang)),
    ])
    failures += f'<div class="boundary-box"><h3>{T("今回は、網を辿る効果を検証できていない。","Network traversal was not exercised in this study.",lang)}</h3><p>{T("全3条件でgraph expansions、graph edges、associated hitsはすべて0でした。二進数の索引を使った検索は実行しましたが、連想経路や複数経路の合流が効いたという結果ではありません。保存・検索速度の計時も今回は行っていません。","Graph expansions, graph edges and associated hits were all zero in every condition. Retrieval used the binary index, but these results do not show an effect of associative traversal or converging paths. Storage and retrieval speed were not timed here.",lang)}</p></div>'
    body += section('failures','02 / FAILURE ANALYSIS',T('検索を守る仕組みが、検索も止めていた。','The safeguards also suppressed retrieval.',lang),content=failures)

    method = cards([
        (T('01 別の会話を選ぶ','01 Select further conversations',lang),T('保存済み171セッションから、過去8研究で使用・閲覧が記録された会話を除外。8〜60件の対象発話を持つ18候補を時刻とIDで並べ、本文の適性や成績を見る前に最初の4件を選びました。各会話の先頭8件を全文のまま保存し、計32メッセージを使いました。','From 171 archived sessions, conversations with recorded use or exposure in eight prior studies were excluded. Eighteen sessions with 8–60 eligible messages were sorted by time and ID; the first four were selected before judging content suitability or performance. The first eight whole messages per session supplied 32 source messages.',lang)),
        (T('02 原文だけで索引を作る','02 Build an index from source alone',lang),T('1会話の8メッセージを1場面として扱い、実際のAIが原文だけから53特徴を付け、別のAIがレビューしました。検索用の概念は52。索引作成者には質問や正解を渡さず、質問作成前に固定しました。これは粗い場面単位の取得評価です。','Eight messages from each conversation formed one scene. An actual AI authored 53 source-only features and another reviewed them; the retrieval inventory contained 52 cue concepts. Indexing did not receive queries or targets and was frozen before query authoring. The endpoint is coarse scene-level retrieval.',lang)),
        (T('03 質問・対象・AIの判断を残す','03 Retain queries, targets and actual AI choices',lang),T('対象あり16問（文字一致4・言い換え12）、対象なし8問、紛らわしい対象8問を作成。別工程で全32問の対象指定を照合しました。検索手掛かりのAIには語彙と質問だけを渡し、原文・対象・検索結果は見せませんでした。実際の出力とレビューを保存しています。','Sixteen positive queries (four literal, twelve paraphrase), eight absent and eight confusable queries were authored. A separate step checked all 32 target labels. The cue-authoring AI saw the vocabulary and queries, but not sources, target labels or retrieval results. Actual outputs and reviews were retained.',lang)),
        (T('04 3条件を同じ入力で比較','04 Compare three conditions on fixed inputs',lang),T('元の発話による検索、AIの手掛かりによる検索、その結果に原文ゲートを加えた検索を比較。後二者は同じ検索候補を使い、ゲートの有無を分けました。全32問を採点し、結果を見た後の除外や正解の付け替えはありません。','The original-query baseline, AI-cue retrieval and AI cues with a source gate were compared. The latter two shared the same retrieved candidates, isolating the gate. All 32 original labels were scored, with no post-result exclusions or relabeling.',lang)),
    ])
    method += f'<p class="note">{T("選定前の方針は実際の作業ログにありますが、本文を読む前の独立したファイル固定はありません。「未使用」は保持されたローカル記録で過去の使用が見つからなかった意味で、未記録の閲覧やモデルの学習履歴まで保証しません。役割分担は同じホスト上の指示による分離で、外部の盲検評価やアクセス隔離ではありません。使用モデルの識別情報は取得できていません。","The selection policy is recorded in the work log, but there was no separate on-disk freeze before reading source bodies. Unused means no prior use was found in retained local records; it does not guarantee absence of undocumented exposure or model-training overlap. Roles were separated by instructions on a shared host, not external blinding or access isolation. Model identifiers were unavailable.",lang)}</p>'
    body += section('method','03 / FIXED INPUTS',T('どの会話と、どの手順を使ったか。','Which conversations and procedure were used.',lang),content=method)

    amendment = cards([
        (T('最初の条件：技術的失敗','Initial condition: technical failure',lang),T('原文の索引は保存できましたが、ゲートが要求する厳密な証拠形式との不一致で実行が止まりました。一つの特徴に、正規の語を含まない補助的な文脈引用が付いていたためです。この失敗を保持し、採点済みの結果は得られていないと記録しました。','The source index was saved, but execution stopped on a mismatch with the gate’s stricter evidence contract. One feature included a secondary context quote without its canonical term. This failure is retained; no scored results were observed from that condition.',lang)),
        (T('別条件：証拠の形式だけを修正','Separate condition: evidence-only amendment',lang),T('該当する文脈引用1件だけを除き、原文だけを見る実際のAIが再レビューしました。原文、特徴のキー、bit mask、逆引き索引は同じ。32問・対象指定・保存済みのAI出力も同じものを再利用し、修正条件で初めて採点結果を得ました。新しい質問を作り直した試験ではありません。','Only the one context quote was removed, followed by an actual source-only AI review. Source text, feature keys, bit masks and postings stayed unchanged. The same 32 queries, labels and saved AI outputs were reused. Scored results were first observed after this amendment; questions were not freshly authored again.',lang)),
    ])
    body += section('amendment','04 / RETAINED TECHNICAL FAILURE',T('失敗を消さず、修正条件を分ける。','Retain the failure and separate the amendment.',lang),content=amendment)

    checks = [
        T('別のPythonプロセスで、保存済みAI出力を使った検索結果とゲート判断が一致。','Separate Python processes reproduced retrieval and gate decisions using the same saved AI outputs.',lang),
        T('独立した再計算とcold replayで、全32問・3条件の結果を照合。','A separate recalculation and cold replay checked all 32 queries across three conditions.',lang),
        T('技術確認7件は成功。45件の人工入力による工学チェックは、実会話32問とは別に実行。','Seven technical checks passed. Forty-five synthetic engineering checks were separate from the 32 real-source queries.',lang),
        T('元の失敗条件、修正条件、原文選定、索引、質問、実際のAI出力、レビューを非公開の固定記録として保持。','The original failed condition, amendment, source selection, index, queries, actual AI outputs and reviews remain in private frozen records.',lang),
    ]
    verification = '<div class="boundary-box"><ul>' + ''.join(f'<li>{x}</li>' for x in checks) + '</ul></div>'
    verification += f'<p class="note">{T("一致したのは保存済み入力での再生です。AIを再度呼び出して同じ意味判断になるかは試していません。技術確認の成功は、取得精度、人格連続性、感情、脳の再現の証明ではありません。原文照合は内部確認で、公開ファイルだけで第三者が意味索引の妥当性やエンジンを再検証できるデータセットではありません。","The matching runs replayed saved inputs. Regenerating AI interpretations was not tested. Technical checks do not prove retrieval accuracy, personality continuity, affect or brain reproduction. Source checks were internal; public files do not enable independent semantic-index auditing or engine reruns.",lang)}</p>'
    body += section('verification','05 / VERIFICATION',T('再現した範囲を限定する。','State exactly what replay reproduced.',lang),content=verification)

    cat = {'literal':T('文字一致','Literal',lang),'paraphrase':T('言い換え','Paraphrase',lang),'absent':T('対象なし','Absent',lang),'confusable':T('紛らわしい対象','Confusable',lang)}
    rows = []
    for q in d['per_query']:
        cells = [q['id'], cat[q['category']]]
        for c in d['conditions']:
            outcome = q['conditions'][c['id']]
            if not outcome['search_executed']:
                text = T('検索前に停止','Stopped before search',lang)
            elif outcome['target_hit']:
                text = T('対象場面を取得','Target scene hit',lang)
            elif outcome['returned_candidate']:
                text = T('対象外候補を返却','Non-target candidate returned',lang)
            elif c['id'] == 'gated_semantic' and q['conditions']['raw_semantic']['returned_candidate']:
                text = T('候補を棄却','Candidate rejected',lang)
            else:
                text = T('候補なし','No candidate',lang)
            cells.append(text)
        rows.append(cells)
    outcomes = table(T('今回専用の公開ラベルQ01〜Q32：全問の結果','Study-specific opaque labels Q01–Q32: every outcome',lang), ['ID',T('種別','Category',lang)] + [cross_label(c['id'],lang) for c in d['conditions']], rows, 'run-table')
    body += section('queries','06 / ALL 32 QUERIES',T('停止と棄却を、取得失敗と分けて残す。','Distinguish abstention, rejection and retrieval misses.',lang),T('ラベルは今回専用です。質問本文・原文・人物名・出典ID・特徴語は公開しません。','These labels belong to this study only. Query text, source text, personal names, source IDs and feature terms are not published.',lang),f'<details><summary>{T("全32問の内訳を見る","View all 32 outcomes",lang)}</summary>{outcomes}</details>')

    implementation = cards([
        (T('LRE：追加する検索経路を反映','LRE: an additive recall route deployed',lang),T('2026-10-21時点で、非公開正本のmainと維持しているローカルruntimeを更新しました。元の発話による検索を残し、AIの検索仮説を追加する方式です。研究の厳格な全停止ゲートを、そのまま既存検索の置き換えにはしていません。この32問の成績を実機の成績とは扱いません。','As of 2026-10-21, canonical private main and the maintained local runtime checkout were updated. AI search hypotheses are added while retaining original-query retrieval. The study’s strict all-or-nothing gate does not replace the existing route. These 32-query results are not deployed-runtime performance measurements.',lang)),
        (T('SHIORI：実験ブランチまで反映','SHIORI: experimental adapter updated',lang),T('非公開の実験ブランチへ、既存の原文リンクを使う明示的なadapterと、入力時の証拠形式確認を反映しました。LRE mainへの統合はしていません。稼働中のSQLiteの場所は未確認で、その実機DBへの適用や全Wakeの完了は確認していません。','An explicit adapter using original-source links and an input-evidence preflight were merged into the private experimental branch. SHIORI is not merged into LRE main. The operational SQLite location remains unconfirmed; its update and a full Wake completion have not been established.',lang)),
    ])
    implementation += f'<details><summary>{T("実装確認と残る既存エラー","Implementation checks and an existing failure",lang)}</summary><div class="source-note"><p>{T("LREの検索関連83チェックと、実験adapterを含む96工学チェックは成功。LRE保守チェック468件は467成功・既存失敗1件で、変更前の正本でも同じ失敗を確認しました。CURRENT文書の世代・継続先の整合性に関するものです。記憶を書き換えて成功扱いにはしていません。","The 83 LRE recall checks and 96 engineering checks including the experimental adapter passed. LRE maintenance reported 467 passes and one existing failure out of 468; the same failure was reproduced on the pre-change canonical version. It concerns generation and continuation-edge consistency in CURRENT documents. Memory was not rewritten to make the check pass.",lang)}</p><p>{T("これらは別の実装検証です。研究の45人工チェック、7技術確認、32問の結果とは合算しません。","These are separate implementation validations. They are not pooled with the 45 synthetic study checks, seven technical checks or 32-query outcomes.",lang)}</p></div></details>'
    body += section('implementation','07 / IMPLEMENTATION STATUS',T('研究結果と、実機への反映を分ける。','Separate study findings from deployment.',lang),content=implementation)

    next_steps = cards([
        (T('検索と回答への採用を分ける','Separate retrieval from answer adoption',lang),T('否定・失敗・仮定を含む記録も検索候補に残し、戻った原文を読んでから、答えに使えるかを判断する。','Keep records of negation, failure and hypothetical discussion retrievable, then inspect the returned source before deciding whether it supports an answer.',lang)),
        (T('言い換えと対象同一性を分ける','Separate paraphrases from entity identity',lang),T('一般的な言い換えへの文字制約を緩める一方で、人・対象・出来事の混同を原文単位で確かめる。','Avoid overconstraining generic paraphrases while checking person, object and event identity within the original source.',lang)),
        (T('網の効果と速度を別々に測る','Measure network effects and speed separately',lang),T('経路・合流を有効／無効にした比較と、条件を揃えた保存・検索時間の測定を行う。今回は未検証だった部分を次の評価対象にする。','Compare traversal and convergence enabled versus disabled, and measure storage and recall timing under matched conditions. Evaluate what this study did not exercise.',lang)),
    ])
    next_steps += f'<p class="note">{T("今回の32問は修正確認用の既知の回帰問題として残し、改善の評価には別の未使用会話と新しい質問を使います。","Keep these 32 queries as known regression cases. Evaluate improvements on further unused conversations with newly authored queries.",lang)}</p>'
    body += section('next','08 / NEXT RESEARCH',T('次は、取りこぼしを減らせるか。','Next: can relevant recall be recovered?',lang),content=next_steps)

    limits = [
        T('選定した4会話・最初の8件ずつ・研究用32問の小規模評価。日常会話全体への精度推定や統計的な一般化は行いません。','A small evaluation on four selected conversations, their first eight messages each and 32 research queries; it does not estimate everyday accuracy or support statistical generalization.',lang),
        T('自然な想起への因果効果、最終回答の正確さ、LREの全Wake、Emotion、人格連続性、主観的経験、生物学的脳の再現は測定していません。','Causal effects on natural recall, final-answer accuracy, full LRE Wake, Emotion, personality continuity, subjective experience and biological brain reproduction were not measured.',lang),
        T('公開するのは匿名化した集計と問別の結果です。会話原文、証拠引用、質問、原文のID、特徴語、SQLite、私的な実行コード・詳細ログは非公開で保持します。','Only opaque aggregates and per-query outcomes are public. Original conversations, evidence quotes, queries, native source IDs, feature vocabulary, SQLite, private execution code and detailed logs remain private.',lang),
        T('公開JSONから集計を再計算できます。原文の照合やエンジンの再実行には、公開していない入力が必要です。','The public JSON permits aggregate recalculation. Source auditing and engine reruns require inputs that are not published.',lang),
    ]
    limits_html = '<div class="boundary-box"><ul>' + ''.join(f'<li>{x}</li>' for x in limits) + '</ul></div>'
    limits_html += f'<details><summary>{T("保持した研究記録の識別子","Retained study identifiers",lang)}</summary><div class="source-note"><p>Study manifest SHA-256: <code>{d["provenance"]["study_manifest_sha256"]}</code></p><p>Scored condition manifest SHA-256: <code>{d["provenance"]["scored_condition_manifest_sha256"]}</code></p><p>Report SHA-256: <code>{d["provenance"]["report_sha256"]}</code></p><p>{T("hashは記録の識別子です。科学的妥当性や公開再現性そのものを証明しません。","Hashes identify retained records; they do not themselves establish scientific validity or public reproducibility.",lang)}</p></div></details>'
    limits_html += f'<div class="download-links"><a href="../../{NEW_DATA_FILE}" download>{T("公開集計JSONを取得","Download public summary JSON",lang)}</a><a href="../../{ "results.html" if lang=="ja" else "results.en.html"}#studies">{T("過去の研究結果も見る","View earlier study records",lang)} →</a></div>'
    body += section('limits','09 / PUBLIC SCOPE AND LIMITS',T('結果の範囲を、記録と一緒に残す。','Retain the limits alongside the result.',lang),content=limits_html)
    return document(lang, True, T('SHIORI 別会話での再検証','SHIORI cross-session replication',lang), T('別の実会話4件・32問。対象取得7/16から5/16、紛らわしい候補6/8から0/8。技術的失敗と修正条件、限界、次の課題を記録。','Four further real conversations, 32 queries: positive hits fell from 7/16 to 5/16; confusable false returns fell from 6/8 to 0/8. Technical failure, amendment, limits and next steps.',lang), body, study_path=NEW_STUDY, record_date=d['date'])


if __name__ == '__main__':
    from build_retrieval_hypotheses import build as build_latest, load_summary
    from build_event_compatibility import build as build_event, load_summary as load_event_summary
    load_summary()
    load_event_summary()
    adoption_updates = ADOPTION_PUBLICATION.prepare_updates(ROOT, ADOPTION_D) if ADOPTION_D is not None else {}
    working_updates = WORKING_PUBLICATION.prepare_updates(ROOT, WORKING_D) if WORKING_D is not None else {}
    action_updates = ACTION_PUBLICATION.prepare_updates(ROOT, ACTION_D) if ACTION_D is not None else {}
    for lang, filename in [('ja','index.html'),('en','en.html')]:
        listing = 'results.html' if lang == 'ja' else 'results.en.html'
        (ROOT/listing).write_text(landing(lang)+'\n')
        (ROOT/STUDY/filename).write_text(study(lang)+'\n')
        (ROOT/NEW_STUDY).mkdir(parents=True, exist_ok=True)
        (ROOT/NEW_STUDY/filename).write_text(cross_session(lang)+'\n')
    build_latest()
    build_event()
    for relative, text in adoption_updates.items():
        destination = ROOT / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text, encoding='utf-8')
    for relative, text in working_updates.items():
        destination = ROOT / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text, encoding='utf-8')
    for relative, text in action_updates.items():
        destination = ROOT / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text, encoding='utf-8')
    print('Built 18 public pages from seven public summaries; README and sitemap updated.' if action_updates else 'Built 16 public pages from six public summaries; README and sitemap updated.' if working_updates else 'Built 14 public pages from five public summaries; README and sitemap updated.' if adoption_updates else 'Built 10 public pages from four public summaries.')

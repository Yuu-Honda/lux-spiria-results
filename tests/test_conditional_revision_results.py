"""Artificial engineering fixtures stay in memory/tmp, never study exports."""
import copy
import hashlib
from html.parser import HTMLParser
import importlib.util
import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result


mod = module('conditional_engineering', 'tools/build_conditional_revision.py')
pub = module('conditional_publication_engineering', 'tools/conditional_revision_publication.py')


def fixture():
    d = {'schema_version': 1, 'study_id': 'conditional-revision-2026-10-27', 'date': '2026-10-27',
         'sample': dict(mod.SAMPLE), 'items': [], 'review': {
             'change_types': ['conditional_update', 'confirmation', 'deferred'],
             'legacy_rule_preserved': [True, False, True], 'grounded': [True, True, False],
             'canonical_characters': 1000, 'sha256': 'a' * 64},
         'packets': {key: {'raw_sha256': 'b' * 64, 'canonical_characters': 100 + i}
                     for i, key in enumerate(mod.PACKETS)},
         'scope': {**{key: True for key in mod.SCOPE_TRUE}, **{key: False for key in mod.SCOPE_FALSE},
                   'provider_metadata': None},
         'provenance': {key: 'a' * 64 for key in mod.PROVENANCE},
         'replay': {key: 'c' * 64 for key in ('manifest_sha256', 'readme_sha256', 'zip_sha256')}}
    d['provenance'].update(code_sha256=mod.CODE_SHA256, protocol_sha256=mod.PROTOCOL_SHA256)
    for ci, condition in enumerate(mod.CONDITIONS):
        for i, task in enumerate(mod.LATER if condition in mod.ARMS else mod.OLD_IDS):
            if condition in mod.ARMS:
                source = mod.LATER[task]; origin, fmt = mod.CATALOG[source]
            else:
                source = origin = mod.OLD_IDS[task]
                fmt = 'legacy_root' if condition == 'legacy' else 'wrapped_v2'
            # Deliberately mixed synthetic outcomes, including every paired category.
            accepted = ((i % 4 in (0, 2)) if condition == mod.ARMS[0] else
                        (i % 4 in (0, 1)) if condition == mod.ARMS[1] else i % 2 == 0)
            status = 'execution_error' if not accepted and i % 2 else 'ok'
            scored = condition not in ('legacy', 'wrapped')
            prediction = ('accepted', 'rejected', 'uncertain')[i % 3]
            d['items'].append({'condition': condition, 'id': task, 'source': source,
                'origin_alias': origin, 'format': fmt, 'execution_status': status,
                'error': {'type': 'ActionError', 'sha256': 'e' * 64} if status == 'execution_error' else None,
                'validation_status': 'accepted' if accepted else 'rejected',
                'artifact_sha256': None if status == 'execution_error' else 'd' * 64,
                'prediction': prediction, 'prediction_scored': scored,
                'prediction_agreement': None if not scored or prediction == 'uncertain' else prediction == ('accepted' if accepted else 'rejected'),
                'canonical_characters': 100 + i, 'action_sha256': hashlib.sha256(('artificial-' + (task if condition in ('legacy', 'wrapped') else condition + task)).encode()).hexdigest(),
                'budget_exceeded': False})
    d.update(mod.recalculate(d['items']))
    return d


def temporary_inputs(root, d):
    for relative in mod.SOURCE_FILES:
        path = root / relative; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / relative).read_bytes())
    for relative, key, value in [(mod.REPLAY + 'README.md', 'readme_sha256', b'artificial replay instructions\n'),
                                  (mod.REPLAY + 'manifest.json', 'manifest_sha256', b'{"artificial":true}\n'),
                                  (mod.ZIP_FILE, 'zip_sha256', b'artificial engineering archive')]:
        path = root / relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(value)
        d['replay'][key] = hashlib.sha256(value).hexdigest()


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__(); self.ids = []; self.refs = []; self.lang = None; self.captions = 0
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs: self.ids.append(attrs['id'])
        if tag == 'html': self.lang = attrs.get('lang')
        if tag == 'caption': self.captions += 1
        self.refs.extend(attrs[key] for key in ('href', 'src') if attrs.get(key))


class ConditionalRevisionEngineering(unittest.TestCase):
    def setUp(self): self.d = fixture()

    def test_complete_artificial_contract_and_nontrivial_pairs(self):
        self.assertIs(mod.validate_summary(self.d), self.d)
        self.assertEqual(len(self.d['items']), 21)
        self.assertEqual(set(row['classification'] for row in self.d['paired']), set(mod.CLASSIFICATIONS))
        self.assertEqual(sum(row['items'] for row in self.d['counts'].values()), 21)

    def test_absence_is_identity_and_standalone_refuses_without_writes(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp); self.assertEqual(pub.prepare_updates(root), {})
            with patch.object(mod, 'ROOT', root), self.assertRaises(FileNotFoundError): mod.build()
            self.assertEqual(list(root.iterdir()), [])
        for fn, args in [(pub.integrate_home, ('same', 'ja', None)),
                         (pub.integrate_listing, ('same', 'en', None)),
                         (pub.integrate_readme, ('same', None)), (pub.integrate_sitemap, ('same', None))]:
            self.assertEqual(fn(*args), 'same')

    def test_recursive_unknown_keys_and_strings_fail_closed(self):
        dictionaries = []; strings = []
        def visit(node, path=()):
            if isinstance(node, dict):
                dictionaries.append(path)
                for key, child in node.items(): visit(child, path + (key,))
            elif isinstance(node, list):
                for i, child in enumerate(node): visit(child, path + (i,))
            elif isinstance(node, str): strings.append(path)
        visit(self.d)
        for paths, unknown in [(dictionaries, True), (strings, False)]:
            for path in paths:
                bad = copy.deepcopy(self.d); node = bad
                for key in (path if unknown else path[:-1]): node = node[key]
                if unknown: node['private_source'] = 'PRIVATE_SENTINEL'
                else: node[path[-1]] = 'PRIVATE_SENTINEL'
                with self.subTest(path=path, unknown=unknown), self.assertRaises(ValueError): mod.validate_summary(bad)

    def test_json_duplicates_nonfinite_and_bad_export_never_write(self):
        texts = ['{}', json.dumps(self.d).replace('"schema_version": 1', '"schema_version":1,"schema_version":1', 1)]
        for value in ('NaN', 'Infinity', '-Infinity'):
            texts.append(json.dumps(self.d).replace('"canonical_characters": 1000', '"canonical_characters":' + value, 1))
        for text in texts:
            with self.subTest(text=text[:20]), TemporaryDirectory() as tmp:
                root = Path(tmp); path = root / mod.DATA_FILE; path.parent.mkdir(); path.write_text(text)
                with patch.object(mod, 'ROOT', root), self.assertRaises(ValueError): mod.build()
                with self.assertRaises(ValueError): pub.prepare_updates(root)
                self.assertFalse((root / mod.STUDY).exists())
                self.assertEqual(path.read_text(), text)

    def test_all_item_identity_source_origin_and_format_bindings(self):
        for field, value in [('id', 'F99'), ('condition', 'private'), ('source', 'S06'), ('origin_alias', 'D03'), ('format', 'wrapped_v2')]:
            bad = copy.deepcopy(self.d); bad['items'][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): mod.validate_summary(bad)
        for edit in ('missing', 'duplicate'):
            bad = copy.deepcopy(self.d)
            if edit == 'missing': bad['items'].pop()
            else: bad['items'][-1] = copy.deepcopy(bad['items'][-2])
            with self.subTest(edit=edit), self.assertRaises(ValueError): mod.validate_summary(bad)

    def test_saved_actions_reused_and_old_predictions_are_unscored(self):
        for field, value in [('prediction_scored', True), ('prediction_agreement', True)]:
            bad = copy.deepcopy(self.d); bad['items'][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): mod.validate_summary(bad)
        for field, value in [('prediction', 'rejected'), ('canonical_characters', 102), ('action_sha256', 'f' * 64)]:
            bad = copy.deepcopy(self.d); bad['items'][3][field] = value
            with self.subTest(reuse=field), self.assertRaises(ValueError): mod.validate_summary(bad)
        bad = copy.deepcopy(self.d); bad['items'][-1]['prediction_agreement'] = 'true'
        with self.assertRaises(ValueError): mod.validate_summary(bad)

    def test_error_artifact_and_validation_branches_bind(self):
        failed = next(i for i, item in enumerate(self.d['items']) if item['execution_status'] == 'execution_error')
        for index, changes in [(failed, {'artifact_sha256': 'd' * 64}), (failed, {'validation_status': 'accepted'}),
                               (failed, {'error': None}), (0, {'error': {'type': 'ActionError', 'sha256': 'e' * 64}}),
                               (0, {'artifact_sha256': None}), (0, {'execution_status': 'unavailable'})]:
            bad = copy.deepcopy(self.d); bad['items'][index].update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError): mod.validate_summary(bad)
        for status in ('invalid_action', 'execution_error'):
            bad = copy.deepcopy(self.d); bad['items'][failed]['execution_status'] = status
            bad.update(mod.recalculate(bad['items'])); mod.validate_summary(bad)
        self.assertIn('ActionError', mod.render('en', self.d))

    def test_counts_and_paired_outcomes_must_recalculate(self):
        for condition in mod.CONDITIONS:
            for field in mod.COUNT_FIELDS:
                bad = copy.deepcopy(self.d); bad['counts'][condition][field] += 1
                with self.subTest(condition=condition, field=field), self.assertRaises(ValueError): mod.validate_summary(bad)
        for field, value in [('classification', 'regressed'), ('format', 'wrapped_v2'), ('id', 'F02')]:
            bad = copy.deepcopy(self.d); bad['paired'][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): mod.validate_summary(bad)

    def test_strict_integer_caps_do_not_change_semantic_outcomes(self):
        for value in (True, 1.0, float('nan'), float('inf'), -1, 0):
            bad = copy.deepcopy(self.d); bad['items'][0]['canonical_characters'] = value
            with self.subTest(value=value), self.assertRaises(ValueError): mod.validate_summary(bad)
        bad = copy.deepcopy(self.d); item = next(item for item in bad['items'] if item['condition'] == 'repair' and item['validation_status'] == 'accepted')
        item.update(canonical_characters=6001, budget_exceeded=True); bad['review']['canonical_characters'] = 6001
        bad.update(mod.recalculate(bad['items'])); mod.validate_summary(bad)
        self.assertEqual(bad['counts']['repair']['budget_exceeded'], 1)
        self.assertEqual(item['validation_status'], 'accepted')
        self.assertIn('6001/6000', mod.render('en', bad))
        bad['counts']['repair']['accepted'] = True
        with self.assertRaises(ValueError): mod.validate_summary(bad)

    def test_role_freeze_interface_and_provenance_boundaries(self):
        for field in mod.SCOPE_TRUE | mod.SCOPE_FALSE:
            bad = copy.deepcopy(self.d); bad['scope'][field] = not bad['scope'][field]
            with self.subTest(scope=field), self.assertRaises(ValueError): mod.validate_summary(bad)
        for field in ('code_sha256', 'protocol_sha256', 'review_sha256'):
            bad = copy.deepcopy(self.d); bad['provenance'][field] = 'f' * 64
            with self.subTest(provenance=field), self.assertRaises(ValueError): mod.validate_summary(bad)
        bad = copy.deepcopy(self.d); bad['scope']['provider_metadata'] = {}
        with self.assertRaises(ValueError): mod.validate_summary(bad)
        bad = copy.deepcopy(self.d); bad['packets']['repair_before']['canonical_characters'] = float('inf')
        with self.assertRaises(ValueError): mod.validate_summary(bad)
        bad = copy.deepcopy(self.d); bad['review']['grounded'][0] = 1
        with self.assertRaises(ValueError): mod.validate_summary(bad)

    def test_sources_manifest_readme_and_external_zip_verified_before_writes(self):
        for relative in (*mod.SOURCE_FILES, mod.REPLAY + 'manifest.json', mod.REPLAY + 'README.md', mod.ZIP_FILE):
            with self.subTest(relative=relative), TemporaryDirectory() as tmp:
                root = Path(tmp); temporary_inputs(root, self.d)
                (root / relative).write_bytes(b'changed')
                with self.assertRaises(ValueError): pub.prepare_updates(root, self.d)
                self.assertFalse((root / mod.STUDY).exists())
        with TemporaryDirectory() as tmp:
            root = Path(tmp); temporary_inputs(root, self.d); mod.require_public_inputs(root, self.d)
            self.assertNotIn((root / mod.REPLAY).resolve(), (root / mod.ZIP_FILE).resolve().parents)
            self.assertEqual({path.name for path in (root / mod.REPLAY).iterdir()}, {'README.md', 'manifest.json'})
            (root / mod.ZIP_FILE).unlink()
            with self.assertRaises(ValueError): mod.require_public_inputs(root, self.d)

    def test_render_bilingual_semantics_and_conditional_findings(self):
        self.assertNotIn('added review did not change', mod.finding(self.d, 'en'))
        self.assertNotIn('All three actual review entries are classified as confirmation', mod.finding(self.d, 'en'))
        for item in self.d['items']:
            if item['condition'] == mod.ARMS[1]:
                raw = next(row for row in self.d['items'] if row['condition'] == mod.ARMS[0] and row['id'] == item['id'])
                for key in ('execution_status', 'error', 'validation_status', 'artifact_sha256'):
                    item[key] = copy.deepcopy(raw[key])
                item['prediction_agreement'] = None if item['prediction'] == 'uncertain' else item['prediction'] == item['validation_status']
        self.d['review']['change_types'] = ['confirmation'] * 3
        self.d.update(mod.recalculate(self.d['items'])); mod.validate_summary(self.d)
        self.assertIn('added review did not change', mod.finding(self.d, 'en'))
        self.assertIn('conditional_update is zero', mod.finding(self.d, 'en'))
        for lang in ('ja', 'en'):
            html = mod.render(lang, self.d); page = Page(html)
            self.assertEqual(page.lang, lang); self.assertEqual(len(page.ids), len(set(page.ids)))
            self.assertGreaterEqual(page.captions, 9)
            for ref in ('../../assets/lux-symbol.png', '../../theme-dark.css', 'conditional-revision.css', '../../' + mod.ZIP_FILE, '../../' + mod.REPLAY + 'README.md'):
                self.assertIn(ref, page.refs)
            self.assertIn('All 21' if lang == 'en' else '全21', html)
            self.assertNotIn('PRIVATE_SENTINEL', html); self.assertNotIn('<script', html)
        for text in ('not scored as new-AI errors', 'Actors do not receive full current JSON', 'three contexts and four turns',
                     'freeze all 12 before feedback', 'not spontaneous conceptual learning', 'remain null', 'does not regenerate fresh AI decisions'):
            self.assertIn(text, mod.render('en', self.d))

    def test_latest_only_home_and_seven_listing_cards_preserved(self):
        for name, lang in [('index.html', 'ja'), ('index.en.html', 'en')]:
            before = (ROOT / name).read_text(); after = pub.integrate_home(before, lang, self.d)
            self.assertEqual(pub.LATEST.sub('', before), pub.LATEST.sub('', after))
            self.assertEqual(after.count('data-mechanism '), 4)
            self.assertEqual(pub.integrate_home(after, lang, self.d), after)
        for name, lang in [('results.html', 'ja'), ('results.en.html', 'en')]:
            before = pub.CARD.sub('', (ROOT / name).read_text())
            before = re.sub(r'<article class="study-card" data-study="experience-retention">.*?</article>', '', before, flags=re.S)
            cards = re.findall(r'<article class="study-card".*?</article>', before, re.S)
            self.assertEqual(len(cards), 7); after = pub.integrate_listing(before, lang, self.d)
            self.assertEqual(after.count('<article class="study-card"'), 8)
            for card in cards: self.assertIn(card, after)
            self.assertEqual(pub.integrate_listing(after, lang, self.d), after)

    def test_readme_history_sitemap_and_plan_are_side_effect_free(self):
        before = (ROOT / 'README.md').read_text(); after = pub.integrate_readme(before, self.d)
        for start, end in [('<!-- ACTION_FEEDBACK_STUDY_START -->', '<!-- ACTION_FEEDBACK_STUDY_END -->'),
                           ('<!-- WORKING_MEMORY_STUDY_START -->', '<!-- WORKING_MEMORY_STUDY_END -->'),
                           ('<!-- EVENT_ADOPTION_STUDY_START -->', '<!-- EVENT_ADOPTION_STUDY_END -->')]:
            self.assertIn(before.split(start)[1].split(end)[0], after)
        self.assertEqual(pub.integrate_readme(after, self.d), after)
        before = (ROOT / 'sitemap.xml').read_text(); after = pub.integrate_sitemap(before, self.d)
        self.assertEqual(pub.integrate_sitemap(after, self.d), after)
        for line in before.splitlines():
            if '<loc>' in line: self.assertIn(line, after)
        with TemporaryDirectory() as tmp:
            root = Path(tmp); temporary_inputs(root, self.d)
            for name in ('index.html', 'index.en.html', 'README.md', 'sitemap.xml'):
                (root / name).write_bytes((ROOT / name).read_bytes())
            snapshot = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}
            plan = pub.prepare_updates(root, self.d)
            self.assertEqual(set(plan), {mod.STUDY + 'index.html', mod.STUDY + 'en.html', 'index.html', 'index.en.html', 'README.md', 'sitemap.xml'})
            self.assertEqual(snapshot, {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()})

    def test_actual_audited_export_and_publication_when_supplied(self):
        if not (ROOT / mod.DATA_FILE).is_file(): self.skipTest('Actual audited export not supplied')
        d = mod.load_summary(); mod.require_public_inputs(ROOT, d)
        for name, expected in pub.prepare_updates(ROOT, d).items():
            if (ROOT / 'data/experience-retention-2026-10-28.json').is_file() and not name.startswith(mod.STUDY):
                continue  # The ninth study owns current latest metadata.
            self.assertEqual((ROOT / name).read_text(), expected, name)
        pages = module('conditional_actual_main', 'tools/build_pages.py')
        for name, lang in [('results.html', 'ja'), ('results.en.html', 'en')]:
            self.assertEqual((ROOT / name).read_text(), pages.landing(lang) + '\n')


if __name__ == '__main__': unittest.main()

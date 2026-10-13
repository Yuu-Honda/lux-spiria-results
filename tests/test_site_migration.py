"""Check migrated route closure, original animations and immutable data."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
import hashlib,json,unittest
ROOT=Path(__file__).resolve().parents[1]
BASE='https://yuu-honda.github.io/lux-spiria-results/'
class Page(HTMLParser):
 def __init__(self,p):
  super().__init__();self.ids=[];self.refs=[];self.canonical=None;self.feed(p.read_text())
 def handle_starttag(self,t,attrs):
  a=dict(attrs)
  if 'id' in a:self.ids.append(a['id'])
  for k in ('href','src'):
   if a.get(k):self.refs.append(a[k])
  if t=='link' and a.get('rel')=='canonical':self.canonical=a['href']
class Migration(unittest.TestCase):
 def test_all_public_site_files_migrated(self):
  m=json.loads((ROOT/'site-migration.json').read_text())
  self.assertEqual(m['source_commit'],'d3718887c4ffc18ea655d2b5ce030ba4ad791d2b')
  for f in m['files']:
   p=ROOT/f['path'];self.assertTrue(p.is_file(),f['path'])
   if p.suffix in {'.css','.js','.png','.jpeg','.jpg','.pdf'} or f['path'].startswith(('assets/','history/')):
    self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),f['source_sha256'],f['path'])
 def test_current_pages_language_and_local_links(self):
  for name in ['index.html','index.en.html','continuation.html','continuation.en.html','results.html','results.en.html']:
   p=ROOT/name;page=Page(p)
   self.assertEqual(len(page.ids),len(set(page.ids)))
   self.assertTrue(page.canonical.startswith(BASE),name)
   for ref in page.refs:
    u=urlsplit(ref)
    if u.scheme or u.netloc:
     self.assertFalse(ref.startswith('https://yuu-honda.github.io/lux-spiria/'),ref)
     continue
    dest=(p.parent/unquote(u.path)).resolve() if u.path else p
    if dest.is_dir():dest=dest/'index.html'
    self.assertTrue(dest.is_file(),(name,ref))
    if u.fragment and dest.suffix=='.html':self.assertIn(u.fragment,Page(dest).ids,(name,ref))
 def test_same_site_results_links_and_pwa(self):
  for name,lang,home,results in [('index.html','ja','./','results.html'),('index.en.html','en','index.en.html','results.en.html')]:
   text=(ROOT/name).read_text();self.assertIn('href="'+results+'">Results</a>',text)
   self.assertEqual(text.count('data-mechanism '),4)
   manifest=json.loads((ROOT/('site.webmanifest' if lang=='ja' else 'site.en.webmanifest')).read_text())
   self.assertEqual(manifest['start_url'].removeprefix('./'),home.removeprefix('./'))
 def test_existing_english_results_url(self):
  s=(ROOT/'en.html').read_text();self.assertIn("'results.en.html'+location.search+location.hash",s)
if __name__=='__main__':unittest.main()

/* Run the real walkthrough script against a minimal layout-aware DOM.
 * This checks scroll/resize behavior; browser QA checks actual CSS geometry.
 * Usage: node tests/test_scroll_runtime.js
 */
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '..', 'mechanism.js'), 'utf8');

class Element {
  constructor() {
    this.dataset = {};
    this.style = {setProperty(name, value) { this[name] = value; }};
    this.attributes = new Map();
    this.selectors = new Map();
    this.listeners = new Map();
    this.hidden = false;
  }
  querySelector(selector) { return this.selectors.get(selector) || null; }
  querySelectorAll(selector) { return this.selectors.get(selector) || []; }
  setAttribute(name, value) { this.attributes.set(name, value); }
  removeAttribute(name) { this.attributes.delete(name); }
  addEventListener(name, callback) { this.listeners.set(name, callback); }
}

function harness(lang) {
  const listeners = new Map();
  const frames = [];
  let frameId = 0;
  let programmaticScrolls = 0;
  const window = {
    innerHeight: 900, scrollY: 0,
    matchMedia: () => ({matches: false}),
    addEventListener(name, callback) {
      if (!listeners.has(name)) listeners.set(name, []);
      listeners.get(name).push(callback);
    },
    scrollTo() { programmaticScrolls++; }
  };
  const stories = [
    ['overview', 5, 620, 480], ['shiori', 5, 640, 500],
    ['lre', 5, 600, 460], ['emotion', 6, 660, 520]
  ].map(([system, count, normalHeight, compactHeight], index) => {
    const root = new Element();
    const track = new Element();
    const scenes = Array.from({length: count}, () => new Element());
    const nodes = Array.from({length: count}, () => new Element());
    const links = Array.from({length: count - 1}, () => new Element());
    const measured = [];
    const documentTop = 1000 + index * 12000;
    root.dataset.system = system;
    root.closest = selector => selector === '[data-scroll-story]' ? track : null;
    root.selectors.set('[data-node]', nodes);
    root.selectors.set('[data-link]', links);
    root.selectors.set('[data-mechanism-scene]', scenes);
    for (const selector of ['[data-scroll-previous]', '[data-scroll-next]',
      '[data-motion-status]', '[data-motion-progress]', '[data-motion-count]',
      '[data-motion-announcement]']) root.selectors.set(selector, new Element());
    track.getBoundingClientRect = () => ({top: documentTop - window.scrollY});
    root.getBoundingClientRect = () => {
      const visible = scenes.flatMap((scene, i) => scene.hidden ? [] : [i]);
      assert.equal(visible.length, 1, `${lang}/${system}: measure one scene at a time`);
      const compact = root.dataset.compact === 'true';
      measured.push(compact);
      // Different scene heights expose measuring only the current scene.
      const height = (compact ? compactHeight : normalHeight) + visible[0] * 5;
      return {top: documentTop - window.scrollY, height};
    };
    scenes.forEach((scene, i) => {
      scene.selectors.set('h4', {textContent: `${system} step ${i + 1}`});
      scene.getBoundingClientRect = () => ({
        top: documentTop + i * normalHeight - window.scrollY, height: normalHeight
      });
      scene.scrollIntoView = () => { programmaticScrolls++; };
    });
    return {root, track, scenes, nodes, links, measured, documentTop,
      normalHeight: normalHeight + (count - 1) * 5,
      compactHeight: compactHeight + (count - 1) * 5};
  });
  const document = {
    documentElement: {lang},
    querySelectorAll: selector => selector === '[data-mechanism]' ? stories.map(s => s.root) : [],
    getElementById: () => null
  };
  vm.runInNewContext(source, {
    document, window, location: {hash: ''},
    requestAnimationFrame(callback) { frames.push(callback); return ++frameId; }
  }, {filename: 'mechanism.js'});
  function emit(name) { for (const callback of listeners.get(name) || []) callback(); }
  function flush() {
    assert.ok(frames.length <= 1, 'events coalesce into one animation frame');
    while (frames.length) frames.shift()();
  }
  function assertOneScene() {
    for (const story of stories) {
      const {root, scenes, nodes} = story;
      const step = Number(root.dataset.step);
      assert.equal(scenes.filter(scene => !scene.hidden).length, 1, `${lang}/${root.dataset.system}: no static list`);
      assert.equal(scenes[step].hidden, false);
      assert.equal(nodes[step].attributes.get('aria-current'), 'step');
    }
  }
  function scroll(story, fraction, step) {
    const height = parseFloat(story.root.style.minHeight);
    const range = parseFloat(story.track.style['--story-height']) - height;
    const start = story.documentTop - parseFloat(story.track.style['--pin-top']);
    window.scrollY = start + range * fraction;
    emit('scroll');
    emit('scroll');
    flush();
    assert.equal(Number(story.root.dataset.step), step, `${lang}/${story.root.dataset.system}: scroll ${fraction}`);
    assertOneScene();
  }
  function walkthroughs() {
    for (const story of stories) {
      const last = story.scenes.length - 1;
      scroll(story, 0, 0);
      scroll(story, .5, Math.floor(story.scenes.length / 2));
      scroll(story, 1, last);
      assert.equal(story.root.querySelector('[data-motion-progress]').style.width, '100%');
      if (story.root.dataset.system === 'shiori') {
        assert.equal(story.root.style['--thread-travel'], '1', 'final SHIORI path is complete');
      }
      scroll(story, 0, 0);
    }
  }
  function assertLayout(compact) {
    for (const story of stories) {
      assert.equal(story.root.dataset.compact, String(compact));
      assert.equal(story.track.dataset.scrollEnabled, 'true');
      assert.equal(story.root.dataset.scrollMode, 'scroll');
      assert.equal(parseFloat(story.root.style.minHeight), compact ? story.compactHeight : story.normalHeight);
      if (compact) assert.ok(parseFloat(story.track.style['--pin-top']) < 0, 'tall card pins below its top');
    }
    assertOneScene();
  }
  assertLayout(false);
  walkthroughs();
  stories.forEach(story => { story.measured.length = 0; });
  window.innerHeight = 400;
  emit('resize');
  flush();
  assertLayout(true);
  for (const story of stories) {
    assert.deepEqual(story.measured, [
      ...Array(story.scenes.length).fill(false), ...Array(story.scenes.length).fill(true)
    ], 'short viewport retries every scene with compact layout');
  }
  walkthroughs();
  stories.forEach(story => { story.measured.length = 0; });
  window.innerHeight = 900;
  emit('resize');
  flush();
  assertLayout(false);
  for (const story of stories) assert.deepEqual(story.measured, Array(story.scenes.length).fill(false));
  walkthroughs();
  assert.equal(programmaticScrolls, 0, 'all steps advance through scroll events, without buttons');
}

for (const lang of ['ja', 'en']) harness(lang);
console.log('Scroll runtime: 4 stories × JA/EN × normal/short/restored viewport passed.');

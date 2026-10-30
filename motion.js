/* Decorative motion layer for the home page (ambient memory network, reveals,
 * pointer light). It never changes text or data: count-ups end on the exact
 * original text, and reduced-motion users get the static page. */
(() => {
  'use strict';
  const root = document.documentElement;
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)');
  const finePointer = window.matchMedia('(hover: hover) and (pointer: fine)');
  const english = root.lang === 'en';
  root.classList.add('fx');

  const make = (tag, className, parent) => {
    const el = document.createElement(tag);
    if (className) el.className = className;
    el.setAttribute('aria-hidden', 'true');
    if (parent) parent.appendChild(el);
    return el;
  };

  // ---------- Ambient layers ----------
  make('div', 'fx-aurora', document.body);
  const canvas = make('canvas', 'fx-sky', document.body);
  const cursor = make('div', 'fx-cursor', document.body);
  const progress = make('div', 'fx-progress', document.body);

  // ---------- Pause: follow the hero's existing motion toggle ----------
  let paused = false;
  const toggle = document.getElementById('neural-motion-toggle');
  const syncPause = () => {
    paused = Boolean(toggle && toggle.getAttribute('aria-pressed') === 'true');
    root.classList.toggle('fx-paused', paused);
  };
  if (toggle) new MutationObserver(syncPause).observe(toggle, {attributes: true, attributeFilter: ['aria-pressed']});
  syncPause();

  // ---------- Memory-network canvas ----------
  const ctx = canvas.getContext('2d');
  const COLORS = [[136, 215, 255], [182, 161, 219], [242, 228, 201]];
  let w = 0, h = 0, dpr = 1, nodes = [], pulses = [];
  const mouse = {x: -9999, y: -9999};

  function resize() {
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    w = window.innerWidth; h = window.innerHeight;
    canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const count = Math.min(130, Math.round((w * h) / 13000));
    nodes = Array.from({length: count}, (_, i) => ({
      x: Math.random() * w, y: Math.random() * h * 1.6,
      vx: (Math.random() - .5) * .22, vy: (Math.random() - .5) * .22,
      r: Math.random() * 1.6 + .5, z: Math.random() * .7 + .3,
      c: COLORS[i % 7 === 0 ? 2 : i % 2], t: Math.random() * Math.PI * 2,
    }));
    pulses = [];
  }

  const LINK = 130;
  function frame(time) {
    ctx.clearRect(0, 0, w, h);
    const sy = window.scrollY;
    const pos = nodes.map(n => {
      if (!paused && !reduce.matches) {
        n.x += n.vx; n.y += n.vy; n.t += .02;
        if (n.x < -20) n.x = w + 20; if (n.x > w + 20) n.x = -20;
        if (n.y < -20) n.y = h * 1.6; if (n.y > h * 1.6) n.y = -20;
      }
      let y = (n.y - sy * n.z * .25) % (h * 1.6);
      if (y < 0) y += h * 1.6;
      return {n, x: n.x, y: y - h * .3};
    });
    for (let i = 0; i < pos.length; i++) {
      const a = pos[i];
      for (let j = i + 1; j < pos.length; j++) {
        const b = pos[j];
        const dx = a.x - b.x, dy = a.y - b.y, d = dx * dx + dy * dy;
        if (d < LINK * LINK) {
          const alpha = (1 - Math.sqrt(d) / LINK) * .2 * Math.min(a.n.z, b.n.z) * 1.6;
          ctx.strokeStyle = `rgba(${a.n.c.join(',')},${alpha})`;
          ctx.lineWidth = .7;
          ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
          if (!paused && !reduce.matches && pulses.length < 14 && Math.random() < .00035) pulses.push({a: a.n, b: b.n, p: 0});
        }
      }
      const mdx = a.x - mouse.x, mdy = a.y - mouse.y, md = Math.sqrt(mdx * mdx + mdy * mdy);
      if (md < 190) {
        ctx.strokeStyle = `rgba(242,228,201,${(1 - md / 190) * .35})`;
        ctx.lineWidth = .8;
        ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(mouse.x, mouse.y); ctx.stroke();
      }
      const glow = .45 + Math.sin(a.n.t) * .25 + (md < 190 ? .4 : 0);
      ctx.fillStyle = `rgba(${a.n.c.join(',')},${glow * a.n.z})`;
      ctx.beginPath(); ctx.arc(a.x, a.y, a.n.r * (md < 190 ? 1.8 : 1), 0, Math.PI * 2); ctx.fill();
    }
    // recall signals travelling along links
    const byNode = new Map(pos.map(p => [p.n, p]));
    pulses = pulses.filter(s => {
      s.p += .012;
      const a = byNode.get(s.a), b = byNode.get(s.b);
      if (!a || !b || s.p >= 1) return false;
      const x = a.x + (b.x - a.x) * s.p, y = a.y + (b.y - a.y) * s.p;
      const g = ctx.createRadialGradient(x, y, 0, x, y, 10);
      g.addColorStop(0, 'rgba(255,248,230,.95)'); g.addColorStop(1, 'rgba(136,215,255,0)');
      ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, y, 10, 0, Math.PI * 2); ctx.fill();
      return true;
    });
    if (!reduce.matches && !document.hidden) raf = requestAnimationFrame(frame);
    else raf = 0;
  }
  let raf = 0;
  const start = () => { if (!raf) raf = requestAnimationFrame(frame); };
  resize();
  if (reduce.matches) frame(0); else start();
  let resizeTimer;
  window.addEventListener('resize', () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(() => { resize(); if (reduce.matches) frame(0); }, 150); });
  document.addEventListener('visibilitychange', () => { if (!document.hidden && !reduce.matches) start(); });
  reduce.addEventListener('change', () => { if (!reduce.matches) start(); else frame(0); });

  // ---------- Pointer: cursor light, hero tilt ----------
  const visual = document.querySelector('.neural-visual');
  window.addEventListener('pointermove', e => {
    if (e.pointerType !== 'mouse') return;
    mouse.x = e.clientX; mouse.y = e.clientY;
    document.body.classList.add('fx-has-pointer');
    cursor.style.transform = `translate3d(${e.clientX}px, ${e.clientY}px, 0)`;
    if (visual && !reduce.matches) {
      const r = visual.getBoundingClientRect();
      const px = (e.clientX - (r.left + r.width / 2)) / window.innerWidth;
      const py = (e.clientY - (r.top + r.height / 2)) / window.innerHeight;
      visual.style.setProperty('--fx-ry', `${(px * 10).toFixed(2)}deg`);
      visual.style.setProperty('--fx-rx', `${(-py * 8).toFixed(2)}deg`);
    }
  }, {passive: true});
  document.addEventListener('pointerleave', () => { mouse.x = mouse.y = -9999; document.body.classList.remove('fx-has-pointer'); });

  // ---------- Hero headline: per-character rise ----------
  const h1 = document.querySelector('.hero h1');
  if (h1 && !reduce.matches) {
    let i = 0;
    const split = node => {
      [...node.childNodes].forEach(child => {
        if (child.nodeType === Node.TEXT_NODE) {
          // Words stay unbreakable (English); whitespace stays a real text node.
          const frag = document.createDocumentFragment();
          child.textContent.split(/(\s+)/).forEach(part => {
            if (!part) return;
            if (/^\s+$/.test(part)) { frag.appendChild(document.createTextNode(part)); return; }
            const word = document.createElement('span');
            word.className = 'fx-word';
            for (const ch of part) {
              const span = document.createElement('span');
              span.className = 'fx-char'; span.textContent = ch; span.style.setProperty('--i', i++);
              word.appendChild(span);
            }
            frag.appendChild(word);
          });
          child.replaceWith(frag);
        } else if (child.nodeType === Node.ELEMENT_NODE && child.classList.contains('serif-emphasis')) {
          child.classList.add('fx-char'); child.style.setProperty('--i', i); i += 3;
        } else if (child.nodeType === Node.ELEMENT_NODE && child.tagName !== 'BR') {
          split(child);
        }
      });
    };
    h1.setAttribute('aria-label', h1.textContent.replace(/\s+/g, ' ').trim());
    split(h1);
  }

  // ---------- Keyword bands after the question line ----------
  const question = document.querySelector('.question-line');
  if (question) {
    const bands = english
      ? [['MEMORY', 'EMOTION', 'IDENTITY', 'CHANGE', 'RECALL', 'CONTINUITY'], ['TRACE MEMORY', 'CONNECT CHANGE', 'RETURN TO THE SOURCE', 'COMPARE THEN AND NOW']]
      : [['記憶', '感情', '人格', '変化', '想起', '連続性'], ['MEMORY', 'EMOTION', 'IDENTITY', 'CHANGE', 'RECALL', 'CONTINUITY']];
    let after = question;
    bands.forEach((words, index) => {
      const band = make('div', 'fx-marquee');
      if (index) band.dataset.dir = 'rev';
      const track = make('div', 'fx-marquee-track', band);
      for (let k = 0; k < 4; k++) words.forEach(word => { const s = document.createElement('span'); s.textContent = word; track.appendChild(s); });
      after.after(band); after = band;
    });
  }

  // ---------- Section ghost numerals ----------
  const ghosts = [];
  document.querySelectorAll('.section-top').forEach(top => {
    const eyebrow = top.querySelector('.eyebrow');
    const m = eyebrow && eyebrow.textContent.match(/^\s*(\d{2})\s*\//);
    if (!m) return;
    const ghost = make('span', 'fx-ghost', top);
    ghost.textContent = m[1]; ghost.dataset.n = m[1];
    ghosts.push(ghost);
  });

  // ---------- Scroll reveals ----------
  const revealSelectors = [
    '.latest-study', '.question-line',
    '.section-top', '.emotion-layer-card', '.evidence-stat', '.evidence-rows > div',
    '.release-list > a', '.origins h2', '.origins blockquote', '.origins li', '.origins p',
    '.footer > *',
  ];
  const revealables = [];
  revealSelectors.forEach(sel => document.querySelectorAll(sel).forEach((el, idx) => {
    if (el.closest('[data-mechanism]') || el.hasAttribute('data-fx-reveal')) return;
    el.setAttribute('data-fx-reveal', '');
    el.style.setProperty('--fx-d', `${Math.min(idx % 6, 5) * 70}ms`);
    revealables.push(el);
  }));
  if ('IntersectionObserver' in window && !reduce.matches) {
    const io = new IntersectionObserver(entries => entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add('fx-in');
      io.unobserve(entry.target);
      entry.target.querySelectorAll('[data-fx-count]').forEach(countUp);
      if (entry.target.matches('[data-fx-count]')) countUp(entry.target);
    }), {rootMargin: '0px 0px -8% 0px', threshold: .08});
    revealables.forEach(el => io.observe(el));
  } else {
    revealables.forEach(el => el.classList.add('fx-in'));
  }

  // ---------- Count-up (ends on the exact original text) ----------
  function countUp(el) {
    if (el.dataset.fxCounted) return;
    el.dataset.fxCounted = '1';
    const original = el.textContent;
    const target = parseInt(original, 10);
    if (!Number.isFinite(target) || reduce.matches) return;
    const t0 = performance.now(), dur = 1400;
    const step = now => {
      const k = Math.min(1, (now - t0) / dur), eased = 1 - Math.pow(1 - k, 3);
      el.textContent = k < 1 ? String(Math.round(target * eased)) : original;
      if (k < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }
  const countTargets = [
    ...document.querySelectorAll('.evidence-stat strong'),
    ...[...document.querySelectorAll('.latest-study-metric dd > span:not(.latest-study-arrow)')].map(span => span.firstChild).filter(n => n && n.nodeType === Node.TEXT_NODE && /^\d+$/.test(n.textContent.trim())).map(n => {
      const wrap = document.createElement('span'); wrap.textContent = n.textContent; n.replaceWith(wrap); return wrap;
    }),
  ];
  countTargets.forEach(el => { el.classList.add('fx-count'); el.setAttribute('data-fx-count', ''); });

  // ---------- Pointer spotlight + magnetic links ----------
  if (finePointer.matches) {
    document.querySelectorAll('.latest-study, .emotion-layer-card, .evidence-stat, .release-list > a, .mechanism-overview, .mechanism-card').forEach(host => {
      host.classList.add('fx-spot-host');
      make('span', 'fx-spot', host);
      host.addEventListener('pointermove', e => {
        const r = host.getBoundingClientRect();
        host.style.setProperty('--fx-mx', `${e.clientX - r.left}px`);
        host.style.setProperty('--fx-my', `${e.clientY - r.top}px`);
      }, {passive: true});
    });
    document.querySelectorAll('.text-link, .latest-study-link').forEach(link => {
      link.addEventListener('pointermove', e => {
        if (reduce.matches) return;
        const r = link.getBoundingClientRect();
        link.style.setProperty('--fx-tx', `${((e.clientX - r.left) / r.width - .5) * 10}px`);
        link.style.setProperty('--fx-ty', `${((e.clientY - r.top) / r.height - .5) * 8}px`);
      });
      link.addEventListener('pointerleave', () => { link.style.removeProperty('--fx-tx'); link.style.removeProperty('--fx-ty'); });
    });
  }

  // ---------- Scroll-linked: progress bar, ghost numerals ----------
  let ticking = false;
  const onScroll = () => {
    ticking = false;
    const max = document.documentElement.scrollHeight - window.innerHeight;
    progress.style.setProperty('--fx-p', max > 0 ? (window.scrollY / max).toFixed(4) : 0);
    if (reduce.matches) return;
    const vh = window.innerHeight;
    ghosts.forEach(g => {
      const r = g.parentElement.getBoundingClientRect();
      const k = Math.max(0, Math.min(1, 1 - r.top / vh));
      g.style.setProperty('--fx-shift', `${(0.5 - k) * 60}px`);
      g.style.setProperty('--fx-fill', k.toFixed(3));
    });
  };
  window.addEventListener('scroll', () => { if (!ticking) { ticking = true; requestAnimationFrame(onScroll); } }, {passive: true});
  onScroll();
})();

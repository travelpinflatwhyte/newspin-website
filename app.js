(function () {
  'use strict';

  // ---- storage (kept in this browser only) ----
  function load(key, fallback) {
    try { var v = localStorage.getItem(key); return v ? JSON.parse(v) : fallback; } catch (e) { return fallback; }
  }
  function save(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch (e) { /* storage blocked: features degrade quietly */ }
  }
  function localDay(dt) { // the reader's own calendar date, not UTC
    return dt.getFullYear() + '-' + ('0' + (dt.getMonth() + 1)).slice(-2) + '-' + ('0' + dt.getDate()).slice(-2);
  }
  var today = localDay(new Date());
  // "Today" on the home strip is India's date; say so for readers whose date differs
  document.querySelectorAll('[data-ist-day]').forEach(function (el) {
    if (el.getAttribute('data-ist-day') !== today) el.textContent = 'Today in India';
  });
  if (/[?&]tl=a\b/.test(location.search)) document.body.classList.remove('tl-b'); // old phone layout, for comparison
  var follows = load('np_follow', {});   // slug -> date followed
  var seen = load('np_seen', {});        // slug -> date last opened
  var homeSeen = load('np_home', null);  // date of last home visit

  function fmt(d) {
    var dt = new Date(d + 'T00:00:00');
    return dt.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
  }

  var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  function copied(btn) {
    if (btn.classList.contains('copied')) return;
    var tick = document.createElement('span'); tick.className = 'tick'; tick.setAttribute('aria-hidden', 'true'); tick.textContent = '✓';
    btn.classList.add('copied'); btn.insertBefore(tick, btn.firstChild);
    setTimeout(function () { btn.classList.remove('copied'); if (tick.parentNode) tick.parentNode.removeChild(tick); }, 1600);
  }

  // ---- toast ----
  var toast = document.getElementById('toast');
  var toastTimer;
  function say(msg) {
    if (!toast) return;
    toast.textContent = msg; toast.hidden = false;
    clearTimeout(toastTimer); toastTimer = setTimeout(function () { toast.hidden = true; }, 2200);
  }

  // ---- follow buttons ----
  function paintFollow(btn) {
    var slug = btn.getAttribute('data-follow');
    var on = !!follows[slug];
    btn.setAttribute('aria-pressed', on ? 'true' : 'false');
    var label = btn.querySelector('.label');
    if (label) label.textContent = on ? (btn.getAttribute('data-on') || 'Following') : (btn.getAttribute('data-off') || 'Follow');
  }
  document.querySelectorAll('[data-follow]').forEach(function (btn) {
    paintFollow(btn);
    btn.addEventListener('click', function () {
      var slug = btn.getAttribute('data-follow');
      if (follows[slug]) { delete follows[slug]; say('Unfollowed'); }
      else { follows[slug] = today; if (!seen[slug]) seen[slug] = today; save('np_seen', seen); say('Following. You’ll see a green ring when it moves.'); btn.classList.remove('swing'); void btn.offsetWidth; btn.classList.add('swing'); }
      save('np_follow', follows);
      document.querySelectorAll('[data-follow="' + slug + '"]').forEach(paintFollow);
    });
  });

  // ---- share ----
  document.querySelectorAll('[data-share]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var url = btn.getAttribute('data-share') || location.href;
      var title = document.title;
      if (navigator.share) { navigator.share({ title: title, url: url }).catch(function () {}); return; }
      if (navigator.clipboard) { navigator.clipboard.writeText(url).then(function () { say('Link copied'); copied(btn); }, function () { say(url); }); }
      else { say(url); }
    });
  });

  // ---- home: ranking, sorting and filters ----
  // Mirrors rank() in build.py so the order stays right between rebuilds.
  var QUIET_DAYS = 60;
  function daysBetween(a, b) { return Math.round((new Date(b + 'T00:00:00') - new Date(a + 'T00:00:00')) / 86400000); }
  function rank(card) {
    var latest = card.getAttribute('data-latest');
    var next = card.getAttribute('data-next');
    var imp = +card.getAttribute('data-imp') || 3;
    var added = (card.getAttribute('data-added') || '').split(' ').filter(Boolean);
    var days = daysBetween(latest, today);
    var fresh = Math.max(0, 10 - days * 0.5);
    var up = 0, until = null;
    if (next && next >= today) {
      until = daysBetween(today, next);
      up = until <= 7 ? 6 - until * 0.5 : (until <= 21 ? 2 : 0);
    }
    var recent = Math.min(4, added.filter(function (x) { var g = daysBetween(x, today); return g >= 0 && g <= 14; }).length);
    return {
      score: fresh + up + imp * 2 + recent,
      quiet: days > QUIET_DAYS && !(until !== null && until <= 30),
      latest: latest, next: (next && next >= today) ? next : '', imp: imp
    };
  }
  var liveBox = document.getElementById('cards-live');
  var quietBox = document.getElementById('cards-quiet');
  var sortSel = document.getElementById('sort');
  var chips = document.querySelectorAll('[data-filter]');
  var regionBtns = document.querySelectorAll('[data-region]');
  var filt = { cat: 'All', region: 'All' };
  var allCards = Array.prototype.slice.call(document.querySelectorAll('.card[data-slug]'));

  function arrange() {
    if (!liveBox) return;
    var mode = sortSel ? sortSel.value : 'moving';
    var info = allCards.map(function (c) { return { el: c, r: rank(c) }; });
    var cmp = {
      moving: function (a, b) { return b.r.score - a.r.score; },
      latest: function (a, b) { return a.r.latest < b.r.latest ? 1 : a.r.latest > b.r.latest ? -1 : b.r.score - a.r.score; },
      upcoming: function (a, b) {
        if (a.r.next && b.r.next) return a.r.next < b.r.next ? -1 : a.r.next > b.r.next ? 1 : 0;
        if (a.r.next) return -1; if (b.r.next) return 1;
        return b.r.score - a.r.score;
      },
      biggest: function (a, b) { return (b.r.imp - a.r.imp) || (b.r.score - a.r.score); }
    }[mode];
    info.sort(cmp);
    var quietCount = 0;
    info.forEach(function (x) {
      var st = x.el.querySelector('.status');
      if (st && !st.hasAttribute('data-orig')) { st.setAttribute('data-orig', st.textContent); st.setAttribute('data-tone', st.className); }
      if (x.r.quiet && quietBox) {
        quietBox.appendChild(x.el); quietCount++;
        if (st) { st.textContent = 'No update in ' + daysBetween(x.r.latest, today) + ' days'; st.className = 'status tone-quiet'; }
      } else {
        liveBox.appendChild(x.el);
        if (st) { st.textContent = st.getAttribute('data-orig'); st.className = st.getAttribute('data-tone'); }
      }
    });
    var quietSec = document.getElementById('quiet');
    if (quietSec) quietSec.hidden = quietCount === 0;
    applyFilters();
  }

  function applyFilters() {
    var shownLive = 0, shownQuiet = 0, featured = 0;
    allCards.forEach(function (card) { card.classList.remove('featured'); });
    [liveBox, quietBox].forEach(function (box) {
      if (!box) return;
      Array.prototype.forEach.call(box.children, function (card) {
        var okCat = filt.cat === 'All' || card.getAttribute('data-cat') === filt.cat;
        var regions = (card.getAttribute('data-regions') || '').split(' ');
        var okReg = filt.region === 'All' || regions.indexOf(filt.region) !== -1;
        card.hidden = !(okCat && okReg);
        if (card.hidden) return;
        if (box === liveBox) { shownLive++; if (featured < 2) { card.classList.add('featured'); featured++; } }
        else shownQuiet++;
      });
    });
    var none = document.getElementById('nomatch');
    if (none) none.hidden = shownLive + shownQuiet > 0;
    var quietSec = document.getElementById('quiet');
    if (quietSec && quietBox) quietSec.hidden = shownQuiet === 0;
  }

  chips.forEach(function (chip) {
    chip.addEventListener('click', function () {
      filt.cat = chip.getAttribute('data-filter');
      chips.forEach(function (c) { c.setAttribute('aria-pressed', c === chip ? 'true' : 'false'); });
      applyFilters();
    });
  });
  regionBtns.forEach(function (btn) {
    btn.addEventListener('click', function () {
      filt.region = btn.getAttribute('data-region');
      regionBtns.forEach(function (c) { c.setAttribute('aria-pressed', c === btn ? 'true' : 'false'); });
      applyFilters();
    });
  });
  if (sortSel) {
    sortSel.value = load('np_sort', 'moving');
    sortSel.addEventListener('change', function () { save('np_sort', sortSel.value); arrange(); });
  }
  arrange();

  // ---- home v3: day labels in the reader's own time zone; timeline groups fold on phones ----
  (function () {
    var y = (function () { var x = new Date(); x.setDate(x.getDate() - 1); return localDay(x); })();
    document.querySelectorAll('.lu-day[data-day]').forEach(function (li) {
      var day = li.getAttribute('data-day');
      var dt = new Date(day + 'T00:00:00');
      var base = dt.getDate() + ' ' + dt.toLocaleString('en-GB', { month: 'short' });
      var name = day === today ? 'Today' : day === y ? 'Yesterday' : dt.toLocaleString('en-GB', { weekday: 'long' });
      li.textContent = name + ' · ' + base;
    });
    var groups = document.querySelectorAll('.ix-group');
    if (!groups.length || !window.matchMedia) return;
    var mq = window.matchMedia('(max-width:640px)');
    function setGroups() { groups.forEach(function (g, i) { g.open = !mq.matches || i === 0; }); }
    setGroups();
    if (mq.addEventListener) mq.addEventListener('change', setGroups);
    groups.forEach(function (g) {
      g.querySelector('summary').addEventListener('click', function (ev) { if (!mq.matches) ev.preventDefault(); });
    });
  })();

  // ---- micro-interactions ----
  (function () {
    // bubbles: stagger the green ring drawing in
    document.querySelectorAll('.bubbles > li').forEach(function (li, i) { li.style.setProperty('--i', i); });

    // a single soft pulse on stories that changed since the reader last opened them
    if (!reduceMotion) {
      document.querySelectorAll('.card[data-slug]').forEach(function (c) {
        var slug = c.getAttribute('data-slug'), last = seen[slug];
        var added = (c.getAttribute('data-added') || '').split(' ').sort().pop();
        if (last && added > last) c.classList.add('pulse');
      });
      document.querySelectorAll('[data-ix]').forEach(function (a) {
        var slug = a.getAttribute('data-ix'), last = seen[slug];
        var s = (window.NP_STORIES || []).filter(function (x) { return x.slug === slug; })[0];
        if (last && s && s.latestAdded > last) a.classList.add('pulse');
      });
    }

    // Moving now on phones: position dots under the swipe row
    var row = document.querySelector('.cards.moving');
    if (row && row.children.length > 1) {
      var dots = document.createElement('div'); dots.className = 'mv-dots'; dots.setAttribute('aria-hidden', 'true');
      Array.prototype.forEach.call(row.children, function () { dots.appendChild(document.createElement('i')); });
      row.parentNode.insertBefore(dots, row.nextSibling);
      var paintDots = function () {
        var w = row.children[0].getBoundingClientRect().width || 1;
        var idx = Math.round(row.scrollLeft / (w + 12));
        if (row.scrollLeft + row.clientWidth >= row.scrollWidth - 4) idx = row.children.length - 1;
        Array.prototype.forEach.call(dots.children, function (d, i) { d.classList.toggle('on', i === idx); });
      };
      row.addEventListener('scroll', function () { requestAnimationFrame(paintDots); }, { passive: true });
      paintDots();
    }

    // story page: key numbers count up the first time they are seen
    var vals = document.querySelectorAll('.keynums .v');
    if (vals.length && !reduceMotion && 'IntersectionObserver' in window) {
      var run = function (el) {
        var orig = el.textContent;
        var m = orig.match(/^([^\d]*?)(\d[\d,]*(?:\.\d+)?)([^\d]*)$/);
        if (!m) return;
        var target = parseFloat(m[2].replace(/,/g, '')), dec = (m[2].split('.')[1] || '').length;
        if (!isFinite(target) || target === 0) return;
        var t0 = null, dur = 800;
        el.style.fontVariantNumeric = 'tabular-nums';
        var tick = function (ts) {
          if (!t0) t0 = ts;
          var k = Math.min(1, (ts - t0) / dur), ease = 1 - Math.pow(1 - k, 3);
          var v = (target * ease).toLocaleString('en-IN', { minimumFractionDigits: dec, maximumFractionDigits: dec });
          el.textContent = k < 1 ? m[1] + v + m[3] : orig;
          if (k < 1) requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
      };
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) { if (en.isIntersecting) { io.unobserve(en.target); run(en.target); } });
      }, { threshold: 0.6 });
      vals.forEach(function (v) { io.observe(v); });
    }

    // story page: reading progress line under the header
    var tl = document.querySelector('ol.events'), head = document.querySelector('.site-header');
    if (tl && head) {
      var bar = document.createElement('div'); bar.className = 'read-progress'; bar.setAttribute('aria-hidden', 'true');
      var fill = document.createElement('i'); bar.appendChild(fill); head.appendChild(bar);
      var paintBar = function () {
        var r = tl.getBoundingClientRect(), vh = window.innerHeight;
        var k = Math.max(0, Math.min(1, (vh - r.top) / (r.height + vh * 0.5)));
        fill.style.transform = 'scaleX(' + k.toFixed(3) + ')';
      };
      window.addEventListener('scroll', function () { requestAnimationFrame(paintBar); }, { passive: true });
      paintBar();
    }
  })();

  // ---- theme ----
  var themeBtn = document.getElementById('theme-btn');
  function paintTheme() {
    var dark = document.documentElement.getAttribute('data-theme') === 'dark';
    if (themeBtn) themeBtn.setAttribute('aria-label', dark ? 'Switch to light mode' : 'Switch to dark mode');
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute('content', dark ? '#0B0D12' : '#F7F7F4');
  }
  if (themeBtn) themeBtn.addEventListener('click', function () {
    var next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    themeBtn.classList.remove('spin'); void themeBtn.offsetWidth; themeBtn.classList.add('spin');
    try { localStorage.setItem('np_theme', next); } catch (e) {}
    paintTheme();
  });
  paintTheme();

  // ---- home: greeting + bubbles ----
  var seenAtLoad = JSON.parse(JSON.stringify(seen));
  var DATA = window.NP_STORIES || [];
  function addDays(d, n) { var x = new Date(d + 'T00:00:00'); x.setDate(x.getDate() + n); return localDay(x); }
  var threeAgo = addDays(today, -3);
  function isNew(s) { return s.latestAdded > (seenAtLoad[s.slug] || threeAgo); }
  var helloH = document.getElementById('hello-h');
  if (helloH) {
    var hr = new Date().getHours();
    helloH.textContent = hr < 12 ? 'Good morning' : hr < 17 ? 'Good afternoon' : 'Good evening';
    var sub = document.getElementById('hello-sub');
    var mine = DATA.filter(function (s) { return follows[s.slug]; });
    if (sub) {
      if (mine.length) {
        var moved = mine.filter(isNew).length;
        sub.textContent = moved ? moved + ' of your ' + mine.length + ' stories moved since your last visit.' : 'You’re caught up on your ' + mine.length + (mine.length === 1 ? ' story.' : ' stories.');
      } else {
        var n = DATA.filter(function (s) { return s.latestAdded >= threeAgo; }).length;
        sub.textContent = n + (n === 1 ? ' story' : ' stories') + ' moved in the last 3 days. Tap one to catch up.';
      }
    }
    // followed stories first among the bubbles
    var ul = document.querySelector('.bubbles');
    if (ul) {
      var lis = Array.prototype.slice.call(ul.children);
      lis.sort(function (x, y) {
        var fx = follows[x.querySelector('[data-sm-open]').getAttribute('data-sm-open')] ? 1 : 0;
        var fy = follows[y.querySelector('[data-sm-open]').getAttribute('data-sm-open')] ? 1 : 0;
        return fy - fx;
      }).forEach(function (li) { ul.appendChild(li); });
    }
    save('np_home', today);
  }
  function paintBubbles() {
    document.querySelectorAll('.bubble[data-sm-open]').forEach(function (b) {
      var s = byslug(b.getAttribute('data-sm-open'));
      var fresh = s && s.latestAdded > (seen[s.slug] || threeAgo);
      b.classList.toggle('new', !!fresh);
      var name = s ? s.short : '';
      b.setAttribute('aria-label', 'Catch up on ' + name + (fresh ? ', new updates' : ''));
    });
  }
  function byslug(slug) { for (var i = 0; i < DATA.length; i++) if (DATA[i].slug === slug) return DATA[i]; return null; }
  paintBubbles();

  // ---- story mode ("Catch me up") ----
  var sm, smStory, smSlides, smIdx, smOpener, smNarrate = false;
  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
  function buildSm() {
    sm = el('div', 'sm'); sm.hidden = true;
    sm.setAttribute('role', 'dialog'); sm.setAttribute('aria-modal', 'true'); sm.setAttribute('aria-label', 'Catch me up');
    sm.innerHTML = '<div class="sm-card"><div class="sm-bars"></div><div class="sm-top"><div class="sm-who"><span class="sm-av"></span><span><span class="sm-name"></span><span class="sm-pos"></span></span></div><span class="sm-tools"><button type="button" class="sm-listen" aria-pressed="false" aria-label="Read updates aloud" hidden>🔊</button><button type="button" class="sm-x" aria-label="Close">×</button></span></div>' +
      '<button type="button" class="sm-zone prev" aria-label="Previous"></button><button type="button" class="sm-zone next" aria-label="Next"></button>' +
      '<div class="sm-body" aria-live="polite"></div><div class="sm-foot"><p class="sm-hint">Tap the right side for next, left for back</p><div class="sm-actions"><a class="go"></a><a class="ghost"></a></div></div></div>';
    document.body.appendChild(sm);
    sm.querySelector('.sm-x').addEventListener('click', closeSm);
    var lb = sm.querySelector('.sm-listen');
    if (Audio.ok) {
      lb.hidden = false;
      lb.addEventListener('click', function () {
        smNarrate = !smNarrate; lb.setAttribute('aria-pressed', smNarrate ? 'true' : 'false');
        if (smNarrate) speakSlide(); else Audio.stop();
      });
    }
    sm.querySelector('.sm-zone.prev').addEventListener('click', function () { step(-1); });
    sm.querySelector('.sm-zone.next').addEventListener('click', function () { step(1); });
    sm.addEventListener('click', function (e) { if (e.target === sm) closeSm(); });
    document.addEventListener('keydown', function (e) {
      if (!sm || sm.hidden) return;
      if (e.key === 'Escape') closeSm();
      else if (e.key === 'ArrowRight') step(1);
      else if (e.key === 'ArrowLeft') step(-1);
      else if (e.key === 'Tab') { // keep focus inside
        var f = sm.querySelectorAll('button,a[href]'); var first = f[0], lastF = f[f.length - 1];
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); lastF.focus(); }
        else if (!e.shiftKey && document.activeElement === lastF) { e.preventDefault(); first.focus(); }
      }
    });
  }
  function openSm(slug, opener) {
    var s = byslug(slug); if (!s) return;
    if (!sm) buildSm();
    smStory = s; smOpener = opener || smOpener;
    var since = seenAtLoad[slug];
    var fresh = since ? s.events.filter(function (e) { return e.added > since; }) : [];
    smSlides = fresh.length ? fresh : s.events.slice(-3);
    smIdx = 0;
    seen[slug] = today; save('np_seen', seen); paintBubbles();
    sm.querySelector('.sm-card').style.setProperty('--sm-bg', s.bg);
    sm.querySelector('.sm-av').textContent = s.letter;
    sm.querySelector('.sm-name').textContent = s.short;
    var bars = sm.querySelector('.sm-bars'); bars.innerHTML = '';
    smSlides.forEach(function () { bars.appendChild(el('i')); });
    sm.hidden = false; document.documentElement.style.overflow = 'hidden';
    render();
    sm.querySelector('.sm-zone.next').focus();
  }
  function render() {
    var ev = smSlides[smIdx], s = smStory;
    Array.prototype.forEach.call(sm.querySelectorAll('.sm-bars i'), function (b, i) { b.className = i < smIdx ? 'done' : i === smIdx ? 'cur' : ''; });
    sm.querySelector('.sm-pos').textContent = 'Update ' + (smIdx + 1) + ' of ' + smSlides.length + (seenAtLoad[s.slug] && smSlides.length && smSlides[0].added > seenAtLoad[s.slug] ? ' · new since your visit' : ' · latest');
    var body = sm.querySelector('.sm-body'); body.innerHTML = '';
    body.appendChild(el('span', 'sm-pill', ev.label + ' · ' + (ev.forecast ? 'Expected' : ev.status)));
    body.appendChild(el('h2', null, ev.title));
    body.appendChild(el('p', null, ev.summary));
    if (ev.nums && ev.nums.length) {
      var nums = el('div', 'sm-nums');
      ev.nums.forEach(function (n) { var d = el('div'); d.appendChild(el('span', null, n.k || n.label)); d.appendChild(el('b', null, n.v || n.value)); nums.appendChild(d); });
      body.appendChild(nums);
    }
    var go = sm.querySelector('.sm-actions .go'), src = sm.querySelector('.sm-actions .ghost');
    go.href = s.url + '#e' + ev.i; go.textContent = 'Open full timeline';
    src.href = s.url + '#e' + ev.i; src.textContent = ev.sources + (ev.sources === 1 ? ' source' : ' sources');
    var lastOne = smIdx === smSlides.length - 1;
    var nxt = nextStory();
    sm.querySelector('.sm-zone.next').setAttribute('aria-label', lastOne ? (nxt ? 'Next story: ' + nxt.short : 'Close') : 'Next update');
    if (smNarrate) speakSlide();
    sm.querySelector('.sm-hint').textContent = lastOne ? (nxt ? 'Tap right for the next story: ' + nxt.short : 'That’s everything. Tap right to close.') : 'Tap the right side for next, left for back';
  }
  function nextStory() {
    var order = Array.prototype.map.call(document.querySelectorAll('.bubble[data-sm-open]'), function (b) { return b.getAttribute('data-sm-open'); });
    var i = order.indexOf(smStory.slug);
    return i > -1 && i < order.length - 1 ? byslug(order[i + 1]) : null;
  }
  function step(d) {
    if (d > 0 && smIdx === smSlides.length - 1) { var n = nextStory(); if (n) openSm(n.slug); else closeSm(); return; }
    smIdx = Math.max(0, Math.min(smSlides.length - 1, smIdx + d)); render();
  }
  function speakSlide() {
    var ev = smSlides[smIdx];
    Audio.play([{ label: smStory.short + ' · ' + ev.label, text: (smIdx === 0 ? smStory.short + '. ' : '') + ev.label + '. ' + ev.title + '. ' + ev.summary }],
      { title: smStory.short, onEnd: function () { if (sm && !sm.hidden && smNarrate) step(1); }, quiet: true });
  }
  function closeSm() {
    if (smNarrate) Audio.stop();
    sm.hidden = true; document.documentElement.style.overflow = '';
    if (smOpener && smOpener.focus) smOpener.focus();
  }
  document.querySelectorAll('[data-sm-open]').forEach(function (b) {
    b.addEventListener('click', function () { openSm(b.getAttribute('data-sm-open'), b); });
  });


  // ---- listen (uses the device's own text-to-speech; nothing is sent anywhere) ----
  var Audio = (function () {
    var synth = window.speechSynthesis;
    var ok = !!(synth && window.SpeechSynthesisUtterance);
    var queue = [], qi = 0, parts = [], pi = 0, playing = false, rate = 1, opts = {}, voice = null, bar, token = 0;
    try { rate = parseFloat(localStorage.getItem('np_rate')) || 1; } catch (e) {}
    function pickVoice() {
      var vs = synth.getVoices(); if (!vs.length) return;
      var pref = ['en-IN', 'en-GB', 'en-US', 'en'];
      for (var i = 0; i < pref.length && !voice; i++) {
        for (var j = 0; j < vs.length; j++) { if (vs[j].lang && vs[j].lang.replace('_', '-').indexOf(pref[i]) === 0) { voice = vs[j]; break; } }
      }
    }
    if (ok) { pickVoice(); if (synth.addEventListener) synth.addEventListener('voiceschanged', pickVoice); }
    function clean(t) {
      return String(t)
        .replace(/₹\s?([\d.,–-]+)\s*(lakh crore|lakh cr|crore|cr)\b/g, function (m, n, u) { return n + ' ' + (u.indexOf('lakh') === 0 ? 'lakh crore' : 'crore') + ' rupees'; })
        .replace(/₹\s?([\d.,]+)/g, '$1 rupees')
        .replace(/\s\/\s?litre/g, ' per litre').replace(/\bcr\b/g, 'crore').replace(/\bmbpd\b/g, 'million barrels a day')
        .replace(/\bbps\b/g, 'basis points').replace(/≈\s?/g, 'about ').replace(/−/g, 'minus ').replace(/\bvs\b/g, 'versus')
        .replace(/(\d)\s?–\s?(\d)/g, '$1 to $2').replace(/\s·\s/g, ', ').replace(/[▲▼]/g, '').replace(/\bIST\b/g, 'India time');
    }
    function split(t) {
      // break only at a full stop/question mark followed by a space, so 4.3% stays whole
      return clean(t).replace(/([.!?]["'’”)\]]*)\s+/g, '$1\u0001').split('\u0001').filter(function (x) { return x.trim(); });
    }
    function buildBar() {
      bar = document.createElement('div'); bar.className = 'np-player'; bar.hidden = true;
      bar.setAttribute('role', 'region'); bar.setAttribute('aria-label', 'Audio player');
      bar.innerHTML = '<span class="pl-wave" aria-hidden="true"><i></i><i></i><i></i><i></i></span><div class="pl-info"><span class="pl-kick">Listening</span><span class="pl-now" aria-live="polite"></span></div>' +
        '<div class="pl-ctrls"><button type="button" class="pl-pp" aria-label="Pause">❚❚</button><button type="button" class="pl-next" aria-label="Skip to next">⏭</button>' +
        '<button type="button" class="pl-rate" aria-label="Playback speed">1×</button><button type="button" class="pl-x" aria-label="Stop and close player">×</button></div>';
      document.body.appendChild(bar);
      bar.querySelector('.pl-pp').addEventListener('click', function () { playing ? pause() : resume(); });
      bar.querySelector('.pl-next').addEventListener('click', function () { if (opts.onEnd && queue.length === 1) { finishItem(); } else { qi++; pi = 0; speak(); } });
      bar.querySelector('.pl-rate').addEventListener('click', function () {
        rate = rate >= 1.5 ? 1 : rate === 1 ? 1.25 : 1.5;
        try { localStorage.setItem('np_rate', String(rate)); } catch (e) {}
        paint(); if (playing) { speak(); }
      });
      bar.querySelector('.pl-x').addEventListener('click', stop);
    }
    function paint() {
      if (!bar) buildBar();
      var it = queue[qi];
      bar.querySelector('.pl-now').textContent = it ? it.label : '';
      bar.querySelector('.pl-kick').textContent = opts.title ? opts.title : 'Listening';
      var pp = bar.querySelector('.pl-pp'); pp.textContent = playing ? '❚❚' : '▶'; pp.setAttribute('aria-label', playing ? 'Pause' : 'Play');
      bar.querySelector('.pl-rate').textContent = rate + '×';
      document.body.classList.toggle('has-player', !bar.hidden);
      bar.classList.toggle('playing', !!playing);
      document.querySelectorAll('.speaking').forEach(function (el) { el.classList.remove('speaking'); });
      if (it && it.el && playing) it.el.classList.add('speaking');
    }
    function finishItem() { var cb = opts.onEnd; queue = []; playing = false; paint(); if (cb) cb(); }
    function speak() {
      synth.cancel(); var my = ++token;
      if (qi >= queue.length) { if (opts.onEnd) { finishItem(); } else { stop(); } return; }
      var it = queue[qi]; if (!parts.length || pi === 0) parts = split(it.text);
      playing = true; paint();
      var u = new SpeechSynthesisUtterance(parts[pi]);
      if (voice) { u.voice = voice; u.lang = voice.lang; } else { u.lang = 'en-IN'; }
      u.rate = rate;
      u.onend = function () {
        if (my !== token || !playing) return;
        pi++; if (pi >= parts.length) { qi++; pi = 0; parts = []; }
        speak();
      };
      u.onerror = function () { if (my === token) { playing = false; paint(); } };
      synth.speak(u);
    }
    function pause() { playing = false; token++; synth.cancel(); paint(); }
    function resume() { if (!queue.length) return; speak(); }
    function stop() { token++; playing = false; queue = []; qi = 0; pi = 0; parts = []; if (ok) synth.cancel(); if (bar) { bar.hidden = true; paint(); } }
    function play(items, o) {
      if (!ok || !items.length) return;
      opts = o || {}; queue = items; qi = 0; pi = 0; parts = [];
      if (!bar) buildBar(); bar.hidden = !!opts.quiet; speak();
    }
    window.addEventListener('pagehide', function () { if (ok) synth.cancel(); });
    return { ok: ok, play: play, stop: stop };
  })();

  function storyItems(s, max) {
    var since = seenAtLoad[s.slug];
    var fresh = since ? s.events.filter(function (e) { return e.added > since && !e.forecast; }) : [];
    var evs = (fresh.length ? fresh : s.events.filter(function (e) { return !e.forecast; }).slice(-(max || 3))).slice(-(max || 3));
    return evs.map(function (e) {
      return { label: s.short + ' · ' + e.label, text: e.label + '. ' + e.title + '. ' + e.summary, el: document.getElementById('e' + e.i) };
    });
  }
  if (Audio.ok) {
    document.querySelectorAll('.listen-btn').forEach(function (b) { b.hidden = false; });
    document.querySelectorAll('[data-listen-story]').forEach(function (b) {
      b.addEventListener('click', function () {
        var s = byslug(b.getAttribute('data-listen-story')); if (!s) return;
        var onPage = document.body.getAttribute('data-story') === s.slug;
        var items = [{ label: s.short + ' · In 30 seconds', text: s.title + '. ' + s.intro.join(' ') }].concat(storyItems(s, 3));
        if (!onPage) items.push({ label: 'Full timeline', text: 'For the full timeline, open ' + s.short + ' on Newspin.' });
        Audio.play(items, { title: s.short });
      });
    });
    var bb = document.getElementById('briefing-btn');
    if (bb) bb.addEventListener('click', function () {
      var order = Array.prototype.map.call(document.querySelectorAll('.bubble[data-sm-open]'), function (x) { return byslug(x.getAttribute('data-sm-open')); }).filter(Boolean);
      var mine = order.filter(function (s) { return follows[s.slug]; });
      var pool = (mine.length ? mine : order).filter(function (s) { return s.latestAdded >= threeAgo || mine.length; }).slice(0, 6);
      var hr = new Date().getHours();
      var items = [{ label: 'Your briefing', text: (hr < 12 ? 'Good morning' : hr < 17 ? 'Good afternoon' : 'Good evening') + '. Here is your Newspin briefing: ' + pool.length + ' stories that moved.' }];
      pool.forEach(function (s) {
        var last = s.events.filter(function (e) { return !e.forecast; }).slice(-1)[0];
        items.push({ label: s.short, text: s.short + '. ' + last.title + '. ' + last.summary });
      });
      items.push({ label: 'End of briefing', text: 'That is your briefing. Tap any story for the full timeline.' });
      Audio.play(items, { title: 'Your briefing' });
    });
  }

  // ---- story page ----
  var story = document.body.getAttribute('data-story');
  if (story) {
    var evs = Array.prototype.slice.call(document.querySelectorAll('.ev[data-added]'));
    var last = seen[story];
    var fresh = last ? evs.filter(function (li) { return li.getAttribute('data-added') > last; }) : [];
    var bar = document.getElementById('newbar');
    if (fresh.length && bar) {
      bar.hidden = false;
      bar.querySelector('.k').textContent = 'You last opened this story on ' + fmt(last);
      bar.querySelector('.h').textContent = fresh.length + ' new ' + (fresh.length === 1 ? 'development' : 'developments') + ' since your last visit';
      fresh.forEach(function (li) { var b = li.querySelector('.badge-new'); if (b) b.hidden = false; });
      var onlyBtn = bar.querySelector('button');
      var only = false;
      onlyBtn.addEventListener('click', function () {
        only = !only;
        onlyBtn.setAttribute('aria-pressed', only ? 'true' : 'false');
        onlyBtn.textContent = only ? 'Show full timeline' : 'Show only what’s new';
        evs.forEach(function (li) { li.hidden = only && fresh.indexOf(li) === -1; });
      });
    }
    seen[story] = today; save('np_seen', seen);

    // detail level
    var segBtns = document.querySelectorAll('[data-mode]');
    function setMode(mode, persist) {
      segBtns.forEach(function (b) { b.setAttribute('aria-pressed', b.getAttribute('data-mode') === mode ? 'true' : 'false'); });
      document.querySelectorAll('.ev details').forEach(function (d) { d.open = mode === 'detailed'; });
      if (persist) save('np_mode', mode);
    }
    segBtns.forEach(function (b) { b.addEventListener('click', function () { setMode(b.getAttribute('data-mode'), true); }); });
    setMode(load('np_mode', 'simple'), false);
  }
})();

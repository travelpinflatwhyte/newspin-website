(function () {
  'use strict';

  // ---- storage (kept in this browser only) ----
  function load(key, fallback) {
    try { var v = localStorage.getItem(key); return v ? JSON.parse(v) : fallback; } catch (e) { return fallback; }
  }
  function save(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch (e) { /* storage blocked: features degrade quietly */ }
  }
  var today = new Date().toISOString().slice(0, 10);
  if (/[?&]tl=a\b/.test(location.search)) document.body.classList.remove('tl-b'); // old phone layout, for comparison
  var follows = load('np_follow', {});   // slug -> date followed
  var seen = load('np_seen', {});        // slug -> date last opened
  var homeSeen = load('np_home', null);  // date of last home visit

  function fmt(d) {
    var dt = new Date(d + 'T00:00:00');
    return dt.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
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
      else { follows[slug] = today; if (!seen[slug]) seen[slug] = today; save('np_seen', seen); say('Following. We’ll catch you up here.'); }
      save('np_follow', follows);
      document.querySelectorAll('[data-follow="' + slug + '"]').forEach(paintFollow);
      renderCatchup();
    });
  });

  // ---- share ----
  document.querySelectorAll('[data-share]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var url = btn.getAttribute('data-share') || location.href;
      var title = document.title;
      if (navigator.share) { navigator.share({ title: title, url: url }).catch(function () {}); return; }
      if (navigator.clipboard) { navigator.clipboard.writeText(url).then(function () { say('Link copied'); }, function () { say(url); }); }
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

  // ---- theme ----
  var themeBtn = document.getElementById('theme-btn');
  function paintTheme() {
    var dark = document.documentElement.getAttribute('data-theme') === 'dark';
    if (themeBtn) themeBtn.setAttribute('aria-label', dark ? 'Switch to light mode' : 'Switch to dark mode');
  }
  if (themeBtn) themeBtn.addEventListener('click', function () {
    var next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    try { localStorage.setItem('np_theme', next); } catch (e) {}
    paintTheme();
  });
  paintTheme();

  // ---- home: greeting + bubbles ----
  var seenAtLoad = JSON.parse(JSON.stringify(seen));
  var DATA = window.NP_STORIES || [];
  function addDays(d, n) { var x = new Date(d + 'T00:00:00'); x.setDate(x.getDate() + n); return x.toISOString().slice(0, 10); }
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
  var sm, smStory, smSlides, smIdx, smOpener;
  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
  function buildSm() {
    sm = el('div', 'sm'); sm.hidden = true;
    sm.setAttribute('role', 'dialog'); sm.setAttribute('aria-modal', 'true'); sm.setAttribute('aria-label', 'Catch me up');
    sm.innerHTML = '<div class="sm-card"><div class="sm-bars"></div><div class="sm-top"><div class="sm-who"><span class="sm-av"></span><span><span class="sm-name"></span><span class="sm-pos"></span></span></div><button type="button" class="sm-x" aria-label="Close">×</button></div>' +
      '<button type="button" class="sm-zone prev" aria-label="Previous"></button><button type="button" class="sm-zone next" aria-label="Next"></button>' +
      '<div class="sm-body" aria-live="polite"></div><div class="sm-foot"><p class="sm-hint">Tap the right side for next, left for back</p><div class="sm-actions"><a class="go"></a><a class="ghost"></a></div></div></div>';
    document.body.appendChild(sm);
    sm.querySelector('.sm-x').addEventListener('click', closeSm);
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
  function closeSm() {
    sm.hidden = true; document.documentElement.style.overflow = '';
    if (smOpener && smOpener.focus) smOpener.focus();
  }
  document.querySelectorAll('[data-sm-open]').forEach(function (b) {
    b.addEventListener('click', function () { openSm(b.getAttribute('data-sm-open'), b); });
  });

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

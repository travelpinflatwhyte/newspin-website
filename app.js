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

  // ---- home: catch-up across followed stories ----
  function renderCatchup() {
    var box = document.getElementById('catchup');
    var data = window.NP_STORIES;
    if (!box || !data) return;
    var intro = document.getElementById('catchup-intro');
    var mine = data.filter(function (s) { return follows[s.slug]; });
    if (!mine.length) { box.hidden = true; if (intro) intro.hidden = false; return; }
    box.hidden = false; if (intro) intro.hidden = true;
    var moved = mine.filter(function (s) {
      var since = seen[s.slug] || follows[s.slug];
      return s.latestAdded > since;
    });
    var h = box.querySelector('h1');
    var kicker = box.querySelector('.kicker');
    var list = box.querySelector('ul');
    var all = box.querySelector('[data-all]');
    kicker.textContent = homeSeen ? 'Last visit ' + fmt(homeSeen) : 'Your stories';
    h.textContent = moved.length
      ? moved.length + ' of your ' + mine.length + ' ' + (mine.length === 1 ? 'story' : 'stories') + ' moved since you last looked'
      : 'You’re caught up on your ' + mine.length + ' ' + (mine.length === 1 ? 'story' : 'stories');
    list.innerHTML = '';
    (moved.length ? moved : mine).forEach(function (s) {
      var li = document.createElement('li');
      var a = document.createElement('a'); a.href = s.url; a.textContent = s.short;
      var span = document.createElement('span');
      span.appendChild(a);
      span.appendChild(document.createTextNode(': ' + s.latestTitle + ' (' + s.latestLabel + ')'));
      li.appendChild(span); list.appendChild(li);
    });
    if (all) { all.href = (moved[0] || mine[0]).url; all.textContent = moved.length ? 'Start with ' + (moved[0].short) : 'Open ' + mine[0].short; }
  }
  renderCatchup();
  if (document.getElementById('catchup')) save('np_home', today);

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

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

  // ---- home: filter chips ----
  var chips = document.querySelectorAll('[data-filter]');
  chips.forEach(function (chip) {
    chip.addEventListener('click', function () {
      var cat = chip.getAttribute('data-filter');
      chips.forEach(function (c) { c.setAttribute('aria-pressed', c === chip ? 'true' : 'false'); });
      document.querySelectorAll('.card[data-cat]').forEach(function (card) {
        card.hidden = !(cat === 'All' || card.getAttribute('data-cat') === cat);
      });
    });
  });

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

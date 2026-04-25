/* ── Carousel ── */
(function () {
  const track = document.querySelector('.carousel-track');
  if (!track) return;
  const slides = track.querySelectorAll('.carousel-slide');
  const dots = document.querySelectorAll('.carousel-dot');
  let current = 0, timer;

  function goTo(n) {
    current = (n + slides.length) % slides.length;
    track.style.transform = `translateX(-${current * 100}%)`;
    dots.forEach((d, i) => d.classList.toggle('active', i === current));
  }

  function next() { goTo(current + 1); }

  document.querySelector('.carousel-btn-prev')?.addEventListener('click', () => { goTo(current - 1); resetTimer(); });
  document.querySelector('.carousel-btn-next')?.addEventListener('click', () => { next(); resetTimer(); });
  dots.forEach((d, i) => d.addEventListener('click', () => { goTo(i); resetTimer(); }));

  function resetTimer() { clearInterval(timer); timer = setInterval(next, 5000); }

  if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    timer = setInterval(next, 5000);
  }
  goTo(0);
})();

/* ── Mobile Nav ── */
(function () {
  const hamburger = document.querySelector('.hamburger');
  const menu = document.querySelector('.nav-mobile-menu');
  if (!hamburger || !menu) return;
  hamburger.addEventListener('click', () => {
    const isOpen = menu.classList.toggle('open');
    menu.style.display = isOpen ? 'flex' : 'none';
    hamburger.setAttribute('aria-expanded', isOpen);
  });
})();

/* ── Synopsis expand/collapse ── */
(function () {
  const text = document.querySelector('.synopsis-text');
  const toggle = document.querySelector('.synopsis-toggle');
  if (!text || !toggle) return;
  const LIMIT = 300;
  const full = text.textContent;
  if (full.length <= LIMIT) { toggle.remove(); return; }
  let expanded = false;
  text.textContent = full.slice(0, LIMIT) + '…';
  toggle.addEventListener('click', () => {
    expanded = !expanded;
    text.textContent = expanded ? full : full.slice(0, LIMIT) + '…';
    toggle.textContent = expanded ? 'Show less' : 'Show more';
  });
})();

/* ── Bookmark toggle ── */
(function () {
  const btn = document.getElementById('bookmark-btn');
  if (!btn) return;
  const mangadexId = btn.dataset.mangadexId;
  const csrfToken = document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '';

  btn.addEventListener('click', async () => {
    const listType = btn.dataset.listType || 'reading';
    try {
      btn.disabled = true;
      const res = await fetch('/api/bookmark/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
        body: JSON.stringify({ mangadex_id: mangadexId, list_type: listType }),
      });
      const data = await res.json();
      if (data.action === 'removed') {
        btn.classList.remove('bookmarked');
        btn.querySelector('.btn-label').textContent = 'Add to List';
      } else {
        btn.classList.add('bookmarked');
        btn.querySelector('.btn-label').textContent = 'Bookmarked ✓';
        btn.dataset.listType = data.list_type;
      }
    } catch (e) {
      console.error('Bookmark error', e);
    } finally {
      btn.disabled = false;
    }
  });
})();

/* ── Reader progress indicator ── */
(function () {
  const progress = document.querySelector('.reader-progress');
  const pages = document.querySelectorAll('.page-wrapper');
  if (!progress || !pages.length) return;

  const io = new IntersectionObserver(entries => {
    let visible = 0;
    entries.forEach(e => { if (e.isIntersecting) visible = parseInt(e.target.dataset.page); });
    if (visible) progress.textContent = `${visible} / ${pages.length}`;
  }, { threshold: 0.5 });

  pages.forEach((p, i) => { p.dataset.page = i + 1; io.observe(p); });
})();

/* ── Advanced Search (Browse page) ── */
(function () {
  /* Dropdown toggles */
  document.querySelectorAll('.adv-dropdown-btn').forEach(btn => {
    btn.addEventListener('click', e => {
      e.stopPropagation();
      const panel = document.getElementById(btn.dataset.target);
      const isOpen = panel.classList.contains('open');
      document.querySelectorAll('.adv-dropdown-panel').forEach(p => p.classList.remove('open'));
      document.querySelectorAll('.adv-dropdown-btn').forEach(b => b.classList.remove('active'));
      if (!isOpen) {
        panel.classList.add('open');
        btn.classList.add('active');
      }
    });
  });

  /* Close dropdowns on outside click */
  document.addEventListener('click', e => {
    if (!e.target.closest('.adv-dropdown-wrap')) {
      document.querySelectorAll('.adv-dropdown-panel').forEach(p => p.classList.remove('open'));
      document.querySelectorAll('.adv-dropdown-btn').forEach(b => b.classList.remove('active'));
    }
  });

  /* Filter row toggle */
  const filterToggle = document.getElementById('adv-filter-toggle');
  const filterRow = document.getElementById('adv-filter-row');
  filterToggle?.addEventListener('click', () => {
    filterRow.classList.toggle('open');
    filterToggle.classList.toggle('active');
  });

  /* Genre tag cycling: neutral → include → exclude → neutral */
  const state = {};
  document.querySelectorAll('.genre-filter-tag').forEach(tag => {
    tag.addEventListener('click', () => {
      const id = tag.dataset.id;
      const cur = state[id] || null;
      state[id] = cur === null ? 'include' : cur === 'include' ? 'exclude' : null;
      tag.className = 'tag genre-filter-tag ' + (
        state[id] === 'include' ? 'include' : state[id] === 'exclude' ? 'exclude' : 'neutral'
      );
    });
  });

  /* Inject genre values on form submit */
  document.querySelector('.browse-filter-form')?.addEventListener('submit', () => {
    const inc = Object.entries(state).filter(([, v]) => v === 'include').map(([k]) => k);
    const exc = Object.entries(state).filter(([, v]) => v === 'exclude').map(([k]) => k);
    const i = document.getElementById('id_genres_include');
    const x = document.getElementById('id_genres_exclude');
    if (i) i.value = inc.join(',');
    if (x) x.value = exc.join(',');
  });
})();

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
  // Touch swipe support
  let touchStartX = 0, touchStartY = 0;
  track.addEventListener('touchstart', e => {
    touchStartX = e.touches[0].clientX;
    touchStartY = e.touches[0].clientY;
  }, { passive: true });
  track.addEventListener('touchend', e => {
    const dx = e.changedTouches[0].clientX - touchStartX;
    const dy = e.changedTouches[0].clientY - touchStartY;
    if (Math.abs(dx) > Math.abs(dy) && Math.abs(dx) > 50) {
      dx < 0 ? (goTo(current + 1), resetTimer()) : (goTo(current - 1), resetTimer());
    }
  }, { passive: true });
  goTo(0);
})();

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
(function () {
  const bookmarkSelect = document.getElementById('bookmark-select');
  if (bookmarkSelect) {
    bookmarkSelect.addEventListener('change', async () => {
      const mangadexId = bookmarkSelect.dataset.mangadexId;
      const listType = bookmarkSelect.value;
      const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value
                     || document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '';
      bookmarkSelect.disabled = true;
      try {
        const res = await fetch('/api/bookmark/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
          },
          body: JSON.stringify({ mangadex_id: mangadexId, list_type: listType })
        });
        if (!res.ok) throw new Error('Network error');
        const data = await res.json();
        if (data.action === 'removed') {
          bookmarkSelect.classList.remove('is-bookmarked');
        } else {
          bookmarkSelect.classList.add('is-bookmarked');
        }
      } catch (err) {
        console.error('Bookmark toggle failed:', err);
        alert('Failed to update bookmark.');
      } finally {
        bookmarkSelect.disabled = false;
      }
    });
  }
})();
(function () {
  const progress = document.querySelector('.reader-progress');
  const pages = document.querySelectorAll('.page-wrapper');
  if (!progress || !pages.length) return;
  const io = new IntersectionObserver(entries => {
    let visible = 0;
    entries.forEach(e => { if (e.isIntersecting) visible = parseInt(e.target.dataset.page); });
    if (visible) {
      const ch = progress.dataset.chapter ? `${progress.dataset.chapter} \u2022 ` : '';
      progress.textContent = `${ch}${visible} / ${pages.length}`;
    }
  }, { threshold: 0.5 });
  pages.forEach((p, i) => { p.dataset.page = i + 1; io.observe(p); });
})();
(function () {
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
  document.addEventListener('click', e => {
    if (!e.target.closest('.adv-dropdown-wrap')) {
      document.querySelectorAll('.adv-dropdown-panel').forEach(p => p.classList.remove('open'));
      document.querySelectorAll('.adv-dropdown-btn').forEach(b => b.classList.remove('active'));
    }
  });
  const filterToggle = document.getElementById('adv-filter-toggle');
  const filterRow = document.getElementById('adv-filter-row');
  filterToggle?.addEventListener('click', () => {
    filterRow.classList.toggle('open');
    filterToggle.classList.toggle('active');
  });
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
  document.querySelector('.browse-filter-form')?.addEventListener('submit', () => {
    const inc = Object.entries(state).filter(([, v]) => v === 'include').map(([k]) => k);
    const exc = Object.entries(state).filter(([, v]) => v === 'exclude').map(([k]) => k);
    const i = document.getElementById('id_genres_include');
    const x = document.getElementById('id_genres_exclude');
    if (i) i.value = inc.join(',');
    if (x) x.value = exc.join(',');
  });
})();

(function () {
  function abortPendingImageRequests() {
    const mangaPages = document.querySelectorAll('img.manga-page');
    const emptyImage = 'data:image/gif;base64,R0lGODlhAQABAAD/ACwAAAAAAQABAAACADs=';
    mangaPages.forEach(image => {
      if (!image.complete) {
        image.src = emptyImage;
      }
    });
  }

  const navigationLinks = document.querySelectorAll('.reader-nav a.btn, .reader-topbar a.btn');
  navigationLinks.forEach(link => {
    link.addEventListener('click', abortPendingImageRequests);
  });
})();

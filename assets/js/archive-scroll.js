// Server-rendered pages remain crawlable; readers stay on one scrolling document.
(async () => {
  const content = document.querySelector('[data-archive-list]');
  if (!content) return;
  const nav = document.querySelector('.archive-pagination');
  const annual = content.dataset.archiveList === 'annual';
  // Match homepage preloading: leave room for Space/PageDown and network latency.
  const preloadDistance = Math.max(1200, innerHeight * 2);
  const current = location.pathname;
  let next = nav?.querySelector('[rel="next"]')?.getAttribute('href') || '';
  let loaded = [current];
  let busy = false;
  let restoring = true;
  let userMoved = false;
  let anchorLock;
  let observer;
  let retryAction;
  let saved;
  let storageKey;
  try {
    const id = history.state?.archiveReader || crypto.randomUUID();
    history.replaceState({ ...history.state, archiveReader: id }, '');
    storageKey = `archive-reader:${id}`;
    saved = JSON.parse(sessionStorage.getItem(storageKey) || 'null');
    history.scrollRestoration = 'manual';
  } catch (_) { /* Scrolling remains available without browser storage. */ }

  const status = document.createElement('div');
  status.className = 'archive-scroll-status';
  const message = document.createElement('span');
  message.setAttribute('role', 'status');
  const retry = document.createElement('button');
  retry.type = 'button';
  retry.textContent = '再試行';
  retry.hidden = true;
  status.append(message, retry);
  content.after(status);
  if (nav) nav.hidden = true;

  const markAnchors = () => {
    content.querySelectorAll('.listing-card-link').forEach(link => {
      link.dataset.scrollAnchor = new URL(link.href).pathname;
    });
    content.querySelectorAll('.weeknotes-entry').forEach(week => {
      const key = week.querySelector('.weeknotes-entry-title').id;
      week.querySelectorAll('[id]').forEach(node => { node.dataset.scrollAnchor = `${key}/${node.id}`; });
    });
    // Replace placeholders with the real headings as their pages arrive.
    document.querySelectorAll('[data-archive-anchor]').forEach(link => {
      const id = link.dataset.archiveAnchor;
      if ([...content.querySelectorAll('[id]')].some(node => node.id === id)) {
        link.removeAttribute('id');
        link.classList.remove('archive-anchor-placeholder');
        link.setAttribute('href', `#${id}`);
      }
    });
  };
  const captureAnchor = () => {
    const nodes = [...content.querySelectorAll('[data-scroll-anchor]')];
    const node = annual
      ? nodes.filter(node => node.getBoundingClientRect().top <= 0).at(-1) || nodes[0]
      : nodes.find(node => node.getBoundingClientRect().bottom > 0) || nodes.at(-1);
    if (!node || node.getBoundingClientRect().top > innerHeight) return null;
    return { key: node.dataset.scrollAnchor, offset: node.getBoundingClientRect().top };
  };
  const save = () => {
    if (restoring || !storageKey) return;
    try {
      sessionStorage.setItem(storageKey, JSON.stringify({
        path: current, first: loaded[0], count: loaded.length, y: scrollY, anchor: captureAnchor(),
      }));
    } catch (_) { /* Storage can be disabled or full. */ }
  };
  const position = snapshot => {
    const target = [...content.querySelectorAll('[data-scroll-anchor]')]
      .find(node => node.dataset.scrollAnchor === snapshot.anchor?.key);
    window.scrollTo({ top: target ? scrollY + target.getBoundingClientRect().top - snapshot.anchor.offset : snapshot.y, behavior: 'instant' });
  };
  const releaseAnchor = event => {
    if (event?.target?.closest?.('.archive-scroll-status button')) return;
    userMoved = true;
    anchorLock = null;
  };
  for (const event of ['wheel', 'touchstart', 'pointerdown', 'keydown']) {
    window.addEventListener(event, releaseAnchor, { passive: true });
  }
  window.addEventListener('hashchange', releaseAnchor);
  // Storage writes are synchronous, including the last scroll before a reload.
  // Avoid history mutations during pagehide so bfcache stays usable.
  window.addEventListener('scroll', save, { passive: true });
  window.addEventListener('pagehide', save);
  if ('ResizeObserver' in window) new ResizeObserver(() => {
    if (anchorLock && !userMoved) position(anchorLock);
  }).observe(content);

  const merge = (destination, source) => {
    for (const child of [...source.children]) {
      const group = child.dataset.archiveGroup;
      const existing = group && [...destination.children].find(node => node.dataset.archiveGroup === group);
      if (existing) {
        existing.querySelector('[data-archive-children]').append(...child.querySelector('[data-archive-children]').children);
      } else destination.append(child);
    }
  };
  const fetchPage = async url => {
    const parsed = new URL(url, location.href);
    if (parsed.origin !== location.origin) throw new Error('Unexpected archive origin');
    const response = await fetch(parsed.href);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const page = new DOMParser().parseFromString(await response.text(), 'text/html');
    const items = page.querySelector('[data-archive-list]');
    if (!items?.children.length || items.dataset.archiveList !== content.dataset.archiveList) throw new Error('Invalid archive page');
    return { items, next: page.querySelector('.archive-pagination [rel="next"]')?.getAttribute('href') || '' };
  };
  const changed = () => {
    markAnchors();
    document.dispatchEvent(new Event('archive:loaded'));
    if (annual) document.dispatchEvent(new Event('annual:loaded'));
    save();
  };
  const fail = action => {
    message.textContent = '続きの読み込みに失敗しました。再試行してください。';
    retry.hidden = false;
    retryAction = action;
    observer?.unobserve(status);
  };
  const loadNext = async () => {
    if (busy || !next) return false;
    busy = true;
    message.textContent = '読み込み中…';
    try {
      if (loaded.includes(next)) throw new Error('Pagination cycle');
      const url = next;
      const page = await fetchPage(url);
      merge(content, page.items);
      loaded.push(url);
      next = page.next;
      changed();
      message.textContent = next ? '' : 'すべて読み込みました';
      retry.hidden = true;
      return true;
    } finally { busy = false; }
  };
  const observe = () => {
    if (next) requestAnimationFrame(() => {
      if (busy || restoring || !retry.hidden) return;
      const bounds = status.getBoundingClientRect();
      // A short page can leave the sentinel in the preload area after appending.
      // Continue filling the buffer without waiting for another intersection.
      if (bounds.bottom >= 0 && bounds.top <= innerHeight + preloadDistance) advance();
      else observer?.observe(status);
    });
    else observer?.disconnect();
  };
  const advance = async () => {
    if (busy || restoring || !next) return;
    observer?.unobserve(status);
    try { await loadNext(); observe(); } catch (_) { fail(advance); }
  };
  if ('IntersectionObserver' in window) {
    observer = new IntersectionObserver(entries => {
      if (entries.some(entry => entry.isIntersecting)) advance();
    }, { rootMargin: `0px 0px ${preloadDistance}px 0px` });
  } else {
    window.addEventListener('scroll', () => {
      if (retry.hidden && status.getBoundingClientRect().top < innerHeight + preloadDistance) advance();
    }, { passive: true });
  }
  retry.addEventListener('click', () => { retry.hidden = true; retryAction?.(); });
  window.addEventListener('online', () => { if (!retry.hidden) retry.click(); });

  const restore = async () => {
    try {
      if (saved?.path === current && Number.isInteger(saved.count) && saved.count > 0) {
        if (saved.first !== loaded[0]) {
          const page = await fetchPage(saved.first);
          content.replaceChildren(...page.items.children);
          loaded = [saved.first];
          next = page.next;
          changed();
        }
        while (loaded.length < saved.count && next) await loadNext();
        if (!userMoved && Number.isFinite(saved.y)) {
          anchorLock = saved;
          position(saved);
        }
      }
      restoring = false;
      save();
      document.documentElement.dataset.archiveReady = 'true';
      document.dispatchEvent(new Event('archive:ready'));
      observe();
    } catch (_) { fail(restore); }
  };
  markAnchors();
  await restore();

})();

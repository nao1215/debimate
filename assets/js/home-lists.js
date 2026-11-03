// Fetch only the next small batch. Archive links also work without JavaScript.
const homeListState = { ...history.state?.homeLists };
const restorations = [];
// Space/PageDown advances almost a viewport. Reserve two viewports ahead.
const preloadDistance = Math.max(1200, window.innerHeight * 2);
let userMoved = false;
let pageActive = true;
const suspendLists = [];
const resumeLists = [];
window.addEventListener('pagehide', () => {
  pageActive = false;
  clearTimeout(scrollTimer);
  suspendLists.forEach(suspend => suspend());
});
window.addEventListener('pageshow', () => {
  pageActive = true;
  resumeLists.forEach(resume => resume());
});
for (const event of ['wheel', 'touchstart', 'keydown', 'pointerdown']) {
  window.addEventListener(event, () => { userMoved = true; }, { once: true, passive: true });
}
const restoreY = history.state?.homeScrollY;
const remember = () => {
  try {
    history.replaceState({ ...history.state, homeLists: homeListState, homeScrollY: window.scrollY }, '');
  } catch (_) {
    // Loading still works if history storage is unavailable.
  }
};
// Mutating history during pagehide can evict Chrome's back/forward cache.
let scrollTimer;
window.addEventListener('scroll', () => {
  clearTimeout(scrollTimer);
  scrollTimer = setTimeout(remember, 100);
}, { passive: true });

// Content-addressed batch URLs can disappear after deployment while the
// browser still holds the old homepage. Reload only when its list has changed.
let latestHome;
const refreshChangedList = async (key, originalNext, signal) => {
  try {
    latestHome ??= fetch(window.location.href, { cache: 'no-cache' }).then(async response => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return new DOMParser().parseFromString(await response.text(), 'text/html');
    });
    const latest = (await latestHome).querySelector(`[aria-labelledby="${key}"]`);
    if (!latest || !pageActive || signal.aborted) return false;
    const latestNext = latest.querySelector('.home-list-status')?.dataset.next;
    if (latestNext === originalNext) return false;
    remember();
    window.location.reload();
    return true;
  } catch (_) {
    latestHome = undefined;
    return false;
  }
};

document.querySelectorAll('.home-columns > section').forEach((section) => {
  const status = section.querySelector('.home-list-status');
  if (!status) return;
  const message = status.querySelector('[role="status"]');
  const button = status.querySelector('button');
  const key = section.getAttribute('aria-labelledby');
  const total = Number(status.dataset.total);
  let visible = section.querySelectorAll('.post-entry').length;
  const saved = homeListState[key];
  const target = Number.isInteger(saved) ? Math.min(total, Math.max(visible, saved)) : visible;
  let next = status.dataset.next;
  let loading = false;
  let observer;
  let controller;
  let interrupted = false;
  button.hidden = false;

  const load = async () => {
    if (!pageActive || loading || !next) return false;
    loading = true;
    const request = new AbortController();
    controller = request;
    observer?.unobserve(status);
    button.disabled = true;
    message.textContent = '読み込み中…';
    try {
      const response = await fetch(next, { signal: request.signal });
      if (!response.ok) {
        if ((response.status === 404 || response.status === 410) &&
            !request.signal.aborted && await refreshChangedList(key, status.dataset.next, request.signal)) return false;
        throw new Error(`HTTP ${response.status}`);
      }
      const payload = await response.json();
      if (request.signal.aborted) return false;
      if (typeof payload.html !== 'string' || typeof payload.next !== 'string') throw new Error('Invalid batch');
      const template = document.createElement('template');
      template.innerHTML = payload.html;
      const count = template.content.querySelectorAll('.post-entry').length;
      if (!count) throw new Error('Empty batch');
      section.insertBefore(template.content, status);
      visible += count;
      next = payload.next;
      homeListState[key] = visible;
      remember();
      message.textContent = `${total} 件中 ${visible} 件`;
      button.hidden = !next;
      button.textContent = 'もっと見る';
      return true;
    } catch (_) {
      if (request.signal.aborted) return false;
      message.textContent = '読み込めませんでした。再試行するか、上の一覧リンクをご利用ください。';
      button.textContent = '再試行';
      return false;
    } finally {
      loading = false;
      button.disabled = false;
      if (request.signal.aborted) {
        message.textContent = `${total} 件中 ${visible} 件`;
        button.textContent = 'もっと見る';
      }
      resume();
    }
  };
  const observe = () => {
    if (next && pageActive) requestAnimationFrame(async () => {
      if (!pageActive || loading || !observer) return;
      // Adding a short batch can leave the sentinel inside the preload area.
      // Fill that area explicitly instead of waiting for another intersection.
      const bounds = status.getBoundingClientRect();
      if (bounds.bottom >= 0 && bounds.top <= window.innerHeight + preloadDistance) {
        if (await load()) observe();
      } else observer.observe(status);
    });
    else observer?.disconnect();
  };
  // A navigation-cancelled fetch is not a network failure. Resume it when
  // the same document returns from the back/forward cache, even if its
  // rejection settles after pageshow.
  const resume = () => {
    if (!pageActive || loading || !interrupted) return;
    interrupted = false;
    void (async () => {
      do { if (!await load()) return; } while (visible < target && next);
      observe();
    })();
  };
  suspendLists.push(() => {
    observer?.disconnect();
    if (loading) {
      interrupted = true;
      controller.abort();
    }
  });
  resumeLists.push(() => {
    if (interrupted) resume();
    else observe();
  });
  button.addEventListener('click', async () => { if (await load()) observe(); });
  if ('IntersectionObserver' in window) {
    observer = new IntersectionObserver(async (entries) => {
      if (entries.some((entry) => entry.isIntersecting) && await load()) observe();
    }, { rootMargin: `0px 0px ${preloadDistance}px 0px` });
  }
  restorations.push((async () => {
    while (visible < target && next) {
      if (!await load()) return; // Do not retry failed requests automatically.
    }
    observe();
  })());
});
// Fetching saved batches is asynchronous; restore the old position once the
// layout is back, unless the reader has already started interacting.
Promise.all(restorations).then(() => {
  if (!userMoved && Number.isFinite(restoreY)) window.scrollTo(0, restoreY);
});

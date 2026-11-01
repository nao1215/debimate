// Fetch only the next small batch. Archive links also work without JavaScript.
const homeListState = { ...history.state?.homeLists };
const restorations = [];
let userMoved = false;
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
  button.hidden = false;

  const load = async () => {
    if (loading || !next) return false;
    loading = true;
    observer?.unobserve(status);
    button.disabled = true;
    message.textContent = '読み込み中…';
    try {
      const response = await fetch(next);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json();
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
      message.textContent = '読み込めませんでした。再試行するか、上の一覧リンクをご利用ください。';
      button.textContent = '再試行';
      return false;
    } finally {
      loading = false;
      button.disabled = false;
    }
  };
  const observe = () => {
    if (next) requestAnimationFrame(() => observer?.observe(status));
    else observer?.disconnect();
  };
  button.addEventListener('click', async () => { if (await load()) observe(); });
  if ('IntersectionObserver' in window) {
    observer = new IntersectionObserver(async (entries) => {
      if (entries.some((entry) => entry.isIntersecting) && await load()) observe();
    }, { rootMargin: '0px 0px 400px 0px' });
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

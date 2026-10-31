// All cards remain in HTML; reveal the next batch as the list end approaches.
// Keep list heights across reload/back so native scroll restoration uses the same layout.
const homeListState = history.state?.homeLists || {};
const rememberVisible = (key, count) => {
  homeListState[key] = count;
  try {
    history.replaceState({ ...history.state, homeLists: homeListState }, '');
  } catch (_) {
    // Progressive loading still works when history storage is unavailable.
  }
};
document.querySelectorAll('.home-columns > section').forEach((section) => {
  const cards = [...section.querySelectorAll('.post-entry')];
  const batch = 6;
  if (cards.length <= batch) return;
  const status = section.querySelector('.home-list-status');
  if (!('IntersectionObserver' in window)) {
    cards.forEach((card) => card.classList.remove('home-deferred'));
    status.textContent = `${cards.length} 件中 ${cards.length} 件`;
    return;
  }
  const key = section.getAttribute('aria-labelledby');
  const saved = homeListState[key];
  let visible = Number.isInteger(saved) ? Math.min(cards.length, Math.max(batch, saved)) : batch;
  cards.slice(visible).forEach((card) => { card.hidden = true; });
  cards.forEach((card) => card.classList.remove('home-deferred'));
  status.textContent = `${cards.length} 件中 ${visible} 件`;
  rememberVisible(key, visible);
  const observer = new IntersectionObserver((entries) => {
    if (!entries.some((entry) => entry.isIntersecting)) return;
    observer.unobserve(status);
    const start = visible;
    visible = Math.min(visible + batch, cards.length);
    cards.slice(start, visible).forEach((card) => { card.hidden = false; });
    status.textContent = `${cards.length} 件中 ${visible} 件`;
    rememberVisible(key, visible);
    if (visible < cards.length) {
      // Fill the viewport if needed; CSS disables anchoring to the moving list end.
      requestAnimationFrame(() => observer.observe(status));
    } else {
      observer.disconnect();
    }
  }, { rootMargin: '0px 0px 400px 0px' });
  if (visible < cards.length) observer.observe(status);
});

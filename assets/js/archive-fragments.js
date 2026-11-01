// Resolve anchors that used to live on a single, unpaginated archive.
const routeArchiveFragment = async () => {
  const hash = location.hash;
  let id;
  try { id = decodeURIComponent(hash.slice(1)); } catch (_) { return; }
  if (!id) return;
  const target = document.getElementById(id);
  if (target && !target.classList.contains('archive-anchor-placeholder')) return;
  let destination = [...document.querySelectorAll('[data-archive-anchor]')]
    .find(link => link.dataset.archiveAnchor === id)?.href;
  if (!destination) {
    const index = document.querySelector('[data-anchor-index]')?.dataset.anchorIndex;
    if (!index) return;
    try {
      const response = await fetch(index);
      if (!response.ok) return;
      const targets = await response.json();
      if (Object.hasOwn(targets, id)) destination = targets[id] + hash;
    } catch (_) { return; }
  }
  if (destination && location.hash === hash) {
    const url = new URL(destination, location.href);
    if (url.origin === location.origin && url.pathname !== location.pathname) location.replace(url.href);
  }
};
window.addEventListener('hashchange', routeArchiveFragment);
if (document.querySelector('[data-archive-list]') && !document.documentElement.dataset.archiveReady) {
  document.addEventListener('archive:ready', routeArchiveFragment, { once: true });
} else routeArchiveFragment();

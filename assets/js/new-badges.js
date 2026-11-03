(() => {
  const day = 86400000;
  const japanOffset = 9 * 60 * 60 * 1000;
  const selector = '[data-new-date]';
  const update = root => {
    const today = Math.floor((Date.now() + japanOffset) / day);
    const apply = badge => {
      const value = badge.dataset.newDate;
      const created = /^\d{4}-\d{2}-\d{2}$/.test(value)
        ? Date.parse(`${value}T00:00:00Z`) : NaN;
      const age = today - created / day;
      badge.hidden = !(age >= 0 && age < (Number(badge.dataset.newDays) || 14));
    };
    if (root.matches?.(selector)) apply(root);
    root.querySelectorAll?.(selector).forEach(apply);
  };
  // Home batches and archive pagination insert cards after the initial render.
  new MutationObserver(records => {
    for (const record of records) record.addedNodes.forEach(update);
  }).observe(document.body, { childList: true, subtree: true });

  let timer;
  const refresh = () => {
    clearTimeout(timer);
    update(document);
    const untilMidnight = day - ((Date.now() + japanOffset) % day);
    timer = setTimeout(refresh, untilMidnight + 50);
  };
  window.addEventListener('pageshow', refresh);
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) refresh();
  });
  refresh();
})();

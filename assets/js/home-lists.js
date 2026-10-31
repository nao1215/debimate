// Keep complete lists in HTML for no-JS readers; reveal cards progressively.
document.querySelectorAll('.home-columns > section').forEach((section) => {
  const cards = [...section.querySelectorAll('.post-entry')];
  const batch = 6;
  if (cards.length <= batch) return;
  let visible = batch;
  cards.slice(visible).forEach((card) => { card.hidden = true; });
  cards.forEach((card) => card.classList.remove('home-deferred'));
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'home-list-more';
  button.textContent = 'もっと見る';
  button.setAttribute('aria-label', `${section.querySelector('h2').textContent}をもっと見る`);
  const status = document.createElement('p');
  status.className = 'home-list-status';
  status.setAttribute('aria-live', 'polite');
  section.append(button, status);
  let observer;
  const update = () => {
    status.textContent = `${cards.length} 件中 ${visible} 件`;
    if (visible === cards.length) {
      button.hidden = true;
      observer?.disconnect();
    }
  };
  const reveal = (manual = false) => {
    const start = visible;
    visible = Math.min(visible + batch, cards.length);
    cards.slice(start, visible).forEach((card) => { card.hidden = false; });
    if (manual) cards[start]?.querySelector('.entry-link')?.focus({ preventScroll: true });
    update();
  };
  button.addEventListener('click', () => reveal(true));
  if ('IntersectionObserver' in window) {
    observer = new IntersectionObserver((entries) => {
      if (entries.some((entry) => entry.isIntersecting)) reveal();
    }, { rootMargin: '0px 0px 200px 0px' });
    observer.observe(button);
  }
  update();
});

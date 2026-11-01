const initializeListCards = () => {
// A removed or unavailable remote thumbnail must not leave a broken card.
document.querySelectorAll('img[data-card-fallback]:not([data-fallback-ready])').forEach((image) => {
  image.dataset.fallbackReady = 'true';
  const fallback = () => {
    image.removeAttribute('srcset');
    image.removeAttribute('sizes');
    image.src = image.dataset.cardFallback;
    delete image.dataset.cardFallback;
  };
  image.addEventListener('error', fallback, { once: true });
  if (image.complete && !image.naturalWidth) fallback();
});

// Weeknotes without usable media remain text-only cards.
document.querySelectorAll('img[data-card-optional]:not([data-optional-ready])').forEach((image) => {
  image.dataset.optionalReady = 'true';
  const remove = () => image.remove();
  image.addEventListener('error', remove, { once: true });
  if (image.complete && !image.naturalWidth) remove();
});

};
document.addEventListener('archive:loaded', initializeListCards);
initializeListCards();

// Keep autoplay for visible previews, without fetching offscreen videos/posters.
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
document.querySelectorAll('[data-game-demo]').forEach(video => {
  const showPoster = () => {
    if (video.dataset.poster) {
      video.poster = video.dataset.poster;
      delete video.dataset.poster;
    }
  };
  if (!('IntersectionObserver' in window)) {
    showPoster();
    return;
  }
  let visible = false;
  video.muted = true;
  const update = () => {
    if (visible && !document.hidden && !reducedMotion.matches) {
      showPoster();
      if (video.dataset.src) {
        video.src = video.dataset.src;
        delete video.dataset.src;
      }
      video.play().catch(() => {});
    } else {
      video.pause();
    }
  };
  document.addEventListener('visibilitychange', update);
  reducedMotion.addEventListener('change', update);
  const posterObserver = new IntersectionObserver(entries => {
    if (entries.some(entry => entry.isIntersecting)) {
      showPoster();
      posterObserver.disconnect();
    }
  }, { rootMargin: '200px' });
  posterObserver.observe(video);
  new IntersectionObserver(entries => {
    visible = entries[0].isIntersecting;
    update();
  }).observe(video);
});

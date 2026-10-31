// GIF-like previews: no controls or audio, and no downloads until visible.
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
document.querySelectorAll('[data-game-demo]').forEach(video => {
  if (!('IntersectionObserver' in window)) return;
  let visible = false;
  video.muted = true;
  const update = () => {
    if (visible && !document.hidden && !reducedMotion.matches) {
      video.play().catch(() => {}); // Keep the poster if autoplay is unavailable.
    } else {
      video.pause();
    }
  };
  document.addEventListener('visibilitychange', update);
  reducedMotion.addEventListener('change', update);
  new IntersectionObserver(entries => {
    visible = entries[0].isIntersecting;
    update();
  }).observe(video);
});

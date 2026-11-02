// Import Mermaid only when a diagram approaches the viewport, then render one
// diagram per task so a long article does not monopolize the main thread.
const pendingDiagrams = new Set();
const watchedDiagrams = new WeakSet();
let renderer;
let rendering = false;
let renderedCount = 0;
const nearViewport = node => {
  if (!node.isConnected || !node.getClientRects().length) return false;
  const bounds = node.getBoundingClientRect();
  return bounds.bottom >= -400 && bounds.top <= innerHeight + 400;
};
const loadRenderer = () => {
  if (!renderer) {
    renderer = import('https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs')
      .then(({ default: mermaid }) => {
        mermaid.initialize({ startOnLoad: false, theme: 'neutral' });
        return mermaid;
      });
  }
  return renderer;
};
const renderPending = async () => {
  if (rendering) return;
  rendering = true;
  try {
    while (pendingDiagrams.size) {
      const node = pendingDiagrams.values().next().value;
      pendingDiagrams.delete(node);
      if (!node.isConnected || node.dataset.processed || node.dataset.mermaidError) continue;
      if (observer && !nearViewport(node)) continue;
      const source = node.textContent;
      try {
        const mermaid = await loadRenderer();
        // The reader may have scrolled away during the module download.
        if (observer && !nearViewport(node)) continue;
        // mermaid.run() restarts its ID counter on every call, so diagrams rendered one by one
        // all became "mermaid-0" and a later diagram was drawn into an earlier SVG. Give each a unique ID.
        const { svg, bindFunctions } = await mermaid.render(`mermaid-lazy-${++renderedCount}`, source);
        node.innerHTML = svg;
        node.dataset.processed = 'true';
        bindFunctions?.(node);
        observer?.unobserve(node);
      } catch (error) {
        // Keep the definition readable and let unrelated diagrams render.
        node.textContent = source;
        delete node.dataset.processed;
        node.dataset.mermaidError = 'true';
        observer?.unobserve(node);
        console.warn('Mermaid rendering failed', error);
      }
      await new Promise(resolve => setTimeout(resolve, 0));
    }
  } finally {
    rendering = false;
  }
};
const observer = 'IntersectionObserver' in window ? new IntersectionObserver(entries => {
  for (const entry of entries) {
    if (entry.isIntersecting) pendingDiagrams.add(entry.target);
    else pendingDiagrams.delete(entry.target);
  }
  void renderPending();
}, { rootMargin: '400px 0px' }) : null;
const watchDiagrams = () => {
  for (const node of document.querySelectorAll('pre.mermaid:not([data-processed])')) {
    if (watchedDiagrams.has(node)) continue;
    watchedDiagrams.add(node);
    if (observer) observer.observe(node);
    else pendingDiagrams.add(node);
  }
  if (!observer) void renderPending();
};
document.addEventListener('annual:loaded', watchDiagrams);
watchDiagrams();

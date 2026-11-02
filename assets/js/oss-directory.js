(() => {
  const form = document.querySelector('[data-oss-filters]');
  if (!form) return;
  const query = form.elements.query;
  const language = form.elements.language;
  const normalize = text => text.normalize('NFKC').toLocaleLowerCase();
  const projects = [...document.querySelectorAll('[data-oss-project]')].map(element => ({
    element, text: normalize(element.textContent), ...element.dataset,
  }));
  const tabs = [...document.querySelectorAll('[data-oss-tabs] button')];
  let category = 'popular';
  const update = () => {
    const words = normalize(query.value).trim().split(/\s+/).filter(Boolean);
    let count = 0;
    projects.forEach(project => {
      const inCategory = category === 'all' || (category === 'popular' ? project.popular === 'true' : project.category === category);
      const visible = inCategory && (!language.value || project.language === language.value) && words.every(word => project.text.includes(word));
      project.element.hidden = !visible;
      if (visible) count++;
    });
    tabs.forEach(tab => tab.setAttribute('aria-pressed', String(tab.dataset.category === category)));
    document.querySelector('[data-oss-count]').textContent = words.length || language.value ? `${count} 件が見つかりました` : '';
    document.querySelector('[data-oss-empty]').hidden = count !== 0;
    document.querySelector('[data-oss-games]').hidden = category !== 'games';
  };
  form.addEventListener('submit', event => event.preventDefault());
  const searchAll = () => { category = 'all'; update(); };
  form.addEventListener('input', searchAll);
  form.addEventListener('change', searchAll);
  form.addEventListener('reset', () => { requestAnimationFrame(update); });
  tabs.forEach(tab => tab.addEventListener('click', () => {
    category = tab.dataset.category;
    update();
  }));
  update();
  form.hidden = false;
  document.querySelector('[data-oss-tabs]').hidden = false;
})();

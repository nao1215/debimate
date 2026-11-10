(() => {
  const form = document.querySelector('[data-notes-filters]');
  if (!form) return;
  const grid = document.getElementById('notes-results');
  const groupsRoot = document.querySelector('[data-notes-groups]');
  const query = form.elements.query;
  const select = form.elements.category;
  const normalize = text => text.normalize('NFKC').toLocaleLowerCase();
  const items = [...grid.querySelectorAll('[data-notes-item]')].map((element, index) => ({
    ...element.dataset, element, index,
    topics: JSON.parse(element.dataset.topics || '[]'),
    text: normalize(`${element.textContent} ${element.dataset.topics || ''}`),
  }));
  const heads = new Map([...document.querySelectorAll('[data-notes-head]')].map(head => [head.dataset.notesHead, {
    element: head, topics: JSON.parse(head.querySelector('[data-notes-topics]')?.textContent || '[]'),
  }]));
  const tabs = [...document.querySelectorAll('[data-notes-tabs] button')];
  const keys = tabs.map(tab => tab.dataset.category);
  const fromHash = () => (keys.includes(location.hash.slice(1)) ? location.hash.slice(1) : 'all');
  let category = fromHash();

  // カテゴリのタブでは、小分類ごとの見出しを立てる。複数の小分類に属するカードは複製して並べる。
  // 小分類の中は、そのカテゴリのノート（weight 順）→ 別カテゴリのノート → ブログ記事・外部リンクの順。
  const renderGroups = visible => {
    groupsRoot.replaceChildren();
    const head = heads.get(category);
    if (!head) return;
    const order = [...head.topics];
    visible.forEach(item => (item.topics.length ? item.topics : ['その他']).forEach(topic => { if (!order.includes(topic)) order.push(topic); }));
    order.forEach(topic => {
      const members = visible
        .filter(item => (item.topics.length ? item.topics : ['その他']).includes(topic))
        .sort((a, b) => (a.related === 'true') - (b.related === 'true') || Number(a.weight) - Number(b.weight) || a.index - b.index);
      if (!members.length) return;
      const section = document.createElement('section');
      section.className = 'notes-topic';
      const title = document.createElement('h3');
      title.textContent = topic;
      const count = document.createElement('span');
      count.textContent = `${members.length}件`;
      title.append(count);
      const cards = document.createElement('div');
      cards.className = 'listing-cards';
      members.forEach(item => {
        const card = item.element.cloneNode(true);
        card.hidden = false;
        card.querySelectorAll('img[loading="eager"]').forEach(img => { img.loading = 'lazy'; });
        cards.append(card);
      });
      section.append(title, cards);
      groupsRoot.append(section);
    });
  };

  const update = () => {
    const words = normalize(query.value).trim().split(/\s+/).filter(Boolean);
    const grouped = heads.has(category);
    const visible = items.filter(item => {
      const inCategory = category === 'all' ? item.related !== 'true' : item.category === category;
      return inCategory && words.every(word => item.text.includes(word));
    });
    items.forEach(item => { item.element.hidden = grouped || !visible.includes(item); });
    grid.hidden = grouped;
    if (grouped) renderGroups(visible); else groupsRoot.replaceChildren();
    heads.forEach((head, key) => { head.element.hidden = key !== category; });
    tabs.forEach(tab => tab.setAttribute('aria-pressed', String(tab.dataset.category === category)));
    select.value = category;
    document.querySelector('[data-notes-count]').textContent = words.length ? `${visible.length} 件が見つかりました` : '';
    const empty = document.querySelector('[data-notes-empty]');
    empty.hidden = visible.length !== 0;
    empty.textContent = words.length ? '該当するノートはありません。キーワードやカテゴリを変えてみてください。' : 'まだノートはありません。';
    document.dispatchEvent(new Event('archive:loaded'));
  };
  const choose = next => {
    category = next;
    history.replaceState(null, '', category === 'all' ? location.pathname : `#${category}`);
    update();
  };
  form.addEventListener('submit', event => event.preventDefault());
  query.addEventListener('input', update);
  select.addEventListener('change', () => choose(select.value));
  form.addEventListener('reset', () => requestAnimationFrame(() => choose('all')));
  tabs.forEach(tab => tab.addEventListener('click', () => choose(tab.dataset.category)));
  window.addEventListener('hashchange', () => { category = fromHash(); update(); });
  update();
  form.hidden = false;
  document.querySelector('[data-notes-tabs]').hidden = false;
})();

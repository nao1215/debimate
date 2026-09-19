import * as params from '@params';

let fuse;
const resultList = document.getElementById('searchResults');
const searchInput = document.getElementById('searchInput');
const searchStatus = document.getElementById('searchStatus');
let first;
let last;
let currentElement = null;
let resultsAvailable = false;

function escapeHtml(value) {
  const element = document.createElement('span');
  element.textContent = value;
  return element.innerHTML;
}

function plainText(value) {
  const template = document.createElement('template');
  template.innerHTML = value || '';
  return (template.content.textContent || '').replace(/\s+/g, ' ').trim();
}

function truncate(value, limit = 150) {
  return value.length > limit ? `${value.slice(0, limit).trim()}…` : value;
}

function setStatus(message) {
  searchStatus.textContent = message;
}

function renderResults() {
  const query = searchInput.value.trim();
  resultList.innerHTML = '';
  resultsAvailable = false;

  if (!query) {
    setStatus('キーワードを入力すると、最大20件の候補を表示します。');
    return;
  }
  if (!fuse) {
    setStatus('検索データを読み込んでいます…');
    return;
  }

  const options = params.fuseOpts ? {limit: params.fuseOpts.limit} : undefined;
  const results = options ? fuse.search(query, options) : fuse.search(query);
  if (results.length === 0) {
    setStatus(`「${query}」に一致するページはありませんでした。`);
    return;
  }

  resultList.innerHTML = results.map(({item}) => {
    const title = escapeHtml(item.title);
    const summary = escapeHtml(truncate(plainText(item.summary || item.content)));
    const permalink = escapeHtml(item.permalink);
    return `<li class="post-entry search-result">
      <a class="search-result-link" href="${permalink}" aria-label="${title}">
        <span class="search-result-title">${title}<span aria-hidden="true">→</span></span>
        ${summary ? `<span class="search-result-summary">${summary}</span>` : ''}
      </a>
    </li>`;
  }).join('');

  setStatus(`「${query}」の検索結果: ${results.length}件`);
  resultsAvailable = true;
  first = resultList.firstElementChild;
  last = resultList.lastElementChild;
}

function searchOptions() {
  const defaults = {
    distance: 100,
    threshold: 0.4,
    ignoreLocation: true,
    keys: ['title', 'permalink', 'summary', 'content']
  };
  if (!params.fuseOpts) return defaults;
  return {
    isCaseSensitive: params.fuseOpts.iscasesensitive ?? false,
    includeScore: params.fuseOpts.includescore ?? false,
    includeMatches: params.fuseOpts.includematches ?? false,
    minMatchCharLength: params.fuseOpts.minmatchcharlength ?? 1,
    shouldSort: params.fuseOpts.shouldsort ?? true,
    findAllMatches: params.fuseOpts.findallmatches ?? false,
    keys: params.fuseOpts.keys ?? defaults.keys,
    location: params.fuseOpts.location ?? 0,
    threshold: params.fuseOpts.threshold ?? 0.4,
    distance: params.fuseOpts.distance ?? 100,
    ignoreLocation: params.fuseOpts.ignorelocation ?? true
  };
}

window.addEventListener('load', async () => {
  try {
    const response = await fetch('../index.json');
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    fuse = new Fuse(await response.json(), searchOptions());
    renderResults();
  } catch (error) {
    console.error(error);
    setStatus('検索データを読み込めませんでした。時間をおいて再度お試しください。');
  }
});

searchInput.addEventListener('input', renderResults);

function focusResult(item) {
  document.querySelectorAll('#searchResults .focus').forEach((element) => {
    element.classList.remove('focus');
  });
  if (!item) {
    searchInput.focus();
    currentElement = null;
    return;
  }
  item.classList.add('focus');
  currentElement = item.querySelector('a');
  currentElement.focus();
}

document.addEventListener('keydown', (event) => {
  const active = document.activeElement;
  const insideSearch = document.getElementById('searchbox')?.contains(active) ||
    document.querySelector('.search-panel')?.contains(active) || resultList.contains(active);

  if (event.key === 'Escape' && insideSearch) {
    searchInput.value = '';
    renderResults();
    focusResult(null);
    return;
  }
  if (!resultsAvailable || !insideSearch) return;

  if (event.key === 'Enter' && active === searchInput) {
    event.preventDefault();
    first.querySelector('a').click();
  } else if (event.key === 'ArrowDown') {
    event.preventDefault();
    const item = active === searchInput ? first : active.closest('li')?.nextElementSibling;
    focusResult(item || last);
  } else if (event.key === 'ArrowUp') {
    event.preventDefault();
    const item = active.closest('li')?.previousElementSibling;
    focusResult(item);
  }
});

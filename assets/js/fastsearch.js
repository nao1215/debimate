// サイト内検索。/index.json（layouts/_default/index.json）を読み、部分一致で絞り込む。
//
// 以前は Fuse.js の曖昧検索を使っていたが、日本語では「なぜ当たったのか」が
// 分からない結果が混ざり、閾値を絞っても順位の理由を説明できなかった。
// 今は空白区切りの語をすべて含むレコードだけを残し、次の順に並べる。
//
//   1. タイトル完全一致
//   2. タイトル部分一致
//   3. 見出し一致（技術ノートの h2/h3）
//   4. 本文一致
//   同点なら 記事 → 技術ノート → Weeknotes の順、その中で新しい順
//   （Weeknotes は記事の周辺話を書くことが多く、元の記事より上に来ると遠回りになる）
const LIMIT = 30;
const SNIPPET_BEFORE = 40;
const SNIPPET_AFTER = 90;
const TYPE_LABELS = {
  post: '記事',
  weeknotes: 'Weeknotes',
  note: '技術ノート',
  page: 'ページ'
};
const TYPE_ORDER = {post: 0, note: 1, weeknotes: 2, page: 3};

let records;
const resultList = document.getElementById('searchResults');
const searchInput = document.getElementById('searchInput');
const searchStatus = document.getElementById('searchStatus');
let first;
let last;
let resultsAvailable = false;

// 全角英数と半角カナの揺れを吸収し、大文字小文字を区別しない
function normalize(value) {
  return (value || '').normalize('NFKC').toLowerCase();
}

function escapeHtml(value) {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function prepare(item) {
  const headings = item.headings || [];
  return {
    ...item,
    headings,
    key: {
      title: normalize(item.title),
      headings: headings.map(normalize),
      content: normalize(item.content)
    }
  };
}

function includesAll(text, terms) {
  return terms.every((term) => text.includes(term));
}

// 小さいほど上位。どこにも無い語があれば null
function rank(record, query, terms) {
  const {key} = record;
  const everywhere = [key.title, ...key.headings, key.content].join('\n');
  if (!includesAll(everywhere, terms)) return null;
  if (key.title === query) return 0;
  if (includesAll(key.title, terms)) return 1;
  if (includesAll([key.title, ...key.headings].join('\n'), terms)) return 2;
  return 3;
}

// text 中で terms のいずれかに当たる範囲を、重なりをまとめて返す
function matchRanges(text, terms) {
  const lower = text.toLowerCase();
  const ranges = [];
  for (const term of terms) {
    let from = 0;
    while (term) {
      const at = lower.indexOf(term, from);
      if (at < 0) break;
      ranges.push([at, at + term.length]);
      from = at + term.length;
    }
  }
  ranges.sort((a, b) => a[0] - b[0]);
  const merged = [];
  for (const range of ranges) {
    const tail = merged[merged.length - 1];
    if (tail && range[0] <= tail[1]) tail[1] = Math.max(tail[1], range[1]);
    else merged.push([...range]);
  }
  return merged;
}

function highlight(text, terms) {
  let html = '';
  let cursor = 0;
  for (const [start, end] of matchRanges(text, terms)) {
    html += escapeHtml(text.slice(cursor, start));
    html += `<mark>${escapeHtml(text.slice(start, end))}</mark>`;
    cursor = end;
  }
  return html + escapeHtml(text.slice(cursor));
}

// 最初に当たった語の周辺を切り出す。本文に無ければ冒頭を出す
function snippet(content, terms) {
  const [hit] = matchRanges(content, terms);
  const center = hit ? hit[0] : 0;
  const start = Math.max(0, center - SNIPPET_BEFORE);
  const end = Math.min(content.length, center + SNIPPET_AFTER);
  const head = start > 0 ? '…' : '';
  const tail = end < content.length ? '…' : '';
  return head + highlight(content.slice(start, end).trim(), terms) + tail;
}

function matchedHeading(record, terms) {
  const index = record.key.headings.findIndex((heading) => terms.some((term) => heading.includes(term)));
  return index < 0 ? '' : record.headings[index];
}

function formatDate(value) {
  const [year, month, day] = (value || '').split('-').map(Number);
  return year ? `${year}年${month}月${day}日` : '';
}

function meta(record) {
  if (record.type === 'weeknotes') return escapeHtml(record.parent_title);
  return [record.parent_title, formatDate(record.date)].filter(Boolean).map(escapeHtml).join(' · ');
}

function renderRecord(record, terms) {
  const heading = matchedHeading(record, terms);
  const label = TYPE_LABELS[record.type] || TYPE_LABELS.page;
  return `<li class="post-entry search-result">
    <a class="search-result-link" href="${escapeHtml(record.url)}">
      <span class="search-result-meta">
        <span class="search-result-badge search-result-badge-${escapeHtml(record.type)}">${label}</span>
        <span>${meta(record)}</span>
      </span>
      <span class="search-result-title">${highlight(record.title, terms)}</span>
      ${heading ? `<span class="search-result-heading">見出し: ${highlight(heading, terms)}</span>` : ''}
      <span class="search-result-summary">${snippet(record.content || '', terms)}</span>
    </a>
  </li>`;
}

function search(value) {
  const query = normalize(value).replace(/\s+/g, ' ').trim();
  const terms = [...new Set(query.split(' ').filter(Boolean))];
  const hits = [];
  for (const record of records) {
    const score = rank(record, query, terms);
    if (score !== null) hits.push({record, score});
  }
  hits.sort((a, b) => a.score - b.score ||
    (TYPE_ORDER[a.record.type] ?? 3) - (TYPE_ORDER[b.record.type] ?? 3) ||
    b.record.date.localeCompare(a.record.date));
  return {terms, hits};
}

function setStatus(message) {
  searchStatus.textContent = message;
}

function renderResults() {
  const input = searchInput.value.trim();
  resultList.innerHTML = '';
  resultsAvailable = false;

  if (!input) {
    setStatus(`キーワードを入力すると、最大${LIMIT}件の候補を表示します。`);
    return;
  }
  if (!records) {
    setStatus('検索データを読み込んでいます…');
    return;
  }

  const {terms, hits} = search(input);
  if (hits.length === 0) {
    setStatus(`「${input}」に一致するページはありませんでした。`);
    return;
  }

  resultList.innerHTML = hits.slice(0, LIMIT).map(({record}) => renderRecord(record, terms)).join('');
  setStatus(hits.length > LIMIT
    ? `「${input}」の検索結果: ${hits.length}件（上位${LIMIT}件を表示）`
    : `「${input}」の検索結果: ${hits.length}件`);
  resultsAvailable = true;
  first = resultList.firstElementChild;
  last = resultList.lastElementChild;
}

window.addEventListener('load', async () => {
  try {
    const response = await fetch('../index.json');
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    records = (await response.json()).map(prepare);
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
    return;
  }
  item.classList.add('focus');
  item.querySelector('a').focus();
}

document.addEventListener('keydown', (event) => {
  // IME で変換中の Enter（確定）・矢印（候補選択）・Esc（取消）は IME に任せる。
  // ここで拾うと、確定の Enter で先頭の結果へ飛び、矢印で入力欄からフォーカスが外れる。
  // keyCode 229 は isComposing を立てない古い Safari 向け
  if (event.isComposing || event.keyCode === 229) return;

  const active = document.activeElement;
  const insideSearch = document.querySelector('.search-panel').contains(active) ||
    resultList.contains(active);

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

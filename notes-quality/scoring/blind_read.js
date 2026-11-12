export const meta = {
  name: 'blind-read-score3',
  description: 'Blind reader impressions of the remaining score-3 debimate notes (3 notes + 1 anchor per agent, 2 agents at a time)',
  phases: [{ title: 'Read' }],
}
const ROOT = '/home/nao/ghq/github.com/nao1215/debimate/'
const targets = args.targets
const anchors = ['content/notes/software-architecture/sidecar/index.md', 'projects/ml/notes/math/information-theory/index.md']
const chunks = []
for (let i = 0; i < targets.length; i += 3) chunks.push(targets.slice(i, i + 3))
const SCHEMA = {
  type: 'object',
  properties: {
    notes: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          path: { type: 'string' },
          impression: { type: 'string', description: '率直な感想 3〜5 文。何が記憶に残ったか、他のネット記事と比べて読む価値があるか' },
          stop_points: { type: 'string', description: '読むのをやめたくなった地点（行番号と理由）。無ければ「無し」' },
          errors: { type: 'array', items: { type: 'string' }, description: '誤り・古い情報・根拠の無い主張の疑い。行番号・何が誤りか・正しくはどうか。無ければ空' },
          english_figures: { type: 'boolean', description: '図の文字が英語のままか' },
          buried_best: { type: 'string', description: '一番面白い実験・事故・数値と、それが記事のどこにあるか（埋もれているか）' },
          embarrass: { type: 'string', enum: ['困る', '少し気になる', '困らない'] },
          urgency: { type: 'string', enum: ['高', '中', '低'] },
          overall: { type: 'integer', minimum: 1, maximum: 5 },
        },
        required: ['path', 'impression', 'stop_points', 'errors', 'english_figures', 'buried_best', 'embarrass', 'urgency', 'overall'],
      },
    },
    ranking: { type: 'string', description: '4 本を良い順に。一番良いノートと比べて他に足りないもの 2〜3 行' },
  },
  required: ['notes', 'ranking'],
}
function prompt(chunk, idx) {
  const anchor = anchors[idx % 2]
  const list = [...chunk]
  list.splice(idx % (chunk.length + 1), 0, anchor)
  return `あなたは技術ブログ debimate.jp の読者役です。Web と DB の経験はあるエンジニアですが、各ノートの分野は詳しくありません。リポジトリのファイルは編集・作成しないでください（読むだけ）。git log や採点ファイル（notes-quality/、.note-review/ の既存ファイル）は見ないでください。先入観無しの感想が欲しいからです。SVG を PNG に変えて見る時など作業用のファイルは ${ROOT}.note-review/work/blind/tmp${idx}/ にだけ置いてください（/tmp は使わない）。

次の ${list.length} 本の技術ノートを、それぞれ上から順に全部読んでください（Markdown の原稿。図は同じディレクトリか images/ にあり、WebP は Read で見られます。主要な図は何枚か実際に見てください）。
${list.map((p, i) => `${i + 1}. ${ROOT}${p}`).join('\n')}

誤りの疑いは、自分の知識で確かめられる範囲で具体的に（行番号・何が誤りか・正しくはどうか）。疑いが弱いものは「疑い」と書く。無ければ空にする。
各ノートを StructuredOutput の notes に 1 件ずつ入れてください（path はリポジトリからの相対パス）。日本語で。`
}
phase('Read')
const results = []
for (let i = 0; i < chunks.length; i += 2) {
  const batch = chunks.slice(i, i + 2)
  const r = await parallel(batch.map((c, j) => () => agent(prompt(c, i + j), { label: `read:${c.map(p => p.split('/')[p.split('/').length - 2]).join(',')}`, phase: 'Read', schema: SCHEMA })))
  results.push(...r.filter(Boolean))
  log(`${Math.min(i + 2, chunks.length)}/${chunks.length} 組`)
}
return results
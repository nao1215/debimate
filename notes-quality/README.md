# notes-quality

技術ノート（`content/notes`）と ML ノート（`projects/ml/notes`）の書き方の基準と、それを守らせる関門です。ブログ記事（`content/post`）と weeknotes は対象外です。

## 何が止まるか

- commit（`hooks/pre-commit`）: 変えたノートが規則を満たさない時。新規と大きな改稿は全部の規則、小さな修正は足した行だけを見ます。
- push（`hooks/pre-push`）と GitHub Actions（`deploy.yml` の notes-gate）: 上に加え、新規と大きな改稿のノートに総合 4 以上の点の記録（`scores/<区分>__<スラッグ>.json`）が無い時。点を付けた版から 5 行より多く足していれば、採点し直しが要ります。CI で止まるとビルドとデプロイも止まります。

新しい環境では、最初に次を 1 回実行します。

```sh
git config core.hooksPath notes-quality/hooks
```

## 中身

| パス | 役割 |
|---|---|
| `gate.py` | 関門の本体。`note`・`commit`・`push`・`score`・`record` |
| `check_note.py`、`style_check.sh`、`textruns.py`、`name_drift.py` | 機械で見られる規則（太字、「を、」、表記、括弧、区切り、図の形式、文字だけの区間） |
| `author_grep.sh`、`build_vocab.py` | 本人の実文（`content/post/ja` と `content/weeknotes`）で語を照合する |
| `drift_words.tsv` | 本人の実文にほとんど無く、ノートで使わない語 |
| `style/` | 文体・語彙・本人の用例 |
| `completion_checklist.md`、`checklists/` | 完了のチェックリストの雛形と、ノートごとに埋めたもの |
| `opening_log.tsv` | 書いた順の冒頭の型と題の形。直前の 3 本と同じ型を続けないために使う |
| `scoring/` | 採点の物差し（`rubric.md`）、決定の記録（`decisions.md`）、抜き出しの作り方、基準の 5 本の抜き出し |
| `scores/` | ノートごとの総合点と、点を付けた版（git の blob） |

規則を変える時は、先に `scoring/decisions.md` に日付と著者の言葉を書きます。機械で判定できる規則は `gate.py` か `drift_words.tsv` に、判定できない規則は `style/` に足します。

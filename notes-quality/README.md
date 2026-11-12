# notes-quality

技術ノート（`content/notes`）と ML ノート（`projects/ml/notes`）の書き方の基準と、それを守らせる関門です。ブログ記事（`content/post`）と weeknotes は対象外です。

## 何が止まるか

- commit（`hooks/pre-commit`）: 変えたノートが規則を満たさない時。新規と大きな改稿は全部の規則、小さな修正は足した行だけを見ます。小さな修正でも、見出しを変えたら他のノートからの `#見出し` リンクが切れないかを見ます。glossary.tsv の訳語を置き換えて古い語が同じノートに残る時は、止めずに知らせます。
- push（`hooks/pre-push`）: 上に加え、新規と大きな改稿のノートに、別の担当が基準の 5 本と一緒に付けた総合 4 以上の点の記録（`scores/<区分>__<スラッグ>.json`）が無い時。点を付けた版から 5 行より多く足していれば、採点し直しが要ります。
- GitHub Actions（`deploy.yml` の notes-gate）: pre-push と同じ範囲（今回の push の分）を同じ基準で見ます。hook を飛ばした push に気づくためのもので、NG のノートは警告を出すだけです。デプロイは止めず、古い版にも戻しません。
- 記事（`content/post`）・weeknotes だけの commit と push では、どの hook も何もしません。

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
| `review_cache.py`、`reviews/` | 精読の記録（debimate-note-review スキル）。記事ごとの判断と、確認した時の git の版。2026-11-12 に SQLite から移した |

規則を変える時は、先に `scoring/decisions.md` に日付と著者の言葉を書きます。機械で判定できる規則は `gate.py` か `drift_words.tsv` に、判定できない規則は `style/` に足します。

## 自動で作り直すもの

GitHub Actions の `.github/workflows/style-refresh.yml` が週 1 回（日曜 9:00）`refresh_style.py` を走らせ、次を作り直して、変わっていれば main に commit します。文体はすぐには変わらないので、ノートの commit では作り直しません。`style/variant_groups.tsv` を変えた時は、手で `python3 notes-quality/refresh_style.py` を走らせるか、workflow を手動で動かします。手で書き足しません。

- `style/variants.tsv`: 表記・語の揺れ（`style/variant_groups.tsv` の組）を、2023 年以降の本人の技術記事と weeknotes で数えたもの。本人の使用が 5% 未満の形は関門で NG になります。
- `style/vocabulary.md`: 本人の実文とノートの言い回しの差。
- `style/corpus.sha256`: 学習に使う技術記事のハッシュ。

omokage のプロファイルは git に入れず、`omokage_check.py` が技術記事の変化を見て `~/.cache/debimate-omokage/` に作り直します（初回 1 分ほど）。関門は一致度 85% 未満を NG にします。omokage が無い環境（CI）ではこの判定を飛ばします。非技術記事と LLM が書いた記事は `style/corpus_nontechnical.txt` と `style/corpus_llm_written.txt` に足して学習から外します。

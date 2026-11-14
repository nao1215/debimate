# Snapshot Testing のノートの実験

ノート: https://debimate.jp/notes/software-testing/snapshot-testing/

## 1. markdown の Mermaid を golden に固定する（exp_flowchart.sh）

`flowchart/` は、github.com/nao1215/markdown で流れ図を作り、`testdata/deploy.mmd` と比べる golden テストです。
`UPDATE_GOLDEN=1 go test ./...` で golden を書き直し、付けなければ比べます。

`exp_flowchart.sh` は、markdown v0.13.0 と v1.0.0 のそれぞれで golden を書き、`go test -count=3` を回し、
`render/render.mjs` で mermaid に描かせます。結果は `output/flowchart.txt` と `output/deploy-*.png` です。

render.mjs は mermaid 11.16.1 と puppeteer 25.6.0 を使います。node_modules を置いたディレクトリを引数に渡します。

```sh
mkdir -p /path/to/render && cd /path/to/render
npm init -y && npm pkg set type=module
npm install mermaid@11.16.1 puppeteer@25.6.0
cd -
./exp_flowchart.sh /path/to/render
```

## 2. atago の正規化（exp_atago.sh）

`specs/` の 5 つの spec を、atago v0.4.2 と v0.26.1 で、golden を書く実行（record）と比べる実行（verify）に分けて回します。
HOME を変えて、golden を書いた機械と比べる機械が違う場合を作ります。結果は `output/atago.txt` です。

```sh
./exp_atago.sh /path/to/workdir
```

- root: ホームが / の時に、全ての / が ~ になるか
- home: ホームが /home/nao の時に、/home/naoki が ~ki になるか
- crlf: 行末の \r\r\n で、更新の直後に落ちるか
- secret: 秘密の途中にエスケープがある時に、秘密が golden に残るか
- timestamp: マスクした時刻が 1970 年に変わっても通るか

環境は `output/environment.txt` にあります。

## 3. markdown の描画の検査に掛ける

markdown の CI（DocRender）が使う `scripts/mermaid-check/check.mjs` に、1 の 2 つの golden を Markdown の mermaid ブロックとして渡した結果が `output/docrender_check.txt` です。どちらも 0 failed で、v0.13.0 の出力も通ります。

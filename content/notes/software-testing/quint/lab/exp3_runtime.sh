#!/usr/bin/env bash
# 実験 3: Quint が何を落とし、何を要るか。空の HOME で、npm 版と単体の実行ファイルを試す。
# 要るもの: Node 18 以上と npm、gh（単体の実行ファイルを落とす）、JDK 17 と JDK 21（mise で切り替える）
set -u
cd "$(dirname "$0")"
W="${WORK:-$PWD/.runtime}"; rm -rf "$W"; mkdir -p "$W/home" "$W/npm"
# HOME を空にすると mise が設定を見失うので、JDK の場所は先に引く
J17="$(mise where java@17)"; J21="$(mise where java@temurin-21)"
{
  echo "== npm install @informalsystems/quint@0.33.1"
  (cd "$W/npm" && npm init -y >/dev/null && npm install --silent @informalsystems/quint@0.33.1 >/dev/null 2>&1)
  echo "node_modules: $(du -sh "$W/npm/node_modules" | cut -f1), packages: $(cd "$W/npm" && npm ls --all --parseable 2>/dev/null | tail -n +2 | wc -l)"
  echo "== standalone binary"
  gh release download v0.33.1 --repo quint-co/quint -p quint-linux-amd64 -D "$W" --clobber
  chmod +x "$W/quint-linux-amd64"; echo "quint-linux-amd64: $(du -h "$W/quint-linux-amd64" | cut -f1)"
  # /usr/bin に node がある環境でも外せるよう、/usr/bin と /bin から node・npm・npx だけを除いた
  # ディレクトリを PATH にする（tar などの外部コマンドは残す）。空の PATH で回した時の結果も残す
  mkdir -p "$W/emptybin" "$W/nonode"
  for f in /usr/bin/* /bin/*; do
    case "$(basename "$f")" in node|npm|npx|nodejs|corepack) continue ;; esac
    [ -e "$W/nonode/$(basename "$f")" ] || ln -s "$f" "$W/nonode/$(basename "$f")"
  done
  echo "== quint run with an empty PATH"
  env -i HOME="$W/home0" PATH="$W/emptybin" "$W/quint-linux-amd64" run save.qnt --main=rollback --invariant=atomic --max-samples=1000 2>&1 | grep -oE 'Command failed: [a-z]+' | head -1
  rm -rf "$W/home0"
  B="env -i HOME=$W/home PATH=$W/nonode $W/quint-linux-amd64"
  echo "== node on PATH: $(env -i PATH=$W/nonode sh -c 'command -v node || echo none')"
  echo "== first quint run without node (HOME is empty)"
  $B run save.qnt --main=rollback --invariant=atomic --max-samples=1000 2>&1 | grep -E '^\[|error'
  echo "downloaded: $(ls "$W/home/.quint")  $(du -sh "$W/home/.quint"/* | cut -f1)"
  echo "== quint verify without java"
  $B verify save.qnt --main=touched --invariant=atomic --max-steps=6 2>&1 | grep -E 'Downloading|java|^\[' | head -3
  echo "downloaded: $(ls "$W/home/.quint" | tr '\n' ' ') $(du -sh "$W/home/.quint"/apalache* | cut -f1)"
  echo "== quint verify with JDK 17"
  env -i HOME="$W/home" PATH="$J17/bin:$W/nonode" "$W/quint-linux-amd64" verify save.qnt --main=touched --invariant=atomic --max-steps=6 2>&1 | grep -E 'Error|UnsupportedClassVersion|^\[' | head -2
  echo "== quint verify with JDK 21"
  env -i HOME="$W/home" PATH="$J21/bin:$W/nonode" "$W/quint-linux-amd64" verify save.qnt --main=touched --invariant=atomic --max-steps=6 2>&1 | grep -E '^\[' | head -1
} 2>&1 | tee output/exp3_runtime.txt
rm -rf "$W" _apalache-out

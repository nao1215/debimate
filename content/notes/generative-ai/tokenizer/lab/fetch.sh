#!/bin/sh
# トークナイザーのファイルだけを取得する（モデルの重みは取得しない）。
# 使い方: sh fetch.sh <保存先>
set -eu
D=${1:?保存先のディレクトリを指定する}
mkdir -p "$D/qwen3" "$D/llmjp3" "$D/tiktoken"
# Qwen3（Qwen/Qwen3-4B、revision 1cfa9a7208912126459214e8b04321603b3df60c）
curl -sSL -o "$D/qwen3/tokenizer.json" \
  https://huggingface.co/Qwen/Qwen3-4B/resolve/1cfa9a7208912126459214e8b04321603b3df60c/tokenizer.json
# LLM-jp-3（llm-jp/llm-jp-3-1.8b、revision 60acda32e07c72b82ce5a73d60b21b3d65e0c810）
curl -sSL -o "$D/llmjp3/tokenizer.json" \
  https://huggingface.co/llm-jp/llm-jp-3-1.8b/resolve/60acda32e07c72b82ce5a73d60b21b3d65e0c810/tokenizer.json
# tiktoken はこの置き場所をキャッシュとして使い、無ければ自分で取得してハッシュを検証する
echo "TIKTOKEN_CACHE_DIR=$D/tiktoken"
sha256sum "$D/qwen3/tokenizer.json" "$D/llmjp3/tokenizer.json"

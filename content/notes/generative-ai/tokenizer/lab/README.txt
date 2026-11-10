Tokenizer ノートの実験ファイル

texts.py が、2 つの実験で使う文（Wallet ノート冒頭の 2 文、本記事で作った英訳、
Python のコード、数字、絵文字）を持つ。英訳は本記事のために作ったもので、
公式の訳ではない。

実験 1: 小さな BPE を学習する（bpe_train.py）
--------------------------------------------
  Python 3.8 以降の標準ライブラリだけで動く。学習用の文章は、debimate の
  コミット 9bbbeb23 の Wallet ノート（37,097 文字、67,916 バイト）。

    git show 9bbbeb23:content/notes/blockchain-systems/wallet/index.md > wallet.md
    python3 bpe_train.py wallet.md bpe.json

  - バイト単位（最初の記号は 256 種類）で 1,000 回結合する
  - 同じ回数の組が複数ある時は、記号の番号が小さい組を選ぶので、結果は毎回同じ
  - 表示は output_bpe.txt。bpe.json は figures.py がグラフに使う
  - 手元（負荷の高いマシン）で 7 秒前後

実験 2: 公開トークナイザーでトークン数を数える（count_tokens.py）
----------------------------------------------------------------
  取得するのはトークナイザーのファイルだけで、モデルの重みは取得しない。

    sh fetch.sh <保存先>
    TIKTOKEN_CACHE_DIR=<保存先>/tiktoken \
      uv run --with tiktoken==0.12.0 --with tokenizers==0.22.1 \
      python count_tokens.py <保存先> counts.json

  - 確認した版: uv 0.9.7、Python 3.14.4、tiktoken 0.12.0、tokenizers 0.22.1
  - o200k_base / cl100k_base: tiktoken が初回に openaipublic.blob.core.windows.net
    から取得し、SHA-256 を検証してキャッシュする
      o200k_base.tiktoken  446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d
      cl100k_base.tiktoken 223921b76ee99bde995b7ff738513eef100fb51d18c93597a113bcffe865b2a7
  - Qwen3: Qwen/Qwen3-4B の tokenizer.json（revision 1cfa9a72...）
      SHA-256 aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4
  - LLM-jp-3: llm-jp/llm-jp-3-1.8b の tokenizer.json（revision 60acda32...）
      SHA-256 955dc1fa623fab38cc92a3f4ee172423ae6d73201c4207569bfdf5626bc733f0
  - 先頭の <s> などの特殊トークンは数えない（add_special_tokens=False）。
    LLM-jp-3 は文頭に空白の記号（▁）を足すので、その分は数に入る
  - 表示は output_count.txt。counts.json は figures.py が図に使う

図の再生成
----------
  cd .. && uv run --with matplotlib python figures.py

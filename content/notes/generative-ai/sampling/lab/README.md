# sampling の実験

- `sampling.py`: 説明用のロジットで、temperature と top-p ごとに 1 万回選んで数える（`output.txt`）。
- `nexttoken.py`: qwen3:8b に「今日の天気は」の続きを 1 トークン出させ、上位 10 個の確率を temperature 0.5・1.0・1.5 で取る（`output_nexttoken.txt`）。
- `repeat.py`: 同じ問いを 30 回ずつ送り、出力の種類を数える（`output_repeat.txt`）。直前に同じ問いを送っていたので、temperature 0 の 30 回は問いの計算を使い回した状態で始まっている。
- `reload.py`: モデルを `ollama stop` で外してから temperature 0 で 5 回送る、を 5 条件で繰り返す（`output_reload.txt`）。どの条件も 1 回目だけ別の出力になる。
- `cache.py`: 読み込み直後に A・A・A・B・A・A の順に送り、出力と `prompt_eval_duration` を並べる（`output_cache.txt`）。

前提: Ollama 0.22.1 を localhost:11434 で動かし、`qwen3:8b` を pull 済み。2026-11-11 に Ryzen AI MAX+ 395（Radeon 8060S、ROCm）で実行した。モデルは並列数 1（起動のログの `Parallel:1`）、Ollama 自身のエンジン（`--ollama-engine`）で読み込まれていた。

`ollama show --parameters` の結果（2026-11-11）:

- qwen3:8b: temperature 0.6、top_k 20、top_p 0.95、repeat_penalty 1
- qwen3-coder:30b: temperature 0.7、top_k 20、top_p 0.8、repeat_penalty 1.05
- hf.co/ggml-org/gpt-oss-20b-GGUF: サンプリングの値の指定なし（stop だけ）

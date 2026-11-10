"""金額が書かれていない文を、スキーマで縛って解かせる（値を作ってしまうかを見る）。

amount_yen を必須の整数にしたスキーマ（run.py の SCHEMA）、null も許すスキーマ、
null も許した上でプロンプトに「書かれていない項目は null」と足した場合（integer|null+ask）の 3 つで、同じ文を解かせる。

使い方:
    OLLAMA_HOST=127.0.0.1:11435 python3 missing.py <モデル>...
"""
import copy
import os
import sys

from run import PROMPT, SCHEMA, chat

TEXT = "佐藤花子さんから2025年6月1日に、先月の請求書について問い合わせの電話があった。"

NULLABLE = copy.deepcopy(SCHEMA)
NULLABLE["properties"]["amount_yen"] = {"type": ["integer", "null"]}
PROMPT_NULL = PROMPT.replace("\n\n文:", "\n文に書かれていない項目は null にしてください。\n\n文:")


def main():
    host = os.environ.get("OLLAMA_HOST", "127.0.0.1:11434")
    print(f"text: {TEXT}")
    for model in sys.argv[1:]:
        for name, schema, prompt in (("integer", SCHEMA, PROMPT),
                                     ("integer|null", NULLABLE, PROMPT),
                                     ("integer|null+ask", NULLABLE, PROMPT_NULL)):
            res = chat(host, model, TEXT, schema, prompt)
            out = " ".join(res["message"]["content"].split())  # 改行と字下げを詰めて 1 行で表示
            print(f"{model:<18} {name:<17} -> {out}")


if __name__ == "__main__":
    main()

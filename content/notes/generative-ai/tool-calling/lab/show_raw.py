"""/api/chat に送る JSON と、返ってくる JSON を 1 往復半だけ表示する。

使い方: OLLAMA_HOST=127.0.0.1:11435 python3 show_raw.py qwen3:8b
"""
import json
import sys

from agent import TOOLS, chat, run_tool

model = sys.argv[1]
tools = [TOOLS["get_weather"]]
messages = [{"role": "user", "content": "東京の今の気温は何度ですか。"}]
print("--- request (1)")
print(json.dumps({"model": model, "messages": messages, "tools": tools},
                 ensure_ascii=False, indent=2))

resp = chat(model, messages, tools, seed=1, think=False)
msg = resp["message"]
print("--- response (1): message")
print(json.dumps(msg, ensure_ascii=False, indent=2))

messages.append(msg)
for tc in msg.get("tool_calls", []):
    result = run_tool(tc["function"]["name"], tc["function"]["arguments"], {})
    messages.append({"role": "tool", "tool_name": tc["function"]["name"],
                     "content": json.dumps(result, ensure_ascii=False)})
print("--- request (2): appended messages")
print(json.dumps(messages[1:], ensure_ascii=False, indent=2))

resp = chat(model, messages, tools, seed=1, think=False)
print("--- response (2): message")
print(json.dumps(resp["message"], ensure_ascii=False, indent=2))

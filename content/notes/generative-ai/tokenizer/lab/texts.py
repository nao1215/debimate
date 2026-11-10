"""count_tokens.py と bpe_train.py が使う文。"""

# 日本語は debimate の Wallet ノート冒頭の 2 文。英語は本記事のために作った訳。
TEXTS = {
    "ja": "ウォレット（wallet）は、Bitcoin などの暗号資産を受け取り、残高を確認し、"
          "他の相手に送るためのソフトウェアです。PC やスマートフォンの画面で操作するタイプと、"
          "コマンドを入力して操作するタイプがあります。",
    "en": "A wallet is software for receiving crypto assets such as Bitcoin, checking "
          "the balance, and sending them to others. Some wallets are operated on the "
          "screen of a PC or smartphone, and others by typing commands.",
    # LoRA ノートの lab/count_params.py の関数
    "code": 'def read_header(path):\n'
            '    with open(path, "rb") as f:\n'
            '        (length,) = struct.unpack("<Q", f.read(8))\n'
            '        header = json.loads(f.read(length))\n'
            '    metadata = header.pop("__metadata__", {})\n'
            '    return length, header, metadata\n',
    "digits": "2026-11-10 14:05:09 load average: 100.70, 226.82, 290.79 "
              "size 6938040682 bytes",
    "emoji": "👍 👍🏽 👨‍👩‍👧 🇯🇵 🦉",
}
# 冒頭の図に使う短い文（区切りの位置を出力する）
SHORT = {"ja": "秘密鍵を安全に保管する", "en": "Store the private key safely",
         "digits": "6938040682", "emoji": "👍🏽👨‍👩‍👧"}

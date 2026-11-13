# ACL なし: 4 か所が、決済サービスの status の文字列をそのまま読む。
# どの関数も、書いた時点（v1: PAID・PENDING・FAILED）の値で分岐を書き、最後に else を置いている。

def shipping(p):  # 出荷
    if p["status"] == "PAID":
        return "出荷する"
    elif p["status"] == "FAILED":
        return "取り消す"
    else:
        return "出荷を待つ"


def mail(p):  # 購入者へのメール
    if p["status"] == "PAID":
        return "お礼のメール"
    elif p["status"] == "FAILED":
        return "失敗のメール"
    else:
        return "入金案内のメール"


def sales(p):  # 売上の計上
    if p["status"] in ("PENDING", "FAILED"):
        return "計上しない"
    else:
        return "計上する"


def stock(p):  # 在庫の引当
    if p["status"] in ("PAID", "PENDING"):
        return "引当を保つ"
    else:
        return "引当を外す"

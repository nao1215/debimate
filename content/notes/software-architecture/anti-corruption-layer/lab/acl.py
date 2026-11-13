# ACL あり: 決済サービスの status を読むのは translate() だけ。
# 4 か所は、自分たちの語（PaymentState）だけで分岐する。
import enum
import logging

log = logging.getLogger("acl")


class PaymentState(enum.Enum):
    PAID = "支払済"
    AWAITING_DEPOSIT = "入金待ち"
    FAILED = "失敗"
    UNCONFIRMED = "確認中"  # 決済サービスから、意味の分からない値が来た


KNOWN = {
    "PAID": PaymentState.PAID,
    "PENDING": PaymentState.AWAITING_DEPOSIT,
    "FAILED": PaymentState.FAILED,
}


def translate_with_fallback(p):  # 版 B: 知らない値を、書いた時点の残りの値として読む
    return KNOWN.get(p["status"], PaymentState.AWAITING_DEPOSIT)


def translate(p):  # 版 C: 知らない値は「確認中」にして、記録を残す
    state = KNOWN.get(p["status"])
    if state is None:
        log.warning("知らない status: %r（payment_id=%s）", p["status"], p["payment_id"])
        return PaymentState.UNCONFIRMED
    return state


# 自分たちの語は 4 つで閉じているので、4 か所とも全ての状態を表に書く（else を置かない）。
ACTIONS = {
    #                              出荷          メール              売上          在庫
    PaymentState.PAID:             ("出荷する",   "お礼のメール",     "計上する",   "引当を保つ"),
    PaymentState.AWAITING_DEPOSIT: ("出荷を待つ", "入金案内のメール", "計上しない", "引当を保つ"),
    PaymentState.FAILED:           ("取り消す",   "失敗のメール",     "計上しない", "引当を外す"),
    PaymentState.UNCONFIRMED:      ("出荷を待つ", "送らない",         "計上しない", "引当を保つ"),
}


def shipping(s):
    return ACTIONS[s][0]


def mail(s):
    return ACTIONS[s][1]


def sales(s):
    return ACTIONS[s][2]


def stock(s):
    return ACTIONS[s][3]

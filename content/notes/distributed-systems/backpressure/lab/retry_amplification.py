"""各層が独立に再試行した時、最下層に届く試行回数の最大値を計算する。

前提: 1 回のユーザー操作が L 層を順に呼び出す。最下層が失敗し続け、
各層は下の層の失敗を受けるたびに再試行し、全ての試行が最下層まで届く。
"""


def worst_case(retries, layers):
    return (1 + retries) ** layers  # 1 層あたり 1 + retries 回呼ぶ


def retry_only_at_one_layer(retries):
    return 1 + retries  # 拒否した層の直上だけが再試行する


def with_budget(ratio, layers):
    # 単純化: SRE 本の 10% はクライアントごとの再試行の比率で、各層が要求数の
    # ratio 倍までしか再試行しないとみなして層の数だけ掛ける
    return (1 + ratio) ** layers  # 各層の再試行を要求数の ratio 倍までに抑える


print("layers  retry=1  retry=2  retry=3  one-layer(r=3)  budget10%")
for layers in range(1, 6):
    print(f"{layers:>6} {worst_case(1, layers):>8} {worst_case(2, layers):>8}"
          f" {worst_case(3, layers):>8} {retry_only_at_one_layer(3):>15}"
          f" {with_budget(0.1, layers):>10.2f}")

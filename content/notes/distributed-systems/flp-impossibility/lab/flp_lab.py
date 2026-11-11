"""FLP の筋書きを小さな合意プロトコルで再現する（FLP の厳密なモデルより単純化してある）。"""
import itertools
import random

N = 3  # プロセス数。1 台の停止に備え、自分を含めて N - 1 = 2 通を集めたら先に進む
OTHERS = [tuple(j for j in range(N) if j != i) for i in range(N)]
# 配送順の選び方: 各段階で、各プロセスが「自分以外の誰のメッセージを先に受け取るか」
SCHEDULES = list(itertools.product(itertools.product(*OTHERS), repeat=2))


def run_round(x, first1, first2):
    """1 ラウンドを進める。x は各プロセスの推定値。決めたプロセスと値も返す。"""
    # 段階 1: 推定値を交換する。先に届いた 2 通（自分の値を含む）が一致すれば提案、割れたら "?"
    proposal = [x[i] if x[i] == x[first1[i]] else "?" for i in range(N)]
    # 段階 2: 提案を交換する。2 通とも同じ値の提案なら決定する
    new_x, decided = [], {}
    for i in range(N):
        values = [v for v in (proposal[i], proposal[first2[i]]) if v != "?"]
        if len(values) == 2:
            decided[i] = values[0]
        new_x.append(values[0] if values else 0)  # 決め手が無ければ 0 に戻す（決定的な規則）
    return tuple(new_x), decided


def reachable_decisions(x):
    """状態 x から、配送順の選び方しだいで到達できる決定値の集合。"""
    found, seen, stack = set(), {x}, [x]
    while stack:
        state = stack.pop()
        for first1, first2 in SCHEDULES:
            nxt, decided = run_round(state, first1, first2)
            found |= set(decided.values())
            if not decided and nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return found


def check_agreement():
    """全ての状態と配送順で、違う値の決定が出ないこと、決定後は全員の推定値が揃うことを確かめる。"""
    for x in itertools.product((0, 1), repeat=N):
        for first1, first2 in SCHEDULES:
            nxt, decided = run_round(x, first1, first2)
            assert len(set(decided.values())) <= 1
            assert not decided or set(nxt) == set(decided.values())
    print(f"[check] agreement holds: {2 ** N} states x {len(SCHEDULES)} schedules")


def adversary(x, _rng):
    """決定を出さず、次の状態も bivalent に留まる配送順を選ぶ。"""
    for first1, first2 in SCHEDULES:
        nxt, decided = run_round(x, first1, first2)
        if not decided and reachable_decisions(nxt) == {0, 1}:
            return first1, first2
    raise RuntimeError("bivalent に留まる配送順が無い")


def fair_random(_x, rng):
    """遅れるメッセージをラウンドごとにランダムに選ぶ。"""
    return rng.choice(SCHEDULES)


def run(name, scheduler, x, rounds, seed=1, verbose=True):
    """全員が決めるか rounds に達するまで回す。decisions は {プロセス: (値, 決めたラウンド)}。"""
    rng, decisions = random.Random(seed), {}
    if verbose:
        print(f"[{name}] start x={x} reachable={sorted(reachable_decisions(x))}")
    for r in range(1, rounds + 1):
        x, decided = run_round(x, *scheduler(x, rng))
        for i, v in decided.items():
            decisions.setdefault(i, (v, r))
        if verbose and (r <= 3 or len(decisions) == N):
            print(f"  round {r}: x={x} decided={decisions}")
        if len(decisions) == N:
            break
    else:
        if verbose:
            print(f"  ... round {rounds}: x={x} decided={decisions} reachable={sorted(reachable_decisions(x))}")
    assert len({v for v, _ in decisions.values()}) <= 1, "agreement violated"
    return decisions


def timeout_vote(values, delay_ms, timeout_ms):
    """全員の値を待つが、timeout までに届かない相手は止まったと見なして多数決（同数なら小さい値）。"""
    print(f"[timeout] values={values} timeout={timeout_ms}ms")
    for i in range(N):
        heard = [values[i]] + [values[j] for j in OTHERS[i] if delay_ms[j][i] <= timeout_ms]
        suspected = [j for j in OTHERS[i] if delay_ms[j][i] > timeout_ms]
        decision = max(sorted(set(heard)), key=heard.count)
        print(f"  p{i}: heard={heard} suspected={suspected} -> decide {decision}")


if __name__ == "__main__":
    check_agreement()
    start = (0, 1, 1)
    run("fair", fair_random, start, rounds=50)
    results = [run("fair", fair_random, start, 50, seed, verbose=False) for seed in range(10000)]
    undecided = sum(len(d) < N for d in results)
    print(f"  10000 seeds: undecided={undecided} max_round={max(r for d in results for _, r in d.values())}")
    run("adversary", adversary, start, rounds=1000)
    # p2 のメッセージは p1 には 10ms で届くが、p0 には 150ms 掛かる。p2 は止まっていない
    delay = [[0, 10, 10], [10, 0, 10], [150, 10, 0]]  # delay[送信元][宛先]
    timeout_vote(start, delay, timeout_ms=100)

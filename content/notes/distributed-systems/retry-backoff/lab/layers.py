"""3 段の呼び出しの各段が 3 回まで試すと、最下段に何回届くかを数える。

frontend -> backend -> db の順に呼び、db は常に失敗する。
各段は下の段が失敗したら、合計 3 回（最初の 1 回 + 再試行 2 回）まで試す。
"""

calls = {"frontend": 0, "backend": 0, "db": 0}


def db():
    calls["db"] += 1
    raise ConnectionError("db is overloaded")


def with_retry(fn, attempts=3):
    def wrapper():
        for i in range(attempts):
            try:
                return fn()
            except ConnectionError:
                if i == attempts - 1:
                    raise
    return wrapper


def backend():
    calls["backend"] += 1
    return with_retry(db)()


def frontend():
    calls["frontend"] += 1
    return with_retry(backend)()


try:
    with_retry(frontend)()          # ユーザーの 1 回の操作
except ConnectionError:
    pass
print(calls)

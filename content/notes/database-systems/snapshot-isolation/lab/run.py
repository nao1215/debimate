"""条件付き引き出しを直列・並行で比較する。Python 3とDocker、postgres:17が必要。
python3 run.py : 外部ポート/永続ボリュームを使わず専用コンテナを最後に停止する。
"""
import subprocess
import time
import uuid

name = 'snapshot-lab-' + uuid.uuid4().hex[:10]

def docker(*args, **kwargs):
    return subprocess.run(['docker', *args], text=True, check=True, **kwargs)

class Session:
    def __init__(self):
        self.p = subprocess.Popen(['docker', 'exec', '-i', name, 'psql', '-X', '-Atq',
                                   '-v', 'ON_ERROR_STOP=1', '-U', 'postgres', '-h', '127.0.0.1'],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, text=True)

    def sql(self, sql):
        marker = 'end_' + uuid.uuid4().hex
        self.p.stdin.write(sql + "\nSELECT '" + marker + "';\n")
        self.p.stdin.flush()
        lines = []
        while True:
            line = self.p.stdout.readline()
            if not line:
                error = self.p.stderr.read()
                self.p.wait(timeout=10)
                raise RuntimeError(error.strip())
            if line.strip() == marker:
                return lines
            lines.append(line.strip())

    def close(self):
        if self.p.poll() is None:
            self.p.stdin.close()
            self.p.wait(timeout=10)
        self.p.stdout.close()
        self.p.stderr.close()


def scenario(label, isolation, parallel):
    admin = Session()
    a, b = Session(), Session()
    try:
        admin.sql("TRUNCATE accounts; INSERT INTO accounts VALUES ('x', 50), ('y', 50);")
        decisions, seen = [], []
        a.sql('BEGIN ISOLATION LEVEL ' + isolation + ';')
        first = int(a.sql('SELECT sum(balance) FROM accounts;')[0])
        if parallel:
            b.sql('BEGIN ISOLATION LEVEL ' + isolation + ';')
            second = int(b.sql('SELECT sum(balance) FROM accounts;')[0])
        # 同じアプリケーション規則: 合計が100以上なら100を引く。
        for i, (session, account) in enumerate([(a, 'x'), (b, 'y')]):
            if i == 1 and not parallel:
                b.sql('BEGIN ISOLATION LEVEL ' + isolation + ';')
                second = int(b.sql('SELECT sum(balance) FROM accounts;')[0])
            total = first if i == 0 else second
            seen.append(total)
            if total < 100:
                session.sql('ROLLBACK;')
                decisions.append('insufficient')
                continue
            try:
                session.sql("UPDATE accounts SET balance = balance - 100 WHERE id = '" + account + "'; COMMIT;")
                decisions.append('committed')
            except RuntimeError as error:
                if 'could not serialize access' not in str(error):
                    raise
                decisions.append('serialization_failure')
        final = int(admin.sql('SELECT sum(balance) FROM accounts;')[0])
        print(f'{label}: seen={seen}, decisions={decisions}, total={final}')
        expected = ([100, 0], ['committed', 'insufficient'], 0) if not parallel else (
            ([100, 100], ['committed', 'committed'], -100) if isolation == 'REPEATABLE READ'
            else ([100, 100], ['committed', 'serialization_failure'], 0))
        assert (seen, decisions, final) == expected
    finally:
        a.close(); b.close(); admin.close()

try:
    docker('run', '-d', '--rm', '--name', name, '--network', 'none',
           '--tmpfs', '/var/lib/postgresql/data', '-e', 'POSTGRES_HOST_AUTH_METHOD=trust',
           'postgres:17', stdout=subprocess.DEVNULL)
    for _ in range(60):
        ready = subprocess.run(['docker', 'exec', name, 'pg_isready', '-U', 'postgres', '-h', '127.0.0.1'],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if ready.returncode == 0:
            break
        time.sleep(0.5)
    else:
        raise RuntimeError('PostgreSQL did not become ready')
    admin = Session()
    try:
        print('PostgreSQL', admin.sql('SHOW server_version;')[0])
        admin.sql('CREATE TABLE accounts (id text PRIMARY KEY, balance integer NOT NULL);')
    finally:
        admin.close()
    scenario('serial RR', 'REPEATABLE READ', False)
    scenario('parallel RR', 'REPEATABLE READ', True)
    scenario('parallel SERIALIZABLE', 'SERIALIZABLE', True)
finally:
    subprocess.run(['docker', 'stop', name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

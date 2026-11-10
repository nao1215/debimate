同じアドレスの登録が同時に届いた時に、SELECT で確かめてから INSERT する方式で
何件のレコードが残るかを、一意制約の無い表とある表で数える実験。

再現手順（Docker と postgres:17 のイメージが必要。約 2 分）:

    ./run.sh > output.txt
    uv run --with matplotlib python ../figures.py   # images/unique-constraint_race.svg を作る

run.sh はコンテナ note-unique-constraint を起動し、ホストのポートは公開せずに
docker exec で操作し、終了時に削除する。

ファイル:
  setup.sql                     表 users_plain（一意制約なし）・users_unique（一意制約あり）と、
                                23505 を受け取って violations に記録する関数
  check_then_insert_*.sql       pgbench のスクリプト。各クライアントが user1, user2, ... の順に
                                SELECT count(*) → 0 件なら INSERT（自動コミット、READ COMMITTED）
  output.txt                    PostgreSQL 17.11、32 コアの Linux での結果

並行実行の結果なので、再実行で数値は少し変わる（2 回の実行で rows_per_email の差は
1 件あたり最大 1.7 件、ほとんどは 0.1 件程度）。一意制約のある表が常に 1.00 件で
重複 0 件になることは変わらない。

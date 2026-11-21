#!/bin/sh
# Envio HyperIndex の reorg 実験を回す。PostgreSQL と Hasura を Docker で立て、drive.py を実行し、最後に消す。
set -eu
cd "$(dirname "$0")"
F=${FOUNDRY:-$(dirname "$(command -v anvil)")}
SOLC=${SOLC:-solc}
(cd proj && npm ci --no-audit --no-fund)
docker network create indexer-note-envio-net
docker run -d --name indexer-note-envio-pg --network indexer-note-envio-net -p 127.0.0.1:15461:5432 \
  -e POSTGRES_PASSWORD=testing -e POSTGRES_USER=postgres -e POSTGRES_DB=envio-dev postgres:18
sleep 6
docker run -d --name indexer-note-envio-hasura --network indexer-note-envio-net -p 127.0.0.1:18831:8080 \
  -e HASURA_GRAPHQL_DATABASE_URL=postgres://postgres:testing@indexer-note-envio-pg:5432/envio-dev \
  -e HASURA_GRAPHQL_ENABLE_CONSOLE=false -e HASURA_GRAPHQL_ADMIN_SECRET=testing \
  -e HASURA_GRAPHQL_STRINGIFY_NUMERIC_TYPES=true -e HASURA_GRAPHQL_UNAUTHORIZED_ROLE=public \
  -e HASURA_GRAPHQL_NO_OF_RETRIES=10 hasura/graphql-engine:v2.43.0
until curl -sf http://127.0.0.1:18831/healthz >/dev/null; do sleep 1; done
ANVIL=$F/anvil SOLC=$SOLC python3 drive.py | tee output/drive.txt || true
docker rm -f indexer-note-envio-hasura indexer-note-envio-pg
docker network rm indexer-note-envio-net

# ==========================================================
# debimate Makefile — Hugo blog utilities
# ==========================================================

# デフォルトターゲット
.DEFAULT_GOAL := help

# サイト情報
HUGO := hugo
SERVER_PORT := 1313
BASE_URL := https://debimate.jp

# `make weekly 20260810` のように日付を位置引数で受け取る。
# Make は引数もターゲットとして実行しようとするため、日付を「何もしない
# ターゲット」として定義して握り潰す。weekly が最初のゴールの時だけ定義
# するのは、無条件の catch-all ルール (%:) にすると build を buld と
# 打ち間違えた時にエラーにならず黙って成功してしまうため
ifeq (weekly,$(firstword $(MAKECMDGOALS)))
WEEKLY_ARG := $(word 2,$(MAKECMDGOALS))
ifneq ($(WEEKLY_ARG),)
$(eval $(WEEKLY_ARG):;@:)
endif
endif

# ==========================================================
# タスク定義
# ==========================================================

help:  ## コマンド一覧を表示
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

serve: ## ローカル開発サーバ起動 (Draft/Future含む)
	$(HUGO) server -D -F --disableFastRender --port $(SERVER_PORT)

build: redirects ## 本番用ビルド（最小化あり）
	$(HUGO) --minify

weekly: ## 新しい週報を作成 (例: make weekly 20260810。省略時は今週の月曜)
	@set -eu; \
	arg="$(WEEKLY_ARG)"; \
	if [ -z "$$arg" ]; then \
	  arg="$$(date -d "-$$(( $$(date +%u) - 1 )) days" +%Y%m%d)"; \
	  echo "日付の指定がないので、今週の月曜 ($$arg) を使う"; \
	fi; \
	digits="$$(printf '%s' "$$arg" | tr -d '-')"; \
	case "$$digits" in \
	  [0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]) ;; \
	  *) echo "Usage: make weekly 20260810"; exit 1;; \
	esac; \
	slug="$$(printf '%s' "$$digits" | sed -E 's/^(.{4})(.{2})(.{2})$$/\1-\2-\3/')"; \
	if ! checked="$$(date -d "$$slug" +%Y-%m-%d)"; then echo "存在しない日付: $$slug"; exit 1; fi; \
	if [ "$$(date -d "$$slug" +%u)" != "1" ]; then \
	  echo "注意: $$slug は月曜ではない (既存の週報は全て月曜始まり)"; \
	fi; \
	$(HUGO) new "content/weekly/$$slug/index.md"

bbs: ## BBS のスレッド一覧を GitHub Discussions から取得して data/bbs.json を更新
	python3 scripts/fetch_bbs.py

redirects: ## 移行前URL向けのalias・リダイレクトを再生成
	python3 scripts/ensure_post_aliases.py
	python3 scripts/gen_legacy_redirects.py

redirects-check: ## 移行前URL向けのリダイレクトが最新か検証
	python3 scripts/ensure_post_aliases.py --check
	python3 scripts/gen_legacy_redirects.py --check

lint-links: ## サイト内リンク切れ・localhostリンクを検査（ビルドから実施）
	$(HUGO) --minify
	python3 scripts/check_links.py

lint-links-external: ## 外部リンク込みでmuffetを実行（403/429が出るので参考値）
	@command -v muffet >/dev/null || (echo "muffet が無い: go install github.com/raviqqe/muffet/v2@latest" && exit 1)
	$(HUGO) server --port $(SERVER_PORT) --bind 127.0.0.1 --renderToMemory & \
	  server=$$!; \
	  trap 'kill $$server' EXIT; \
	  until curl -sf -o /dev/null http://localhost:$(SERVER_PORT)/; do sleep 1; done; \
	  muffet -c 16 -t 20 http://localhost:$(SERVER_PORT)

clean: ## publicディレクトリ削除
	rm -rf public

new: ## 新しい記事を作成 (例: make new title="my-post-title")
	@test -n "$(title)" || (echo "Usage: make new title='my-post-title'" && exit 1)
	$(HUGO) new "content/post/$(title)/index.md"
	@echo "created: content/post/$(title)/index.md"

check: ## Front MatterのYAML構文を検証
	find content/post -name index.md -print0 | xargs -0 -n1 yq eval --front-matter extract '.' >/dev/null && echo "YAML OK"

deploy: build ## デプロイ実行（GitHub Actionsを利用）
	@git add .
	@git commit -m "chore: deploy $(shell date +'%Y-%m-%d %H:%M:%S')" || true
	@git push origin main
	@echo "Pushed to main. GitHub Pages will build automatically."

logs: ## デプロイジョブの最新ログを表示
	@gh run list --limit 1
	@gh run watch

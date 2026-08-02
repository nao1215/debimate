# ==========================================================
# debimate Makefile — Hugo blog utilities
# ==========================================================

# デフォルトターゲット
.DEFAULT_GOAL := help

# サイト情報
HUGO := hugo
SERVER_PORT := 1313
BASE_URL := https://debimate.jp

# ==========================================================
# タスク定義
# ==========================================================

help:  ## コマンド一覧を表示
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

serve: weekly-latest ## ローカル開発サーバ起動 (Draft/Future含む)
	$(HUGO) server -D -F --disableFastRender --port $(SERVER_PORT)

build: weekly-latest redirects ## 本番用ビルド（最小化あり）
	$(HUGO) --minify

weekly-latest: ## Top 用の最新週報リンクデータを生成
	python3 scripts/gen_weekly_latest.py

weekly-latest-check: ## Top 用の最新週報リンクデータが最新か検証
	python3 scripts/gen_weekly_latest.py --check

redirects: ## 移行前URL向けのalias・リダイレクトを再生成
	python3 scripts/ensure_post_aliases.py
	python3 scripts/gen_legacy_redirects.py

redirects-check: ## 移行前URL向けのリダイレクトが最新か検証
	python3 scripts/ensure_post_aliases.py --check
	python3 scripts/gen_legacy_redirects.py --check

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

---
title: "【GitHub Actions】 github/issue-metrics でPRマージにかかる時間を分析"
type: post
date: 2024-12-31
categories:
  - "linux"
tags:
  - "github-actions"
cover:
  image: images/issue-metrics-sample-output.png
  alt: "【GitHub Actions】 github/issue-metrics でPRマージにかかる時間を分析"
  hidden: false
images: ["images/issue-metrics-sample-output.png"]
---

## 前書き：PRマージに時間がかかっていた

2024年は、私のPull Request（PR）がなかなかマージできない課題がありました。

このように書くと「あなたが書いたPRのサイズが大きかったり、色々と他者に配慮できていないだけでは？」と考える人もいらっしゃるかもしれません。その可能性は当然あります。

認識のレベル感を合わせるために、前提を以下に示します。

- 私の作るPRサイズは50〜500行（プラス分のみ。テストコード、自動生成コードを含む）
- PR Descriptionには、実装背景や関連PRリンク、設計ドキュメントリンクを書く
- チームメンバ数は8名
- チーム内のPRは常時15〜20個近く溜まっており、自分は1日に2〜3個作る

最初は「若いメンバ多いからな」とボンヤリ考えていたのですが、キチンとデータを見て判断すべきだろうと考えました。実は、[Four Keys](https://book.impress.co.jp/books/1118101029)（ソフトウェア開発チームのパフォーマンスを測る指標）が流行った時にPR分析ツール（[nao1215/leadtime](https://github.com/nao1215/leadtime)）を作っていました。しかし、調査した結果、より優れたツールである[github/issue-metrics](https://github.com/github/issue-metrics?tab=readme-ov-file) がリリースされていました。めでたい。

本記事では、[github/issue-metrics](https://github.com/github/issue-metrics?tab=readme-ov-file) の導入方法を簡単に紹介します。殆ど公式のREADMEどおりです。

## github/issue-metricsの概要

github/issue-metricsは、GitHub Actionsであり、指定したリポジトリ内のIssue、Pull Request、Discussionに関するメトリクスを取得できます。一つのGitHub Actions workflowで、複数のリポジトリの情報を取得することもできます。

取得できるメトリクス配下のとおりです。

1. 作成から最初のコメント／レビューまでの期間（ドラフト期間は除外）
2. 作成からクローズするまでの期間（ドラフト期間は除外）
3. 作成から回答までの期間（Discussion only）
4. ラベル適用から削除までの期間
5. ドラフト期間（Pull Request only）

上記の期間は、PR作成者やボットからコメントした場合は、計測対象外となります。「他の人がアクション（コメント、レビュー、回答）するまでの時間」が計測されているようです。

以下に、[公式READMから引用したサンプルレポート](https://github.com/github/issue-metrics?tab=readme-ov-file#getting-started)を示します。

![](images/issue-metrics-sample-output.png)

## GitHub Actionsの作り方

[公式READMEに記載されているGitHub Actions workflowファイル](https://github.com/github/issue-metrics?tab=readme-ov-file#getting-started)を以下に示します。

以下は`.github/workflows/issue-metrics.yml`に保存することを前提としています。cronで一ヶ月に一度（毎月の1日午前2時3分）に起動し、Step "Get datas for last month"で先月の月初／月末の日を計算し、Step "Run issue-metrics tool"でリポジトリ内のデータを集めています。最後のStep "Create issue"でIssueにメトリクスデータを"Monthly issue metrics report"というタイトルで出力します。

```
name: Monthly issue metrics
on:
  workflow_dispatch:
  schedule:
    - cron: "3 2 1 * *"

permissions:
  contents: read

jobs:
  build:
    name: issue metrics
    runs-on: ubuntu-latest
    permissions:
      issues: write
      pull-requests: read
    steps:
      - name: Get dates for last month
        shell: bash
        run: |
          # Calculate the first day of the previous month
          first_day=$(date -d "last month" +%Y-%m-01)

          # Calculate the last day of the previous month
          last_day=$(date -d "$first_day +1 month -1 day" +%Y-%m-%d)

          #Set an environment variable with the date range
          echo "$first_day..$last_day"
          echo "last_month=$first_day..$last_day" >> "$GITHUB_ENV"

      - name: Run issue-metrics tool
        uses: github/issue-metrics@v3
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          SEARCH_QUERY: 'repo:owner/repo is:issue created:${{ env.last_month }} -reason:"not planned"'

      - name: Create issue
        uses: peter-evans/create-issue-from-file@v5
        with:
          title: Monthly issue metrics report
          token: ${{ secrets.GITHUB_TOKEN }}
          content-filepath: ./issue_metrics.md
```

上記の内容をそのままコピペしただけでは、動きません。

Step "Run issue-metrics tool"の `SEARCH_QUERY` を調整する必要があります。[SEARCH\_QUERYの仕様](https://github.com/github/issue-metrics/blob/main/docs/search-query.md)は公式サイトに説明があります。

例えば、私が管理するnao1215/markdownのPRメトリクス（先月分）を取得する`SEARCH_QUERY`は、以下のようになります。"repo:"にリポジトリ名を指定し、"is:"にPRを指定しています。

```
SEARCH_QUERY: 'repo:nao1215/markdown is:pr created:${{ env.last_month }} -reason:"not planned"'
```

取得対象のPR期間は、"2023-05-01..2023-05-31"のように"${YYYY-MM-DD}..${YYYY-MM-DD}で指定しています。全PRのメトリクスデータが欲しい場合は、${リポジトリ作成日}..${GitHub Actions実行日の日付}と指定してください。

「Markdownじゃなくて、Excelで図示して見たいんだよね！」という場合は、[一度メトリクスをjsonで出力](https://github.com/github/issue-metrics/blob/main/docs/example-using-json-instead-markdown-output.md)して、jsonを別形式に変換する方法が考えられます。試していません。

## 最後に：github/issue-metricsで何が分かったか

ざっくりコメントを書くと、PRのマージにかかる時間は予想より非常に短かったです。私がせっかちなだけだったかもしれない。

私が作成していないPRであっても、マージに時間がかかるケースがありました。それらのPRには、「ドメイン自体が複雑」「PRサイズが大きい」「仕様が曖昧（チーム内で共通認識を持つ時間が必要）」の傾向があるかな、ぐらいの感覚を持ちました。

統計のプロが登場すると、また別の見方になるかもしれません。

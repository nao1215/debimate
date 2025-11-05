---
title: "【Golang】AWS Rainbowプロジェクト始めました - インタラクティブにS3操作するs3hubコマンド"
type: post
date: 2024-02-05
categories:
  - "linux"
  - "体験談"
tags:
  - "aws"
  - "golang"
cover:
  image: images/colorful-2174045_1920.png
  alt: "【Golang】AWS Rainbowプロジェクト始めました - インタラクティブにS3操作するs3hubコマンド"
  hidden: false
images: ["post/2024-02-05-【golang】aws-rainbowプロジェクト始めました-インタラクティ/images/colorful-2174045_1920.png"]
---

## 前書き

2023年に[「2024年のOSS活動は、AWSユーティリティツールに絞ること」](https://debimate.jp/2023/12/28/2023%e5%b9%b4%e3%81%ae%e6%8c%af%e3%82%8a%e8%bf%94%e3%82%8a-2024%e5%b9%b4%e3%81%ae%e6%8a%b1%e8%b2%a0/)と目標を立て、AWS関連のOSSをまとめる[Rainbowプロジェクト（nao1215/rainbow）](https://github.com/nao1215/rainbow)を作り始めました。早いもので2024年も1ヶ月経ったので、何か作ってないと進捗上マズイですよね！一つ作りましたよ！（後述）

Rainbowは、私の好きなRitchie Blackmore's Rainbowから拝借しました。複数のツールやライブラリを集約する予定なので、虹というネーミングは無難なところだと思ってます。

本記事では、Rainbowプロジェクトをどのように推し進めていきたいかと、先日に初版が完成したs3hubコマンドを紹介します。

## Rainbowは複数のツールを一つのリポジトリに集約

私は組み込みエンジニアだったので、BusyBoxやCoreutilsのような「複数のユーティリティを一つのリポジトリに集約する方法」に慣れています。Rainbowプロジェクトは、その頃の思想をそのまま引き継いでいます。

リポジトリに複数のツールを集約するメリットは、リポジトリ内の共通コード（例：BusyBoxのlibbb）が程良くテストされることです。Rainbowプロジェクトの場合、AWS SDKを実行する部分が共通化され、1回テストコードを書けば複数のツールでAWS SDK関連コードを使い回せます。

ただし、失うモノもそれなりにあります。例えば、複数のツールを一つのリポジトリに集約すると、バージョン管理が面倒になります。従来は「git tag version」と「ツール（ライブラリ）バージョン」が1対1で対応していましたが、Rainbowプロジェクトの場合は1対Nになります。ツール毎に異なるバージョンを付けたい場合、git tag versionを採用できません。何らかの方法で、ツール毎にバージョン値をバイナリに埋め込む必要があります。

## Rainbowは模範的なプロジェクトを目指す

模範的なプロジェクトとは、テストコードが書かれており、CHANGELOG、CONTRIBUTING、CODE OF CONDUCTなどのドキュメントがキチンと揃っている状態を指します。開発者が参入しやすいエコシステムが出来上がっている状態とも言い換えられます。

ドキュメントに力を入れる一環で、README駆動開発を採用しています。後述するs3hubコマンドはREADMEを作ってから実装を始めました。ドキュメントに力を入れれば、より多くのユーザー／開発者が集まるだろうと楽観視しています。

## Rainbowはインフラ構築の面倒臭さを解消する

私は、AWSインフラ構築のフィードバックループが長すぎると感じています。CloudFormationを用いたインフラデプロイは反映時間が長く、失敗した時に状態を戻すのに時間がかかります。

また、SRE（Site Reliability Engineering）の文脈でトイルという言葉があります。トイルは、何度も繰り返される手作業であり、自動化できる作業を指します。私は、重要でもないアラートの原因を調査する度に「この作業（トイル）は自動化したい……！」と強く感じていました。開発に投入できた工数を調査に使うのは、ビジネス的にも好ましくありません。

このような面倒臭さを解消する第一弾として、s3hubコマンドを開発しました。s3hubは「S3にあるログファイルをダウンロードして中身を覗きたい」や「CloudFormationスタック削除時に残存したS3バケットを削除したい」といった課題を解決します。

![](images/s3hub-interactive.gif)

s3hubは、S3バケット作成、S3バケット／S3オブジェクトのダウンロード、S3バケット／S3オブジェクトの削除がインタラクティブに実行する機能を持ちます。

2023年にフロントエンド開発の勉強でElmを学んだおかげで、Elmアーキテクチャを採用しているTUI（[charmbracelet/bubbletea](https://github.com/charmbracelet/bubbletea)）でインタラクティブモードを実装できました。TUI部分のコードは汚いですが、技術的な成長を感じました。良いことだ。

## Rainbowで次に何を作る？

2024年2月段階で考えているのは、以下の通りです。

- CloudFormationスタックのリストアップ、削除コマンド
- 定期実行バッチを簡単に作成するツール（CloudFormation生成ツール）
- アラート発生時、当該時刻のCloudWatchメトリクス／CloudWatch Logsを良い感じに抽出
- CloudFormationテンプレート集

上記は、「私が現状抱えている課題を解消するために作りたいツール」と「AWSリソースの標準的な構成を説明する同人誌を書くための材料（CloudFormationテンプレート集）」です。

2024年は技術同人誌を出版してみたいので、RainbowプロジェクトにAWS + Golang関係の知見を集約しようと考えています。

## Rainbowの裏目標

「GitHub Starの数が[nao1215/gup](https://github.com/nao1215/gup)を超えること」と「GitHub Sponsorsを獲得すること」です。

gupは運良くそれなりの数のGitHub Starを集めましたが、そろそろgupを超えるOSSを産み出したいなと思っているところです。また、AWS費用をGitHub Sponsorsで賄えたら良いなと。

実際のところは、localstack（AWSモック）が[Hobby Plan（個人のPublic OSSは無料）](https://www.localstack.cloud/pricing)を打ち出したので、そこまで大きなAWS費用はかかっていません。しかし、localstackはAWSと挙動が異なる部分があるので、AWSでの動作確認が必須です。

より多くのAWSリソースをようになると、大きなコストがかかる見込みです。そのため、GitHub Sponsorsが現れると嬉しいな〜なんて夢を見ています。

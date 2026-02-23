---
title: "GitHub Personal Access Tokenをコミットする人がいた話、類似例、漏洩対策ツール【GitHub Secret scanning、gitleaks、git-secrets、gitguardian】"
type: post
date: 2025-04-27
categories:
  - "linux"
tags:
  - "github"
cover:
  image: "images/key-2114293_640.jpg"
  alt: "GitHub Personal Access Tokenをコミットする人がいた話、類似例、漏洩対策ツール【GitHub Secret scanning、gitleaks、git-secrets、gitguardian】"
  hidden: false
---

###  前書き：セキュリティのお勉強中

本記事は、ユーザー2376名のGitHub リポジトリ8017件を調べたら、GitHub Personal Access Token 16件（全て失効済み）が見つかったという話です。悪用されたら困るので、トークン探しに使ったコードは公開しません。

このような調査をした理由は、セキュリティツールを開発するための下調べをしたかったからです。

現職では不正対策に関わることになったので、最近はセキュリティスキルを伸ばしていこうとしています。セキュリティ分野はセキュリティツール開発、バグバウンティで小遣い稼ぎができる可能性があるので、[副業を探している私](https://x.com/ARC_AED/status/1915608450278756808)に丁度いいなとも思っています。

---


### GitHub Personal Access Tokenの漏洩例を読んだ

私は、セキュリティを勉強する一環で、HackerOneのレポートに目を通しています。その中で、[GitHub Personal Access Tokenが漏洩した例](https://hackerone.com/reports/1087489)を見つけました。

漏洩例のレポートでは、ECサイト会社の社員が公開していたmacOS向けElectronアプリ内に、GitHub Personal Access Tokenが含まれていたことを報告しています。

発見者がGitHub APIを通じてPersonal Access Tokenを検証した結果、ECサイト会社（組織）に属するリポジトリのうち、アクセス範囲がパブリック／プライベートを問わず読み書き可能（pull: true, push: true, admin: false）であったことが確認されました。Personal Access Tokenを悪用すれば、ShopifyのGitHubリポジトリに対して任意のコードをプッシュし、バックドアを仕込むなどの深刻な被害を引き起こす可能性がありました。

上記のレポートを読み、私が考えたのは「Credentials（シークレット）の漏洩を防ぐには、組織（Organization）配下のレポジトリをスキャンするだけでは足りない」ということです。エンジニア個々人が管理するリポジトリも定期的に監視しないと、会社に損害を与える可能性があります。

---


### Credentialsをコミットする人はどの程度いるのか

先程のHackerOneのレポートを読んで私が次に考えたのは、「あるユーザーが管理するGitHub Repositoryをスキャンし、Credentialsの有無をレポートするツールは需要があるかどうか」でした。このツールを開発することは、比較的容易いです。そして、Credentialsをウッカリとコミットする人は存在します（見たことあります）。

GitHub公式が[GitHub Secret scanning](https://docs.github.com/ja/code-security/secret-scanning/introduction/about-secret-scanning)を提供していますが、この機能はEnterprise向けで[高価（年間252ドル）](https://github.co.jp/pricing.html)です。個人開発者向けのツールとして、安価なCredentialsスキャン機能は需要があるのではないかと考えました。そう思い立った私は、以下のようなシェルスクリプトを作って実験しました（悪用されたくないので、コードを示しません）。ユーザーやリポジトリの情報は、[GitHub API](https://docs.github.com/ja/rest?apiVersion=2022-11-28)で取得しています。

1. 指定組織のユーザー取得
2. 人気ユーザー（フォロワー数が多く、Botやスパムではないと予測されるユーザー）の取得
3. ユーザーのリポジトリ取得（フォークや半年以上更新されていないものは除外）
4. リポジトリのクローンとスキャン
5. トークンの検証（ユーザー情報が取得可能か）
6. スキャン結果をCSVに記録

スキャン結果は、ユーザー2376名のGitHubリポジトリ8017件を調べたら、GitHub Personal Access Token 16件（全て失効済み）でした。予想より多かったです。

試作ツールを検証した感想としては、以下の点に厳しさがありました。

- プライベートリポジトリをスキャンできない
- ユーザーがプライベートリポジトリからリリースしたアプリをスキャンできない
- 今回のツールはLLM（生成AI）が一瞬で作れてしまえる難易度なので、MOAT（優位性）がない

---


### 類似のツール

深くは調査していませんが、Credentialsを検知するツールは複数あります。私はOSS開発でgitleaksを使っており、稀に誤検知しますが、特に不満はありません。

- [GitGurdian](https://www.gitguardian.com/)：CredentialsをスキャンするSaaS。チーム規模が一定数を超えるとお高くなる。正直な感想としては、GitHub本家のSecret scanningとの棲み分けが分からない。無料の範疇であれば、GitGuardiaを使いたい。
- [gitleaks](https://github.com/gitleaks/gitleaks)：CredentialsをスキャンするOSS。検査寄り。コミット時、プッシュ時、GitHub Actions等でCredentialsを検知する。過去コミットもチェックする。組織利用になるとライセンスキーが必要。
- [git-secrets](https://github.com/awslabs/git-secrets)：gitleaksと機能的にはほぼ同様だが、初期ルールが少なめ。その一方でルール追加が容易。

---


### 最後に

個人開発アプリからGitHub Personal Access Tokenが漏洩するケースの存在を知れたことが、今回の収穫でした。話は変わりますが、セキュリティの勉強すると、「あれ、もしかして過去に実装したアレはよろしくなかったのでは？」と思う瞬間があります。これも成長ですね。

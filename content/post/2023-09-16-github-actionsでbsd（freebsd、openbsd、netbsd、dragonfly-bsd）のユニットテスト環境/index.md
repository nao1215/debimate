---
title: "GitHub ActionsでBSD（FreeBSD、OpenBSD、NetBSD、Dragonfly BSD）のユニットテスト環境を構築する方法"
type: post
date: 2023-09-16
categories:
  - "linux"
tags:
  - "golang"
  - "go言語"
  - "環境構築"
cover:
  image: "images/BSD_wordmark.svg_.png"
  alt: "GitHub ActionsでBSD（FreeBSD、OpenBSD、NetBSD、Dragonfly BSD）のユニットテスト環境を構築する方法"
  hidden: false
---

## 前書き：BSDはクロスプラットフォーム対応の鬼門

私は、GolangでOSSを開発することが多く、Golangは様々なOS向けの実行バイナリを簡単に作成できる特徴があります。この特徴を活かして、「クロスプラットフォーム対応しよう！」と考えるのは自然なことです。

クロスプラットフォーム対応の実装面で最も苦労するのは、Windows対応です。Windowsは、その出自がUNIX／Linux系と異なるため、Windowsを意識した実装が必要になります。例えば、ファイルパスや改行コードに関する実装に注意を払うことになるでしょう。

本記事の主題ですが、CI（継続的インテグレーション）で苦労するのは、BSD対応です。理由は単純で、GitHub ActionsがBSDをサポートしていないからです。また、BSDユーザーが少ないため、BSDのCIに関するノウハウがネット検索で見つかりづらいです。そのため、トライアンドエラーを繰り返して環境構築することになります。

つい最近、GitHub ActionsでFreeBSD、OpenBSD、NetBSD、DragonFly BSD向けのユニットテスト環境構築が成功したので、本記事ではその紹介をします。[検証に利用したOSSのリンクを貼っておきます。](https://github.com/nao1215/gup)Golang以外の言語でも、本記事の内容は使えます。

## 検証環境

2023年9月16日時点のGitHub Actions、Golang v1.20を使用しています。

GitHub ActionsでBSDをテストするには、Virtual Machine（VM）を利用します。仮想環境を利用するため、実行時間が10〜20分ぐらいかかります。利用しているVMを以下に示します。

- [vmactions/freebsd-vm](https://github.com/vmactions/freebsd-vm)@v0
- [cross-platform-actions/action](https://github.com/cross-platform-actions/action)@v0.19.0
- [vmactions/dragonflybsd-vm](https://github.com/vmactions/dragonflybsd-vm)@v0

## FreeBSD：.github/workflows/freebsd.yml

run節の"pkg install"の部分は、必要なパッケージをインストールする処理を記載してください。"go mod download"以降の処理は、golangでテストをするための処理なので、自身が使っているプログラミング言語に合わせてテスト実行コマンドを記載してください。

```
name: FreeBSDTest

on:
  workflow_dispatch:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: macos-12
    name: A job to run test in FreeBSD
    steps:
      - uses: actions/checkout@v4
      - name: Test in FreeBSD
        id: test
        uses: vmactions/freebsd-vm@v0
        with:
          usesh: true
          run: |
            pkg install -y go
            go mod download
            go test -race -v ./...

```

## OpenBSD：.github/workflows/openbsd.yml

使用しているVMはFreeBSDと異なりますが、run節で実施している内容は概ねFreeBSDと同様です。ただし、使用しているパッケージマネージャが異なります。そして、sudoで管理者権限を付与しないとパッケージを追加できません。

```
name: OpenBSDTest

on: [push]

jobs:
  test:
    runs-on: ${{ matrix.os.host }}
    strategy:
      matrix:
        os:
          - name: openbsd
            architecture: x86-64
            version: "7.3"
            host: macos-12

    steps:
      - uses: actions/checkout@v4

      - name: Test on ${{ matrix.os.name }}
        uses: cross-platform-actions/action@v0.19.0
        with:
          operating_system: ${{ matrix.os.name }}
          architecture: ${{ matrix.os.architecture }}
          version: ${{ matrix.os.version }}
          shell: bash
          memory: 5G
          cpu_count: 4
          run: |
            sudo pkg_add go
            go mod download
            go test -race -v ./...

```

## NetBSD：.github/workflows/netbsd.yml

問題児。トライアンドエラーの回数が多かったです。テスト実行時間がダントツで長い。20分以上かかります（Linux環境だと30秒ぐらいで終わります）

パッケージマネージャーからgolangをインストールしただけだと、エラーが出ます。具体的には、テスト対象ソフトウェアで使用する外部パッケージを取得する際に**"tls: failed to verify certificate: x509: certificate signed by unknown authority"**が出ます。

このエラーはTLS証明書が古かったり、誤っていたりすると発生します。新しいTLS証明書をインストールするために"mozilla-rootcerts install"を使用しています。

その他に厄介なポイントは、パッケージマネージャでインストールしたバイナリへのパスが通っていないことです。

コマンド実行時にフルパス指定する必要があります。goコマンドは、バージョン情報がパスに含まれるため（\`/usr/pkg/go120/bin/go\`の"go120"部分の120はバージョン情報のため）、バージョンが上がるとGitHub Actionsのワークフローが動かなくなると思われます。

```
name: NetBSDTest

on: [push]

jobs:
  test:
    runs-on: ${{ matrix.os.host }}
    strategy:
      matrix:
        os:
          - name: netbsd
            architecture: x86-64
            version: "9.3"
            host: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Test on ${{ matrix.os.name }}
        uses: cross-platform-actions/action@v0.15.0
        with:
          operating_system: ${{ matrix.os.name }}
          architecture: ${{ matrix.os.architecture }}
          version: ${{ matrix.os.version }}
          shell: bash
          memory: 5G
          cpu_count: 4
          run: |
            sudo pkgin -y install go  mozilla-rootcerts
            sudo /usr/pkg/sbin/mozilla-rootcerts install
            /usr/pkg/go120/bin/go mod download
            /usr/pkg/go120/bin/go test -race -v ./...

```

## DragonFly BSD：.github/workflows/dragonfly.yml

DragonFly BSDは、golangの一部機能が使えなかったり（例："go test"で"-race"オプション非対応）、DragonFly BSDに対応していない外部パッケージがありました。

他のBSDがテストをパスしても、DragonFly BSDではパスしない可能性があります。例えば、私はDragonFly BSDのみデスクトップ通知機能の実装を変えました。

```
name: DragonflyBSDTest

on: [push]

jobs:
  test:
    runs-on: macos-12
    name: A job to run test in DragonflyBSD
    steps:
      - uses: actions/checkout@v3
      - name: Test in DragonflyBSD
        id: test
        uses: vmactions/dragonflybsd-vm@v0
        with:
          usesh: true
          prepare: |
            pkg install -y go

          #  -race is not supported on dragonfly/amd64
          run: |
            go mod download
            go test -v ./...

```

## 最後に：BSDユーザー、開発辛くない？

BSDは、Linuxの影に隠れていますが、商用利用されています。

例えば、FreeBSDはNintendo Switchで利用されています。そんなBSDですが、CI／CD（継続的インティグレーション／継続的デリバリー）に関する知見が少なく、正式にBSD対応しているソフトウェアも少ないです（Linuxで動けば、BSDである程度動くのでしょうが……）

BSDでセルフホステッドランナー（サーバー）を準備すれば、CI／CD環境を構築できると思われますが、個人開発レベルだとやや面倒臭さを感じてしまいます。私ぐらいのモノグサだと、どこかのサービスを利用したい。

現代的なBSDユーザーの開発環境を知りたいな、と感じた次第です。

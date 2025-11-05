---
title: "【golang】sqlcコマンドで「SQLクエリから型安全なGoコードを生成」し、生産性を上げたい"
type: post
date: 2022-06-25
categories:
  - "linux"
tags:
  - "golang"
  - "go言語"
  - "sql"
cover:
  image: images/sql.jpg
  alt: "【golang】sqlcコマンドで「SQLクエリから型安全なGoコードを生成」し、生産性を上げたい"
  hidden: false
images: ["post/2022-06-25-【golang】sqlcコマンドで「sqlクエリから型安全なgoコード/images/sql.jpg"]
---

## 前書き：sqlcとは

本記事は、[kyleconroy/sqlc](https://github.com/kyleconroy/sqlc)の基本的な情報を紹介します。

sqlcは、DBスキーマ（DBテーブル定義）、SQLクエリ定義、設定ファイルの3点をインプットとして、型安全なCRUDコード + DBテーブルに対応したモデル（構造体）を自動生成します。ここでのモデルの自動生成には、複数テーブルをJOINしたクエリ用の構造体も含まれます。

個人的な視点では、sqlcは「SQLクエリを検証してから、そのクエリを実行するGolangコードを書いて、クエリ結果を受け取るための構造体を書くのが大変」という課題を解決するツールです。独自の[DSL（Domain Specific Language）](https://e-words.jp/w/DSL.html#:~:text=DSL%20%E3%80%90Domain%2DSpecific%20Language%E3%80%91,%E8%A8%80%E8%AA%9E%E3%81%AA%E3%81%A9%E3%81%8C%E8%A9%B2%E5%BD%93%E3%81%99%E3%82%8B%E3%80%82)は殆ど登場しないので、SQLをゴリゴリ書ける開発者には使いやすいツールです。

## sqlcに着目した理由

sqlcに着目した理由は、標準パッケージ主体の開発スタイル（ORM "Object-Relational Mapping"を避けた開発スタイル）の中で、少しでも実装量を減らして開発速度を向上させたいからです。

ORM（例：[go-gorm/gorm](https://github.com/go-gorm/gorm)、[ent/ent](https://github.com/ent/ent)）を避ける理由は、「ブラックボックス化されるSQLクエリ」「実行速度の低下」「複雑なクエリを書きづらい」などが挙げられます。それらしい理由を書いていますが、これらは世間一般で語られる理由です。

私がORMを使わない理由は、単純に現職のサーバーサイドチームの意向に従っているだけです（私はYESマン）。私は前職が組み込みエンジニアだった関係でDBド素人であり、ORMのメリット／デメリットを考慮した技術選定ができません。そのため、会社で経験値の高い方法（標準パッケージ主体の開発スタイル）に従った方が安全でした。

（そもそも技術選定できる立場じゃないしな！）

が、半年も開発していると、「これは改善したほうが良いのでは…？」という部分が出てきました。例えば、テストコードのためだけにCRUDコードを実装する時間が無駄に感じられました。DBスキーマ（DBテーブル定義）は[kayac/ddl-maker](https://github.com/kayac/ddl-maker)を用いてGolang構造体からSQLファイルを自動生成していますが、ddl-makerはCRUDコードを自動生成しません。

そんな中でsqlcを採用すれば、SQLクエリさえ書けばCRUDコードを自動生成できます。現職の課題を解決（※）するには、ピッタリです

※ 「ddl-maker用の構造体」と「sqlcが自動生成する構造体」が同じ役割を持つ、という新たな課題が発生します。しかし、この問題は弊社固有のものなので、皆さんは気にされなくて大丈夫です。

## DBおよびプログラミング言語のサポート状況

sqlcは、GolangでMySQL／PostgreSQLをサポートしています。他の言語サポートは、開発段階のようです。[今後](https://docs.sqlc.dev/en/latest/reference/language-support.html)は、サポートDBにSQLiteを追加し、サポート言語にC#, TypeScriptを追加するようです。

|   Language   |   MySQL   |   PostgreSQL   |
| --- | --- | --- |
| Go | Stable | Stable |
| Kotlin | Beta | Beta |
| Python | Beta | Beta |

## sqlcのインストール方法

公式のインストール手順は、[公式ドキュメント](https://docs.sqlc.dev/en/latest/overview/install.html)を参照してください。Golangユーザーであれば、定番の方法でインストールできます。

```
(注釈) Go >= 1.17
$ go install github.com/kyleconroy/sqlc/cmd/sqlc@latest

(注釈) Go < 1.17
$ go get github.com/kyleconroy/sqlc/cmd/sqlc
```

Macユーザーであれば"$ brew install sqlc"、Ubuntuユーザーであれば"$ sudo snap install sqlc"でインストールする方法もあります。

## sqlcのインプットファイル一覧

前提として、sqlcによる自動生成には、以下のファイルを準備する必要があります。

- DBテーブル定義（schema.sql）
- SQLクエリ定義（query.sql）
- sqlc設定ファイル（sqlc.yaml or sqlc.json）

これらのサンプル（書き方）を順番に説明します。言語はGolang、DBはMySQLとします。

## DBテーブル定義（schema.sql）

DBテーブル定義として、MySQLかPostgeSQL用の"CREATE TABLE〜"文を記載したファイルを準備します。sqlc独自の文法やDSLは、登場しません。

今回はサンプルとして、ユーザー、部署、ユーザーと部署の中間テーブルを作成するschema.sqlを用意します。

```
CREATE TABLE `user` (
    `id` BIGINT UNSIGNED NOT NULL,
    `name` text NOT NULL,
    `created_at` DATETIME NOT NULL,
    `updated_at` DATETIME NOT NULL,
    PRIMARY KEY (`id`)
) ENGINE = InnoDB DEFAULT CHARACTER SET utf8mb4;

CREATE TABLE `department` (
    `id` BIGINT UNSIGNED NOT NULL,
    `name` text NOT NULL,
    `created_at` DATETIME NOT NULL,
    `updated_at` DATETIME NOT NULL,
    PRIMARY KEY (`id`)
) ENGINE = InnoDB DEFAULT CHARACTER SET utf8mb4;

CREATE TABLE `user_department_relation` (
    `id` BIGINT UNSIGNED NOT NULL,
    `user_id` BIGINT UNSIGNED NOT NULL,
    `department_id` BIGINT UNSIGNED NOT NULL,
    `created_at` DATETIME NOT NULL,
    PRIMARY KEY (`id`)
) ENGINE = InnoDB DEFAULT CHARACTER SET utf8mb4;

```

## SQLクエリ定義（query.sql）

SQLクエリ定義として、sqlcに自動生成して欲しいCRUDコード用のSQLクエリを実装します。ここでの定義では、sqlcの独自のDSL（正確には、"[Query annotations](https://docs.sqlc.dev/en/latest/reference/query-annotations.html)"）を用いて「生成するCRUDコードの関数名」と「返り値」を指定する必要があります。

Query annotationsの文法は\`-- name: $関数名 $返り値の種類\`であり、SQLクエリの上に記載します。下表に、Query annotationsの一覧を示します。

| **Query annotation** | **役割** |
| --- | --- |
| :exec | ExecContext のの実行結果（errorインターフェース）を返す |
| :execresult | ExecContext の実行結果である「sql.Result」、「errorインターフェース」を返す |
| :execrows | ExecContext の実行結果である「影響を与えた行の数」、「errorインターフェース」を返す |
| :execlastid | ExecContext の実行結果である「最終ID（last ID）」、「errorインターフェース」を返す |
| :many | QueryContextの実行結果である「取得した複数レコード」、「errorインターフェース」を返す |
| :one | QueryRowContextの実行結果である「取得したレコード」、「errorインターフェース」を返す |
| :batchexec | Batchオブジェクト（このオブジェクトはExec、Closeメソッドを持つ）を返す。PostgreSQLのみ使用可能 |
| :batchmany | Batchオブジェクト（このオブジェクトはQuery、Closeメソッドを持つ）を返す。PostgreSQLのみ使用可能 |
| :batchone | Batchオブジェクト（このオブジェクトはQueryRow、Closeメソッドを持つ）を返す。PostgreSQLのみ使用可能 |

以下に、SQLクエリ定義（query.sql）の例を示します。

`user`テーブルに対して、「SELECT、INSERT、UPDATE、UPSERT、DELETEするクエリ」および「 \`user\` , \`department\` ,  \`user\_department\_relation\` をJOINして、ユーザー名と部署名を表示するクエリ」を実装しています。

```
-- name: GetUser :one
SELECT
    *
FROM
    user
WHERE
    id = ?
LIMIT
    1;

-- name: ListUsers :many
SELECT
    *
FROM
    user
ORDER BY
    created_at ASC;

-- name: CreateUser :execresult
INSERT INTO
    user (id, name, created_at, updated_at)
VALUES
    (?, ?, ?, ?);

-- name: UpdateUserName :execresult
UPDATE
    user
SET
    name = ?,
    updated_at = ?
WHERE
    id = ?;

-- name: UpsertUser :execresult
INSERT INTO
    user (id, name, created_at, updated_at)
VALUES
    (?, ?, ?, ?) ON DUPLICATE KEY
UPDATE
    name = ?,
    updated_at = ?;

-- name: DeleteUser :execrows
DELETE FROM
    user
WHERE
    id = ?;

-- name: ListUserDepartment :many
SELECT
    u.name AS user_name,
    d.name AS department_name
FROM
    user_department_relation AS udr
    LEFT JOIN user AS u ON udr.user_id = u.id
    LEFT JOIN department AS d ON udr.department_id = d.id;

```

上記の例で、少し工夫している部分は、取得するカラムに対して意図的に別名を付けている箇所です。具体的には、JOINを用いたクエリです。

以下に示すクエリでは、`user`テーブルと`department`テーブルは、どちらもカラム名がnameです。sqlcがこのクエリから構造体を自動生成した場合、構造体のフィールド名が"Name", "Name\_2"となり、少し残念な感じになります。

```
-- name: ListUserDepartment :many
SELECT
    u.name,
    d.name
FROM
    user_department_relation AS udr
    LEFT JOIN user AS u ON udr.user_id = u.id
    LEFT JOIN department AS d ON udr.department_id = d.id;

```

そこで、意図的に`SELECT u.name AS user_name, d.name AS department_name 〜`と書くこと（AS句でカラムに別名をつけること）によって、sqlcが人間に優しい構造体フィールド名（"UserName"、"DepartmentName"）を命名するようにしています。

## sqlc設定ファイル（sqlc.yaml or sqlc.json）

[sqlc設定ファイル](https://docs.sqlc.dev/en/latest/reference/config.html)は、yaml形式もしくはjson形式がサポートされています。設定ファイルにはVersion 1とVersion 2があり、今回の例ではVersion 2を採用します。

sqlc設定ファイルでは、大別して以下の3点を設定します。

- インプットファイルのパス情報
- 使用するDB情報
- アウトプットするファイルの情報

今回の例では、プロジェクトルートディレクトリ直下にsqlcディレクトリを作り、この中にsqlcに関するファイルを集約します。sqlcが自動生成するファイルは`<PROJECT_ROOT>/sqlc_output_dir`以下に集約し、それらのパッケージ名は"query"とします。

以下、ディレクトリツリーとsqlc設定ファイルの例です。

```
PROJECT_ROOT
├── go.mod
├── main.go
└── sqlc
       ├── query.sql
       ├── schema.sql
       └── sqlc.yaml

```

```
version: "2"
sql:
  - schema: "schema.sql"
    queries: "query.sql"
    engine: "mysql"
    gen:
      go:
        package: "query"
        out: "../sqlc_output_dir"

```

注意点は、以下の通りです

- sqlcインプットファイル（schema、queries）は、sqlc設定ファイル（sqlc.yaml or sqlc.json）を基点とした相対パスを指定
- engineは、postgresqlかmysqlのいずれかが入る
- 自動生成先ディレクトリ（out）は、sqlc設定ファイル（sqlc.yaml or sqlc.json）を基点とした相対パスを指定

## 自動生成の例

sqlcは、generateサブコマンドでCRUDコードを自動生成します。

sqlcは、デフォルトではカレントディレクトリ以下にあるsqlc設定ファイル（sqlc.yaml or sqlc.json）を探します。今回の例では、カレントディレクトリにはsqlc設定ファイルがありません。

このような場合は、--file（-f）オプションを用いて、明示的にsqlc設定ファイルパスを指定する必要があります。

```
$ cd $PROJECT_ROOT
$ ls
go.mod  main.go  sqlc

(注釈) 自動生成
$ sqlc generate --file sqlc/sqlc.yaml

```

自動生成完了後は、以下のようなディレクトリ構成になります。自動生成されたファイルは、db.go、models.go、query.sql.goの3点です。

```
PROJECT_ROOT
├── go.mod
├── main.go
├── sql_output_dir
│   ├── db.go
│   ├── models.go
│   └── query.sql.go
└── sqlc
    ├── query.sql
    ├── schema.sql
    └── sqlc.yaml

```

自動生成されたコードは、以下の通りです。

- **db.go：**SQLクエリの実行時に使用するQueries構造体を定義したファイル

```
// Code generated by sqlc. DO NOT EDIT.
// versions:
//   sqlc v1.14.0

package query

import (
	"context"
	"database/sql"
)

type DBTX interface {
	ExecContext(context.Context, string, ...interface{}) (sql.Result, error)
	PrepareContext(context.Context, string) (*sql.Stmt, error)
	QueryContext(context.Context, string, ...interface{}) (*sql.Rows, error)
	QueryRowContext(context.Context, string, ...interface{}) *sql.Row
}

func New(db DBTX) *Queries {
	return &Queries{db: db}
}

type Queries struct {
	db DBTX
}

func (q *Queries) WithTx(tx *sql.Tx) *Queries {
	return &Queries{
		db: tx,
	}
}

```

- **model.go**：各DBテーブルに対応するモデルを定義したファイル

```
// Code generated by sqlc. DO NOT EDIT.
// versions:
//   sqlc v1.14.0

package query

import (
	"time"
)

type Department struct {
	ID        int64
	Name      string
	CreatedAt time.Time
	UpdatedAt time.Time
}

type User struct {
	ID        int64
	Name      string
	CreatedAt time.Time
	UpdatedAt time.Time
}

type UserDepartmentRelation struct {
	ID           int64
	UserID       int64
	DepartmentID int64
	CreatedAt    time.Time
}

```

- **query.sql.go**：各SQLクエリを実行するメソッドを定義したファイル

```
// Code generated by sqlc. DO NOT EDIT.
// versions:
//   sqlc v1.14.0
// source: query.sql

package query

import (
	"context"
	"database/sql"
	"time"
)

const createUser = `-- name: CreateUser :execresult
INSERT INTO
    user (id, name, created_at, updated_at)
VALUES
    (?, ?, ?, ?)
`

type CreateUserParams struct {
	ID        int64
	Name      string
	CreatedAt time.Time
	UpdatedAt time.Time
}

func (q *Queries) CreateUser(ctx context.Context, arg CreateUserParams) (sql.Result, error) {
	return q.db.ExecContext(ctx, createUser,
		arg.ID,
		arg.Name,
		arg.CreatedAt,
		arg.UpdatedAt,
	)
}

const deleteUser = `-- name: DeleteUser :execrows
DELETE FROM
    user
WHERE
    id = ?
`

func (q *Queries) DeleteUser(ctx context.Context, id int64) (int64, error) {
	result, err := q.db.ExecContext(ctx, deleteUser, id)
	if err != nil {
		return 0, err
	}
	return result.RowsAffected()
}

const getUser = `-- name: GetUser :one
SELECT
    id, name, created_at, updated_at
FROM
    user
WHERE
    id = ?
LIMIT
    1
`

func (q *Queries) GetUser(ctx context.Context, id int64) (User, error) {
	row := q.db.QueryRowContext(ctx, getUser, id)
	var i User
	err := row.Scan(
		&i.ID,
		&i.Name,
		&i.CreatedAt,
		&i.UpdatedAt,
	)
	return i, err
}

const listUserDepartment = `-- name: ListUserDepartment :many
SELECT
    u.name AS user_name,
    d.name AS department_name
FROM
    user_department_relation AS udr
    LEFT JOIN user AS u ON udr.user_id = u.id
    LEFT JOIN department AS d ON udr.department_id = d.id
`

type ListUserDepartmentRow struct {
	UserName       sql.NullString
	DepartmentName sql.NullString
}

func (q *Queries) ListUserDepartment(ctx context.Context) ([]ListUserDepartmentRow, error) {
	rows, err := q.db.QueryContext(ctx, listUserDepartment)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var items []ListUserDepartmentRow
	for rows.Next() {
		var i ListUserDepartmentRow
		if err := rows.Scan(&i.UserName, &i.DepartmentName); err != nil {
			return nil, err
		}
		items = append(items, i)
	}
	if err := rows.Close(); err != nil {
		return nil, err
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	return items, nil
}

const listUsers = `-- name: ListUsers :many
SELECT
    id, name, created_at, updated_at
FROM
    user
ORDER BY
    created_at ASC
`

func (q *Queries) ListUsers(ctx context.Context) ([]User, error) {
	rows, err := q.db.QueryContext(ctx, listUsers)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var items []User
	for rows.Next() {
		var i User
		if err := rows.Scan(
			&i.ID,
			&i.Name,
			&i.CreatedAt,
			&i.UpdatedAt,
		); err != nil {
			return nil, err
		}
		items = append(items, i)
	}
	if err := rows.Close(); err != nil {
		return nil, err
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	return items, nil
}

const updateUserName = `-- name: UpdateUserName :execresult
UPDATE
    user
SET
    name = ?,
    updated_at = ?
WHERE
    id = ?
`

type UpdateUserNameParams struct {
	Name      string
	UpdatedAt time.Time
	ID        int64
}

func (q *Queries) UpdateUserName(ctx context.Context, arg UpdateUserNameParams) (sql.Result, error) {
	return q.db.ExecContext(ctx, updateUserName, arg.Name, arg.UpdatedAt, arg.ID)
}

const upsertUser = `-- name: UpsertUser :execresult
INSERT INTO
    user (id, name, created_at, updated_at)
VALUES
    (?, ?, ?, ?) ON DUPLICATE KEY
UPDATE
    name = ?,
    updated_at = ?
`

type UpsertUserParams struct {
	ID          int64
	Name        string
	CreatedAt   time.Time
	UpdatedAt   time.Time
	Name_2      string
	UpdatedAt_2 time.Time
}

func (q *Queries) UpsertUser(ctx context.Context, arg UpsertUserParams) (sql.Result, error) {
	return q.db.ExecContext(ctx, upsertUser,
		arg.ID,
		arg.Name,
		arg.CreatedAt,
		arg.UpdatedAt,
		arg.Name_2,
		arg.UpdatedAt_2,
	)
}

```

クエリを実行するには、

1. db.goに定義された`New()`に対して、sql.DBもしくはsql.Txを引数渡し
2. `New()`の返り値から、Queries構造体を取得
3. Queries構造体のメソッド（CRUDコード）を実行

という流れで、非常に使いやすく、シンプルです（[参考ドキュメント](https://docs.sqlc.dev/en/stable/tutorials/getting-started-mysql.html)）

## sqlcが持つサブコマンド、オプション

```
$ sqlc --help
Usage:
  sqlc [command]

Available Commands:
  compile     Statically check SQL for syntax and type errors
  completion  Generate the autocompletion script for the specified shell
  generate    Generate Go code from SQL
  help        Help about any command
  init        Create an empty sqlc.yaml settings file
  upload      Upload the schema, queries, and configuration for this project
  version     Print the sqlc version number

Flags:
  -x, --experimental   enable experimental features (default: false)
  -f, --file string    specify an alternate config file (default: sqlc.yaml)
  -h, --help           help for sqlc

Use "sqlc [command] --help" for more information about a command.

```

generateサブコマンド以外で良く使う可能性があるのは、以下の2つと思われます。

- compile：SQLシンタックスおよび型エラーのチェック
- init：sqlc.yamlの生成（あまり記載が埋まってなくて不満……）

## 最後に

sqlcを知った当初は、「SQL書きたくないのにSQLクエリから各種ファイルを自動生成するのか。微妙だなー」という感想でした。しかし、sqlcのインプットとなるSQLクエリは、普段のCRUDコード実装で手書きしている部分です。

そのため、sqlcの導入はあまり負担が増えません。むしろ、Golangコードの実装に使っていた時間が自動生成によってゼロになります。生産性が大きく変わります。

製品コードに使えないまでも、テストコードにsqlcを導入できないかなと考えています（このコメントは、社内の人向けに書いています）

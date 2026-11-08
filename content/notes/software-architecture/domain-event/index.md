---
title: "Domain Event - ドメインで起きた事実を伝える"
date: 2026-08-07
draft: false
series: ["技術ノート", "Software Architecture"]
tags: ["software-architecture", "ddd"]
weight: 4
wrapTables: true
---

Domain Event とは、ドメインの中で既に起きた出来事を表すオブジェクトです。過去の記録なので通常は不変（作った後に値を変えない）で、出来事が起きた時刻と、関与したエンティティの識別子を持ちます。例えば EC サイトで注文の確定と在庫の引き当てを 1 つのトランザクションで行うと、人気商品の注文どうしで、同じ在庫レコードへの更新が競合します。Domain Event は、この 2 つを別のトランザクションに分ける時に使います。

発行から処理までの経路を以下に示します。

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#eaf1f5","primaryTextColor":"#28343b","primaryBorderColor":"#9cabb5","lineColor":"#596b76","textColor":"#28343b","actorBkg":"#eaf1f5","actorBorder":"#9cabb5","actorTextColor":"#28343b","actorLineColor":"#9cabb5","signalColor":"#596b76","signalTextColor":"#28343b","noteBkgColor":"#f7f1e5","noteBorderColor":"#c5b99b","noteTextColor":"#403c32","activationBkgColor":"#edf3ef","activationBorderColor":"#9aafa1"}}}%%
flowchart LR
    subgraph T1["トランザクション 1"]
        A["Order 集約"] -- 記録 --> E["OrderConfirmed"]
        E -- 保存 --> DB[("注文の DB")]
    end
    subgraph T2["トランザクション 2"]
        H["在庫のハンドラ"] --> S["Stock 集約"]
    end
    E -. 配送 .-> H
    classDef default fill:#eaf1f5,stroke:#9cabb5,color:#28343b;
```

上記の図の集約（Aggregate。まとめて一貫性を保つオブジェクトの集まり）のうち、`Order` の確定は `Stock` の更新を待たずに完了し、在庫の引き当ては後から別のトランザクションで実行されます。トランザクションを分けたことで、注文の確定は在庫レコードの更新競合を待たずに進み、代わりに注文と在庫の状態がずれている時間が生まれます。

Domain Event は「ドメインエキスパートが関心を持つ何かが起きた」ことを表します。DDD（Domain-Driven Design、ドメイン駆動設計）での位置付けは、Eric Evans 氏の [DDD Reference](https://www.domainlanguage.com/wp-content/uploads/2016/05/DDD_Reference_2015-03.pdf) にある「ドメインの活動に関する情報を一つ一つ区切られた出来事の連なりとしてモデル化し、それぞれの出来事をドメインオブジェクトとして表現せよ」という記述で示されています。

連なりとは、業務上意味のある出来事を 1 件ずつ明示することです。対象は、ドメインエキスパートが追跡したい出来事、通知を受けたい出来事、他のモデルオブジェクトの状態変化に結び付く出来事で、関係のない活動は無視して構いません。

以下は、Domain Event を使う構成と、全ての状態変更の並びから状態を作り直す [Event Sourcing](../event-sourcing/) の違いです。Domain Event を使っても状態の保存は従来のままです。

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#eaf1f5","primaryTextColor":"#28343b","primaryBorderColor":"#9cabb5","lineColor":"#596b76","textColor":"#28343b","actorBkg":"#eaf1f5","actorBorder":"#9cabb5","actorTextColor":"#28343b","actorLineColor":"#9cabb5","signalColor":"#596b76","signalTextColor":"#28343b","noteBkgColor":"#f7f1e5","noteBorderColor":"#c5b99b","noteTextColor":"#403c32","activationBkgColor":"#edf3ef","activationBorderColor":"#9aafa1"}}}%%
flowchart TB
    subgraph ES["Event Sourcing"]
        direction TB
        A2["Order 集約"] -- 追記 --> E2[("全ての状態変更の<br/>イベントの並び")]
        E2 -- 作り直す --> S2["現在の状態"]
    end
    subgraph DE["Domain Event を使う"]
        direction TB
        A1["Order 集約"] -- 保存 --> S1[("現在の状態")]
        A1 -- 記録 --> E1["業務上意味のある<br/>出来事だけ"]
    end
    classDef default fill:#eaf1f5,stroke:#9cabb5,color:#28343b;
```

<br>

本記事では、1 つの [Bounded Context](../bounded-context/) の中で [Aggregate](../value-object-entity-aggregate/) 同士を繋ぐ用途と、Bounded Context をまたいで他のシステムに伝える用途を説明します。主に扱うのは次の疑問です。

- なぜ Aggregate の間をイベントで繋ぐのか。
- イベントには、どのような形と名前を付けるのか。
- イベントは誰が作るのか。
- イベントは、どのように発行して配送するのか。
- コミットの前にイベントを配ると、受信側で何が起きるのか。
- 同じイベントが重ねて届いた時、受信側はどう扱うのか。

---

### Domain Event が必要な理由

Aggregate は、内部の不変条件（例えば、引き当て数が在庫数を超えないという、常に成り立つべき規則）を保つ単位です。Vaughn Vernon 氏が 2011 年に発表した [Effective Aggregate Design Part I](https://dddcommunity.org/wp-content/uploads/files/pdf_articles/Vernon_2011_1.pdf) には、「適切に設計された Bounded Context は、あらゆる場合において 1 トランザクションにつき 1 つの Aggregate インスタンスだけを変更する」とあります。同じ論文は、この原則が経験則（rule of thumb）で、ほとんどの場合に目指すべき目標だとも添えています。

原則を外して 2 つの Aggregate を 1 つのトランザクションで更新すると、次のようなコードになります。注文の確定と在庫の引き当てを同時に行う実装です。

```go
// confirmOrder は、注文の確定と在庫の引き当てを 1 つのトランザクションで行います。
func (u *usecase) confirmOrder(ctx context.Context, id OrderID) error {
	return u.tx.Do(ctx, func(tx Tx) error {
		order, err := u.orders.Find(tx, id)
		if err != nil {
			return err
		}
		if err := order.Confirm(time.Now()); err != nil {
			return err
		}
		for _, line := range order.Lines() {
			// SKU（Stock Keeping Unit）は在庫を数える単位で、Stock は別の Aggregate
			stock, err := u.stocks.Find(tx, line.SKU)
			if err != nil {
				return err
			}
			if err := stock.Reserve(line.Quantity); err != nil {
				return err
			}
			if err := u.stocks.Save(tx, stock); err != nil {
				return err
			}
		}
		return u.orders.Save(tx, order)
	})
}
```

このコードは 1 台の DB（データベース）の上では動きますが、`Order` と行ごとの `Stock` を同じトランザクションで更新する、原則からの明示的な例外です。同じ SKU が注文行に重複していれば同じ `Stock` を二度読んで保存し得るため、先に SKU ごとに数量を集約するか、Aggregate 側で同じ SKU の予約を一度に検査する必要があります。途中の SKU で失敗した時はトランザクション全体を巻き戻し、配送後の重複は処理済みイベントの一意制約で抑えます。問題は、同じ商品を含む注文が同時に届いた時に現れます。`Stock` は商品ごとに1つしかなく、その商品を含む注文は同じ在庫レコードを更新するため、競合します。

以下は、人気商品への注文が 2 件同時に届いた場合です。`Stock` をバージョン列で守る楽観的ロックの実装を想定しています。

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#eaf1f5","primaryTextColor":"#28343b","primaryBorderColor":"#9cabb5","lineColor":"#596b76","textColor":"#28343b","actorBkg":"#eaf1f5","actorBorder":"#9cabb5","actorTextColor":"#28343b","actorLineColor":"#9cabb5","signalColor":"#596b76","signalTextColor":"#28343b","noteBkgColor":"#f7f1e5","noteBorderColor":"#c5b99b","noteTextColor":"#403c32","activationBkgColor":"#edf3ef","activationBorderColor":"#9aafa1"}}}%%
sequenceDiagram
    participant C1 as Client 1
    participant C2 as Client 2
    participant DB as DB
    C1->>DB: トランザクション開始
    C2->>DB: トランザクション開始
    C1->>DB: Stock（商品 X）をバージョン 7 で読む
    C2->>DB: Stock（商品 X）をバージョン 7 で読む
    C1->>DB: バージョン 7 のまま更新して commit
    Note over DB: バージョンが 8 に上がる
    C2->>DB: バージョン 7 のまま更新
    DB-->>C2: 更新できた行が 0 件なので失敗
    Note over C2: 注文 2 は業務上正しいのに<br/>在庫の競合で失敗する
```

上記の図の Client 2 が失敗したのは、`Order` と `Stock` を同じトランザクションに入れ、注文の確定が在庫の混雑に巻き込まれたからです。行ロックで待つ実装なら失敗しない代わりに、注文の確定が在庫の待ち時間だけ遅くなります。

在庫が別の Bounded Context に移り、DB が分かれた場合は、問題がもっとはっきりします。1 つのローカルトランザクションで両方を更新する経路が無くなり、上のコードは書けなくなります。複数の DB を 1 つのコミットにまとめる分散トランザクション（[2 相コミット](../../distributed-systems/two-phase-commit/)）を持ち込めば形は保てるものの、参加者の 1 つが停止すると全体が待たされます。

コマンドは状態を変えてほしいという要求で、ここでは `order.Confirm(...)` のように Aggregate のメソッドを呼ぶ形で表します。1 つの Aggregate へのコマンドの結果、別の Aggregate で業務規則を実行する必要がある場合は、両者を同時に一致させず、いずれ一致すれば良いと扱います。この考え方を[結果整合性](https://dddcommunity.org/wp-content/uploads/files/pdf_articles/Vernon_2011_2.pdf)と呼び、ある瞬間を切り取ると[ずれている状態を許します](../value-object-entity-aggregate/)。Domain Event は、この結果整合性を実現する手段になります。

---

### イベントの形と名前

名前は過去形にします。何を載せるかは、受信側が自分の処理を完結できる分を目安にします。

```go
// DomainEvent は、種類名を答えられる物を Domain Event として扱うための
// インターフェースです。配送先には Go の型が無いため、種類は文字列で運びます。
type DomainEvent interface {
	Name() string
}

// OrderConfirmed は、注文が確定したという事実を表します。
// 過去に起きた記録なので、作った後は変更しません。
type OrderConfirmed struct {
	EventID    string      // 二重配送を受信側が判定するための識別子
	OccurredAt time.Time   // 出来事がドメインで起きた時刻
	OrderID    OrderID     // 関与したエンティティの識別子
	Lines      []OrderLine // 受信側が処理に必要とする情報の写し
}

func (e OrderConfirmed) Name() string { return "order.confirmed" }
```

識別子だけを載せて受信側から問い合わせ直させる作りもあります。載せる情報が減る代わりに、受信側が発行元に問い合わせる経路が必要になり、問い合わせた時点では既に値が変わっている場合もあります。上の `Lines` は、確定した時点の内容を写して渡す方を選んだ例です。

以降の例では、在庫のハンドラが注文と同じ Bounded Context にあり、`OrderConfirmed` をそのまま受け取るとします。Bounded Context の外に送る場合は、内部のモデルをそのまま出すと受け手が内部の変更に引きずられるので、公開用の形に変換してから送ります（この公開用のイベントを Integration Event と呼んで区別することもあります）。

<br>

イベント名は、処理の依頼ではなく、完了した事実を表します。「注文を確定せよ」というコマンドは、メソッド呼び出しでもキューのメッセージでも、特定の処理の実行とその成否を期待しています。「注文が確定した」という事実は、同じプロセスの中で同期に配る場合でも起きたことを伝えるだけで、発行元は誰がどう処理したかを知りません。起きた事実は取り消せませんが、受信側の処理は失敗することがあります。

時刻の扱いにも注意が必要です。Martin Fowler 氏の [Domain Event](https://martinfowler.com/eaaDev/DomainEvent.html) によると、「出来事が世界で起きた時刻」と「その出来事に気付いた時刻」の 2 つは区別すべきです。どちらを保持しているのかがフィールド名で分かるようにします。

---

### イベントを作る主体

イベントを Aggregate に作らせると扱いやすくなります。状態を変更するAggregate内で、対応するイベントも記録できるからです。呼び出し側で作ると、状態の変更とイベントの発行が別々の場所に散らばり、片方だけを直した時にずれます。Aggregate の状態変更に対応しないイベントは、呼び出し側で作ります。

```go
// Confirm は注文を確定し、確定したという事実をイベントとして記録します。
func (o *Order) Confirm(now time.Time) error {
	if o.status != OrderStatusDraft {
		return errAlreadyConfirmed
	}
	o.status = OrderStatusConfirmed
	o.events = append(o.events, OrderConfirmed{
		EventID:    newEventID(),
		OccurredAt: now,
		OrderID:    o.id,
		Lines:      slices.Clone(o.lines),
	})
	return nil
}

// PullEvents は記録済みのイベントを取り出し、Aggregate の中を空にします。
func (o *Order) PullEvents() []DomainEvent {
	events := o.events
	o.events = nil
	return events
}
```

このコードは、記録と発行を分けています。`Confirm` の時点では、イベントを Aggregate の中に溜めるだけです。ここでの発行は、[Repository](../repository/) の `Save` が `PullEvents` でイベントを取り出し、受信側に渡すことを指します。`PullEvents` を呼ぶのを `Save` だけにする決まりを守れば、保存の前に処理を中断した時に、起きていない事実は配られません。

`PullEvents` は Aggregate の中を空にするので、トランザクションを再試行する構成では、Aggregate を取得し直します。同じオブジェクトで再試行すると、1 回目で空になったイベントは戻りません。

イベントを溜めずに、`Confirm` の中から発行の窓口を直接呼ぶ書き方もあります。この形では、窓口がその場で受信側に届ける実装だと、後の保存が失敗しても配った事実を取り消せません。

---

### 発行と配送

`Save` で取り出したイベントを配る方法には段階があります。最小の構成は、コミットが成功した後に同じプロセスの中でハンドラを呼ぶ形です。弱点は、コミットの直後にプロセスが落ちるとイベントが消える点にあります。逆に、コミットの前にハンドラを呼ぶと、保存に失敗した時に起きていない事実が配られます。どちらの問題も、DB へのコミットと、イベントを受信側に渡す操作（ハンドラの呼び出しや、メッセージを預かって受信側に配るメッセージブローカーへの送信）が別々である限り避けられません。

保存が成功する場合でも、コミットの前に配ると受信側が先に動くことがあります。Ruby のアプリケーションが登録したジョブ（後で実行する処理）を別プロセスで実行する [Sidekiq](https://github.com/sidekiq/sidekiq/wiki/Problems-and-Troubleshooting) は、ジョブがコミットより先に実行されるほど速いので、トランザクションの中でジョブを登録する（本記事のイベントの配送に当たる）と、ジョブがまだコミットされていない行を読みに行き、指定した ID の行が見つからないというエラーで失敗することがあります。直し方の 1 つは、登録をコミットの後に行うことです。ただし、これは先に挙げた最小の構成と同じで、コミットの直後に落ちるとジョブが消えます。

最小の構成で足りるかは、Bounded Context の境界ではなく、後続処理が消えた時に業務が困るかで決まります。決済の後に必ず走らせたい処理があるなら、同じ Bounded Context の中でも足りません。通知が 1 通落ちても業務が回るなら、境界をまたいでいても足ります。

<br>

[Transactional Outbox](https://microservices.io/patterns/data/transactional-outbox.html)では、業務データと送信予定のイベントを同じDBトランザクションで保存します。以下は、その構成です。

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#eaf1f5","primaryTextColor":"#28343b","primaryBorderColor":"#9cabb5","lineColor":"#596b76","textColor":"#28343b","actorBkg":"#eaf1f5","actorBorder":"#9cabb5","actorTextColor":"#28343b","actorLineColor":"#9cabb5","signalColor":"#596b76","signalTextColor":"#28343b","noteBkgColor":"#f7f1e5","noteBorderColor":"#c5b99b","noteTextColor":"#403c32","activationBkgColor":"#edf3ef","activationBorderColor":"#9aafa1"}}}%%
flowchart LR
    subgraph TX["業務データと同じトランザクション"]
        O[("orders<br/>業務データ")]
        OB[("outbox<br/>送信箱")]
    end
    AP["業務処理"] --> O
    AP --> OB
    R["message relay<br/>別プロセス"]
    B["メッセージ<br/>ブローカー"]
    OB -- "溜まった行を読む" --> R
    R -- 転送 --> B
    classDef default fill:#eaf1f5,stroke:#9cabb5,color:#28343b;
```

上記の図の業務処理は、メッセージを外部に送る代わりに、業務データと同じトランザクションで outbox（送信箱）テーブルに書き込みます。

コミットが成立すれば送るべき行が outbox に残り、巻き戻せば業務データと一緒に消えるので、業務データの更新と送信の予約は食い違いません。しかし、relay が止まっている間は送られず、届く回数とタイミングも relay とブローカーの実装で変わります。この保証の範囲は [Transactional Outbox のノート](../../distributed-systems/transactional-outbox/)で扱っています。

outbox テーブルに入るのは、以下のような行です。

| id | event_id | name | payload | occurred_at | sent_at |
|---|---|---|---|---|---|
| 1 | e1 | order.confirmed | `{"order_id":"o-1", ...}` | 2026-08-07T10:00:00Z | 2026-08-07T10:00:03Z |
| 2 | e2 | order.confirmed | `{"order_id":"o-2", ...}` | 2026-08-07T10:00:01Z | NULL |

行を追記するのは Repository の `Save` です。`Order` の状態を書いた後、`PullEvents` で取り出したイベントを 1 件ずつ、同じトランザクションの中で outbox に書きます。`payload` には `EventID` を含むイベントの中身を JSON で入れます。送り先には Go の型が無いからです。outbox は配送を取りこぼさないためのテーブルで、イベントの履歴として設計されたものではありません。

`sent_at` が `NULL` の行が未送信で、relay は次のコードでその行を古い順に送ります。

```go
// runOnce は、未送信の行を古い順に読み、ブローカーに送って送信済みにします。
// 常駐プロセスが一定間隔でこれを呼びます。
func (r *relay) runOnce(ctx context.Context) error {
	rows, err := r.outbox.FindUnsent(ctx, 100)
	if err != nil {
		return err
	}
	for _, row := range rows {
		if err := r.broker.Publish(ctx, row.Name, row.Payload); err != nil {
			return err // 送れなかった行から、次の周回でやり直す
		}
		// ここで停止すると、送信済みを記録しないまま次の周回で再送する
		if err := r.outbox.MarkSent(ctx, row.ID); err != nil {
			return err
		}
	}
	return nil
}
```

件数を区切るのは、outbox が溜まった時に 1 回の処理が長くなり過ぎないようにするためです。途中で失敗しても、`MarkSent` を終えた行は送信済みのまま残り、次の周回は失敗した行から再開します。その代わり、送れない行が残り続けると、後ろの行も送られません。

---

### 受信側の冪等性

冪等とは、同じ処理を何回実行しても、1 回実行した時と同じ結果になる性質です。上の relay は、`Publish` の後で停止したり `MarkSent` に失敗したりすると、次の周回で同じ行をもう一度送ります。受信側に何回届くかはブローカーの配送保証にも左右され、少なくとも 1 回は届く代わりに 2 回以上届くこともある配送（at-least-once 配送）になります。そのため、受信側はイベントに付けた `EventID` を処理済みとして記録しておき、同じ値が来たら何もせずに終えます。

```go
// Handle は、注文の確定を受けて在庫を引き当てます。
// processed テーブルの EventID には一意制約を張り、Insert は
// 制約に当たった時に行を挿入せず inserted = false を返す実装にします。
func (h *stockHandler) Handle(ctx context.Context, ev OrderConfirmed) error {
	return h.tx.Do(ctx, func(tx Tx) error {
		// 処理の前に記録を試み、一意制約に弾かれたら処理済みとして抜ける
		inserted, err := h.processed.Insert(tx, ev.EventID)
		if err != nil {
			return err
		}
		if !inserted {
			return nil
		}
		reserved := make([]*Stock, 0, len(ev.Lines))
		for _, line := range ev.Lines {
			stock, err := h.stocks.Find(tx, line.SKU)
			if err != nil {
				return err
			}
			if err := stock.Reserve(line.Quantity); err != nil {
				// 在庫不足なら在庫を 1 件も保存せず、失敗のイベントを残してコミットする
				return h.outbox.Append(tx, newReservationFailed(ev, line))
			}
			reserved = append(reserved, stock)
		}
		// 全明細の引き当てが揃ってから保存する
		for _, stock := range reserved {
			if err := h.stocks.Save(tx, stock); err != nil {
				return err
			}
		}
		return nil
	})
}
```

記録を処理の前に試しているのは、重複した 2 通目が、1 通目の処理が終わる前に届くこともあるからです。存在を確認してから処理する順序だと、2 つのトランザクションが両方とも「まだ処理していない」を読み、両方が引き当てに進みます。以下は、上のコードで同じイベントの 2 通が重なった場合です。

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#eaf1f5","primaryTextColor":"#28343b","primaryBorderColor":"#9cabb5","lineColor":"#596b76","textColor":"#28343b","actorBkg":"#eaf1f5","actorBorder":"#9cabb5","actorTextColor":"#28343b","actorLineColor":"#9cabb5","signalColor":"#596b76","signalTextColor":"#28343b","noteBkgColor":"#f7f1e5","noteBorderColor":"#c5b99b","noteTextColor":"#403c32","activationBkgColor":"#edf3ef","activationBorderColor":"#9aafa1"}}}%%
sequenceDiagram
    participant H1 as 1 通目の処理
    participant H2 as 2 通目の処理
    participant DB as DB
    H1->>DB: EventID を processed に記録
    H2->>DB: 同じ EventID を記録
    H1->>DB: 在庫を引き当てて commit
    DB-->>H2: 一意制約に弾かれる
    Note over H2,DB: 処理済みとして<br/>何もせずに終える
```

上記の図で引き当てに進むのは 1 通目だけです。一意制約の付いた列への挿入は、同じ値を挿入中で未コミットのトランザクションがあると、その結果が出るまで待たされます。1 通目がコミットすれば 2 通目は弾かれ、巻き戻れば 2 通目が処理を引き継ぎます。

処理済みの記録と在庫の更新を同じトランザクションに入れるのは、途中で落ちた時に両方を一緒に巻き戻すためです。記録だけを先にコミットすると、在庫の更新前に落ちた場合に、引き当てていないのに処理済みの記録が残り、再配送されたイベントは捨てられます。

前提が 2 つあります。1 つは、処理の完了をブローカーに伝えるのがコミットの後であることです。ブローカーは、受信側から完了の通知を受け取るまで同じメッセージを再配送します。コミットの前に伝えると、間で落ちた時にイベントが失われます。もう 1 つは、ハンドラの副作用が全て同じトランザクションに収まることです。外部への通知やメールの送信が混ざると、処理済みの記録では二重実行を防げません。

<br>

保存を明細のループの外に出しているのは、ループの中で保存すると、3 件目で在庫が足りなかった場合に、1 件目と 2 件目の引き当てだけが残ったままコミットされるからです。

`Reserve` の失敗をエラーとして返さないのは、ハンドラがエラーを返すとトランザクションが巻き戻り、処理済みの記録も消えて、同じイベントが再び配送されるからです。在庫不足は再試行しても解消しないので、配送が止まらなくなります。エラーを返すのはデッドロックのように再試行で解消する失敗に限り、在庫不足のような業務上の失敗は別のイベントとして残します。

在庫が足りなくても、注文の確定は既に起きた事実なので取り消せません。注文を取り消す処理を走らせるか、入荷を待って引き当て直すかは、ドメインエキスパートと決めます。

---

### 利点

- 1 つのトランザクションで変更する Aggregate を 1 つに保てるので、競合の範囲が Aggregate の中に収まる
- 競合がユーザーへの応答から切り離され、失敗しても背後で再試行できる
- 発行元は受け取る相手を知らないため、後から処理を追加しても発行元のコードが変わらない
- 「何が起きたか」がコード上の型として残り、業務の語彙とモデルが一致する
- イベントを履歴として永続化する設計にすれば、後から監査や再処理の材料に使える

2 つ目の項目は、競合が消えることを意味しません。人気商品の `Stock` では、引き続き複数の注文による更新が競合します。変わるのは、競合が注文の確定を巻き込まなくなることと、失敗しても背後で引き当て直せることです。

---

### 欠点

イベントで処理を分ける場合は、途中の状態や処理の失敗、配送について、次の対応が必要です。

- 処理が複数のトランザクションに分かれ、途中の状態が外から見える時間ができる
- 失敗した時に元に戻す処理は、業務の言葉で自分で設計する必要がある
- 受信側を冪等にする実装が全てのハンドラに必要
- 発行元のコードを読んでも、そのイベントで何が起きるのかを追えない
- 配送保証のために Transactional Outbox を採用すると、業務と直接関係のない outbox テーブルと relay の運用が増える

---

### 適さないケース

- 1 つの Aggregate の中だけで処理が完結し、外部に伝えるべき出来事も無い更新。イベントを挟む理由がない
- 更新の直後に結果を画面に返す必要があり、数秒の遅れも許容できない業務
- 業務上、複数の Aggregate が必ず同時に成立しなければならない場合。Aggregate の境界の引き方から見直す
- ハンドラが 1 つしかなく、今後も増える見込みが無い連携。関数を直接呼ぶ方が追いやすい

遅れを許容できるかは、ドメインエキスパートに聞いて決めます。Vernon 氏の Effective Aggregate Design Part II も、ドメインエキスパートは開発者より遅延に寛容な場合が多く、数秒から数日の遅れを許すことがあると書いています。

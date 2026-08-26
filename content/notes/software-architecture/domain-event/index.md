---
title: "Domain Event - ドメインで起きた事実を伝える"
date: 2026-08-07
draft: false
series: ["技術ノート", "Software Architecture"]
tags: ["software-architecture", "ddd"]
weight: 4
---

Domain Event とは、ドメインの中で既に起きた出来事を表すオブジェクトです。過去の記録なので通常は不変で、出来事が起きた時刻と、関与したエンティティの識別子を持ちます。ここでは、1 つの [Bounded Context](../bounded-context/) の中で [Aggregate](../value-object-entity-aggregate/) 同士を繋ぐ用途と、Bounded Context をまたいで他のシステムに伝える用途を扱います。

全ての状態変更をイベントの並びとして保存し、状態をその再生で復元する [Event Sourcing](../event-sourcing/) の詳細は対象外とし、違いは末尾で 1 段落だけ触れます。

DDD（Domain-Driven Design、ドメイン駆動設計）での位置付けは、Eric Evans 氏の [DDD Reference](https://www.domainlanguage.com/wp-content/uploads/2016/05/DDD_Reference_2015-03.pdf) に書かれています。同書は Domain Events を「ドメインエキスパートが関心を持つ何かが起きた」と要約し、「ドメインの活動に関する情報を一つ一つ区切られた出来事の連なりとしてモデル化し、それぞれの出来事をドメインオブジェクトとして表現せよ」と書かれています。

連なりというのは、業務上意味のある出来事を 1 件ずつ独立したドメインオブジェクトとして明示する形を指します。同書は続けて、ドメインエキスパートが追跡したい出来事や通知を受けたい出来事、他のモデルオブジェクトの状態変化に結び付く出来事を明示せよと述べており、関係のない活動は無視して良いとしています。現在の状態を捨ててイベントだけを保存せよという指示ではありません。不変である事と、時刻および識別子を持つ事も同じ箇所の記述です。

発行から処理までの経路を以下に示します。

```mermaid
flowchart LR
    subgraph T1["トランザクション 1"]
        A["Order 集約"] -- 記録 --> E["OrderConfirmed"]
        E -- 保存 --> DB[("注文の DB")]
    end
    subgraph T2["トランザクション 2"]
        H["在庫のハンドラ"] --> S["Stock 集約"]
    end
    E -. 配送 .-> H
```

上記の図で 2 つのトランザクションは分かれています。`Order` を確定させる処理は `Stock` の更新を待たずに完了し、在庫の引き当ては後から別のトランザクションで実行されます。点線の配送は、同じプロセスの中でハンドラを呼ぶか、メッセージブローカーを挟むかのどちらかです。トランザクションを分けた事で、注文の確定は在庫の混雑から切り離され、代わりに 2 つの状態がずれている時間が生まれます。

---

### なぜ Domain Event が必要なのか

Aggregate は、内部の不変条件を常に保つ単位です。Vaughn Vernon 氏が 2011 年に発表した [Effective Aggregate Design Part I](https://dddcommunity.org/wp-content/uploads/files/pdf_articles/Vernon_2011_1.pdf) には、「適切に設計された Bounded Context は、あらゆる場合において 1 トランザクションにつき 1 つの Aggregate インスタンスだけを変更する」と書かれています。同じ論文は、この原則が経験則（rule of thumb）で、ほとんどの場合に目指すべき目標だとも添えています。

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

このコードは 1 台の DB（データベース）の上では動きます。問題は、同じ商品を含む注文が同時に届いた時に現れます。`Stock` は商品ごとに 1 つしか無いため、その商品を含む全ての注文が同じ行を奪い合います。

人気商品への注文が 2 件同時に届いた場合は以下の通りです。`Stock` をバージョン列で守る楽観的ロックの実装を想定しています。

```mermaid
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

上記の図の Client 2 は、自分の注文に何の問題も無いのに失敗しています。`Order` と `Stock` を同じトランザクションに入れた事で、注文の確定という業務が在庫の混雑に巻き込まれました。行ロックで待つ実装を選べば失敗はしません。その場合は代わりに、注文の確定が在庫の待ち時間だけ遅くなります。どちらを選んでも、トランザクションが長いほど影響は大きくなり、注文に含まれる商品が増えるほど巻き込まれる相手も増えます。

在庫が別の Bounded Context に移り、DB が分かれた場合はさらに直接的です。1 つのローカルトランザクションで両方を更新する経路が無くなり、上のコードは書けなくなります。複数の DB を 1 つのコミットにまとめる分散トランザクション（[2 相コミット](../../distributed-systems/two-phase-commit/)）を持ち込めば形は保てるものの、参加者の 1 つが停止すると全体が待たされます。

Vernon 氏の [Effective Aggregate Design Part II](https://dddcommunity.org/wp-content/uploads/files/pdf_articles/Vernon_2011_2.pdf) には、この場面での指針が「1 つの Aggregate インスタンスにコマンドを実行した結果、他の 1 つ以上の Aggregate で追加の業務規則を実行する必要があるなら、結果整合性を使え」と書かれています。コマンドは状態を変えてほしいという要求で、`order.Confirm(...)` のように Aggregate のメソッドを呼ぶ形を指します。

同じ論文は Evans 氏の書籍『Domain-Driven Design』から「Aggregate をまたぐ規則は、常に最新である事を期待されない」という一文も引いています。結果整合性とは、いずれ全体が一致するものの、ある瞬間を切り取ると[ずれている状態を許す](../value-object-entity-aggregate/)考え方です。Domain Event は、この結果整合性を実現する手段になります。

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

識別子だけを載せて受信側から問い合わせ直させる作りもあります。載せる情報が減る代わりに、受信側が発行元に問い合わせる経路を持つ事になり、問い合わせた時点では既に値が変わっている場合もあります。上の `Lines` は、確定した時点の内容を写して渡す側の選択です。

過去形の名前は、受け取る相手との関係を決めています。「注文を確定せよ」という命令は特定の処理が実行される事を期待していて、その成否は発行元にとって意味を持ちます。「注文が確定した」という事実は起きた事を伝えるだけで、発行元は誰がどう処理したかを知りません。注意点として、事実を取り消せない事と、受信側が処理を失敗させられない事は別です。受信側の処理は普通に失敗します。

時刻の扱いにも注意が必要です。Martin Fowler 氏の [Domain Event](https://martinfowler.com/eaaDev/DomainEvent.html) には、「出来事が世界で起きた時刻」と「その出来事に気付いた時刻」の 2 つを区別すべきだと書かれています。どちらを保持しているのかがフィールド名で分かるようにします。

---

### 誰がイベントを作るか

イベントを Aggregate に作らせると扱いやすくなります。状態が変わった事を最もよく知っているのは、その状態を持っている Aggregate だからです。呼び出し側で作ると、状態の変更とイベントの発行が別々の場所に散らばり、片方だけを直した時にずれます。Aggregate の状態変更に対応しないイベントは、呼び出し側で作る事になります。

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

記録と発行を分けている点が効いています。`Confirm` の時点ではイベントを外に出さず、Aggregate の中に溜めるだけです。溜めたイベントを取り出すのは Repository の `Save` だけなので、途中で処理を中断すれば、イベントは外に出ないまま終わります。この順序によって、起きていない事実を配ってしまう事故を防げます。

Vernon 氏の論文は、`Confirm` と同じ役割のメソッドの中から発行の窓口を直接呼ぶ書き方を示しています。その形で同じ `Confirm` を書くと以下になります。

```go
// publisher はパッケージレベルの変数です。
var publisher eventPublisher

// Confirm は注文を確定し、確定したという事実をその場で発行します。
func (o *Order) Confirm(now time.Time) error {
	if o.status != OrderStatusDraft {
		return errAlreadyConfirmed
	}
	o.status = OrderStatusConfirmed
	publisher.Publish(OrderConfirmed{
		EventID:    newEventID(),
		OccurredAt: now,
		OrderID:    o.id,
		Lines:      slices.Clone(o.lines),
	})
	return nil
}
```

違いは `o.events` への追記が `publisher.Publish` に変わった 1 行だけです。発行の窓口をパッケージレベルの変数に置いているのは、Vernon 氏の論文が `DomainEventPublisher.instance()` というシングルトン経由で呼んでいるからです。

`Order` に窓口を持たせず、引数でも渡さない形にすると、`Confirm` の呼び出し側はイベントが出る事を知らずに済みます。その代わり、`Order` の依存がシグネチャに現れず、テストで差し替える経路も外から見えなくなります。

この形では `Publish` を呼んだ時点でイベントが外に出るため、この後の保存が失敗しても、配ってしまった事実は取り消せません。溜めてから取り出す形にすると、外に出る場所が `Save` の 1 箇所に限られるので、コミットするまで出ない事がコードの構造で保証されます。その代わり `PullEvents` が Aggregate の中を空にするので、トランザクションを再試行する構成では、Aggregate を取得し直す必要があります。

---

### 発行と配送

溜めたイベントを取り出すのは [Repository](../repository/) の保存処理です。配送のさせ方には段階があり、必要な分だけ選びます。最小の構成は、コミットが成功した後に同じプロセスの中でハンドラを呼ぶ形です。後続処理が消えても業務が成立するなら、これで足ります。弱点は、コミットの直後にプロセスが落ちるとイベントが消える点にあります。逆に、コミットの前にハンドラを呼ぶと、保存に失敗した時に起きていない事実が配られます。この 2 つは、DB とメッセージの 2 箇所に別々に書く限り避けられません。

どこまでの保証が必要かは、Bounded Context の境界ではなく、後続処理が消えた時に業務が困るかで決まります。同じ Bounded Context の中でも、決済の後に必ず走らせたい処理があるなら、この最小の構成では足りません。逆に境界をまたいでいても、通知が 1 通落ちても業務が回るなら、これで済みます。

[Transactional Outbox](https://microservices.io/patterns/data/transactional-outbox.html) は、書き込み先を DB の 1 箇所に寄せて解きます。メッセージを外部に送る代わりに、業務データを更新するのと同じトランザクションの中で outbox テーブルに書き込みます。outbox は送信箱で、宛先の決まった手紙を投函するまで置いておく場所です。

溜まった行を別プロセスの relay が読み、メッセージブローカーに転送します。DB の更新とイベントの配送のどちらか片方だけが成立する状態を避けたい場合の、代表的な選択肢になります。DB の変更ログを読んで外部に流す CDC（Change Data Capture、変更データキャプチャ）のように、outbox テーブルを置かない解き方もあります。

outbox テーブルに入るのは、以下のような行です。

| id | event_id | name | payload | occurred_at | sent_at |
|---|---|---|---|---|---|
| 1 | e1 | order.confirmed | `{"order_id":"o-1", ...}` | 2026-08-07T10:00:00Z | 2026-08-07T10:00:03Z |
| 2 | e2 | order.confirmed | `{"order_id":"o-2", ...}` | 2026-08-07T10:00:01Z | NULL |

`sent_at` が `NULL` の行が未送信です。relay はその行だけを古い順に拾って送り、送れたら時刻を書き込みます。`payload` にイベントの中身を JSON で入れているのは、送り先に Go の型が無いからです。送信済みの行をいつまで残すかは、別に決める話になります。outbox は配送を取りこぼさないための送信箱で、イベントの履歴として設計されたものではありません。

以下が構成です。

```mermaid
flowchart LR
    subgraph TX["1 つのトランザクション"]
        O["orders テーブル"]
        B["outbox テーブル"]
    end
    U["orderRepository.Save"] --> O
    U --> B
    R["message relay"] -- 未送信を読む --> B
    R -- 転送 --> Q["メッセージブローカー"]
    Q --> H["在庫のハンドラ"]
```

上記の図の relay は、業務の処理とは別のプロセスです。注文の処理は outbox に書いた時点で完了しており、ブローカーが停止していても注文は受け付けられます。1 つのトランザクションに収まるのは、業務データの更新と送信の予約までです。更新したのに送られない状態と、送ったのに更新されていない状態は、これで消えます。実際に届くタイミングと回数は、relay とブローカーの都合で決まります。

コードでは、Repository が Aggregate の状態と溜まったイベントを同じトランザクションで書きます。

```go
// Save は、Order の状態と発行するイベントを同じトランザクションで書きます。
func (r *orderRepository) Save(tx Tx, o *Order) error {
	if err := r.upsert(tx, o); err != nil {
		return err
	}
	for _, ev := range o.PullEvents() {
		if err := r.outbox.Append(tx, ev); err != nil {
			return err
		}
	}
	return nil
}
```

relay 側は、未送信の行を拾って送り、送信済みにする処理の繰り返しです。

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

1 周で読む件数を区切っているのは、outbox が溜まった時に 1 回の処理が長くなり過ぎないようにするからです。途中で失敗しても、そこまでに `MarkSent` を終えた行は送信済みとして残るので、次の周回は失敗した行から再開します。`Publish` と `MarkSent` の間で停止した場合だけ、同じ行がもう一度送られます。

---

### 受信側は冪等にする

冪等とは、同じ処理を何回実行しても、1 回実行した時と同じ結果になる性質です。relay は、ブローカーに送った後、送信済みの記録を書く前に落ちる場合があります。再開した relay は同じ行をもう一度送るので、受信側には同じイベントが 2 回届きます。少なくとも 1 回は届く代わりに、2 回以上届く事もある配送（at-least-once 配送）になります。

同じイベントが 2 回届く経路は以下の通りです。

```mermaid
sequenceDiagram
    participant R as message relay
    participant Q as ブローカー
    participant H as 在庫のハンドラ
    R->>Q: OrderConfirmed（EventID: e1）
    Q->>H: 配送
    H->>H: 在庫を引き当てる
    Note over R: 送信済みを記録する前に停止
    R->>Q: OrderConfirmed（EventID: e1）
    Q->>H: 再び配送
    H->>H: e1 は処理済みなので何もしない
```

上記の図のハンドラは、2 回目の配送で在庫を二重に減らしていません。イベントに付けた `EventID` を処理済みとして記録しておき、同じ値が来たら何もせずに終えます。

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
				// 在庫不足は再試行しても解消しないため、1 件も保存せずに
				// 引き当ての失敗を別のイベントとして残してコミットする
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

処理済みの記録と在庫の更新を同じトランザクションに入れている点が要です。別のトランザクションに分けると、在庫を更新した直後に落ちた場合に対処できません。再開したハンドラは処理済みの記録を見付けられず、同じ引き当てをもう一度実行します。

記録を処理の前に試している理由は、同じイベントが同時に 2 通届く場合にあります。存在を確認してから処理する順序だと、2 つのトランザクションが両方とも「まだ処理していない」を読み、両方が引き当てに進みます。先に記録を試みれば、後から来た方が一意制約に弾かれます。冪等性を支えているのは同一トランザクションではなく、この一意制約です。同一トランザクションは、失敗した時に在庫の更新も一緒に巻き戻す役目を持ちます。

前提が 2 つあります。1 つは、処理の完了をブローカーに伝えるのがコミットの後である事です。コミットの前に伝えると、間で落ちた時にイベントが失われます。もう 1 つは、ハンドラの副作用が全て同じトランザクションに収まる事です。外部への通知やメールの送信が混ざると、処理済みの記録では二重実行を防げません。

保存を明細のループの外に出しているのは、途中で失敗した時に引き当てを 1 件も残さないからです。ループの中で保存すると、3 件目で在庫が足りなかった場合に、1 件目と 2 件目の引き当てだけが残ったままコミットされます。注文の一部だけが確保された状態は、業務としてどちらとも決められません。全て引き当てるか、1 件も引き当てないかのどちらかに寄せます。

`Reserve` の失敗をエラーとして返していない点にも理由があります。ハンドラがエラーを返すとトランザクションが巻き戻り、処理済みの記録も消えて、同じイベントが再び配送されます。在庫不足は再試行しても解消しないため、エラーを返すと同じイベントが配送され続けます。エラーを返すのは、デッドロックのように再試行で解消する失敗に限ります。在庫不足のような業務上の失敗は、別のイベントとして残す扱いが必要です。

引き当ての失敗を受けて何をするかは、業務として決めます。在庫が足りなくても、注文の確定は既に起きた事実なので取り消せません。注文を取り消す処理を走らせるか、入荷を待って引き当て直すか、ドメインエキスパートと決める事になります。

---

### 利点

- Aggregate を 1 トランザクション 1 つに保てるので、競合の範囲が Aggregate の中に収まる
- 競合がユーザーへの応答から切り離され、失敗しても背後で再試行できる
- 発行元は受け取る相手を知らないため、後から処理を追加しても発行元のコードが変わらない
- 「何が起きたか」がコード上の型として残り、業務の語彙とモデルが一致する
- イベントを履歴として永続化する設計にすれば、後から監査や再処理の材料に使える

2 つ目の項目は、競合そのものが消える事を意味しません。人気商品の `Stock` は変わらず全ての注文から奪い合われ、その商品に対する更新の処理量も変わりません。変わるのは、競合が注文の確定を巻き込まなくなる事と、失敗しても背後で引き当て直せる事です。同じ商品への更新そのものを分散させたいなら、在庫を複数の枠に割る設計が別に必要です。

---

### 欠点

以下は、Aggregate の境界を守る事と、発行元と受信側の結合を切る事を優先した結果として現れる制約です。

- 処理が複数のトランザクションに分かれ、途中の状態が外から見える時間ができる
- 失敗した時に元に戻す処理は、業務の言葉で自分で設計する事になる
- 受信側を冪等にする実装が全てのハンドラに必要
- 発行元のコードを読んでも、そのイベントで何が起きるのかを追えない
- 配送保証のために Transactional Outbox を採用すると、業務と直接関係のない outbox テーブルと relay の運用が増える

---

### 適さないケース

- 1 つの Aggregate の中だけで処理が完結し、外部に伝えるべき出来事も無い更新。イベントを挟む理由がない
- 更新の直後に結果を画面に返す必要があり、数秒の遅れも許容できない業務
- 業務上、複数の Aggregate が必ず同時に成立しなければならない場合。Aggregate の境界の引き方から見直す
- ハンドラが 1 つしかなく、今後も増える見込みが無い連携。関数を直接呼ぶ方が追いやすい

最後の判断は、遅延を許容できるかをドメインエキスパートに聞いて決めます。Vernon 氏の Effective Aggregate Design Part II も、ドメインエキスパートは開発者より遅延に寛容な場合が多く、数秒から数日の遅れを許す事があると書いています。

---

### 似た概念との比較

発行の目的と届く範囲で、イベントと名の付くものを並べます。

| | Domain Event | Integration Event | コマンド |
|---|---|---|---|
| 表すもの | ドメインで起きた事実 | 他システムに公開する事実 | これから行う要求 |
| 主に使う範囲 | 同じ Bounded Context の中 | Bounded Context の外 | 特定の受け手 1 つ |
| 発行側が期待するもの | 事実が伝わる事 | 事実が伝わる事 | 特定の処理が実行される事 |
| 発行側にとっての処理結果 | 成否に依存しない | 成否に依存しない | 成否が意味を持つ |
| 取り消せるか | 事実は取り消せない | 事実は取り消せない | 受け手が拒否できる |
| 残す期間 | 業務要件で決める。監査に使うなら長期 | 同左 | 処理が終わるまで |
| 名前の形 | 過去形 | 過去形 | 命令形 |

同期で配るか非同期で配るかは、この 3 つを分ける軸ではありません。Domain Event を同じプロセスの中で同期に配れば、呼び出し側はハンドラの終了まで待ちます。コマンドをキューに入れれば、呼び出し側は待たずに戻ります。待つかどうかは配送の実装で決まり、発行側が事実を伝えたいのか処理を実行させたいのかとは別の話です。

Integration Event は、外部に公開する事を前提に形を決めた Domain Event だと考えられます。内部のモデルをそのまま外に出すと、受け手が内部の変更に引きずられます。Bounded Context の境界を越える時は、公開用の形に変換してから送ります。

なお、Domain Event を同じ Bounded Context の中で使うという線引きは、後から広まった運用上の指針です。Evans 氏の DDD Reference は、Domain Event をノードをまたいで伝わるものとして説明しており、範囲を Bounded Context の中に限っていません。

[Event Sourcing](../event-sourcing/) は、この表の 3 つとは軸が違います。メッセージの種類ではなく、状態そのものを Domain Event の並びとして永続化し、再生で復元する方式です。保存されるのは Domain Event なので、どちらかを選ぶ関係にはありません。Domain Event を使う事は、Event Sourcing を採用する事を意味しません。

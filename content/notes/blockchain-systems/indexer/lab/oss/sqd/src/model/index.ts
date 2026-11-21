import {Entity, PrimaryColumn, Column} from '@subsquid/typeorm-store'

// アドレスごとの残高。id はアドレス（小文字）。
@Entity()
export class Balance {
    constructor(props?: Partial<Balance>) {
        Object.assign(this, props)
    }

    @PrimaryColumn()
    id!: string

    @Column('numeric', {transformer: {to: (v: bigint) => v.toString(), from: (v: string) => BigInt(v)}})
    amount!: bigint
}

module.exports = class Init1700000000000 {
    name = 'Init1700000000000'
    async up(db) {
        await db.query(`CREATE TABLE "balance" ("id" character varying NOT NULL, "amount" numeric NOT NULL, CONSTRAINT "PK_balance" PRIMARY KEY ("id"))`)
    }
    async down(db) {
        await db.query(`DROP TABLE "balance"`)
    }
}
